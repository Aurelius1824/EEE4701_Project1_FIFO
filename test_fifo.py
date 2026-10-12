"""STUDENT STARTER -- Week 4 FIFO testbench.

Build a driver / monitor / scoreboard testbench around the FWFT FIFO. Use the
golden model (models.fifo_model.FifoModel) as your scoreboard and check count,
full, empty, and rd_data *every* cycle. Hit the corners: fill to full, drain to
empty, write-while-full (dropped), read-while-empty (ignored), simultaneous
read+write, and pointer wrap.

Run:            make                # (or make SIM=icarus)
Score:          cd code && just mutate fifo        # found/total (released pool)

Right now this only does three writes and one weak check -- raise the found/total.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from models.fifo_model import FifoModel


@cocotb.test()
async def test_smoke(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wr_data.value = 0
    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)

    for i in range(3):
        dut.wr_en.value = 1
        dut.wr_data.value = 0x40 + i
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
    dut.wr_en.value = 0
    assert int(dut.count.value) == 3, f"count={int(dut.count.value)}"
    # TODO: read the values back and check rd_data order against a FifoModel;
    # TODO: add full/empty corners, simultaneous read+write, and wrap-around.
