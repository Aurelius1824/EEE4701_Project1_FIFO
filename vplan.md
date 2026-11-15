# FIFO Verification Plan -- Project 1

## 1. Objective & Scope

The objective of this project is to verify a design under test (DUT) that the verification team did not write: a synchronous first-word fall-through (FWFT) FIFO. The DUT will be evaluated against its written specification using a layered testbench, constrained-random stimulus, directed scenarios, functional coverage, scoreboard checking, and mutation analysis.

The verification focuses on data ordering, occupancy tracking, status flags, reset behavior, boundary conditions, simultaneous operations, idle behavior, and circular pointer wraparound. The configured instance uses an 8-bit data width and an eight-entry FIFO depth.

The verification environment distinguishes between stimulus reachability (whether a scenario was driven), functional coverage (whether the defined model records the scenario), checking and observability (whether an incorrect response would be detected), and mutation detection (whether an injected implementation fault is detected). A passing simulation, high coverage percentage, or high mutation score is not independently sufficient to establish complete verification.

## 2. DUT Configuration & Specification

| Parameter | Configuration |
|---|---|
| Data width | 8 bits |
| FIFO depth | 8 entries |
| Clock | Synchronous, active on rising edge |
| Reset | Active-low synchronous (`rst_n`) |
| Output mode | First-word fall-through (FWFT) |

The behavioral reference is `Spec/fifo.md`; `Spec/fifo.sv` is the supplied SystemVerilog implementation. Expected behavior must be derived from the written specification, not inferred from implementation details.

The verification focuses on:
- Synchronous reset: on the active rising edge while reset is asserted, occupancy clears, `empty=1`, and `full=0`.
- Write acceptance: a write is accepted when `wr_en=1` and the pre-edge FIFO is not full. A write while full is dropped.
- Read acceptance: a read is accepted when `rd_en=1` and the pre-edge FIFO is not empty. A read while empty is ignored.
- Simultaneous read/write: in a nonempty, nonfull state, one entry is removed and one is added on the same edge; occupancy remains unchanged and ordering is preserved.
- Status flags: `full` is asserted exactly at depth and `empty` exactly at zero.
- Ordering: accepted entries are returned in FIFO order.
- FWFT behavior: `rd_data` presents the oldest entry whenever the FIFO is nonempty.

All four `wr_en`/`rd_en` combinations are legal stimulus. Read-while-empty and write-while-full are legal boundary requests whose effects must be checked, not illegal transactions. The reference model applies acceptance rules using pre-edge occupancy.

## 3. Verification Architecture

The testbench is organized into components with distinct responsibilities. The implementation is in `test_fifo.py`.

**Transaction Generator -- FifoTxn**

The PyVSC `@vsc.randobj` transaction contains randomized `wr_en`, `rd_en`, and `wr_data`, plus a non-random `count` input supplied from the reference model before randomization. The `c_bias()` constraint applies occupancy-dependent distributions:

| Occupancy region | Write enable | Read enable |
|---|---:|---:|
| Near empty (`count <= 1`) | 72% on / 28% off | 42% on / 58% off |
| Near full (`count >= DEPTH-1`) | 42% on / 58% off | 72% on / 28% off |
| Interior | 80% on / 20% off | 80% on / 20% off |

These are intended solver weights, not guaranteed measured frequencies. The actual distribution should be evaluated from run data. Every fourth post-randomization transaction also receives a selected corner-data value from the pattern list.

**Driver -- FifoDriver**

The driver applies `rst_n`, `wr_en`, `rd_en`, and `wr_data` on the falling clock edge so inputs are stable before the active rising edge. It supports randomized and directed transactions, including reset injection during normal operation.

**Monitor -- FifoMonitor**

The monitor samples `count`, `full`, and `empty` and checks that they are resolvable. It checks `rd_data` for resolvability only when the FIFO is nonempty. No value requirement is imposed on `rd_data` while empty because the specification leaves it undefined in that condition.

