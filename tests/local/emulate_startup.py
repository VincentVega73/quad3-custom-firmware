"""Run only the image's C-runtime memory initializer, without any device I/O."""
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

def initialize(image):
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    u.mem_map(0x08010000, 0x10000)
    u.mem_write(0x08010000, image)
    u.mem_map(0x20000000, 0x10000)
    u.reg_write(UC_ARM_REG_SP, 0x20001fb8)
    u.reg_write(UC_ARM_REG_LR, 0x0801fff1)
    reads, writes = set(), set()
    u.hook_add(UC_HOOK_MEM_READ, lambda u,a,p,n,v,d: reads.update(range(p,p+n)))
    u.hook_add(UC_HOOK_MEM_WRITE, lambda u,a,p,n,v,d: writes.update(range(p,p+n)))
    u.emu_start(0x0801cbe9, 0x0801fff0, count=1000000)
    if u.reg_read(UC_ARM_REG_PC) != 0x0801fff0:
        raise RuntimeError('initializer did not return')
    return bytes(u.mem_read(0x20000000, 0x1fb8)), reads, writes
