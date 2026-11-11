"""Constrained-random + functional-coverage testbench for the FWFT FIFO.

Coverage is sampled once per active clock edge using the PRE-edge reference
model occupancy and the request pins.  The scoreboard remains the correctness
oracle; cocotb-coverage records which specified scenarios were exercised.

Run from the project directory with the course-provided simulator command.
"""
import random

import cocotb
import vsc
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb_coverage.coverage import CoverPoint, CoverCross, coverage_db

from models.fifo_model import FifoModel

WIDTH = 8
DEPTH = 8
# SEED = 0xDEADBEEF
SEED = 0xCAFEF00D
CYCLES = 1200
MASK = (1 << WIDTH) - 1

CORNER_DATA = (
    0x00, 0xFF, 0xAA, 0x55, 0x80, 0x01, 0x7F, 0xFE, 0xF0, 0x0F
)

# Claude was utilized to assist with the coverage model report and visualization.  
# The coverage model is a set of bins and crosses that are used to track the coverage of the FIFO design under test.
def classify_operation(wr_en, rd_en):
    if wr_en and rd_en:
        return "simultaneous"
    if wr_en:
        return "write_only"
    if rd_en:
        return "read_only"
    return "idle"


def classify_boundary(count, wr_en, rd_en, reset):
    if reset:
        return "reset"
    if count == 0 and rd_en and not wr_en:
        return "read_while_empty"
    if count == DEPTH and wr_en and not rd_en:
        return "write_while_full"
    if count == 0 and wr_en and rd_en:
        return "simultaneous_at_empty"
    if count == DEPTH and wr_en and rd_en:
        return "simultaneous_at_full"
    if 0 < count < DEPTH and wr_en and rd_en:
        return "simultaneous_interior"
    if count == 0:
        return "empty_state"
    if count == DEPTH:
        return "full_state"
    return "interior_state"