**Golden Model and Scoreboard -- FifoModel / FifoScoreboard**

The reference model maintains an independent queue of expected entries and applies the specification's acceptance rules using pre-edge state. The scoreboard checks:
- Occupancy is within zero through depth and matches the model.
- `full` and `empty` agree with occupancy and the model.
- The FWFT head matches the oldest model entry whenever nonempty.
- Synchronous reset produces the required empty state.
- State outputs do not change before the active rising edge in response to input changes.

The model is the functional oracle. It must not reproduce implementation-specific pointer arithmetic or internal memory behavior unless that behavior is specified.

**Testbench Coordinator -- FifoTB**

The coordinator initializes the DUT, sequences the driver, updates the reference model, invokes scoreboard checks, samples coverage, tracks visited occupancy values, and runs directed closure sequences. Failures should include cycle and transaction context.

## 4. Functional Coverage Plan

Functional coverage measures whether the testbench exercised selected FIFO states, operations, and corner cases. Coverage is sampled per transaction using the reference model's pre-edge occupancy and the requested operation.

**Occupancy Coverage**

The FIFO has nine legal occupancy values. Exact bins from zero through eight are required. Grouped descriptions (empty, one-entry, interior, one-slot-left, full) may aid reporting but do not replace exact occupancy bins.

**Operation Coverage**

Four operation bins are required: idle, write-only, read-only, and simultaneous read/write. These classify requested enables. A separate accepted-action classification distinguishes requests from operations actually accepted by the FIFO.

**Boundary Coverage**

The model tracks reset, empty-state, full-state, interior-state, read-while-empty, write-while-full, simultaneous-at-empty, simultaneous-at-full, and simultaneous-in-interior conditions. Classification uses pre-edge occupancy. Directed tests separately call out one-entry and near-full simultaneous cases.

**Reset Coverage**

Reset coverage includes initial reset, operational reset from nonempty occupancy, reset with each combination of read/write enables, repeated reset assertion, and post-reset recovery. The directed reset sweep exercises occupancies zero through eight under all four enable combinations. Post-reset checks attempt a read while empty, refill, and drain to ensure stale contents do not reappear.

**Data Coverage**

Data classes include zero, all ones, alternating patterns, MSB-only, LSB-only, and other/random. The pattern list includes `0x00`, `0xFF`, `0xAA`, `0x55`, `0x80`, and `0x01`. Walking-one and walking-zero sequences are directed stimulus; they should not be described as separate coverage bins unless the model explicitly distinguishes them.

**Pointer and Ordering Coverage**

Internal pointers are not treated as externally observable signals. Accepted read/write counts serve as wraparound proxies, while repeated traffic crosses the circular-buffer boundary. Ordering is checked by comparing each valid FWFT head against the reference queue. These proxies do not prove the internal pointer value directly.

**Cross Coverage**

The executable model contains the following crosses:

| Cross | Dimensions | Objective |
|---|---|---|
| `occupancy_x_operation` | Exact occupancy × requested operation | Exercise operations at each meaningful occupancy. |
| `occupancy_x_boundary` | Exact occupancy × boundary classification | Exercise boundary and reset conditions in relevant states. |
| `operation_x_boundary` | Requested operation × boundary classification | Pair boundary requests with their operation. |

Impossible combinations are excluded using documented ignore bins. For example, a full-state boundary cannot occur at occupancy three. The sampler checks that no observed transaction maps to an ignored combination.

The current executable model does not implement every cross proposed in the initial planning discussion. In particular, reset-by-enable and operation-by-data-pattern are not separate implemented crosses. Results must not claim those crosses are closed unless they are implemented and exported.

**Illegal and Ignore Bins**

No read/write enable combination is illegal. Read-while-empty and write-while-full are legal requests. Empty-state `rd_data` is excluded from data comparisons because it is unspecified. Ignore bins are permitted only for impossible or meaningless combinations justified by the classifier or specification; difficult-to-reach legal scenarios must not be ignored merely to improve coverage.

