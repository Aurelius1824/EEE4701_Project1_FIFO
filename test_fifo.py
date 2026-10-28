"""STUDENT STARTER -- Week 5 constrained-random FIFO testbench (pyvsc).

Goal: replace directed stimulus with a @vsc.randobj transaction and a proper
scoreboard so the constrained-random suite finds the whole FIFO mutant pool.

Right now this is deliberately weak: the transaction is uniform random (no bias
toward the boundaries), the run is short, and the scoreboard checks *only*
count. That leaves the full/empty flags, the FWFT head (rd_data), pointer wrap,
and the simultaneous-read+write corner completely unchecked -- raise the
found/total by finishing the TODOs.

Run:    make SIM=icarus
Score:  cd code && just mutate fifo_crv            # released pool
        cd code && just mutate fifo_crv hidden     # hidden pool (grading)
"""
import random

import cocotb
import vsc
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

from models.fifo_model import FifoModel

# Utilized an AI model to assist with learning and TB refinement.
# After hidden score was obtained, utilize AI model to accelerate TB refinement,
# to increase mutant detection

WIDTH = 8
DEPTH = 8
SEED = 0xDEADBEEF
CYCLES = 1200   # (256*256)/2^4
MASK = (1 << WIDTH) - 1

CORNER_DATA = (0x00, 0xFF, 0xAA, 0x55, 0x80, 0x01, 0x7F, 0xFE, 0xF0, 0x0F)


