"""Execute native source transitions and NVRAM serialization under Unicorn.

No device access. The peripheral drivers listed in the resulting JSON are stubs.
The timer tests execute two original decrement fragments; they do not simulate
interrupt scheduling, elapsed milliseconds, analog audio or real flash writes.
"""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from firmware_patch import build, PAYLOAD, ORIGINAL_SIZE
from emulate_startup import initialize
from test_support import protect_inputs, runtime_versions
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import *

BASE, RAMBASE, STOP, SP = 0x08010000, 0x20000000, 0x0801FFF0, 0x20001FB8
EXPECTED = '7dff59e986643543c28c7f71c1f43f78c936867b25b078e0c1bd0ea5a6fe3853'
DISPATCH, WORKER, SAVE_POLL, RESTORE = 0x080132E8, 0x08012E64, 0x0801598C, 0x08015526
EVENTS = {1: 0x5017, 5: 0x5018, 6: 0x5019, 7: 0x501A,
          3: 0x501B, 2: 0x501C, 4: 0x501D, 0: 0x501E}
NAMES = {0: 'Bluetooth', 1: 'USB', 2: 'Optical', 3: 'Coax',
         4: 'ARC', 5: 'AUX1', 6: 'AUX2', 7: 'Phono'}
ROUTING_MASKS = {0: 0x800, 1: 0x800, 2: 0x800, 3: 0x800,
                 4: 0x800, 5: 0x200, 6: 0x400, 7: 0x100}
HANDLER_CODE_END = BASE + ORIGINAL_SIZE + len(PAYLOAD) - 4
STATE = {'requested': 0xED3, 'applied': 0x436, 'stage': 0xEEA,
         'timer': 0xEEB, 'flags': 0xEEF, 'ready': 0xEE0,
         'save_delay': 0xFA7, 'page': 0xF29, 'power': 0xED1}
# Half-open code ranges. Literal pools are read, never intentionally executed.
RANGES = [(0x080132E8, 0x08013A1C), (0x0801A008, 0x0801AAE4),
          (0x080145CC, 0x08014662), (0x08014D30, 0x08014D8E),
          (0x080130F6, 0x08013118), (0x080131F8, 0x08013296),
          (0x08012E64, 0x08012F60), (0x08012F64, 0x08012F76),
          (0x08012F8C, 0x08013018), (0x08011FB4, 0x08012162),
          (0x08016EF0, 0x08016F4C), (BASE + ORIGINAL_SIZE, HANDLER_CODE_END),
          (0x08014446, 0x0801444E),
          (0x0801031A, 0x0801032A), (0x080105F4, 0x08010604),
          (0x080154F0, 0x0801550C), (0x08015526, 0x080159A0)]
CALLEE_REGS = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
               UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11]
MD = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
MD.detail = True
STUB_NAMES = {
    0x08011F40: 'routing register serial output',
    0x08011A0C: 'analog/digital downstream selection',
    0x08012B20: 'AUX2 AV-direct boundary helper',
    0x08014B9E: 'digital/USB coordination',
    0x08014CC6: 'digital/USB coordination',
    0x08015E9E: 'digital reconfiguration request',
    0x08015E2C: 'digital reconfiguration request',
    0x08018242: 'CEC command queue (captures argument 0xC0)',
    0x0801ABAE: 'flash unlock/control',
    0x0801ABCE: 'flash lock/control',
    0x0801ACC0: 'flash control/status setup',
    0x0801B03C: 'flash programming primitive; writes to simulated memory only',
}


def allowed(address):
    return any(lo <= address < hi for lo, hi in RANGES)


