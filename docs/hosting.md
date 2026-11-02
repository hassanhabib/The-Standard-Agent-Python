# Hosting an agent over HTTP

`standard_agents.host` exposes one agent over HTTP with the routes, gates, JSON and
server-sent events of the C# host (Standard.Agents.Host). It is built on the standard library:
an asyncio HTTP/1.1 server written for this host, no web framework, no dependency.

```bash
python -m standard_agents.host --urls http://0.0.0.0:5000
```

Ctrl+C (or SIGTERM) stops it, and it closes the agent it composed, which stops any MCP server
process that agent started.

## Routes

| Method | Route | Body | Answers |
|---|---|---|---|
| GET | `api/Home` | | the heartbeat, open even when the agent routes are locked |
| POST | `api/V1/agents/runs` | `{"prompt": "...", "sessionId": "..."}` and the rest of the V1 request | the run's outcome as JSON |
| POST | `api/V1/agents/streams` | the same | the run as server-sent events, then its outcome |
| POST | `api/Agents/runs` | `{"prompt": "..."}` | the V0 run |
| POST | `api/Agents/streams` | `{"prompt": "..."}` | the V0 stream |

```bash
curl -s http://localhost:5000/api/V1/agents/runs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 47 * 89?"}'
```

## Configuration

The host reads the keys the C# host reads, named as it names them, from environment variables
(with `__` standing for `:`) and then from the command line (`--Host:ApiKey=...`), the later
source winning.

| Key | Meaning |
|---|---|
| `urls` | where to listen (default `http://localhost:5000`); `http` only |
| `Host:ApiKey` | when set, every agent route wants this value in an `X-Api-Key` header |
| `Host:Authentication:Authority` | when set, every agent route wants an authenticated caller (see below) |
| `Agent:Config` | a JSON agent document to compose the agent from (see `StandardAgent.from_json`) |
| `Agent:Url`, `Agent:ApiKey`, `Agent:Model` | the brain, when no document is given |
| `Agent:Skills` | a skills folder |
| `Agent:Memory` | a memory file; without it the host's agent has no memory, because one instance serves every caller |

Without `Agent:Config`, an `agent.json` in the working directory is picked up on its own. Without
either, the agent is composed from the `Agent:` keys:

```bash
Agent__Url=http://localhost:11434/v1/ Agent__Model=llama3.1 python -m standard_agents.host
```

`python -m standard_agents.host --schema` prints the JSON Schema of the agent document, and
`--validate [path]` checks a document and exits.

## Composing the host in code

```python
from standard_agents import StandardAgent
from standard_agents.host.program import create_host

host = create_host(
    {"urls": "http://0.0.0.0:5000", "Host:ApiKey": "psk-live-7"},
    agent_factory=lambda principals: StandardAgent().on_brain(brain))
```

`agent_factory` is handed the host's principal resolver and called on the first request that
needs the agent. `authenticate` is the authentication scheme: an async function that reads a
request and returns who it is, or None for an anonymous caller.

## Where it differs from the C# host

- **Bearer tokens are not validated.** Setting `Host:Authentication:Authority` locks every agent
  route as the C# host does, but the standard library has no RS256 or ES256 verification and no
  OIDC metadata client, so nothing unlocks it on its own: every agent route answers 401, and the
  host logs why, unless `create_host` is given an `authenticate` scheme (for example one built on
  a JWT library the deployment trusts). `Host:Authentication:Audience` is read by nothing.
- **No HTTPS and no HTTP/2.** An `https` URL is refused; put TLS in front of the host.
- **No OpenTelemetry export** (`OTEL_EXPORTER_OTLP_ENDPOINT` is ignored), no pooled HTTP handler
  under the agent's brokers, and no `appsettings.json` or user secrets.
- **Framing.** A whole response carries `Content-Length` where Kestrel chunks a JSON body, and no
  `Server` header is sent. A stream is chunked on HTTP/1.1, as Kestrel's is.
- **Errors.** A JSON binding error names the path and the type as System.Text.Json does, without
  the line and byte position. An unhandled exception is a 500 with no body, as ASP.NET answers
  outside Development.
- `Expect: 100-continue` is answered before the gates run.