def classify_data(data):
    data &= MASK
    if data == 0x00:
        return "zero"
    if data == MASK:
        return "all_ones"
    if data == int("AA" * (WIDTH // 8), 16):
        return "alternating_10"
    if data == int("55" * (WIDTH // 8), 16):
        return "alternating_01"
    if data == (1 << (WIDTH - 1)):
        return "msb_only"
    if data == 1:
        return "lsb_only"
    return "other"


# ---------------------------------------------------------------------------
# Bin legality.  Several cross bins cannot occur by construction because
# classify_boundary() already encodes occupancy and operation.  Example:
# "full_state" implies count == DEPTH, so (occupancy=3, "full_state") is
# impossible.  Those bins are excluded from the crosses with ign_bins, and
# cycle() asserts that no sampled transaction ever lands on an ignored bin,
# so a classifier bug cannot hide behind the ignore list.
# ---------------------------------------------------------------------------
OPERATION_BINS = ["idle", "write_only", "read_only", "simultaneous"]
BOUNDARY_BINS = [
    "reset", "empty_state", "full_state", "interior_state",
    "read_while_empty", "write_while_full",
    "simultaneous_at_empty", "simultaneous_at_full",
    "simultaneous_interior",
]

_BOUNDARIES_AT_EMPTY = {
    "empty_state", "read_while_empty", "simultaneous_at_empty",
}
_BOUNDARIES_AT_FULL = {
    "full_state", "write_while_full", "simultaneous_at_full",
}
_BOUNDARIES_INTERIOR = {"interior_state", "simultaneous_interior"}

# Operations that classify_boundary() can pair with each boundary bin.
# Reset is driven independently of wr_en/rd_en, so all four are legal there.
_OPERATIONS_FOR_BOUNDARY = {
    "reset": set(OPERATION_BINS),
    "empty_state": {"idle", "write_only"},
    "full_state": {"idle", "read_only"},
    "interior_state": {"idle", "read_only", "write_only"},
    "read_while_empty": {"read_only"},
    "write_while_full": {"write_only"},
    "simultaneous_at_empty": {"simultaneous"},
    "simultaneous_at_full": {"simultaneous"},
    "simultaneous_interior": {"simultaneous"},
}


def occupancy_boundary_possible(count, boundary):
    if boundary == "reset":
        return True  # a reset can arrive at any occupancy
    if count == 0:
        return boundary in _BOUNDARIES_AT_EMPTY
    if count == DEPTH:
        return boundary in _BOUNDARIES_AT_FULL
    return boundary in _BOUNDARIES_INTERIOR


def operation_boundary_possible(operation, boundary):
    return operation in _OPERATIONS_FOR_BOUNDARY[boundary]


OCC_X_BOUNDARY_IGN = [
    (occ, bnd)
    for occ in range(DEPTH + 1)
    for bnd in BOUNDARY_BINS
    if not occupancy_boundary_possible(occ, bnd)
]
OP_X_BOUNDARY_IGN = [
    (op, bnd)
    for op in OPERATION_BINS
    for bnd in BOUNDARY_BINS
    if not operation_boundary_possible(op, bnd)
]


# One sample call updates all coverpoints and crosses.  The occupancy and
# boundary classification are based on the pre-edge state, not the result.
@CoverPoint(
    "fifo.occupancy",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: count,
    bins=list(range(DEPTH + 1)),
)
@CoverPoint(
    "fifo.operation",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: operation,
    bins=OPERATION_BINS,
)
@CoverPoint(
    "fifo.boundary",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: boundary,
    bins=BOUNDARY_BINS,
)
@CoverPoint(
    "fifo.data_pattern",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: data_class,
    bins=[
        "zero", "all_ones", "alternating_10", "alternating_01",
        "msb_only", "lsb_only", "other",
    ],
)
@CoverPoint(
    "fifo.accepted_action",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: accepted,
    bins=["none", "write", "read", "read_and_write", "reset"],
)
@CoverPoint(
    "fifo.reset",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: reset,
    bins=[True, False],
)
@CoverPoint(
    "fifo.write_wrap_proxy",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: write_wrap,
    bins=[False, True],
)
@CoverPoint(
    "fifo.read_wrap_proxy",
    xf=lambda count, operation, boundary, data_class, accepted, reset,
           write_wrap, read_wrap: read_wrap,
    bins=[False, True],
)
@CoverCross(
    "fifo.occupancy_x_operation",
    items=["fifo.occupancy", "fifo.operation"],
)
@CoverCross(
    "fifo.occupancy_x_boundary",
    items=["fifo.occupancy", "fifo.boundary"],
    ign_bins=OCC_X_BOUNDARY_IGN,
)
@CoverCross(
    "fifo.operation_x_boundary",
    items=["fifo.operation", "fifo.boundary"],
    ign_bins=OP_X_BOUNDARY_IGN,
)
def sample_fifo_coverage(
    count, operation, boundary, data_class, accepted, reset,
    write_wrap, read_wrap
):
    """Feed one observed transaction into the functional coverage model."""
    pass



@vsc.randobj
class FifoTxn:
    def __init__(self, width=WIDTH):
        self.wr_en = vsc.rand_bit_t(1)
        self.rd_en = vsc.rand_bit_t(1)
        self.wr_data = vsc.rand_bit_t(width)
        # Occupancy is supplied by the testbench before randomize().
        self.count = vsc.uint32_t()
        self._step = 0

    @vsc.constraint
    def c_bias(self):
        # Bias toward filling near empty and draining near full.
        with vsc.if_then(self.count <= 1):
            vsc.dist(self.wr_en, [vsc.weight(1, 72), vsc.weight(0, 28)])
            vsc.dist(self.rd_en, [vsc.weight(1, 42), vsc.weight(0, 58)])
        with vsc.else_if(self.count >= DEPTH - 1):
            vsc.dist(self.wr_en, [vsc.weight(1, 42), vsc.weight(0, 58)])
            vsc.dist(self.rd_en, [vsc.weight(1, 72), vsc.weight(0, 28)])
        with vsc.else_then():
            vsc.dist(self.wr_en, [vsc.weight(1, 80), vsc.weight(0, 20)])
            vsc.dist(self.rd_en, [vsc.weight(1, 80), vsc.weight(0, 20)])

    def post_randomize(self):
        self._step += 1
        if self._step % 4 == 0:
            self.wr_data = CORNER_DATA[
                (self._step // 4) % len(CORNER_DATA)
            ]


class FifoDriver:
    """Drives FIFO inputs on the falling edge."""
    def __init__(self, dut):
        self.dut = dut

    async def drive(self, wr_en, rd_en, wr_data, rst_n=1):
        await FallingEdge(self.dut.clk)
        self.dut.rst_n.value = int(bool(rst_n))
        self.dut.wr_en.value = int(bool(wr_en))
        self.dut.rd_en.value = int(bool(rd_en))
        self.dut.wr_data.value = int(wr_data) & MASK


class FifoMonitor:
    """Samples observable FIFO outputs."""
    def __init__(self, dut):
        self.dut = dut

    def sample(self):
        for signal in ("count", "full", "empty"):
            value = getattr(self.dut, signal).value
            assert value.is_resolvable, f"{signal} is X/Z: {value}"

        count = int(self.dut.count.value)
        full = bool(self.dut.full.value)
        empty = bool(self.dut.empty.value)

        if not empty:
            value = self.dut.rd_data.value
            assert value.is_resolvable, f"rd_data is X/Z while non-empty: {value}"
            rd_data = int(value)
        else:
            # The specification leaves rd_data unspecified while empty.
            rd_data = None

        return {
            "count": count,
            "full": full,
            "empty": empty,
            "rd_data": rd_data,
        }


class FifoScoreboard:
    """Compares the DUT against the queue-based FifoModel."""
    def __init__(self, monitor, model):
        self.monitor = monitor
        self.model = model
        self.cycle_number = 0

    def check(self, context="", was_reset=False):
        got = self.monitor.sample()
        prefix = f"Cycle {self.cycle_number}"
        if context:
            prefix += f" | {context}"

        assert 0 <= got["count"] <= DEPTH, (
            f"{prefix}: count out of range [0,{DEPTH}], got {got['count']}"
        )
        assert got["full"] == (got["count"] == DEPTH), (
            f"{prefix}: full inconsistent with DUT count={got['count']}"
        )
        assert got["empty"] == (got["count"] == 0), (
            f"{prefix}: empty inconsistent with DUT count={got['count']}"
        )

        if was_reset:
            assert (
                got["count"] == 0
                and got["empty"] is True
                and got["full"] is False
            ), f"{prefix}: synchronous reset did not clear FIFO"

        assert got["count"] == self.model.count, (
            f"{prefix}: expected count={self.model.count}, got={got['count']}"
        )
        assert got["full"] == self.model.full, (
            f"{prefix}: expected full={self.model.full}, got={got['full']}"
        )
        assert got["empty"] == self.model.empty, (
            f"{prefix}: expected empty={self.model.empty}, got={got['empty']}"
        )

        # FWFT data is checked only when valid (!empty).
        if not self.model.empty:
            assert got["rd_data"] == self.model.head, (
                f"{prefix}: expected head=0x{self.model.head:02X}, "
                f"got 0x{got['rd_data']:02X}"
            )


class FifoTB:
    """Coordinates driver, monitor, reference model, scoreboard and coverage."""
    def __init__(self, dut):
        self.dut = dut
        self.driver = FifoDriver(dut)
        self.monitor = FifoMonitor(dut)
        self.model = FifoModel(WIDTH, DEPTH)
        self.scoreboard = FifoScoreboard(self.monitor, self.model)

        # These counters are coverage proxies for pointer rollover.  The DUT
        # pointers are not part of the specified interface and are not probed.
        self.accepted_writes = 0
        self.accepted_reads = 0
        self.visited_counts = set()

    async def cycle(self, wr_en=0, rd_en=0, wr_data=0, rst_n=1, context=""):
        pre_count = self.model.count
        pre_empty = self.model.empty
        pre_full = self.model.full

        await self.driver.drive(wr_en, rd_en, wr_data, rst_n=rst_n)
        await Timer(1, units="ns")

        # Before the active edge, registered state must still reflect the
        # previous model state.
        self.scoreboard.check(context=f"pre-edge | {context}")

        if not rst_n:
            self.model.reset()
            accepted = "reset"
            do_wr = do_rd = False
            self.accepted_writes = 0
            self.accepted_reads = 0
        else:
            # FifoModel.step() gates requests using pre-edge full/empty state.
            do_wr, do_rd = self.model.step(
                wr_en=wr_en, rd_en=rd_en, wr_data=wr_data
            )
            accepted = (
                "read_and_write" if do_wr and do_rd else
                "write" if do_wr else
                "read" if do_rd else
                "none"
            )
            self.accepted_writes += int(do_wr)
            self.accepted_reads += int(do_rd)

        await RisingEdge(self.dut.clk)
        await Timer(1, units="ns")
        self.scoreboard.cycle_number += 1
        self.scoreboard.check(context=context, was_reset=(not rst_n))

        operation = classify_operation(bool(wr_en), bool(rd_en))
        boundary = classify_boundary(
            pre_count, bool(wr_en), bool(rd_en), not bool(rst_n)
        )
        assert occupancy_boundary_possible(pre_count, boundary), (
            f"classifier produced ignored bin ({pre_count}, {boundary})"
        )
        assert operation_boundary_possible(operation, boundary), (
            f"classifier produced ignored bin ({operation}, {boundary})"
        )
        sample_fifo_coverage(
            pre_count,
            operation,
            boundary,
            classify_data(wr_data),
            accepted,
            not bool(rst_n),
            self.accepted_writes >= DEPTH,
            self.accepted_reads >= DEPTH,
        )

        if rst_n:
            self.visited_counts.add(pre_count)
            self.visited_counts.add(self.model.count)

    def check_basic_coverage(self):
        missing = set(range(DEPTH + 1)) - self.visited_counts
        assert not missing, (
            f"Stimulus did not visit occupancy values: {sorted(missing)}"
        )


def check_coverage_closure():
    """Fail with a list of the remaining holes if any item is below 100%."""
    holes = {}
    for name in coverage_db:
        item = coverage_db[name]
        if not isinstance(item, (CoverPoint, CoverCross)):
            continue
        missing = [
            b for b, hits in item.detailed_coverage.items()
            if hits < item.at_least
        ]
        if missing:
            holes[name] = missing
    assert not holes, f"Coverage holes remain: {holes}"


async def goto_occupancy(tb, target, tag):
    """Walk the FIFO to `target` occupancy with ordinary reads/writes."""
    while tb.model.count < target:
        await tb.cycle(
            wr_en=1, wr_data=(0x10 + tb.model.count) & MASK,
            context=f"{tag}: fill to {target}",
        )
    while tb.model.count > target:
        await tb.cycle(rd_en=1, context=f"{tag}: drain to {target}")


async def post_reset_integrity(tb, tag):
    """After a reset the FIFO must behave like a fresh one.

    A read must be ignored (empty), and a full-depth write/read pass with
    fresh data must come back in order.  Stale pre-reset entries or pointers
    that were not cleared show up as scoreboard mismatches.
    """
    await tb.cycle(rd_en=1, context=f"{tag}: read right after reset")
    for i in range(DEPTH):
        await tb.cycle(
            wr_en=1, wr_data=(0xE0 ^ (i * 0x11)) & MASK,
            context=f"{tag}: post-reset fill {i}",
        )
    assert tb.model.full, f"{tag}: FIFO did not refill to full after reset"
    while not tb.model.empty:
        await tb.cycle(rd_en=1, context=f"{tag}: post-reset drain")


async def directed_reset_sweep(tb):
    """Reset at every occupancy under every enable combination.

    Closes the occupancy x boundary(reset) and operation x boundary(reset)
    holes, and adds hold-reset and back-to-back reset scenarios.
    """
    combos = [(0, 0), (1, 0), (0, 1), (1, 1)]  # (wr_en, rd_en)

    for occ in range(DEPTH + 1):
        for wr_en, rd_en in combos:
            tag = f"reset sweep occ={occ} wr={wr_en} rd={rd_en}"
            await goto_occupancy(tb, occ, tag)
            await tb.cycle(
                wr_en=wr_en, rd_en=rd_en,
                wr_data=(0xB0 + occ) & MASK, rst_n=0,
                context=f"{tag}: synchronous reset",
            )
            assert tb.model.count == 0, f"{tag}: model not cleared by reset"
            await post_reset_integrity(tb, tag)

    # Reset held for several consecutive cycles, with enables asserted.
    for occ in (0, DEPTH // 2, DEPTH):
        tag = f"reset hold occ={occ}"
        await goto_occupancy(tb, occ, tag)
        for k in range(3):
            await tb.cycle(
                wr_en=1, rd_en=1, wr_data=0xFF, rst_n=0,
                context=f"{tag}: cycle {k}",
            )
        await post_reset_integrity(tb, tag)


@cocotb.test()
async def fifo_test_CRV(dut):
    """Directed corner cases, seeded constrained-random traffic, and coverage."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    tb = FifoTB(dut)

    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wr_data.value = 0
    dut.rst_n.value = 0

    # Synchronous active-low reset.
    for _ in range(3):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
    tb.model.reset()
    tb.scoreboard.check("after initial reset", was_reset=True)
    dut.rst_n.value = 1

    random.seed(SEED)
    txn = FifoTxn()

    # Seeded constrained-random phase. Feed the ACTUAL current occupancy
    # into the transaction; the solver's bias is therefore state-aware.
    for cycle_idx in range(CYCLES):
        if cycle_idx in (38, 150) and tb.model.count > 0:
            await tb.cycle(
                wr_en=1, rd_en=1, wr_data=0xA5, rst_n=0,
                context="operational synchronous reset with enables asserted",
            )
            continue

        txn.count = tb.model.count
        txn.randomize()
        await tb.cycle(
            wr_en=int(txn.wr_en),
            rd_en=int(txn.rd_en),
            wr_data=int(txn.wr_data),
            context=(
                f"seed=0x{SEED:X}, random_cycle={cycle_idx}, "
                f"pre_count={tb.model.count}"
            ),
        )

    # Explicitly visit every occupancy and sample idle behavior at each.
    for target in range(DEPTH + 1):
        while tb.model.count < target:
            await tb.cycle(
                wr_en=1, wr_data=(0x30 + tb.model.count) & MASK,
                context=f"directed fill to occupancy {target}",
            )
        while tb.model.count > target:
            await tb.cycle(
                rd_en=1, context=f"directed drain to occupancy {target}"
            )
        await tb.cycle(
            wr_en=0, rd_en=0, wr_data=0xFF,
            context=f"idle hold at occupancy {target}",
        )

    # Empty boundary: read ignored; simultaneous request accepts write only.
    await tb.cycle(rd_en=1, context="read while empty")
    await tb.cycle(
        wr_en=1, rd_en=1, wr_data=0xA5,
        context="simultaneous request at empty",
    )

    # Fill to full, then test dropped write and simultaneous request at full.
    while not tb.model.full:
        await tb.cycle(
            wr_en=1, wr_data=(0x50 + tb.model.count) & MASK,
            context="directed fill to full",
        )
    await tb.cycle(
        wr_en=1, context="write while full must be dropped"
    )
    await tb.cycle(
        wr_en=1, rd_en=1, wr_data=0x5A,
        context="simultaneous request at full",
    )

    # Interior simultaneous read/write preserves occupancy and FIFO ordering.
    while tb.model.count < 3:
        await tb.cycle(wr_en=1, wr_data=0x70 + tb.model.count,
                       context="prepare interior simultaneous operation")
    before = tb.model.count
    await tb.cycle(
        wr_en=1, rd_en=1, wr_data=0xC3,
        context="simultaneous read/write in interior",
    )
    assert tb.model.count == before, "interior simultaneous R/W changed count"

    # Repeated accepted writes and reads exercise wraparound traffic.
    while not tb.model.empty:
        await tb.cycle(rd_en=1, context="drain before wraparound sequence")
    for i in range(DEPTH * 4):
        await tb.cycle(
            wr_en=1, wr_data=(0x80 + i) & MASK,
            context="wraparound write traffic",
        )
        if i % 3 != 0:
            await tb.cycle(rd_en=1, context="wraparound read traffic")
    while not tb.model.empty:
        await tb.cycle(rd_en=1, context="final wraparound drain")

    # Repeated boundary attempts and walking data patterns.
    for i in range(4):
        await tb.cycle(rd_en=1, wr_data=0xAA ^ i,
                       context="repeated read while empty")
    for i in range(DEPTH):
        await tb.cycle(wr_en=1, wr_data=(1 << i) & MASK,
                       context="walking-one fill")
    for i in range(4):
        await tb.cycle(wr_en=1, wr_data=(~(1 << i)) & MASK,
                       context="repeated write while full")
    for _ in range(DEPTH):
        await tb.cycle(rd_en=1, context="walking-pattern drain")

    # Directed reset coverage: every occupancy x every enable combination.
    await directed_reset_sweep(tb)

    tb.check_basic_coverage()

    # Emit a machine-readable coverage database and a readable console report.
    coverage_db.report_coverage(dut._log.info, bins=True)
    coverage_db.export_to_yaml("fifo_coverage.yml")
    dut._log.info("Functional coverage exported to fifo_coverage.yml")
    check_coverage_closure()
