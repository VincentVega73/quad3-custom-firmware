"""Offline Thumb execution checks; hardware-facing callees are explicit stubs.

These tests verify dispatch/control-flow and selected state writes only.
They do not emulate the amplifier, analog behavior, updater or recovery.
"""
from pathlib import Path
import argparse
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from firmware_patch import build, BASE, ORIGINAL_SIZE, EXPECTED, HOOK, PAYLOAD
from emulate_startup import initialize
from test_support import protect_inputs, runtime_versions
import hashlib
import json
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB, KS_MODE_LITTLE_ENDIAN
import struct, itertools, time
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import *

RAMBASE=0x20000000
STOP=0x0801fff0
ENTRY=0x080132e8
RANGES=[(0x080132e8,0x08013a1c),(0x0801a008,0x0801aae4),
        (0x080145cc,0x08014662),(0x08014d30,0x08014d8e),
        (0x080130f6,0x08013118),(0x080131f8,0x08013296),
        (0x08012f64,0x08012f76),(0x08016ef0,0x08016f4c),
        (0x0801c588,0x0801c7c6),
        (BASE+ORIGINAL_SIZE,BASE+ORIGINAL_SIZE+len(PAYLOAD)-4)]
# Exact external call targets found in the reviewed stock ranges.
# Every one is an explicit zero-return ABI stub; unknown targets fail.
STUB_TARGETS = {0x08010A40, 0x08010BD8, 0x08010CA8, 0x08010D54,
                0x08012210, 0x080123EC, 0x08012594, 0x0801270C,
                0x08012DAA, 0x08014D24, 0x08015152, 0x080157CE,
                0x08015CA0, 0x0801672C, 0x08016E82, 0x08018242,
                0x08019E18, 0x08019F0E}
REGS=[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,
      UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_SP]
MD=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_LITTLE_ENDIAN)
MD.detail=True

class Runner:
    all_stubs = {}
    def __init__(self,image,initial):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.u.mem_map(BASE,0x10000)
        self.u.mem_write(BASE,image)
        self.u.mem_map(RAMBASE,0x10000)
        self.u.mem_map(0x40000000,0x1000)
        self.initial=initial
        self.calls=[]
        self.cache={}
        self.u.hook_add(UC_HOOK_CODE,self.hook)
    def hook(self,u,address,size,_):
        if BASE+ORIGINAL_SIZE <= address < BASE+ORIGINAL_SIZE+len(PAYLOAD)-4:
            assert u.reg_read(UC_ARM_REG_SP)%8==0, 'RC2 handler SP alignment'
        if not any(lo<=address<hi for lo,hi in RANGES):
            raise AssertionError(f'Unapproved execution at {address:08x}')
        ins=self.cache.get(address)
        if ins is None:
            ins=next(MD.disasm(bytes(u.mem_read(address,size)),address))
            self.cache[address]=ins
        if ins.mnemonic=='bl':
            target=ins.operands[0].imm
            if not any(lo<=target<hi for lo,hi in RANGES):
                assert target in STUB_TARGETS, f'Unlisted external call {target:08x}'
                self.all_stubs.setdefault(target, set()).add(address)
                self.calls.append((target,u.reg_read(UC_ARM_REG_R0)))
                # Stub external calls at their callsite, never perform device I/O.
                for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]:
                    u.reg_write(reg,0)
                u.reg_write(UC_ARM_REG_PC,(address+size)|1)
    def reset(self,changes=None):
        self.u.mem_write(RAMBASE,self.initial)
        if changes:
            for offset,data in changes.items(): self.u.mem_write(RAMBASE+offset,data)
        for i,reg in enumerate(REGS[:-1]): self.u.reg_write(reg,0x44440000+i)
        self.calls=[]
    def invoke(self,entry=ENTRY):
        self.u.reg_write(UC_ARM_REG_SP,0x20001fb8)
        self.u.reg_write(UC_ARM_REG_LR,STOP|1)
        self.u.emu_start(entry|1,STOP,count=20000)
        assert self.u.reg_read(UC_ARM_REG_PC)==STOP
        return bytes(self.u.mem_read(RAMBASE,0x1000)),tuple(self.calls),tuple(self.u.reg_read(r) for r in REGS)
    def state(self,event,power,source,page,extras=None):
        changes={0xeae:struct.pack('<H',event),0xed1:bytes([power]),0xed3:bytes([source]),0xf29:bytes([page])}
        if extras: changes.update(extras)
        self.reset(changes)
        return self.invoke()
    def decode(self,address,raw_command,inverse=None,reset_memory=True):
        if reset_memory:
            self.reset()
        frame=(address<<16)|(raw_command<<8)|((raw_command^255) if inverse is None else inverse)
        for duration in [13500]+[2250 if frame&(1<<bit) else 1125 for bit in range(31,-1,-1)]:
            self.u.mem_write(0x40000024,struct.pack('<H',duration))
            self.invoke(0x0801c5a2)
        self.invoke(0x0801c6c2)
        initial_event=struct.unpack('<H',self.u.mem_read(RAMBASE+0xeae,2))[0]
        self.u.mem_write(RAMBASE+0xf4a,b'\0')
        self.invoke(0x0801c6c2)
        released_event=struct.unpack('<H',self.u.mem_read(RAMBASE+0xeae,2))[0]
        return initial_event,released_event

