#!/usr/bin/env python3
"""A slice of the Strata record's question set, run the way eval_run.py runs it (Inspect AI gsm8k / mmlu_pro from inspect_evals, as they ship, non-thinking, temperature 0, at most 3,072 new tokens, max_connections 8):
the set is `dataset[i-1::n][:LIMIT]` (shard 1/2, LIMIT 150: the 150 questions of benchmarks/cards/2026-10-10 and the Strata runs, the same Inspect sample ids), and the slice is its questions START..END-1.
    eval_slice.py BASE_URL MODEL TASK(gsm8k|mmlu_pro) SHARD(i/n) LIMIT START END OUTDIR
Writes OUTDIR/evals.json (one row, the slice's accuracy, n, and the range) and Inspect's log in OUTDIR/logs; merge_slices.py combines slices."""
import json
import sys
from importlib.metadata import version
from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_evals.gsm8k import gsm8k
from inspect_evals.mmlu_pro import mmlu_pro

base, model, task_id, shard, limit, start, end, out = sys.argv[1:9]
i, n, limit, start, end = *map(int, shard.split("/")), int(limit), int(start), int(end)
harness = {"inspect_ai": version("inspect-ai"), "inspect_evals": version("inspect-evals")}
TASKS = {"gsm8k": ("openai/gsm8k", gsm8k(), "10-shot, numeric match, non-thinking"), "mmlu_pro": ("TIGER-Lab/MMLU-Pro", mmlu_pro(shuffle=False), "0-shot chain of thought, non-thinking")}
dataset, task, notes = TASKS[task_id]
task.dataset = task.dataset[i - 1::n][:limit][start:end]
log = inspect_eval(task, model=f"openai-api/glyd/{model}", model_base_url=base, limit=None, log_dir=f"{out}/logs", temperature=0, max_tokens=3072,
                   max_connections=8, extra_body={"chat_template_kwargs": {"enable_thinking": False}}, display="plain")[0]
assert log.status == "success", f"{task_id}: {log.status} {log.error}"
Path(out).mkdir(parents=True, exist_ok=True)
Path(out, "evals.json").write_text(json.dumps([{"dataset": dataset, "task_id": task_id, "value": log.results.scores[0].metrics["accuracy"].value, "n": log.results.completed_samples,
                                               "shard": shard, "limit": limit, "slice": [start, end], "harness": harness, "notes": notes}], indent=2) + "\n")