## 5. Feature List

Each feature has a stable identifier used by the test matrix, coverage objectives, and results report. A feature is exercised when its stimulus occurs and checked when the corresponding scoreboard or monitor assertion evaluates the result.

| Feature ID | Feature | Description and expected behavior |
|---|---|---|
| FIFO-01 | Synchronous reset | Active-low reset clears occupancy on the next rising edge and sets `empty=1`, `full=0`; exercised initially and during operation. |
| FIFO-02 | Write acceptance | A write in a nonfull state is accepted and appended to the FIFO in order. |
| FIFO-03 | Full-state write rejection | A write while full is dropped; occupancy and existing contents remain unchanged. |
| FIFO-04 | Read acceptance | A read in a nonempty state removes exactly the oldest entry and updates occupancy. |
| FIFO-05 | Empty-state read rejection | A read while empty is ignored; the FIFO remains empty without underflow. |
| FIFO-06 | Simultaneous read/write | Acceptance follows pre-edge empty/full conditions; in a nonempty, nonfull state both operations occur and occupancy remains unchanged. |
| FIFO-07 | Occupancy and status flags | Count remains from zero through depth; `full` and `empty` match occupancy. |
| FIFO-08 | FIFO ordering and FWFT output | When nonempty, output presents the oldest queued entry; accepted operations preserve FIFO order. |
| FIFO-09 | Data-path integrity | Corner values and walking-bit patterns are stored and returned without corruption. |
| FIFO-10 | Circular progression and idle stability | Repeated accepted traffic crosses the circular-buffer boundary without ordering errors; idle cycles preserve state and valid head data. |

These are externally specified behaviors. The feature list does not imply direct observation of internal pointers or every internal memory location.

## 6. Test Matrix and Requirement Traceability

The current testbench implements these scenarios as directed portions of the single Cocotb test entry point `fifo_test_CRV`. The IDs below are scenario identifiers, not separate Cocotb test functions.

| Test ID | Test scenario | Feature IDs | Stimulus and expected check | Coverage evidence |
|---|---|---|---|---|
| T01 | Initial synchronous reset | FIFO-01, FIFO-07 | Assert reset across rising edges; check count=0, empty=1, full=0. | Reset, occupancy 0, reset action. |
| T02 | Fill from empty to full | FIFO-02, FIFO-07, FIFO-08 | Write distinct values to depth; check acceptance and status transitions. | Occupancy 0..8, write-only, accepted write. |
| T03 | Drain full to empty | FIFO-04, FIFO-07, FIFO-08 | Read until empty; compare each FWFT head with queue order. | Occupancy 8..0, read-only, accepted read. |
| T04 | Write while full | FIFO-03, FIFO-07, FIFO-08 | Assert write while full; verify no count or stored-data change. | Full-state/write-while-full boundary. |
| T05 | Read while empty | FIFO-05, FIFO-07 | Assert read while empty; verify count and flags remain empty. | Empty-state/read-while-empty boundary. |
| T06 | Simultaneous read/write in interior | FIFO-06, FIFO-07, FIFO-08 | Assert both enables at interior occupancy; check count preservation and head advancement. | Simultaneous operation/interior boundary. |
| T07 | Simultaneous read/write at empty and full | FIFO-03 through FIFO-06 | At empty, write may be accepted and read ignored; at full, read may be accepted and write dropped. | Simultaneous-at-empty/full. |
| T08 | Simultaneous read/write at one entry | FIFO-06, FIFO-08 | At occupancy one, consume old head and verify new write becomes next head. | Occupancy one/simultaneous operation. |
| T09 | Repeated pointer-wrap traffic | FIFO-08, FIFO-09, FIFO-10 | Repeat accepted writes/reads across multiple rotations; compare visible data. | Read/write wrap proxies and operation coverage. |
| T10 | Idle hold at each occupancy | FIFO-07, FIFO-08, FIFO-10 | Apply no requests at each occupancy; check count, flags, and valid head stability. | Idle operation across occupancy bins. |
| T11 | Directed data patterns | FIFO-08, FIFO-09 | Write/read corner values and walking-bit patterns; compare returned values. | Data-pattern coverpoint and accepted actions. |
| T12 | Operational reset with active enables | FIFO-01, FIFO-07, FIFO-08 | Assert reset at occupancy states with idle, write-only, read-only, and simultaneous requests; check reset and recovery. | Reset boundary and operation classification. |
| T13 | Constrained-random interleaving | FIFO-01 through FIFO-10 | Run seeded transactions using model occupancy; scoreboard checks each cycle. | Occupancy, operation, boundary, data, action, and crosses. |
| T14 | Directed coverage-closure sweep | FIFO-01 through FIFO-10 | Visit all occupancy values, close legal bins, run reset sweep and recovery checks. | Final coverage export and closure assertions. |

