# FINDINGS — < Porject1> · < Ha Anh Khoi Tran>

> The number is the start of the argument, not the end of it. This file is
> where you say what the number means and what it does not cover.

## Score

| Pool | found | total | % |
|------|------:|------:|--:|
| released (practice) | 8|8 |100% |
| hidden (reported at grading) |20 |20 |100% |

**Command run:**

```
    just test fifo_crv icarus
    just mutate fifo_crv
```

## Survivors

One row per mutant your suite did not find. `Reachable?` is the important
column: a survivor you never reached is a *stimulus* problem, a survivor you
reached but did not notice is a *checking* problem, and they have different
fixes.

| Mutant | What it changes | Reachable by my stimulus? | Observable by my checks? | Why it survived |
|--------|-----------------|---------------------------|--------------------------|-----------------|
| None (All survivors from the released and hidden set were found)   | N /A| Yes  |   Yes     |No mutants survived the final iteration of the test_fifo verification due to the final 2-phase CRV + cross-product sweep|




## What I changed, and what it bought

| Change | Score before | Score after | Which survivors it caught |
|--------|-------------:|------------:|---------------------------|
|Directed Test + Basic Test   |      0        |       8      | full_off by one,   empty_off by one, ignore_full, ignore_empty, count_wr_dec, rd_data_wrptr, mem_corrupt,wrptr_wrap_early.... |
| 5000 random tests   |      8        |       10     |  hard: random test catch cases that we didnt think of |
| Reset  test   |      10       |       14     |  hard + very hard: unreset states |
|Added pre-clock falling edge scoreboard check, X/Z checks, post randomized corner case pattern injections|      14       |       17     |  hard + very hard: Caught mutants pertaining to combinational feedthrough and bit masking datapath faults |
|Added cross-product sweep across every occupoancy, 10 step sim. R+W wraps at each occupancy in the FIFO, and unbroken single walking bit sweeps i.e. 0->8->0|      17       |      20     |  hard + very hard: FWFT head update on sim R+W at count ==1, unintended state mutation during idle, and pure single-enable wrap transistions.|



## Residual risk

What this suite still cannot catch, stated plainly. Name a fault class, not a
mutant id — the pool is a sample, not the population.

1. Eventhough We catch all the bug in the release and hidden pool, we believe that there is still more cases that could be test. Since we are lack of experience so we only try to fix problems in the projects.

2. The FIFO spec leaves FWFT head undefined when the FIFO is empty, our Monitor sets the rd_Data to none and the scoreboard skips comparing the rd_data whenever the model is empty. Any mutant or fault that drives invalid logic on rd_data when empty is true, is reached by the stimulus (saw_empty == True), but is unobservable by the scoreboard checks.

3. There is some hidden bug that the test cannot catch this is due to we cannot see what happen behind the screen. The scoreboard only observes the FIFOs internal memory array through the FWFT head, therfore if a fault corrupts an unoccupied memory slot during a write, that corrupted slot will alwyas be overwritten by the write operation before our rd_ptr could ever reach it.

**If I had another day:**  
I would eliminate the need for the directed Phase 2 cross-product loop by implementing additional probes to immediately detect silent memory writes and pointer mismatches. Additionally, I would introduce a coverage-driven component that automatically biases the constraint solver toward unvisited (count, wr_en, rd_en, wrap) cross-coverage bins until a reasonable coverage percentage is achieved.

Besides improving the testing strategy, I would also put more emphasis on performance testing by optimizing the speed test and evaluating the FIFO's throughput under different operating conditions. This would help identify potential performance bottlenecks and ensure that the design is not only functionally correct but also efficient.