class Machine:
    all_stubs = {}

    def __init__(self, image, initial):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        self.u.mem_map(BASE, 0x10000)
        self.u.mem_write(BASE, image)
        self.u.mem_map(RAMBASE, 0x10000)
        self.u.mem_map(0xA000, 0x1000)
        self.initial = initial
        self.cache = {}
        self.calls = []
        self.flash_writes = []
        self.entries = []
        self.payload_instructions = 0
        self.u.hook_add(UC_HOOK_CODE, self.hook)
        self.reset()

    def hook(self, u, address, size, _):
        assert allowed(address), f'Unapproved execution: {address:08x}'
        if address in (WORKER, 0x08012F64, 0x08012F8C, 0x08011FB4, SAVE_POLL, 0x080157CE):
            self.entries.append(address)
        if BASE + ORIGINAL_SIZE <= address < HANDLER_CODE_END:
            assert u.reg_read(UC_ARM_REG_SP) % 8 == 0, 'RC2 handler broke stack alignment'
            self.payload_instructions += 1
        ins = self.cache.get(address)
        if ins is None:
            ins = next(MD.disasm(bytes(u.mem_read(address, size)), address))
            self.cache[address] = ins
        if ins.mnemonic == 'bl':
            target = ins.operands[0].imm
            if not allowed(target):
                assert target in STUB_NAMES, f'Unlisted external callee: {target:08x}'
                arg = u.reg_read(UC_ARM_REG_R0)
                if target == 0x08018242:
                    assert arg == 0xC0
                self.calls.append((target, arg))
                self.all_stubs.setdefault(target, set()).add(address)
                if target == 0x0801B03C:
                    cursor, word = struct.unpack('<II', u.mem_read(RAMBASE + 0xE88, 8))
                    assert 0xA000 <= cursor < 0xA800 and cursor % 4 == 0
                    assert arg == 1
                    self.flash_writes.append((cursor, word))
                    u.mem_write(cursor, struct.pack('<I', word))
                # Explicit ABI stub policy: return 0 and clobber r1-r3 to 0.
                # No peripheral registers, host devices or actual flash are accessed.
                for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3):
                    u.reg_write(reg, 0)
                u.reg_write(UC_ARM_REG_PC, (address + size) | 1)

    def reset(self, **state):
        self.u.mem_write(RAMBASE, b'\0' * 0x10000)
        self.u.mem_write(RAMBASE, self.initial)
        self.u.mem_write(0xA000, b'\xff' * 0x1000)
        for key, value in dict(requested=0, applied=0, stage=0, timer=0,
                               flags=0xA4, ready=0, save_delay=0, page=0, power=1).items():
            self.byte(STATE[key], state.pop(key, value))
        for key, value in state.items():
            self.byte(int(key, 16), value)
        self.u.mem_write(RAMBASE + 0xE88, struct.pack('<I', 0xA000))
        self.calls.clear()
        self.flash_writes.clear()
        self.entries.clear()

    def byte(self, offset, value=None):
        if value is not None:
            self.u.mem_write(RAMBASE + offset, bytes([value]))
        return self.u.mem_read(RAMBASE + offset, 1)[0]

    def state(self):
        return {key: self.byte(offset) for key, offset in STATE.items()}

    def ram(self):
        return bytes(self.u.mem_read(RAMBASE, 0x1000))

    def invoke(self, entry, end=STOP):
        for index, reg in enumerate(CALLEE_REGS):
            self.u.reg_write(reg, 0x44440000 + index)
        self.u.reg_write(UC_ARM_REG_SP, SP)
        self.u.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.u.emu_start(entry | 1, end, count=20000)
        assert self.u.reg_read(UC_ARM_REG_PC) == end
        assert self.u.reg_read(UC_ARM_REG_SP) == SP
        assert [self.u.reg_read(reg) for reg in CALLEE_REGS] == [0x44440000 + i for i in range(8)]

    def event(self, event):
        self.u.mem_write(RAMBASE + 0xEAE, struct.pack('<H', event))
        self.invoke(DISPATCH)

    def request(self, target):
        before = len(self.entries)
        self.event(EVENTS[target])
        assert self.byte(0xED3) == target
        assert self.byte(0xEEA) == 1 and self.byte(0xEEB) == 0
        assert self.byte(0xFA7) == 3 and self.byte(0xF29) == 4
        assert self.byte(0xF24) == 1
        assert self.u.mem_read(RAMBASE + 0xEAE, 2) == b'\0\0'
        assert 0x08012F64 in self.entries[before:]

    def source_tick(self):
        before = self.byte(0xEEB)
        self.invoke(0x0801031A, 0x0801032A)
        assert self.byte(0xEEB) == max(0, before - 1)

    def save_tick(self):
        before = self.byte(0xFA7)
        self.invoke(0x080105F4, 0x08010604)
        assert self.byte(0xFA7) == (before - 1 if before >= 2 else before)

    def drain(self):
        trace = []
        ticks = 0
        for _ in range(1000):
            before = self.state()
            calls_before = len(self.calls)
            self.invoke(WORKER)
            after = self.state()
            if before != after or self.calls[calls_before:]:
                trace.append({'before': before, 'after': after,
                              'calls': [[hex(a), hex(b)] for a, b in self.calls[calls_before:]]})
            if before['timer']:
                assert before == after and len(self.calls) == calls_before, 'worker ignored its timer'
            if not after['stage']:
                assert after['applied'] == after['requested']
                assert after['flags'] & 1 == 0
                return {'source_ticks': ticks, 'steps': trace}
            self.source_tick()
            ticks += 1
        raise AssertionError('source transition did not converge')