The test function contains an initial reset, a configured 1,200-iteration constrained-random loop, and subsequent directed closure scenarios. Two reset-injection points can replace a random transaction when occupancy is nonzero; therefore, describe this as 1,200 configured loop iterations, not necessarily 1,200 randomized transactions. Directed scenarios run in addition to the loop.

Traceability is bidirectional: every feature appears in at least one test row, and every test row identifies the feature or features it exercises. Where a feature has no dedicated coverage bin, cite the directed scenario and scoreboard check rather than implying the coverage database proves it.

## 7. Constrained-Random Verification Strategy

The constrained-random phase explores combinations of read enable, write enable, and write data under changing occupancy. Before randomization, the testbench supplies the reference model's current occupancy. The driver applies the generated transaction on the falling edge for evaluation on the following rising edge.

| Item | Current configuration |
|---|---|
| Width | 8 bits |
| Depth | 8 entries |
| Seed | `0xCAFEF00D` |
| Configured loop iterations | 1,200 |
| Cocotb entry point | `fifo_test_CRV` |

The earlier seed `0xDEADBEEF` appears in initial planning material but is not the active seed in the current `test_fifo.py`. The executable source and reported run configuration must agree. A regression record should capture source revision, simulator, command, seed, parameters, and coverage export.

The `c_bias()` weights are intended to favor filling near empty, draining near full, and enabling both operations more often in the interior. They are solver weights, not measured percentages. A histogram of actual generated operations by occupancy region is needed before claiming that the distribution behaves as intended.

Directed stimulus remains necessary because randomization does not guarantee specific sequences. Reset at a chosen occupancy, repeated pointer-wrap traffic, and walking-bit sweeps are more efficiently and deterministically generated by directed tasks.

## 8. Coverage Model

The executable cocotb-coverage model in `test_fifo.py` contains eight individual coverpoints:

| Coverpoint | Bins | Meaning |
|---|---:|---|
| `fifo.occupancy` | 9 | Exact pre-edge occupancy, 0 through 8. |
| `fifo.operation` | 4 | Idle, write-only, read-only, simultaneous. |
| `fifo.boundary` | 9 | Reset, state classifications, and boundary requests. |
| `fifo.data_pattern` | 7 | Zero, all ones, alternating, MSB-only, LSB-only, other. |
| `fifo.accepted_action` | 5 | None, write, read, read-and-write, reset. |
| `fifo.reset` | 2 | Reset asserted or deasserted. |
| `fifo.write_wrap_proxy` | 2 | Accepted writes reached the depth threshold or not. |
| `fifo.read_wrap_proxy` | 2 | Accepted reads reached the depth threshold or not. |

