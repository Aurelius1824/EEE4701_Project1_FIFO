# FINDINGS — <HW 5> · <Christian Pumarada>

> The number is the start of the argument, not the end of it. This file is
> where you say what the number means and what it does not cover.

## Score

| Pool | found | total | % |
|released|  8  |    8  |100%|
| hidden | 20  |    20 |100% |

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
|None (All survivors from the released and hidden set were found| N/A| yes | yes | No mutants survived the final iteration of the test_fifo verification due to the final 2-phase CRV + cross-product sweep. The assignment had to go through a few iterations until ALL mutants were found, but with the assistance of AI, many different ideas were able to be explored. In the earlier iteations, intermediate survivors survived due to a reachability gap at count==1 with a simultaneous R+W, idle-hold memory wr_en checks, and unbroken pointer wraps, before the 2nd phase of the TB was added. |


## What I changed, and what it bought

| Change | Score before | Score after | Which survivors it caught |
|--------|-------------:|------------:|---------------------------|
|  Added components from HW4 --> HW5, c_bias constraints, 4096 cycles | 0/20 | 8/20 (8 released) | Caught the standarda released pool of mutants, which were already known so directed tests easily caught them.  |
| Flattened c_bias into a faster 3 branch constraint, changed up the probabities for R & W during the 3 branches| 8/20 | 13/20 | Caught boundary overflow and underflow mutants, plus interior sim R+W wrap bugs; Also cutt down runtime from 29s -> 14s|
| Added pre-clock falling edge scoreboard check, X/Z checks, post randomized corner case pattern injections, and mid-test synchronous reset checks with active enables occuring at the same time. | 13/20 | 17/20 | Caught mutants pertaining to combinational feedthrough, unreset states, and bit masking datapath faults.|
| Added cross-product sweep across every occupoancy, 10 step sim. R+W wraps at each occupancy in the FIFO, and unbroken single walking bit sweeps i.e. 0->8->0 | 17/20 | 20/20 | FWFT head update on sim R+W at count ==1, unintended state mutation during idle, and pure single-enable wrap transistions.|

## Residual risk

What this suite still cannot catch, stated plainly. Name a fault class, not a
mutant id — the pool is a sample, not the population.

1. The scoreboard only observes the FIFOs internal memory array through the FWFT head, therfore if a fault corrupts an unoccupied memory slot during a write, that corrupted slot will alwyas be overwritten by the write operation before our rd_ptr could ever reach it. 
2. The FIFO spec leaves FWFT head undefined when the FIFO is empty, our Monitor sets the rd_Data to none and the scoreboard skips comparing the rd_data whenever the model is empty. Any mutant or fault that drives invalid logic on rd_data when empty is true, is reached by the stimulus (saw_empty == True), but is unobservable by the scoreboard checks.

**If I had another day:** <the one thing you would do next, and why that one>
I would eliminate the need for the directed phase 2 cross product loop by adding probes to immediately detect silent memory writes or pointer mismatches. Additionally, I would like to add a component that can automatically biase the solver toward unvisited (count, wr_en, rd_en, wrap) cross-bins until a reasonable CRV % is achieved.