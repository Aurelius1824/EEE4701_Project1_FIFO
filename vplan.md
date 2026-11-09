# FIFO Verification Plan -- Project 1

## 1. Objective & Scope
The objective of this project is the verification of a DUT that we did not write, in this case, a synchronous FIFO. We are to verify this DUT against it's written spec using a layered testbench, constrained-random stimuli, functional coverage, and mutation observation optimization

The verification will focus on data ordering, occupany tracking, status flags, reset behavior, boundary conditions, simultaneous operations, and pointer wraparound.

The verification environement will distinguish between:
* Stimulus Reachability: Whether a scenario was driven.
* Functional Coverage: Whether the planned feature or cross was observed.
* Checking and Observabaility: Whether incorrect DUT behaviour would be detected.
* Mutation Detection: Whether the testbench detects injected design faults.

The team will no treat passing simulation or a high mutant detection score alone as proof of complete verification.

---

## 2. DUT Configuration & Specification
Parameter   | Configuration
===========================
Data Width  | 8 bits 
FIFO Depth  | 8 Entries
Clk         | Synchronous clock
RST         | Active-Low (RST_N)
Output mode | FWFT

The verification effort focuses on the following behavioral properties:
* Correct synchronous reset operation.
* Correct write and read acceptance conditions.
* Prevention of overflow and underflow.
* Accurate occupancy tracking and status flags.
* Correct simultaneous read/write behavior.
* Preservation of FIFO data ordering.
* Correct FWFT head-data presentation.
* Proper pointer progression and wraparound.
* Stability of FIFO state during idle operation.

Verification will combine constrained-random stimulus with directed corner-case sequences. Functional coverage and mutation testing will provide quantitative evidence of stimulus completeness and verification effectiveness.

The goal is not simply to demonstrate that the DUT passes simulation, but to demonstrate that the verification environment systematically exercises the specified behaviors and detects representative design faults.

## 3. Verification Architecture
The existing HW5 testbench is organized into separate verification components. Project 1 will retain this architecture and formalize the responsibilities of each component.

**Transaction Generator -- FifoTxn**
Implementation: @vsc.randobj constrained-random transaction class.

The transaction generator produces:
* wr_en: Randomized write enable.
* rd_en: Randomized read enable.
* wr_data: Randomized write data.
* count: Non-random occupancy input used to shape the distribution.

The occupancy-dependent constraint function c_bias() applies different probability distributions depending on the FIFO occupancy.

| Occupancy region | Write enable distribution | Read enable distribution |
|---|---|---|
| Near empty (`count <= 1`) | 72% enabled / 28% disabled | 42% enabled / 58% disabled |
| Near full (`count >= DEPTH-1`) | 42% enabled / 58% disabled | 72% enabled / 28% disabled |
| Interior occupancy | 80% enabled / 20% disabled | 80% enabled / 20% disabled |

These weights encourage filling near empty, draining near full, and simultaneous read/write activity in the interior.

The generator also injects representative corner-data patterns periodically, including all-zero, all-one, alternating-bit, and selected boundary-bit patterns.

All combinations of read and write enables are legal under the FIFO specification. Boundary requests are intentionally generated to verify their specified acceptance or rejection behavior.

**Driver -- FifoDriver**
The driver is responsible for applying input transactions to the DUT.

Responsibilities:
* Drive rst_n, wr_en, rd_en, and wr_data.
* Apply input changes on the falling clock edge.
* Maintain stable inputs around the active rising clock edge.
* Support reset injection during normal operation.
* Provide both randomized and directed transactions.

Driving inputs on the falling edge allows the DUT to sample stable inputs on the next rising edge.

**Monitor -- FifoMonitor**
The monitor samples the observable DUT outputs and returns them to the scoreboard.

Signals monitored:
* count
* full
* empty
* rd_data, when nonempty

The monitor checks that required status outputs are resolvable and that rd_data is resolvable whenever the FIFO is nonempty.

The monitor does not impose validity requirements on rd_data when empty because the specification leaves that output undefined in this condition.

**Golden Model & Scoreboard -- FifoModel / FifoScoreboard**
The scoreboard compares the observed DUT behavior against an independent golden model.

The reference model maintains the expected FIFO state and data ordering. Its behavior must follow the written specification rather than assumptions derived from the DUT implementation.

