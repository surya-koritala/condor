# Contributing

Thanks for helping. Bug reports, speed results from your hardware and fixes are all welcome.

## What is in this repository

- `setup.sh` and `tools/`: the installer, the download and start scripts, and the chat app (`tools/chat.html`, `tools/web/`).
- `bench/`: the quality benchmarks behind the README's numbers. `results/`: their logs.
- `tests/`: `node tests/test_flow.js` checks the flowchart renderer; `python3 tests/test_server.py --url http://127.0.0.1:8080` checks
  a running server end to end.

The Glyd engine itself ships compiled (see [ENGINE-LICENSE](ENGINE-LICENSE)), so its source is not here. Problems with the engine are
still welcome as issues.

## Reporting a problem

Open an [issue](https://github.com/surya-koritala/glyd-qwen-3.8-flash/issues) with your GPU, driver, RAM and Linux version, what you
ran, and what it printed. For speed, run `tools/bench.sh` and attach `bench-report.md`.

## Pull requests

- Keep a change small and about one thing, and say how you tested it.
- Sign off your commits (`git commit -s`): it certifies the [Developer Certificate of Origin](https://developercertificate.org/), that you
  wrote the change or have the right to submit it under this repository's license (Apache-2.0).

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