The model also contains three crosses: occupancy × operation (36 bins), occupancy × boundary (29 legal bins after exclusions), and operation × boundary (16 legal bins after exclusions). The resulting defined model contains 121 bins. The initial model reported 111/193 (57.51%); analysis identified 72 impossible cross combinations and 10 reset-related holes. The exclusions reduced the cross denominator, and the directed reset sweep exercised reset scenarios. The final exported result is reported as 121/121 (100%).

This percentage applies only to the implemented model. It does not mean that all possible FIFO behavior, every feature proposed in the initial planning discussion, or all possible implementation faults have been verified. Reset-by-enable and operation-by-data-pattern are not separate crosses in the current model, and pointer wrap is represented by accepted-operation proxies rather than direct pointer observation. These qualifications must remain in the results report.

Coverage uses pre-edge occupancy because full/empty requests are evaluated against the state before the active edge. The sampler checks that no observed sample maps to an ignored bin, helping prevent exclusions from concealing a classification error.

## 9. Risk and Spec Ambiguity

The written FIFO specification is the authority for expected behavior. Where it does not define behavior, the testbench must not invent a pass/fail requirement. The specification leaves `rd_data` undefined while empty; accordingly, the monitor and scoreboard do not require a particular empty-state value and do not compare it against the model.

The specification describes simultaneous read and write in a nonempty, nonfull state, while the testbench also exercises simultaneous requests at empty and full. The reference model applies the individual acceptance rules using pre-edge state: at empty, the write may be accepted and the read is ignored; at full, the read may be accepted and the write is dropped. If the course specification or instructor defines a different priority for these boundary combinations, that clarification must supersede this interpretation and the model must be updated.

Reset is active-low and synchronous. Assertion between rising edges must not be treated as immediate state clearing. The scoreboard checks state before and after the active edge to distinguish synchronous behavior from unintended asynchronous changes. The specification does not define reset-domain crossing, metastability, or physical reset timing.

The interface exposes occupancy, flags, and FWFT data, but not internal pointers or individual memory locations. Wraparound coverage is therefore proxy-based. A pointer fault that does not affect visible head data, flags, or count during the tested sequence may escape detection. Similarly, corruption of an unoccupied memory location may remain hidden if that location is overwritten before it reaches the read pointer.

The verification plan does NOT verify internal pointer values, physical memory-cell integrity, RAM inference quality, timing closure, maximum operating frequency, power, area, metastability, reset-domain crossing, or behavior outside the specified parameter configuration. It does not establish correctness for arbitrary WIDTH and DEPTH values merely because the RTL is parameterized; the current testbench configures WIDTH=8 and DEPTH=8. It does not require a value for `rd_data` when empty, and it cannot classify unspecified behavior as a design failure. It also does not prove the absence of all possible defects: mutation testing evaluates only the supplied mutant population, while functional coverage measures only bins explicitly represented in the model.

Risk treatment depends on reachability and observability. If a fault is not reached, add a directed or constrained-random scenario that drives the relevant state. If a fault is reached but not observed, strengthen the checker only when the written contract provides an observable expected result. Internal probes may improve diagnosis but must be distinguished from interface-level requirements.

## 10. Closure Criteria

Coverage closure is measured by running the regression, inspecting the exported coverage database, classifying uncovered bins, and determining whether each bin is reachable and meaningful. A missing legal bin requires additional stimulus or a documented limitation. An impossible bin may be excluded only with a reason tied to the classifier or specification. A difficult-to-reach legal scenario must not be ignored merely to increase the percentage.

The verification effort is considered functionally closed for this configuration when all of the following are satisfied:

