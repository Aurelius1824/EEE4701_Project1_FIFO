# Coverage Model: holes that appeared and how we closed each one

Evidence: `CoverageModel_Visuals/C1` (before) and `C2_BinClosure` (after), both exported by `test_fifo.py` through cocotb-coverage (`fifo_coverage.yml`). DUT: 8-bit, depth-8 FWFT FIFO, active-low synchronous reset.

## 1. Model
Sampled once per clock cycle with the reference model's pre-edge occupancy.

| Item | Bins |
|---|---|
| `occupancy` | 0..8 (9) |
| `operation` | idle, write_only, read_only, simultaneous (4) |
| `boundary` | reset, empty, full, interior, read_while_empty, write_while_full, simultaneous at empty / full / interior (9) |
| `data_pattern` | zero, all_ones, alternating x2, msb_only, lsb_only, other (7) |
| `accepted_action` | none, write, read, read_and_write, reset (5) |
| `reset`, `write_wrap_proxy`, `read_wrap_proxy` | 2 each |
| Crosses | `occupancy_x_operation` (36), `occupancy_x_boundary`, `operation_x_boundary` |

Target: every legal bin hit at least once (team assumption; the handout gives no number).

## 2. Holes (C1: 111/193 = 57.51%)
All eight single coverpoints and `occupancy_x_operation` were already 100%. The 82 holes were all in the two boundary crosses:

| Cause | Holes | Closure |
|---|---:|---|
| Cross declared over combinations that cannot occur (e.g. occupancy 3 with `write_while_full`) | 72 (52 + 20) | Added `ign_bins` (`OCC_X_BOUNDARY_IGN`, `OP_X_BOUNDARY_IGN`). Cross sizes 81 -> 29 and 36 -> 16. The sampler asserts it never lands on an ignored bin. This is a model fix, not new stimulus. |
| Reset never exercised across states: only 2 reset cycles in the whole run | 10 (7 in occupancy x boundary: reset at occupancy 0, 1, 3, 5, 6, 7, 8; 3 in operation x boundary: idle, write_only, read_only with reset) | `directed_reset_sweep`: reset at every occupancy 0..8 under every enable combination, plus 3-cycle reset holds at occupancy 0, 4, 8, each followed by a post-reset integrity check. Reset cycles 2 -> 47. |

## 3. Result (C2: 121/121 = 100%)
Every previously legal-but-empty bin now has hits: reset at occupancy 0 (11), 1 (4), 3 (4), 5 (4), 6 (4), 7 (4), 8 (5); idle, read_only and write_only with reset (9 each).

## 4. Caveats
- Of the 82 holes, only 10 were real stimulus holes (one root cause: reset). The other 72 were an over-wide model, so "57.5% to 100%" overstates the stimulus improvement.
- Reset was closed with a directed test, not a constraint change. Justification: reset needs a particular state before it fires, random enables rarely produce that, and a reset sequence needs a defined post-reset check.
- The sweep also adds reset-related checking, which the coverage model cannot distinguish from reset coverage.
- Numbers come from the team's own simulator runs (the yml files).
- vplan.md promises the COV-04 (reset x enables) and COV-05 (operation x data pattern) crosses, SIM_RW_ONE / NEAR_FULL bins, and walking-one/zero patterns. The implemented model has none of these as separate bins, and pointer wrap is only a proxy. Either add them or reword the vplan.
- `c_bias` dist weights may not condition on count in pyvsc 1.1.0 (about 0.62 to 0.67 enable rates in every band in an offline replay). Confirm with a histogram before claiming the shaping works.

## 5. Figures
**Figure 1 (C1, before the reset sweep): `CoverageModel_Visuals/C1/fifo_coverage_dashboard.html`.**
Overall 57.51% (111/193). Only the two boundary crosses are below 100%: `operation_x_boundary` 36.11% (13/36) and `occupancy_x_boundary` 27.16% (22/81). In the occupancy x boundary heatmap, red cells are reachable bins never hit. The `reset` column is red at occupancy 0, 1, 3, 5, 6, 7 and 8, and shows only 1 hit each at occupancy 2 and 4, which are the two hard-coded resets. Dots mark bins that cannot occur; the dashboard still counts them in the denominator.

**Figure 2 (C2, after): `CoverageModel_Visuals/C2_BinClosure/fifo_coverage_dashboard_after_reset_sweep.html`.**
Overall 100% (121/121). The unreachable bins are excluded with `ign_bins` (cross sizes 81 -> 29 and 36 -> 16), and `directed_reset_sweep` fills the reset column (47 reset cycles).

Reading the pair: the drop from 193 to 121 bins is the model fix; the filled reset column is the stimulus fix.
