# Fast mode on an RTX 4080 SUPER, October 12, 2026

The Glyd engine in fast mode, with default drafting, on the RTX 4080 SUPER PC described in the top-level README. The questions are the same as
in the Strata runs: Inspect AI's GSM8K and MMLU-Pro as shipped, every second question, the first 150 of each. Decoding is greedy, thinking
is off, and the cap is 3,072 tokens. Each engine session answered at most 75 GSM8K or 50 MMLU-Pro questions.

| | Glyd fast (this run) | Strata Q2_0 | Strata IQ3_XXS |
|---|--:|--:|--:|
| GSM8K 150 | 149 | 148 | 147 |
| MMLU-Pro 150 | 123 (18 at the cap) | not finished | 126 (15 at the cap) |
| HumanEval 164 | 156 (95.1%) | | |
| mean decode over the benchmark replies | 7.10 ms a token (141 tok/s) | | |

Files:
- `gsm8k.txt`, `mmlu_pro.txt`: the merged scores;
- `logs/`: every slice's Inspect log;
- `humaneval/`: the HumanEval log;
- `speed.txt`: the engine's own decode timing.
