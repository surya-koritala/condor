# Using it from other apps

The server (`./setup.sh` or `tools/serve.sh`) speaks the OpenAI chat API and the Anthropic messages API on your own machine:

```
OpenAI-compatible      http://127.0.0.1:8080/v1          (chat completions: /v1/chat/completions)
Anthropic-compatible   http://127.0.0.1:8080/v1/messages
model name             qwen3.8-flash-next (any name works)
API key                any
```

If you started it on another port (`tools/serve.sh 8090`), change the port.

TODO(owner): say which address it listens on, and how to reach it from another machine or a Docker container if that's supported.

## Generic setup

Most OpenAI-compatible apps and SDKs want a base URL and a key. The official OpenAI SDKs read these environment variables:

```sh
export OPENAI_BASE_URL=http://127.0.0.1:8080/v1
export OPENAI_API_KEY=local
```

Python:

```python
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="local")
r = client.chat.completions.create(model="qwen3.8-flash-next", messages=[{"role": "user", "content": "Hi"}])
print(r.choices[0].message.content)
```

In apps with a settings screen (Open WebUI, Continue, Cline, LibreChat and so on), add an "OpenAI-compatible" provider with the base URL
`http://127.0.0.1:8080/v1`, any key, and model `qwen3.8-flash-next`. I haven't tested each app yet; see below.

For Anthropic-style clients, the base URL is `http://127.0.0.1:8080` (no `/v1`), e.g. `ANTHROPIC_BASE_URL=http://127.0.0.1:8080`.

Thinking is off by default. Send `reasoning_effort` to turn it on.

## What is tested

`tests/test_server.py` runs these against a live server. All 9 checks passed in the logged run
(`results/v0.1.0/fast/test_server.txt`) and on the A10 run (`results/v0.1.0/a10`):

```
OpenAI     plain answer, streamed answer, one tool call (not streamed), the tool's result sent back and used
Anthropic  plain answer, streamed answer, one tool use (not streamed)
OpenAI     a client that drops a stream halfway; the next request still gets its own answer
```

You can run it yourself: `python3 tests/test_server.py --url http://127.0.0.1:8080`.

## Not tested yet

- TODO(owner): test tool calls while streaming (`"stream": true` with `tools`), OpenAI and Anthropic.
- TODO(owner): test more than one tool call in a single answer (parallel tool calls).
- TODO(owner): test `tool_choice` (`"required"`, `"none"`, a named function) and the Anthropic equivalent.
- TODO(owner): test long agent loops (many tool round trips in one conversation).
- TODO(owner): test tool calls with thinking on (`reasoning_effort`).
- TODO(owner): test `response_format` / JSON mode.
- TODO(owner): test whether `GET /v1/models` exists; some apps call it to fill their model list.
- TODO(owner): test Open WebUI, Hermes, Continue, Cline and LibreChat end to end and add a short note for each.

## Things that will trip up agent frameworks

- One request at a time. Others queue, so a framework that sends several requests in parallel will see them answered one after another.
  Give it a long timeout.
- Context is 32,768 tokens by default. Agent prompts with many tool definitions get long fast; start the server with a bigger context
  (`GLYD_CTX=65536 tools/serve.sh`, up to 262144) if you need it.

If something doesn't work, open an issue with the client, its version, and what the server printed.