The scoreboard verifies:
- Occupancy matches the reference model.
- full matches the expected full condition.
- empty matches the expected empty condition.
- FWFT head data matches the expected oldest FIFO entry whenever nonempty.
- Occupancy remains within the legal range.
- Full and empty flags remain consistent with occupancy.
- Reset produces the required empty state.
- Input changes before the active clock edge do not cause unintended combinational changes to registered FIFO state outputs.

**Testbench Coordinator -- FifoTB**
Testbench Coordinator — FifoTB

The top-level testbench coordinates the driver, monitor, reference model, scoreboard, and coverage collection.

Responsibilities:
* Initialize and reset the DUT.
* Generate and execute transactions.
* Update the reference model.
* Invoke scoreboard comparisons.
* Record functional coverage.
* Track stimulus reachability.
* Execute directed coverage-closure sequences.
* Report failed checks with cycle and transaction context.

---

## 4. Functional Coverage Plan
Functional coverage will demonstrate that the verification environment has exercised the relevant FIFO states, operations, and corner cases.

The existing HW5 implementation already tracks occupancy and several important stimulus conditions through manual coverage indicators. 

**Occupancy Coverage**
The FIFO has nine possible occupancy values.

| Bin | Condition |
|---|---|
| EMPTY | count = 0 |
| ONE_ENTRY | count = 1 |
| INTERIOR | count = 2 through 6 |
| ONE_SLOT_LEFT | count = 7 |
| FULL | count = 8 |

An additional exact-occupancy coverpoint will distinguish all values from 0 through 8.

**Coverage objective:** Exercise every legal occupancy state.

**Operation Coverage**
| Bin | Condition |
|---|---|
| IDLE | `wr_en=0`, `rd_en=0` |
| WRITE_ONLY | `wr_en=1`, `rd_en=0` |
| READ_ONLY | `wr_en=0`, `rd_en=1` |
| SIMULTANEOUS_RW | `wr_en=1`, `rd_en=1` |

**Coverage objective:** Exercise all four input-enable combinations.

**Boundary Coverage**
The following conditions will be tracked independently:

| Coverage bin | Condition |
|---|---|
| READ_WHILE_EMPTY | `rd_en=1`, pre-count=0 |
| WRITE_WHILE_FULL | `wr_en=1`, pre-count=DEPTH |
| SIM_RW_EMPTY | `wr_en=1`, `rd_en=1`, pre-count=0 |
| SIM_RW_FULL | `wr_en=1`, `rd_en=1`, pre-count=DEPTH |
| SIM_RW_ONE | Both enables asserted, pre-count=1 |
| SIM_RW_INTERIOR | Both enables asserted, pre-count=2 through 6 |
| SIM_RW_NEAR_FULL | Both enables asserted, pre-count=7 |

**Coverage objective:** Exercise read/write acceptance and rejection behavior at critical occupancy boundaries.

**Reset Coverage**
Reset coverage will include:
- Initial reset.
- Reset from nonempty occupancy.
- Reset while read and write enables are asserted.
- Recovery after reset.
- Correct count, full, and empty values following reset.

The reset operation will be checked at the active rising clock edge, consistent with the synchronous reset specification.

**Data Coverage**
Representative data patterns will include:

| Pattern | Purpose |
|---|---|
| `0x00` | All-zero data |
| `0xFF` | All-one data |
| `0xAA` | Alternating bits |
| `0x55` | Complementary alternating bits |
| Walking one | Detect individual bit-path faults |
| Walking zero | Detect stuck-at-one and masking faults |
| Random data | Exercise varied payload combinations |

The data coverage model will track the occurrence of each pattern class.

**Pointer and Ordering Coverage**
Pointer wraparound will be exercised through repeated fill, drain, and simultaneous read/write operations.

The verification environment will check:
- Repeated write-pointer wraparound.
- Repeated read-pointer wraparound.
- FIFO ordering across pointer boundaries.
- Data integrity during simultaneous operations.
- Preservation of data during rejected operations and idle cycles.

The current scoreboard verifies ordering through the FWFT head comparison. Explicit pointer wrap coverage will be added to the coverage collector using observable operation sequences rather than assuming access to internal DUT pointers.

**Cross Coverage**
The following crosses are prioritized:

| Cross | Dimensions | Verification objective |
|---|---|---|
| COV-01 | Occupancy × Operation | Verify each operation at different occupancy states |
| COV-02 | Occupancy × Simultaneous R/W | Verify simultaneous-operation behavior at boundaries and interior states |
| COV-03 | Occupancy × Boundary Attempt | Verify read-while-empty and write-while-full behavior |
| COV-04 | Reset × Operation Enables | Exercise reset with idle and active enables |
| COV-05 | Operation × Data Pattern | Exercise data-path patterns under different operations |