@vsc.randobj
class FifoTxn:
    def __init__(self, width=WIDTH):
        self.wr_en = vsc.rand_bit_t(1)
        self.rd_en = vsc.rand_bit_t(1)
        self.wr_data = vsc.rand_bit_t(width)
        # self.roll = vsc.rand_uint8_t()       # one uniform draw, 0..99
        self.count = vsc.uint32_t()
        self._step = 0


    @vsc.constraint
    def c_bias(self):
        # Case 1: Near empty
        # Lets biased toward writes to fill, while keeping rd_en weight so count==0
        # Exercises read-while-empty and simulatenous r+w at empty
        with vsc.if_then(self.count <= 1):   
            vsc.dist(self.wr_en, [vsc.weight(1, 72), vsc.weight(0, 28)])
            vsc.dist(self.rd_en, [vsc.weight(1, 42), vsc.weight(0, 58)])

        # Case 2: Near full
        # Biases toward reads to drain, while keeping wr_en weight so count==DEPTH
        # exercises write-while-full and simultaneous r+w at full.
        with vsc.else_if(self.count >= DEPTH - 1):  
            vsc.dist(self.wr_en, [vsc.weight(1, 42), vsc.weight(0, 58)])
            vsc.dist(self.rd_en, [vsc.weight(1, 72), vsc.weight(0, 28)])

        # Case 3: Midrange (2 <= count <= DEPTH - 2)
        # Push both enables for frequenct simultaneous r+w bursts
        with vsc.else_then():
            vsc.dist(self.wr_en, [vsc.weight(1, 80), vsc.weight(0, 20)])
            vsc.dist(self.rd_en, [vsc.weight(1, 80), vsc.weight(0, 20)])

    def post_randomize(self):
        self._step += 1
        # On every 4th transaction, force a CORNER
        if self._step % 4 == 0:
             self.wr_data = CORNER_DATA[(self._step // 4) % len(CORNER_DATA)]


class FifoDriver:
    """Drives FIFO's input pins"""
    def __init__(self, dut):
        self.dut = dut

    # Asynchronous drive of FIFO's input pins
    async def drive(self, wr_en, rd_en, wr_data, rst_n=1):
        await FallingEdge(self.dut.clk)
        self.dut.rst_n.value = int(bool(rst_n))
        self.dut.wr_en.value = int(bool(wr_en))
        self.dut.rd_en.value = int(bool(rd_en))
        self.dut.wr_data.value = int(wr_data) & (MASK)

class FifoMonitor:
    """Sample the DUT outputs"""
    def __init__(self, dut):
        self.dut = dut
    
    def sample(self):
        assert self.dut.count.value.is_resolvable, f"Count is X/Z: {self.dut.count.value}"
        assert self.dut.full.value.is_resolvable, f"Full is X/Z: {self.dut.full.value}"
        assert self.dut.empty.value.is_resolvable, f"Empty is X/Z: {self.dut.empty.value}"

        count = int(self.dut.count.value)
        full = bool(self.dut.full.value)
        empty = bool(self.dut.empty.value)

        if not empty:
            # Assert DUT drives real value
            assert self.dut.rd_data.value.is_resolvable, f"rd_data is X/Z when not empty: {self.dut.rd_data.value}"
            rd_data = int(self.dut.rd_data.value)
        else:
            rd_data = None

        # Makes the return easier to use in the scoreboard.
        return {
            "count": count,
            "full": full,
            "empty": empty,
            "rd_data": rd_data
        }


class FifoScoreboard:
    """Use FifoModel as the oracle and check every observable output."""

    def __init__(self, dut, monitor, model):
        self.dut = dut
        self.monitor = monitor
        self.model = model
        self.cycle_number = 0

    def check(self, context="", was_reset=False):
        got = self.monitor.sample() 
        expected = {
            "count": self.model.count,
            "full": self.model.full,
            "empty": self.model.empty,
        }     

        # Contextualize the error message with the cycle number and any additional context.
        prefix = f"Cycle {self.cycle_number}"
        if context:
            prefix += f"| {context}"   

        # Guard against physical overflow (> DEPTH) or underflow (< 0)
        assert 0 <= got["count"] <= DEPTH, (
            f"{prefix}: COUNT out of bounds [0, {DEPTH}, got {got['count']}]"
        )

        # Flag Consistency to make sure that FULL truly means FIFO if FULL
        assert got["full"] == (got["count"] == DEPTH), (
            f"{prefix}: FULL flag ({got['full']}) inconsistent with count {got['count']}]"
        )
        assert got["empty"] == (got["count"] == 0), (
            f"{prefix}: EMPTY flag ({got['empty']}) inconsistent with count {got['count']}]"
        )

        # Check rst functions as expected
        if was_reset:
            assert got["count"] == 0 and got["empty"] is True and got["full"] is False, (
                f"{prefix}: RESET check failed! got count={got['count']}, "
                f"empty={got['empty']}, full={got['full']}"
            )

        # Assert expected vs. got values
        assert got["count"] == expected["count"], (
            f"{prefix}: count expected {expected['count']}, got {got['count']}"
        )

        assert got["full"] == expected["full"], (
            f"{prefix}: full expected {expected['full']}, got {got['full']}"
        )

        assert got["empty"] == expected["empty"], (
            f"{prefix}: empty expected {expected['empty']}, got {got['empty']}"
        )

        # If FIFO not empty, then get data @head (1st entry)
        if not self.model.empty:
            assert got["rd_data"] == self.model.head, (
                f"{prefix}: FWFT head expected 0x{self.model.head:02X}, "
                f"got 0x{got['rd_data']:02X}"
            )


class FifoTB:
    """Coordinates the driver, golden model, monitor, and scoreboard"""
    def __init__(self, dut):
        self.dut = dut
        self.driver = FifoDriver(dut)
        self.monitor = FifoMonitor(dut)
        self.model = FifoModel(WIDTH, DEPTH)
        self.scoreboard = FifoScoreboard(dut, self.monitor, self.model)

        # Stimulus checks and tracking
        self.visited_counts = set()
        self.saw_full = False
        self.saw_empty = False
        self.saw_simultaneous_rw = False
        self.saw_write_while_full = False
        self.saw_read_while_empty = False

    def record_coverage(self, pre_count, pre_full, pre_empty, wr_en, rd_en):
        """Records the coverage of various conditions during the cycle."""
        self.visited_counts.add(pre_count)  # Value before cycle
        self.visited_counts.add(self.model.count)   # Value during cycle

        if pre_full or self.model.full:
            self.saw_full = True
        if pre_empty or self.model.empty:
            self.saw_empty = True
        if wr_en and rd_en:
            self.saw_simultaneous_rw = True
        # Ensure we can see corners with certainity
        if wr_en and not rd_en and pre_full:
            self.saw_write_while_full = True
        if not wr_en and rd_en and pre_empty:
            self.saw_read_while_empty = True
    
    def check_stimulus_coverage(self):
        """Asserts that the CR-walk reached all the required states"""
        assert self.saw_full, "Stimulus self-check failed: Stimuli never saw FULL"
        assert self.saw_empty, "Stimulus self-check failed: Stimuli never saw EMPTY"
        assert self.saw_simultaneous_rw, "Stimulus self-check failed: Stimuli never saw SIMULTANEOUS READ + WRITE"
        assert self.saw_write_while_full, "Stimulus self-check failed: Stimuli never saw WRITE-WHILE-FULL"
        assert self.saw_read_while_empty, "Stimulus self-check failed: Stimuli never saw READ-WHILE-EMPTY"

        expected_counts = set(range(DEPTH + 1))
        missing_counts = expected_counts - self.visited_counts
        assert not missing_counts, f"Stimulus self-check failed: Missed the following counts: {sorted(missing_counts)}"

    async def cycle(self, wr_en=0, rd_en=0, wr_data=0, rst_n=1, context=""):
        """Perform single cycle of driving, sampling the model, and checking."""
        pre_count = self.model.count
        pre_full = self.model.full
        pre_empty = self.model.empty

        # Inputs change on falling edge. Model uses the pre-rising edge
        await self.driver.drive(wr_en, rd_en, wr_data, rst_n=rst_n)
        await Timer(1, units="ns")

        # Pre-rising edge check: Driving wr_en, rd_en, wr_data, or rst_n on the falling edge
        # must NOT combinationally glitch registered state outputs
        self.scoreboard.check(context=f"Pre-clock| {context}")

        if not rst_n:
            self.model.reset()
        else:
            self.model.step(wr_en=wr_en, rd_en=rd_en, wr_data=wr_data)

        await RisingEdge(self.dut.clk)
        await Timer(1, units="ns")  # Allow time for outputs to settle
        self.scoreboard.cycle_number += 1
        self.scoreboard.check(context=context, was_reset=(not rst_n))

        # As we cycle, track the coverage of various conditions
        if rst_n:
            self.record_coverage(pre_count, pre_full, pre_empty, wr_en, rd_en)

@cocotb.test()
async def fifo_test_CRV(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    TB = FifoTB(dut)

    # reset DUT inputs
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wr_data.value = 0
    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
    TB.model.reset()
    TB.scoreboard.check("After RESET", was_reset=True)
    dut.rst_n.value = 1

    # After this cycle we are in a stable state
    await FallingEdge(dut.clk)

    # Seed random w/ our SEED
    random.seed(SEED)

    txn = FifoTxn()

    for cycle_idx in range(CYCLES):
        # inject resets to catch valid rst operations
        if cycle_idx in (38, 150) and TB.model.count > 0:
            await TB.cycle(
                    wr_en=1,
                    rd_en=1,
                    wr_data=0xA5,
                    rst_n=0,
                    context=f"Operational rst_n check with active enables for 'wr' and 'rd'"
                )
            continue

        # Window Scheduler to control which branch of c_bias gets activated
        window = (cycle_idx // 14) % 4

        # Windows of testing phases
        if window == 0:
            txn.count = 0
        elif window == 1:
            txn.count = TB.model.count
        elif window == 2:
            txn.count = DEPTH
        else:
            # If FIFO empty/full jump to middle of FIFO
            if TB.model.count in (0, DEPTH):
                txn.count = DEPTH // 2
            elif TB.model.count < DEPTH // 2:
                txn.count = DEPTH   # Jump to full
            else:
                txn.count = 0   # Jump to empty

        txn.randomize()

        wr, rd, data = int(txn.wr_en), int(txn.rd_en), int(txn.wr_data)

        await TB.cycle(
                wr_en=wr,
                rd_en=rd,
                wr_data=data,
                context=f"Seed=0x{SEED:X}, pre_count={TB.model.count}, wr={wr}, rd={rd}, data=0x{data:02X}"
            )

    for i in range(DEPTH + 1):
        # Cleanly adjust to target occupancy k (0, 1, ...--->8)\
        while TB.model.count < i:
            txn.count = 0
            txn.randomize()
            await TB.cycle(wr_en=1, rd_en=0, wr_data=int(txn.wr_data), context=f"Step fill to {i}")
        while TB.model.count > i:
            txn.count = DEPTH
            txn.randomize()
            await TB.cycle(wr_en=0, rd_en=1, wr_data=int(txn.wr_data), context=f"Step drain to {i}")

        # At exact level i:
        # (a) Test idle hold (wr_en=0, rd_en=0) with inverted wr_data to catch unitended memory/pointer 
        #     writes when wr_en=0
        await TB.cycle(wr_en=0, rd_en=0, wr_data=0xFF ^ (i * 0x11), context=f"Idle hold at count={i}")
        await TB.cycle(wr_en=0, rd_en=0, wr_data=0x00, context=f"Idle hold at count={i}")

        # (b) Execute 10 consecutive simultaneous R+W (wr_en=1, rd_en=1) at exact
        #     occupancy i (wraps both wr_ptr and rd_ptr completely around 7->0 at
        #     count=0, count=1, count=2..6, count=7, and count=8!)
        for wrap_step in range(DEPTH + 2):
            txn.count = DEPTH // 2
            txn.randomize()
            pat = (int(txn.wr_data) ^ (1 << (wrap_step % WIDTH))) & MASK
            await TB.cycle(
                wr_en=1,
                rd_en=1,
                wr_data=pat,
                context=f"Wrap sim R+W at count={i}, step={wrap_step}",
            )

    # Finally, test unbroken pure fill (0->8), write-while-full x4, unbroken pure
    # drain (8->0), and read-while-empty x4 with complement bit patterns
    while not TB.model.empty:
        await TB.cycle(wr_en=0, rd_en=1, wr_data=0x55, context="Clean drain to 0")
    for i in range(4):
        await TB.cycle(wr_en=0, rd_en=1, wr_data=0xAA ^ i, context="Repeated read-while-empty")
    for i in range(DEPTH):
        await TB.cycle(wr_en=1, rd_en=0, wr_data=(1 << i) & MASK, context="Unbroken pure fill 0->8")    # Walking '1'
    for i in range(4):
        await TB.cycle(wr_en=1, rd_en=0, wr_data=(~(1 << i)) & MASK, context="Repeated write-while-full")   # Walking '0'
    for i in range(DEPTH):
        await TB.cycle(wr_en=0, rd_en=1, wr_data=0xFF, context="Unbroken pure drain 8->0")


    # Verify the random walk hit all required corners
    TB.check_stimulus_coverage()