def main():
    if not __debug__:
        raise SystemExit('Run without python -O: verification assertions must stay enabled.')
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original',type=Path,required=True)
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=ROOT/'generated'/'dispatcher_verification_rc2.json')
    args=ap.parse_args()
    protect_inputs(args.output,args.original,args.candidate)
    start=time.time()
    original=args.original.read_bytes()
    patched,payload,hook_bytes=build(original)
    assert patched == args.candidate.read_bytes(), 'Candidate differs from rebuilt RC2 bytes'
    assembly='\n'.join(line.split(';',1)[0] for line in (ROOT/'handler'/'handler_sk2.asm').read_text().splitlines())
    ks=Ks(KS_ARCH_ARM,KS_MODE_THUMB|KS_MODE_LITTLE_ENDIAN)
    assert bytes(ks.asm(assembly,BASE+len(original))[0])==payload
    assert bytes(ks.asm(f'b.w #{BASE+len(original)}',BASE+HOOK)[0])==hook_bytes
    # Decode the complete injected code (the final word is a literal), and
    # require every direct target to be an original or injected boundary.
    code=list(MD.disasm(patched[len(original):-4],BASE+len(original)))
    boundaries={i.address for i in code}
    for lo,hi in [(0x080132e8,0x080138dc),(0x080131f8,0x08013296)]:
        boundaries.update(i.address for i in MD.disasm(original[lo-BASE:hi-BASE],lo))
    branches=[]
    for i in code:
        if i.mnemonic.startswith('b'):
            target=i.operands[0].imm
            assert target in boundaries,(hex(i.address),hex(target),'bad direct target')
            branches.append({'from':hex(i.address),'target':hex(target)})
    hook=next(MD.disasm(patched[HOOK:HOOK+4],BASE+HOOK))
    assert hook.mnemonic=='b.w' and hook.operands[0].imm==BASE+len(original)
    assert patched[:0x120]==original[:0x120]
    # Exhaustively compare the two instruction trampoline against the original
    # for all 16-bit events except the eight intentionally handled events.
    machines=[]
    for image in [original,patched]:
        u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        u.mem_map(BASE,0x10000);u.mem_write(BASE,image)
        u.mem_map(RAMBASE,0x10000)
        machines.append(u)
    fallback_count=0
    fallback_regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
                   UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_SP,UC_ARM_REG_APSR]
    for event in range(0x10000):
        if 0x5017 <= event <= 0x501E: continue
        results=[]
        for u in machines:
            u.mem_write(RAMBASE+0xeae,struct.pack('<H',event))
            u.reg_write(UC_ARM_REG_R4,RAMBASE+0xeae)
            u.reg_write(UC_ARM_REG_R1,0x13579bdf)
            u.reg_write(UC_ARM_REG_SP,0x20001fb8)
            u.emu_start((BASE+HOOK)|1,0x0801334a,count=100)
            assert u.reg_read(UC_ARM_REG_PC)==0x0801334a
            results.append(tuple(u.reg_read(r) for r in fallback_regs))
        assert results[0]==results[1],(event,'trampoline changes registers or flags')
        fallback_count+=1
    initial=initialize(original)[0]
    a,b=Runner(original,initial),Runner(patched,initial)
    events=sorted(set(original[0xcb69:0xcbb0:2]))
    forms=[0,0x1000,0x2000,0x3000,0x4000,0x5000,0x6000,0x7000]
    targets={0x5017:1,0x5018:5,0x5019:6,0x501A:7,
             0x501B:3,0x501C:2,0x501D:4,0x501E:0}
    baseline=changed=blocked=0
    # Representative dispatcher contexts: all source IDs; known power modes;
    # normal, settings, tone, protected page and service-like screen state.
    for power,source,page,event in itertools.product(list(range(7)),range(8),[0,4,0x11,0x12,0x14,0x15,0x1e], [e+f for e in events for f in forms]):
        aa=a.state(event,power,source,page)
        bb=b.state(event,power,source,page)
        expected=event in targets and power==1 and page!=0x12
        if not expected:
            assert aa==bb,(power,source,page,event,'non-target differs')
            baseline+=1
            blocked+=event in targets
        else:
            ram,calls,regs=bb
            assert ram[0xed3]==targets[event]
            assert ram[0xeea]==1 and ram[0xeeb]==0
            assert ram[0xfa7]==3 and ram[0xf29]==4 and ram[0xf24]==1
            assert ram[0xeae:0xeb0]==b'\0\0'
            assert regs==aa[2],'Callee-saved registers or SP changed'
            # Compare native Source-next path from the same previous source,
            # except override current source before native command so target matches.
            # Exact side effect equivalence is tested separately below.
            changed+=1
    # Test all 32 page values and all sources for candidates, with variations in
    # cleanup/display flags and pre-existing source-transition state.
    extended=0
    for page,source,event,profile in itertools.product(range(32),range(8),targets,range(4)):
        extras={0xf6a:bytes([profile&1]),0xeee:bytes([(profile>>1)&1]),0xfa6:bytes([profile&1]),
                0xeea:bytes([profile]),0xeeb:b'\x37',0xf28:bytes([profile&1]),0xf30:bytes([profile&1]),
                0xfa1:bytes([profile&1]),0xf97:b'\x03'}
        aa=a.state(event,1,source,page,extras)
        bb=b.state(event,1,source,page,extras)
        if page==0x12: assert aa==bb
        else:
            assert bb[0][0xed3]==targets[event]
            assert bb[0][0xeea:0xeec]==b'\x01\x00'
            assert bb[2]==aa[2]
        extended+=1
    # Prove side effects equal native Source-next when both choose the same ID.
    native_equiv=0
    for event,target in targets.items():
        for page in range(32):
            if page==0x12: continue
            aa=a.state(0x500b,1,(target-1)%8,page)
            bb=b.state(event,1,(target-1)%8,page)
            assert aa==bb,(event,page,'native source transition differs')
            native_equiv+=1
    # Decode all mapped commands for both accepted raw addresses; alternate
    # address is restricted to power/mute by the event generator.
    decoder=0
    for offset in range(0xcb68,0xcbb0,2):
        raw,event=original[offset:offset+2]
        assert a.decode(0x4c77,raw)==(event,0x5000+event)
        expected=(event,0x5000+event) if event in (7,8) else (0,0)
        assert a.decode(0xccbf,raw)==expected
        decoder+=2
    assert a.decode(0x4c77,0xcc,inverse=0)==(23,0x5017),'inverse byte behavior changed'
    # Owner-captured conventional NEC frames, fed through the real decoder.
    # The firmware's left-shift accumulator bit-reverses each NEC wire byte.
    captured_commands=(0x33,0x23,0x24,0x25,0x26,0x27,0x28,0x29)
    captured_inverses=(0xCC,0xDC,0xDB,0xDA,0xD9,0xD8,0xD7,0xD6)
    reverse=lambda value:int(f'{value:08b}'[::-1],2)
    captured=[]
    bank_sequence_cases=0
    for button,(command,inverse),(event,source) in zip(range(8),zip(captured_commands,captured_inverses),targets.items()):
        assert command ^ inverse == 0xFF
        raw=reverse(command)
        assert b.decode(0x4C77,raw,reverse(inverse)) == (event-0x5000,event)
        # Decode() returns after short release with the event in the mailbox.
        # Set only the normal power/UI guards before running the dispatcher.
        b.u.mem_write(RAMBASE+0xED1,b'\x01')
        b.u.mem_write(RAMBASE+0xF29,b'\x00')
        decoded_result=b.invoke()
        assert decoded_result[0][0xED3] == source
        assert decoded_result[0][0xEEA:0xEEC] == b'\x01\x00'
        # Preserve decoder RAM after consuming the AMP event. Model an unrelated
        # pending selection to expose replay of any previous numeric command.
        b.u.mem_write(RAMBASE+0xED3,bytes([(source+1)%8]))
        b.u.mem_write(RAMBASE+0xEEA,b'\x03\x07')
        for cd_command,cd_inverse in zip(captured_commands,captured_inverses):
            assert b.decode(0xCCBF,reverse(cd_command),reverse(cd_inverse),False) == (0,0)
            after_cd=b.invoke()[0]
            assert after_cd[0xED3] == (source+1)%8, 'CD numeric frame changed requested source'
            assert after_cd[0xEEA:0xEEC] == b'\x03\x07', 'CD numeric frame restarted worker'
            bank_sequence_cases+=1
        assert b.decode(0xCCBF,raw,reverse(inverse)) == (0,0)
        assert b.decode(0x4C77,raw,0) == (event-0x5000,event)
        captured.append({'button':button,'nec_frame':f'32 EE {command:02X} {inverse:02X}',
                         'decoder_command':hex(raw),'event':hex(event),'source_id':source,
                         'amp_bank_pass':True,'cd_bank_filtered':True,'inverse_not_enforced':True})

    # Initial RAM reconstructed by original and patched initializer is identical.
    assert initialize(original)[0]==initialize(patched)[0]
    result={'status':'PASS','baseline_equivalence_cases':baseline,'new_command_cases':changed,
            'payload_matches_assembler':True,'delivery_matches_rebuild':True,'all_16bit_non_target_trampoline_cases':fallback_count,'direct_branches_checked':branches,
            'gated_candidate_cases':blocked,'extended_candidate_cases':extended,
            'native_source_side_effect_equivalence_cases':native_equiv,'decoder_cases':decoder,
            'checksum_validation':'NOT POSSIBLE: bootloader/integrity contract unknown',
            'hardware_validation':'NOT PERFORMED by this test; enumerated external callees are ABI stubs',
            'captured_frame_to_source_cases':captured,
            'amp_then_cd_without_ram_reset_cases':bank_sequence_cases,
            'stub_policy':'Only STUB_TARGETS may be stubbed; r0-r3 set to zero; unknown targets fail.',
            'stubbed_calls':[{'target':hex(t),'callsites':[hex(p) for p in sorted(s)]}
                             for t,s in sorted(Runner.all_stubs.items())],
            'startup_ram_rebuilt_in_memory':True,
            'runtime_versions':runtime_versions(),
            'limits':'Finite enumerated states; no proof for all RAM states, interleaved interrupts, analog timing, updater or recovery.',
            'runtime_seconds':round(time.time()-start,2),
            'original_sha256':EXPECTED,'patched_sha256':hashlib.sha256(patched).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in (
        'status','patched_sha256','baseline_equivalence_cases','new_command_cases',
        'all_16bit_non_target_trampoline_cases','gated_candidate_cases',
        'extended_candidate_cases','native_source_side_effect_equivalence_cases',
        'decoder_cases','runtime_seconds')},indent=2))

if __name__=='__main__': main()
