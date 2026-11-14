# Synchronous FIFO Verification

A Cocotb-based verification environment for a parameterized,
synchronous, first-word fall-through (FWFT) FIFO, developed for **EEE
4701/5703 Project 1: Constrained-Random Verification of a FIFO**.

The testbench combines directed corner-case testing, seeded
constrained-random stimulus, a queue-based reference model, a
scoreboard, functional coverage, and mutation testing.

## Demo

**YouTube demonstration:** \[https://youtu.be/MsMpQS5B_8A]

## Design Under Test

  Parameter / Signal   Configuration
  -------------------- -----------------------------------
  Data width           8 bits
  FIFO depth           8 entries
  Reset                Active-low, synchronous (`rst_n`)
  Clocking             Rising-edge triggered
  Data behavior        First-word fall-through (FWFT)

The FIFO contract is documented in [Spec/fifo.md](Spec/fifo.md), with
the SystemVerilog implementation in [Spec/fifo.sv](Spec/fifo.sv).

The testbench checks FIFO ordering and FWFT head data, occupancy and
status flags, synchronous reset, dropped writes while full, ignored
reads while empty, simultaneous read/write behavior, idle behavior, data
patterns, and pointer-wraparound sequences.

## Verification Architecture

The primary testbench is [test_fifo.py](test_fifo.py).

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  `FifoTxn`                           Uses PyVSC to generate
                                      constrained-random write enable,
                                      read enable, and write data.

  `FifoDriver`                        Drives inputs on the falling clock
                                      edge, before the active rising
                                      edge.

  `FifoMonitor`                       Samples observable outputs and
                                      checks signal resolvability.

  `FifoModel`                         Maintains an independent
                                      queue-based model of expected FIFO
                                      state.

  `FifoScoreboard`                    Compares DUT occupancy, status
                                      flags, and valid FWFT head data
                                      against the reference model.

  Functional coverage                 Tracks occupancy, operation,
                                      boundary, data-pattern,
                                      accepted-action, reset, and
                                      wraparound-proxy coverage.
  -----------------------------------------------------------------------

Read data is compared only when the FIFO is non-empty, consistent with
the specification that `rd_data` is valid when `!empty`.

## Stimulus and Test Scenarios

The Cocotb entry point is `fifo_test_CRV`. It combines directed
scenarios and constrained-random traffic in one test.

### Constrained-random phase

-   Random seed: `0xCAFEF00D`
-   Configured random iterations: `1,200`
-   Randomized fields: `wr_en`, `rd_en`, and `wr_data`
-   Current FIFO occupancy is supplied to the transaction before
    randomization.
-   Data-pattern injection supplements randomized payloads.

The transaction constraints define different enable distributions for
near-empty, near-full, and intermediate occupancy states. The seed makes
the Python random sequence reproducible for a fixed testbench and
simulator environment.

### Directed scenarios

The test explicitly exercises: - Traversal of all occupancy levels from
empty through full. - Idle holds at each occupancy. - Read requests
while empty and write requests while full. - Simultaneous read/write at
empty, full, and interior occupancy. - Repeated read/write activity to
exercise circular-buffer wraparound. - Representative data patterns,
including zero, all ones, alternating bits, and walking-bit sequences. -
Operational reset with enables asserted. - Reset across occupancy levels
and read/write-enable combinations, followed by post-reset integrity
checks.

## Functional Coverage Results

The coverage model samples each transaction using the **pre-edge
reference-model occupancy** and request signals.

  Coverage result           Value
  -------------------- ----------
  Covered bins                121
  Total modeled bins          121
  Reported coverage      **100%**

The model includes individual coverpoints and crosses for occupancy ×
operation, occupancy × boundary, and operation × boundary. Combinations
that cannot occur by construction are excluded using justified ignore
bins. A directed reset sweep closes the remaining reset-related coverage
holes.

Coverage artifacts and analysis are available in: -
[Coverage.md](Coverage.md) --- coverage model, uncovered-bin analysis,
closure actions, and caveats. -
[CoverageModel_Visuals/C1](CoverageModel_Visuals/C1) --- initial
coverage export and dashboard. -
[CoverageModel_Visuals/C2_BinClosure](CoverageModel_Visuals/C2_BinClosure)
--- post-closure coverage export and dashboard.

**Interpretation:** 100% refers to the bins in this defined functional
coverage model. It does not prove that every possible implementation
fault has been detected.

## Mutation Testing

Mutation testing evaluates whether the testbench detects intentional
faults in the FIFO implementation. The results recorded in
[FINDINGS.md](FINDINGS.md) are:

  Mutation pool                            Detected   Total   Score
  -------------------------------------- ---------- ------- -------
  Released practice pool                          8       8    100%
  Hidden pool (as reported at grading)           20      20    100%

The findings document describes testbench improvements and residual
fault classes that may not be observable through the specified FIFO
interface.

## Repository Contents

  ----------------------------------------------------------------------------
  Path                                     Description
  ---------------------------------------- -----------------------------------
  `test_fifo.py`                           Cocotb testbench, constraints,
                                           driver, monitor, scoreboard,
                                           directed sequences, and coverage
                                           collection.

  `Spec/fifo.md`                           FIFO behavioral specification.

  `Spec/fifo.sv`                           SystemVerilog FIFO design.

  `vplan.md`                               Verification plan, feature
                                           objectives, test matrix, and
                                           coverage strategy.

  `Coverage.md`                            Functional coverage analysis and
                                           closure documentation.

  `CoverageModel_Visuals/C1/`              Initial coverage YAML export and
                                           dashboard.

  `CoverageModel_Visuals/C2_BinClosure/`   Coverage export and dashboard after
                                           closure.

  `FINDINGS.md`                            Mutation results, testbench
                                           improvements, and residual risks.

  `HW5_Findings/`                          Historical findings from the HW5
                                           baseline.

  `CONTRIBUTIONS.md`                       Team contribution summary.

  `ai_log.md`                              Documented AI assistance for the
                                           coverage analysis.
  ----------------------------------------------------------------------------

## Running the Verification

The repository documents these course-harness commands:

``` bash
just test fifo_crv icarus
just mutate fifo_crv
```

These commands assume the course-provided simulation and
mutation-testing environment, including its Justfile targets and
required dependencies. The repository does not include every
course-harness or simulator setup file needed to run the commands
independently.

The testbench uses Cocotb, PyVSC, and cocotb-coverage, together with the
course simulator setup. Use the simulator and dependency versions
specified by the course environment when reproducing the recorded
results.

## Project Documentation

-   [Verification Plan](vplan.md)
-   [Coverage Analysis](Coverage.md)
-   [Mutation Findings](FINDINGS.md)
-   [Team Contributions](CONTRIBUTIONS.md)
-   [AI Usage Log](ai_log.md)

## Team

See [CONTRIBUTIONS.md](CONTRIBUTIONS.md) for the recorded team
responsibilities and contributions.
