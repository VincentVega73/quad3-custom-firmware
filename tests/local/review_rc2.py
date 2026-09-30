"""Independent binary/ABI audit. Reads finished RC2; does not import its builder.

Install requirements-emulation.txt; read only user-supplied input images.
All peripheral-facing calls in the dispatcher experiment are explicit stubs.
No USB device, physical target or external process is accessed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
from test_support import protect_inputs, runtime_versions
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import *

BASE = 0x08010000
RAM = 0x20000000
HOOK = 0x3346
EOF = 0xD8F8
EXPECTED_ORIGINAL = '7dff59e986643543c28c7f71c1f43f78c936867b25b078e0c1bd0ea5a6fe3853'
EXPECTED_RC2 = '08555b7437781bcef803f6469eb56428aa1dc30716a262938f7b211a0e863146'
TARGETS = {0x5017: 1, 0x5018: 5, 0x5019: 6, 0x501A: 7,
           0x501B: 3, 0x501C: 2, 0x501D: 4, 0x501E: 0}
MD = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
MD.detail = True
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
        UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def machine(image):
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    u.mem_map(BASE, 0x10000)
    u.mem_write(BASE, image)
    u.mem_map(RAM, 0x10000)
    return u


def init_registers(u, sp=0x20001FA8):
    for n, reg in enumerate(REGS):
        u.reg_write(reg, 0x12340000 + n * 0x101)
    u.reg_write(UC_ARM_REG_R4, RAM + 0xEAE)
    u.reg_write(UC_ARM_REG_SP, sp)
    u.reg_write(UC_ARM_REG_LR, 0x0801FFF1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=ROOT / 'generated' / 'independent_review_rc2.json')
    args = parser.parse_args()
    protect_inputs(args.report, args.original, args.candidate)
    original = args.original.read_bytes()
    rc2 = args.candidate.read_bytes()
    require(len(original) == EOF and sha(original) == EXPECTED_ORIGINAL, 'Unexpected original')
    require(len(rc2) == EOF + 124 and sha(rc2) == EXPECTED_RC2, 'Unexpected candidate')
    diff = [i for i, (a, b) in enumerate(zip(original, rc2)) if a != b]
    require(diff == list(range(HOOK, HOOK + 4)), 'Unexpected original-region mutation')
    require(original[HOOK:HOOK+4] == bytes.fromhex('2088c01f'), 'Wrong hook input')
    hook = list(MD.disasm(rc2[HOOK:HOOK+4], BASE+HOOK))
    require(len(hook) == 1 and hook[0].mnemonic == 'b.w', 'Wrong hook instruction')
    require(hook[0].operands[0].imm == BASE+EOF, 'Wrong hook target')
    code = list(MD.disasm(rc2[EOF:EOF+120], BASE+EOF))
    require(sum(i.size for i in code) == 120, 'Invalid/incomplete Thumb code')
    require(all(i.address % 2 == 0 for i in code), 'Unaligned instruction')
    require(rc2[-4:] == struct.pack('<I', RAM+0xED3), 'Wrong source literal')
    by_address = {i.address: i for i in code}
    literal_loads = [i for i in code if i.mnemonic == 'ldr' and 'pc' in i.op_str]
    require(len(literal_loads) == 1, 'Unexpected literal loads')
    literal_load = literal_loads[0]
    literal_target = ((literal_load.address + 4) & ~3) + literal_load.operands[1].mem.disp
    require(literal_target == BASE + EOF + 120, 'Literal load misses the aligned source address')
    external = {0x080131F8, 0x0801334A, 0x080134D4}
    branches = []
    for ins in [hook[0], *code]:
        if ins.mnemonic in ('b.w', 'bl', 'b', 'beq'):
            target = ins.operands[0].imm
            require(target in by_address or target in external, 'Unknown/nonboundary target')
            displacement = target - (ins.address+4)
            bounds = (-0x1000000, 0xFFFFFE) if ins.size == 4 else ((-0x100, 0xFE) if ins.mnemonic == 'beq' else (-0x800, 0x7FE))
            require(bounds[0] <= displacement <= bounds[1] and displacement % 2 == 0, 'Branch outside encoding range')
            branches.append({'from': hex(ins.address), 'instruction': ins.mnemonic,
                             'target': hex(target), 'pc_relative_displacement': displacement})
    require(by_address[BASE+EOF+2].mnemonic == 'push' and by_address[BASE+EOF+2].op_str == '{r1, r2}', 'Expected aligned scratch save')
    pops = [i for i in code if i.mnemonic == 'pop']
    require(len(pops) == 2 and all(i.op_str == '{r1, r2}' for i in pops), 'Expected both balanced restores')
    require(original[0x32E8:0x32EA] == bytes.fromhex('38b5'), 'Dispatcher frame differs')
    require(original[0x38DA:0x38DC] == bytes.fromhex('31bd'), 'Dispatcher epilogue differs')
    # Entire unchanged partitions are stronger than inferred subsystem extents.
    partitions = []
    for lo, hi in [(0, HOOK), (HOOK+4, EOF)]:
        require(original[lo:hi] == rc2[lo:hi], 'Unchanged partition differs')
        partitions.append({'offset_start': hex(lo), 'offset_end_exclusive': hex(hi),
                           'bytes': hi-lo, 'sha256': sha(rc2[lo:hi])})
    anchors = {
        'vector_table': (0, 0x120),
        'USB_control_reviewed_region': (0x4730, 0x4B7E),
        'HDMI_CEC_reviewed_dispatcher_and_worker_region': (0x82CC, 0x8E12),
        'audio_routing_reviewed_region': (0x1FB4, 0x2164),
        'digital_audio_DAC_DSP_coordination_reviewed_region': (0x5D92, 0x5EB0),
        'protection_reviewed_region': (0x3A40, 0x3B70),
        'power_reviewed_region': (0x0850, 0x0BE0),
        'Bluetooth_reviewed_region': (0x3C38, 0x4578),
        'NVRAM_pack_restore_save_code': (0x54F0, 0x59A0),
        'NVRAM_page_literals': (0xB1A4, 0xB1AC),
        'factory_source_default': (0x9A94, 0x9A9C),
        'front_panel_source_reviewed_region': (0x10F4, 0x136C),
        'source_worker_request': (0x2E64, 0x2F76),
        'IR_decoder_and_event_generator': (0xC5A2, 0xC7C6),
        'IR_command_table': (0xCB68, 0xCBB0),
        'version_string': (0xCEA0, 0xCEB0),
        'runtime_compressed_tail': (0xD6FC, EOF),
    }
    preserved = {}
    for label, (lo, hi) in anchors.items():
        require(original[lo:hi] == rc2[lo:hi], label + ' differs')
        preserved[label] = {'offset_start': hex(lo), 'offset_end_exclusive': hex(hi),
                            'unchanged': True, 'sha256': sha(rc2[lo:hi])}
    # Independent differential fallback with flag variants and boundary events.
    fallback_cases = 0
    for event in [0, 1, 6, 7, 8, 9, 10, 0x500B, 0x500C, 0x5016, 0x501F, 0x5020, 0x6017, 0x7017, 0xFFFF]:
        for flags in [0, 0x10000000, 0xA0000000, 0xF8000000]:
            results = []
            for image in (original, rc2):
                u = machine(image)
                init_registers(u)
                u.reg_write(UC_ARM_REG_APSR, flags)
                u.mem_write(RAM+0xEAE, struct.pack('<H', event))
                u.emu_start((BASE+HOOK)|1, 0x0801334A, count=100)
                require(u.reg_read(UC_ARM_REG_PC) == 0x0801334A, 'Fallback failed to return')
                results.append([u.reg_read(r) for r in REGS] + [u.reg_read(UC_ARM_REG_APSR)])
            require(results[0] == results[1], 'Fallback changed register/flags/SP/LR')
            fallback_cases += 1
    # Emulate each path with volatile-register-clobbering housekeeping stub.
    active = []
    for event, source in TARGETS.items():
        for sp in [0x20001FB8, 0x20001FA8]:
            u = machine(rc2)
            init_registers(u, sp)
            expected_r1 = u.reg_read(UC_ARM_REG_R1)
            expected_r2 = u.reg_read(UC_ARM_REG_R2)
            u.mem_write(RAM+0xEAE, struct.pack('<H', event))
            calls = []
            observed_sp = set()
            def step(uc, address, size, _):
                observed_sp.add(uc.reg_read(UC_ARM_REG_SP))
                require(uc.reg_read(UC_ARM_REG_SP) % 8 == 0, 'Handler lost 8-byte alignment')
                if address == 0x080131F8:
                    require(uc.reg_read(UC_ARM_REG_SP) == sp, 'SP not restored before BL')
                    require(uc.reg_read(UC_ARM_REG_R1) == expected_r1 and uc.reg_read(UC_ARM_REG_R2) == expected_r2, 'Scratch not restored')
                    calls.append(address)
                    for n, reg in enumerate(REGS[:4]):
                        uc.reg_write(reg, 0xFACE0000+n)
                    uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
                else:
                    require(address == BASE+HOOK or BASE+EOF <= address < BASE+EOF+120, 'Unexpected handler execution')
            u.hook_add(UC_HOOK_CODE, step)
            u.emu_start((BASE+HOOK)|1, 0x080134D4, count=100)
            require(u.reg_read(UC_ARM_REG_PC) == 0x080134D4, 'Wrong active exit')
            require(calls == [0x080131F8], 'Housekeeping call count wrong')
            require(u.reg_read(UC_ARM_REG_SP) == sp, 'Active SP not restored')
            require(bytes(u.mem_read(RAM+0xED3, 1)) == bytes([source]), 'Wrong requested source')
            active.append({'event': hex(event), 'source': source, 'initial_sp': hex(sp),
                           'observed_stack_values': [hex(v) for v in sorted(observed_sp)],
                           'housekeeping_calls': len(calls), 'exit': '0x080134d4'})
    result = {
        'status': 'PASS', 'original_sha256': sha(original), 'rc2_sha256': sha(rc2),
        'original_size': len(original), 'rc2_size': len(rc2),
        'changed_original_offsets': [hex(x) for x in diff], 'appended_bytes': 124,
        'handler_code_bytes': 120, 'literal_address': '0x0801d970',
        'literal_value': '0x20000ed3', 'branch_checks': branches,
        'unaltered_partitions': partitions, 'unchanged_subsystem_anchors': preserved,
        'fallback_differential_cases': fallback_cases, 'active_handler_cases': active,
        'stack_alignment_bytes_at_every_executed_handler_instruction': 8,
        'runtime_versions': runtime_versions(), 'hardware_performed': False, 'updater_attempt_performed': False,
        'limits': [
            'Named subsystem ranges are reviewed anchors, not a complete reverse engineering of every subsystem.',
            'All original bytes outside the hook are independently equal, including unclassified code/data.',
            'NVRAM layout code/literals are identical; physical NVRAM pages are absent from the supplied image.',
            'Housekeeping was stubbed in local handler experiments with arbitrary caller-saved register clobbering.',
            'Full dispatcher/worker behavior is covered by the separate primary verifier, not this local ABI experiment.',
            'Physical flash identity, updater acceptance, timing, analog behavior, external USB firmware and recovery are not measured here.'
        ],
    }
    require(args.original.read_bytes() == original, 'Original changed during review')
    require(args.candidate.read_bytes() == rc2, 'Candidate changed during review')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'sha256': sha(rc2), 'fallback_cases': fallback_cases,
                      'active_cases': len(active), 'branches': len(branches), 'unaltered_original_bytes': len(original)-4}, indent=2))


if __name__ == '__main__':
    main()