Crosses will be constructed with appropriate exclusions or ignore bins for combinations that cannot occur or are not meaningful.

The team will not use arbitrary cross-coverage combinations that inflate the coverage denominator without adding verification value.

**Illegal and Ignore Bins**

The FIFO specification permits all four combinations of `wr_en` and `rd_en`. Therefore, none of those combinations will be classified as illegal stimulus.

Read-while-empty and write-while-full are legal requests with specified ignored/dropped behavior, not illegal transactions.

Undefined empty-state `rd_data` observations will be excluded from data comparisons.

Any additional ignore bins must be justified by the written specification.

---

## 5. Test Matrix and Requirement Traceability
The following matrix maps planned verification tests to the specification requirements and functional coverage objectives.

| Test ID | Test scenario | Specification requirements | Coverage objectives |
|---|---|---|---|
| T01 | Initial synchronous reset | FIFO-01, FIFO-07 | Reset, empty occupancy |
| T02 | Fill FIFO from empty to full | FIFO-02, FIFO-07 | Exact occupancy, WRITE_ONLY |
| T03 | Drain FIFO from full to empty | FIFO-04, FIFO-07, FIFO-09 | Exact occupancy, READ_ONLY |
| T04 | Write while full | FIFO-03 | WRITE_WHILE_FULL |
| T05 | Read while empty | FIFO-05 | READ_WHILE_EMPTY |
| T06 | Simultaneous read/write in interior | FIFO-06 | SIMULTANEOUS_RW, interior occupancy |
| T07 | Simultaneous read/write at empty and full | FIFO-02–FIFO-06 | SIM_RW_EMPTY, SIM_RW_FULL |
| T08 | Simultaneous read/write at one entry | FIFO-06, FIFO-08 | SIM_RW_ONE, ordering |
| T09 | Repeated pointer wraparound | FIFO-08, FIFO-10 | Pointer wrap, ordering |
| T10 | Idle-hold behavior | FIFO-02, FIFO-04, FIFO-08 | IDLE × occupancy |
| T11 | Directed data-pattern sequences | FIFO-08, FIFO-09 | Data-pattern coverage |
| T12 | Operational reset with active enables | FIFO-01 | Reset × operation enables |
| T13 | Constrained-random interleaving | FIFO-02–FIFO-10 | Occupancy, operation, and cross coverage |
| T14 | Final directed coverage sweep | FIFO-01–FIFO-10 | Missing-bin closure |

Each test will be associated with the corresponding scoreboard checks and coverage bins.

---

## 6. Constrained-Random Verification Strategy

**Randomization Approach**
The verification environment uses occupancy-dependent constraints to increase the likelihood of exercising boundary conditions and simultaneous operations.

The randomized transaction contains:
- Read enable.
- Write enable.
- Write data.
- Current FIFO occupancy as a non-random constraint input.

The occupancy is updated from the reference model before each transaction is randomized.

**Randomization Distribution**
The constraint distribution is intentionally nonuniform.

Near empty, write operations receive a higher probability to encourage filling.

Near full, read operations receive a higher probability to encourage draining.

In the interior, both enables receive higher probabilities to increase simultaneous operation frequency.

A fixed seed, DEADBEEF, is used to make the randomized sequence reproducible.

**Directed Coverage Closure**
The existing HW5 implementation supplements randomized stimulus with directed sequences.

These include:
- Occupancy adjustment through directed fill and drain.
- Idle-hold checks at each occupancy.
- Repeated simultaneous read/write operations.
- Walking-one and walking-zero data sequences.
- Repeated read-while-empty and write-while-full attempts.
- Uninterrupted FIFO fill and drain sequences.

These sequences are retained because they guarantee exercise of important boundary and pointer-transition conditions.

The team will document which coverage holes were closed through constraint adjustments and which required directed sequences.

**Reproducibility**
The regression will record:
- Random seed.
- Number of randomized cycles.
- FIFO parameter configuration.
- Simulator and test command.
- Coverage results.
- Mutation results.

The current HW5 baseline uses seed `0xDEADBEEF` and 1,200 constrained-random cycles before the directed closure phase.

---

## 7. Coverage Closure and Convergence Criteria
Coverage closure will be performed through measured iteration rather than assuming that a sufficiently long random run automatically exercises every relevant scenario.

