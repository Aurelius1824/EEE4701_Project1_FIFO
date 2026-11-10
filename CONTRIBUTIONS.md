## Christian Pumarada:
- Provided the baseline test_fifo program, as it obtained a 20/20 mutant detection score.
- Defined the vplan.md file
- Team lead

### Robert Ramkissoon
- Wrote `COVERAGE.md`: the coverage model, which holes appeared, and how each was closed.
- Analyzed the C1 (before) and C2 (after reset sweep) exports in `CoverageModel_Visuals/`. Of the 82 holes in C1, 72 came from impossible cross bins, fixed with `ign_bins`. The other 10 were reset holes, closed by `directed_reset_sweep`.
- Compared the implemented coverage model against `vplan.md` and listed the gaps.