def main():
    if not __debug__:
        raise SystemExit('Assertions must be enabled; do not use python -O')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', type=Path, required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--output', type=Path, default=ROOT / 'generated' / 'transition_verification_rc2.json')
    args = ap.parse_args()
    protect_inputs(args.output, args.original, args.candidate)
    start = time.time()
    original = args.original.read_bytes()
    patched = args.candidate.read_bytes()
    rebuilt, _, _ = build(original)
    assert patched == rebuilt, 'Candidate differs from the exact reviewed RC2 build'
    assert patched[:0x3346] == original[:0x3346]
    assert patched[0x334A:len(original)] == original[0x334A:]
    # RC2 specifically preserves two registers and keeps an 8-byte aligned stack.
    payload = list(MD.disasm(patched[len(original):-4], BASE + len(original)))
    assert [i.op_str for i in payload if i.mnemonic in ('push', 'pop')] == ['{r1, r2}'] * 3
    initial = initialize(original)[0]
    assert initial == initialize(patched)[0], 'RC2 changed runtime RAM initialization'
    stock, rc2 = Machine(original, initial), Machine(patched, initial)
    result = {'status': 'PASS', 'original_sha256': EXPECTED,
              'patched_sha256': hashlib.sha256(patched).hexdigest()}

    # Matched native Source-next requests, with all source-worker stages and
    # nonzero timer cases. The initial source is target-1 for both images.
    equivalent = 0
    for target, stage, timer, ready, applied in itertools.product(EVENTS, range(5), (0, 7), (0, 1), range(8)):
        state = dict(requested=(target-1) % 8, applied=applied, stage=stage,
                     timer=timer, ready=ready, flags=0xA5 if stage == 4 else 0xA4)
        stock.reset(**state)
        rc2.reset(**state)
        stock.event(0x500B)
        rc2.request(target)
        assert stock.ram() == rc2.ram(), ('native Source side effects differ', state, target)
        assert stock.calls == rc2.calls
        stock_trace, rc2_trace = stock.drain(), rc2.drain()
        assert stock_trace == rc2_trace
        assert stock.ram() == rc2.ram() and stock.calls == rc2.calls
        equivalent += 1
    result['native_source_full_transition_equivalence_cases'] = equivalent

    repeated = []
    for target, ready in itertools.product(EVENTS, (0, 1)):
        rc2.reset(requested=target, applied=target, ready=ready)
        runs = []
        for _ in range(2):
            rc2.request(target)
            start_calls = len(rc2.calls)
            trace = rc2.drain()
            calls = rc2.calls[start_calls:]
            assert bool(any(t == 0x08011F40 for t, _ in calls)) == (ready != 1)
            assert bool(any(t == 0x08018242 for t, _ in calls)) == (target == 4 and ready != 1)
            runs.append(trace)
        repeated.append({'sequence': f'{NAMES[target]} -> {NAMES[target]}',
                         'ready_flag': ready, 'runs': runs})
    result['repeated_completed_requests'] = repeated

    rc2.reset()
    sequence = []
    for target in (1, 5, 6, 7, 3, 2, 4, 0, 1):
        rc2.request(target)
        trace = rc2.drain()
        routing_word = struct.unpack('<I', rc2.u.mem_read(RAMBASE + 0xE68, 4))[0]
        assert routing_word & 0xF00 == ROUTING_MASKS[target]
        if target == 2:
            assert routing_word & 0xC0 == 0
        elif target == 3:
            assert routing_word & 0xC0 == 0x80
        elif target == 4:
            assert routing_word & 0x40
        elif target == 0:
            assert rc2.byte(0xF53) == 1, 'Native Bluetooth request helper did not run'
        sequence.append({'target': NAMES[target], 'routing_word': hex(routing_word), 'transition': trace})
    result['all_eight_source_cycle'] = sequence

    # New requests overwrite ED3 and restart stage=1,timer=0. There is no queue.
    in_flight = 0
    for old, new, stage, timer, av_direct in itertools.product(EVENTS, EVENTS, range(1, 5), (0, 7), (0, 1)):
        rc2.reset(requested=old, applied=6 if av_direct else 0, stage=stage,
                  timer=timer, flags=0xA5 if stage == 4 else 0xA4)
        rc2.byte(0xFA5, av_direct)
        rc2.request(new)
        call_start = len(rc2.calls)
        trace = rc2.drain()
        assert rc2.byte(0xED3) == new and rc2.byte(0x436) == new
        route_values = [arg for target, arg in rc2.calls[call_start:] if target == 0x08011F40]
        assert len(route_values) == 1
        assert route_values[0] & 0xF00 == ROUTING_MASKS[new]
        assert trace['source_ticks'] == 160
        in_flight += 1
    result['in_flight_latest_request_cases'] = in_flight
    # Every target from every applied source, including the ready fast exit.
    all_source_pairs = 0
    for old, new, ready in itertools.product(EVENTS, EVENTS, (0, 1)):
        rc2.reset(requested=old, applied=old, ready=ready)
        rc2.request(new)
        trace = rc2.drain()
        assert rc2.byte(0x436) == new
        expected_ticks = 50 if old == new and ready == 1 else 160
        assert trace['source_ticks'] == expected_ticks
        all_source_pairs += 1
    result['all_initial_and_target_source_pairs'] = all_source_pairs

    # Three immediate repeats for each target, before the worker gets a turn.
    rapid_repeat = []
    for target in EVENTS:
        rc2.reset(requested=(target + 1) % 8, applied=(target + 1) % 8)
        for _ in range(3):
            rc2.request(target)
        trace = rc2.drain()
        assert rc2.byte(0x436) == target
        assert trace['source_ticks'] == 160
        rapid_repeat.append({'source': NAMES[target], 'requests': 3, 'source_ticks': 160})
    result['rapid_repeated_requests'] = rapid_repeat

    # Every ordered pair of different immediate requests must choose the last.
    immediate_pairs = []
    for first, second in itertools.permutations(EVENTS, 2):
        rc2.reset()
        rc2.request(first)
        rc2.request(second)
        trace = rc2.drain()
        assert rc2.byte(0x436) == second and rc2.byte(0xED3) == second
        assert trace['source_ticks'] == 160
        immediate_pairs.append([NAMES[first], NAMES[second]])
    result['immediate_different_command_pairs'] = immediate_pairs

    # Both command gate and protection page must retain stock behavior.
    gated = 0
    for power, page, target in itertools.product((0, 1, 2, 3, 4, 5, 6, 255), (0, 4, 0x12), EVENTS):
        if power == 1 and page != 0x12:
            continue
        state = dict(requested=2, applied=2, stage=3, timer=7,
                     flags=0xA5, power=power, page=page)
        stock.reset(**state)
        rc2.reset(**state)
        stock.event(EVENTS[target])
        rc2.event(EVENTS[target])
        assert stock.ram() == rc2.ram() and stock.calls == rc2.calls
        assert rc2.byte(0xED3) == 2
        assert rc2.byte(0xEEA) == 3 and rc2.byte(0xEEB) == 7
        gated += 1
    result['power_and_protection_gate_cases'] = gated

    # Real scheduler fragment, real poll/save packing, captured programming and
    # actual stock scanner/restore over a simulated 0xA000 flash page.
    saved = []
    for target in EVENTS:
        rc2.reset()
        rc2.request(target)
        rc2.drain()
        rc2.invoke(SAVE_POLL)
        assert not rc2.flash_writes
        rc2.save_tick()
        assert rc2.byte(0xFA7) == 2
        rc2.invoke(SAVE_POLL)
        assert not rc2.flash_writes
        rc2.save_tick()
        assert rc2.byte(0xFA7) == 1
        rc2.invoke(SAVE_POLL)
        assert rc2.byte(0xFA7) == 0
        assert len(rc2.flash_writes) == 7
        rc2.save_tick()
        rc2.invoke(SAVE_POLL)
        assert rc2.byte(0xFA7) == 0 and len(rc2.flash_writes) == 7
        assert [a for a, _ in rc2.flash_writes] == list(range(0xA000, 0xA01C, 4))
        assert (rc2.flash_writes[0][1] >> 16) & 0xF == target
        rc2.byte(0xED3, (target + 1) % 8)
        rc2.invoke(RESTORE)
        assert rc2.byte(0xED3) == target
        saved.append({'source': NAMES[target], 'scheduler_values': [3, 2, 1, 0],
                      'programmed_words': [[hex(a), hex(w)] for a, w in rc2.flash_writes],
                      'restored_source': rc2.byte(0xED3)})
    result['persistence_save_restore_cases'] = saved
    result['executed_code_ranges'] = [[hex(lo), hex(hi)] for lo, hi in RANGES]
    result['stubbed_calls'] = [{'target': hex(t), 'description': STUB_NAMES.get(t, 'external helper; return-zero ABI stub'),
                               'callsites': [hex(a) for a in sorted(sites)]}
                              for t, sites in sorted(Machine.all_stubs.items())]
    result['handler_alignment_instruction_checks'] = rc2.payload_instructions
    result['timer_model'] = {
        'source_tick_code': '0x0801031A..0x08010328: EEB decremented only when nonzero',
        'save_tick_code': '0x080105F4..0x08010602: FA7 decremented only when >=2',
        'source_delays': [50, 10, 100],
        'elapsed_units': 'firmware source-timer decrement opportunities; not asserted to be milliseconds',
        'execution': 'worker then one source-timer decrement, until idle; save ticks exercised separately',
    }
    result['limitations'] = [
        'Peripheral/analog behavior, real flash erase/programming and power-loss persistence are not emulated.',
        'No bootloader, USB UPDATE, signature acceptance or physical MCU capacity is tested here.',
        'No interrupt preemption or concurrent CEC/USB/power/protection task scheduling is emulated.',
        'Power/protection checks exercise dispatcher guards with fixed RAM states, not physical fault sensing.',
        'Zero-return ABI stubs and enumerated RAM states limit conclusions to the paths listed above.',
    ]
    result['candidate_size'] = len(patched)
    result['runtime_versions'] = runtime_versions()
    result['startup_ram_rebuilt_in_memory'] = True
    result['runtime_seconds'] = round(time.time() - start, 2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'patched_sha256',
        'native_source_full_transition_equivalence_cases', 'in_flight_latest_request_cases',
        'power_and_protection_gate_cases', 'handler_alignment_instruction_checks', 'runtime_seconds')}, indent=2))


if __name__ == '__main__':
    main()