The process is:
1. Run the seeded constrained-random regression.
2. Collect occupancy and operation coverage.
3. Identify missing bins and crosses.
4. Determine whether missing coverage is caused by insufficient stimulus probability, an unreachable combination, or a missing directed sequence.
5. Modify constraints or add a justified directed sequence.
6. Re-run the regression.
7. Verify that the targeted coverage bins have been reached.
8. Confirm that scoreboard checks still pass.
9. Repeat from step 5 as needed
10. Preserve the final regression configuration and results.

**Coverage Closure Criteria**
| Metric | Closure criterion |
|---|---|
| Occupancy | All nine occupancy values observed |
| Operation | All four read/write enable combinations observed |
| Boundary attempts | Read-while-empty and write-while-full observed |
| Simultaneous operations | Empty, one-entry, interior, near-full, and full cases observed |
| Reset | Initial and operational reset scenarios exercised |
| Data patterns | All planned representative patterns observed |
| Pointer wrap | Read and write pointer wrap sequences exercised |
| Scoreboard | No unexplained mismatches |
| Cross coverage | All required, reachable bins covered or explicitly justified |

Coverage closure will be reported alongside the model definition and documented exclusions.

---

## 8. Mutation Testing and Verification Effectiveness
Mutation testing will be used to assess whether the verification environment detects representative FIFO implementation faults.

The team will execute the prescribed mutation command against the released mutant pool and record the resulting found/total score.

The previous HW5 baseline achieved:
- Released mutants: 8/8 found.
- Hidden mutants: 12/12 found.

These values are historical HW5 results and will not automatically be presented as Project 1 results until the corresponding Project 1 gradescopr submission has been executed.

**Mutation Analysis**
Mutation findings will be categorized by:
- Fault type.
- Stimulus reachability.
- Output observability.
- Scoreboard detection.
- Relevant coverage bins.

**Residual Risk**

A high mutation score does not establish that every possible FIFO fault can be detected.

Known limitations include:
1. **Unoccupied memory corruption:** A fault that corrupts an unoccupied internal memory location may remain undetected if the corrupted location is overwritten before becoming the FIFO head.

2. **Undefined empty-state output:** The specification does not define `rd_data` when empty. Therefore, incorrect behavior confined to this condition cannot be classified as a specification violation by the current scoreboard.

3. **Unmodeled internal implementation faults:** Faults that do not propagate to an observable output may remain undetected without additional observability or assertions.

The final findings report will distinguish between stimulus reachability gaps and output observability gaps.

---

## 9. Regression and Sign-Off
The final verification environment will be considered ready for sign-off when the following conditions are satisfied:

- The complete testbench executes successfully.
- All required scoreboard comparisons pass.
- Every specified FIFO occupancy state is exercised.
- All required operation and boundary scenarios are exercised.
- The functional coverage model is implemented and its report is generated.
- Required cross-coverage targets are reached or justified.
- Constrained-random stimulus is reproducible.
- The prescribed mutation regression is executed.
- Mutation findings and residual risks are documented.
- All team deliverables are completed.


### Final Deliverables for Project 1
| Deliverable | Description |
|---|---|
| `vplan.md` | Verification plan and requirement traceability |
| `tb/` | Driver, monitor, scoreboard, and reference model |
| `crv/` | Transaction generation, constraints, and seeded regression |
| Coverage model/report | Functional coverage implementation and results |
| `FINDINGS.md` | Mutation score, survivor analysis, and residual risks |
| `REPORT.pdf` | 4–6 page project report |
| Demo link | Demonstration of the verification environment and evidence |
| `ai_log.md` | AI prompts, predictions, measured outcomes, and fixes |
| `CONTRIBUTIONS.md` | Individual team contributions |

All verification results will be reported with their corresponding configuration and execution evidence.

---

## 10. Verification Conclusion
The existing HW5 implementation provides the foundation for the Project 1 verification environment, Project 1 acts as student's chance to provide full-ownership in regard to a verification project. It already demonstrates constrained-random stimulus generation, occupancy-dependent biasing, reference-model checking, directed boundary testing, and successful detection of the previously evaluated mutant pool.

Project 1 extends this foundation by formalizing the verification plan, establishing requirement traceability, implementing a functional coverage model, documenting coverage closure, and producing a team-level verification report.

The final verification argument will be supported by simulation results, coverage evidence, reproducible regressions, and mutation analysis.