1. **Execution:** the prescribed test command completes without simulator errors or unhandled testbench exceptions.
2. **Scoreboard:** all pre-edge and post-edge checks pass for count, full, empty, reset response, and valid FWFT head data.
3. **Occupancy:** all nine exact occupancy values are visited.
4. **Operations:** idle, write-only, read-only, and simultaneous requests are observed.
5. **Boundaries:** read-while-empty, write-while-full, simultaneous-at-empty, simultaneous-at-full, and simultaneous-in-interior scenarios execute and their specified effects are checked.
6. **Reset:** initial and operational reset are exercised; the directed sweep covers every occupancy under all four enable combinations, and post-reset integrity checks pass.
7. **Data and ordering:** representative patterns are written and read back in order; directed walking-bit sequences complete without mismatch.
8. **Wraparound:** repeated accepted reads and writes cross the circular-buffer boundary, with ordering checked through the reference queue. Wrap coverage is described as proxy-based.
9. **Functional coverage:** all bins in the defined 121-bin model are hit or justified as impossible and excluded; the final export and dashboard are retained.
10. **Reproducibility:** seed, parameters, simulator, command, and source revision are recorded. The active source seed is `0xCAFEF00D`.
11. **Mutation analysis:** released and hidden results are reported from actual runs, with survivors and residual fault classes distinguished. A 100% mutation score is not proof of complete correctness.
12. **Documentation:** the plan, coverage analysis, findings, report, AI usage record, and team contributions agree with the checked-in implementation and run evidence.

Coverage closure and mutation closure are separate sign-off items. The 121/121 result demonstrates that the defined model's bins were exercised; mutation results demonstrate detection of mutants in the stated pools. Neither replaces cycle-by-cycle scoreboard checking or resolves the limitations above.

## 11. Mutation Testing and Verification Effectiveness

Mutation testing assesses whether the testbench detects representative implementation faults. The team records the mutation pool, number found, total number, command, and findings. The project findings record 8/8 released practice mutants and 20/20 hidden mutants as detected. These scores describe only the tested pools.

Each mutation should be analyzed for stimulus reachability and output observability. A mutant that is never activated indicates a stimulus-reachability gap. A mutant that is activated but whose effect is not checked indicates a checking or observability gap. The former calls for more stimulus; the latter calls for a stronger check supported by the specification.

Residual risks involving undefined empty-state output or internal memory corruption are fault classes the current testbench may not detect. They should not be described as surviving mutants when all mutants in the recorded pools were detected.

## 12. Regression and Sign-Off

The final verification environment is ready for sign-off when the closure criteria in Section 10 are satisfied and evidence is preserved. The regression record should include the command, source revision, seed, parameter values, simulator version, test result, coverage export, and mutation findings. If any item changes, results must be regenerated or clearly labeled as belonging to an earlier revision.

### Final Deliverables for Project 1

| Deliverable | Description |
|---|---|
| `vplan.md` | Verification plan, feature list, test matrix, coverage model, risks, and closure criteria. |
| Testbench sources | Driver, monitor, reference model, scoreboard, transaction generation, and directed/random stimulus. |
| Coverage model and exports | Functional coverage implementation, YAML exports, and dashboard evidence. |
| `FINDINGS.md` | Mutation scores, analysis, and residual fault classes. |
| `REPORT.pdf` | Project report with results and limitations. |
| Demo link | Demonstration of the verification environment and evidence. |
| `ai_log.md` | AI prompts, predictions, measured outcomes, and corrections, as applicable. |
| `CONTRIBUTIONS.md` | Individual team contributions. |

## 13. Verification Conclusion

This plan defines an interface-level verification strategy for the configured 8-bit, depth-8 synchronous FWFT FIFO. It combines directed corner-case sequences, occupancy-aware constrained-random stimulus, an independent queue model, cycle-level scoreboard checking, functional coverage, and mutation analysis. The feature list and test matrix provide traceability from specified behavior to stimulus and checking, while the coverage and risk sections distinguish measured results from unverified assumptions.

The final verification argument must be supported by reproducible simulation results, coverage exports, mutation findings, and a clear statement of what remains outside the plan's scope. A successful result means the specified and observable behaviors in this configuration passed the defined checks; it is not a claim that every internal implementation fault or every possible parameterization has been proven correct.
