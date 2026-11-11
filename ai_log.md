# Robert Ramkissoon: Coverage Section

**Date:** 2026-11-08 to 2026-11-10  
**Tool:** Claude (Claude Code session, Sonnet 5.5)

### My Work

I independently performed the coverage analysis, reviewed the coverage exports and dashboards, verified the hole counts and percentages, and determined how the remaining coverage holes were addressed. I used Claude sparingly as a secondary tool for verification and documentation assistance.

### What I Used Claude For

- Reading `test_fifo.py`, `vplan.md`, `fifo.md`, `fifo.sv`, and both `fifo_coverage.yml` exports to cross-reference my analysis.
- Double-checking hole counts, percentages, and coverage calculations that I had already examined.
- Proofreading and tightening the wording of `COVERAGE.md`.
- Formatting my analysis into a clean Markdown document, including tables and figure captions.
- Identifying potential questions a grader might ask, such as the justification for directed tests and excluded bins.

### What I Independently Did and Verified

- Personally checked the 82 C1 coverage holes and their classification into 72 impossible cross bins and 10 reset-related holes.
- Verified the before-and-after coverage figures and dashboards for C1 and C2 against the team's coverage exports.
- Confirmed the relationship between the coverage model, verification plan, and implemented tests.
- Determined and verified how the remaining holes were addressed: 72 impossible cross bins excluded through `ign_bins` and 10 reset holes closed through `directed_reset_sweep`.
- Reviewed and validated the final coverage analysis and documentation.

### Limitations of AI Assistance

Claude did not execute cocotb, run the course simulator, or reproduce any coverage results. All reported coverage numbers originate from the team's actual coverage exports and runs. Claude read the YAML coverage exports and C1 screenshot but did not inspect the dashboard HTML files.
