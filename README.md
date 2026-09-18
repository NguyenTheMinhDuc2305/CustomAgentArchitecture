# Agent Architecture

Python runtime for a multi-agent system that can obtain LLM capacity from two
independent sources:

1. Local subscription-backed clients: Codex and Claude Code.
2. Direct provider APIs using a pool of API keys and models.

The system does not treat a provider session or provider checkpoint as the
source of truth. Every LLM step receives an explicit context envelope rebuilt
from application-owned history. This lets an agent move from a subscription
adapter to an API adapter without losing its working context.

Implementation progress is tracked in [TODO.md](TODO.md).

## Architectural principles

- Agents depend on application ports, not on provider SDKs, command-line tools,
  MCP transports, or secret storage.
- Conversation history and workflow state belong to this application.
- Every LLM request is reproducible from a stored step and its context envelope.
- Provider responses are normalized before they reach an agent.
- Subscription quota exhaustion may trigger an API fallback; arbitrary errors
  do not automatically trigger fallback.
- Tools are namespaced, allow-listed per agent, audited, and checked again at
  execution time.
- Browser calls are serialized unless a future isolation policy explicitly
  allows parallel sessions.

## Runtime overview

```text
                         ┌──────────────────────┐
                         │    Swarm Runtime     │
                         │ coordinator/scheduler│
                         └──────────┬───────────┘
                                    │
                           ┌────────▼────────┐
                           │     Agents      │
                           └───┬─────────┬───┘
                               │         │
                   ┌───────────▼──┐   ┌──▼─────────────┐
                   │  LLM Router  │   │  Tool Service  │
                   └──────┬───────┘   └──────┬─────────┘
                          │                  │
              ┌───────────┴───────────┐      ▼
              │                       │   MCP Gateway
    ┌─────────▼──────────┐  ┌────────▼─────────┐
    │SubscriptionManager│  │ ApiModelManager  │
    ├────────────────────┤  ├──────────────────┤
    │ Codex adapter      │  │ key pool         │
    │ Claude Code adapter│  │ model catalog    │
    │ quota/health state │  │ rate-limit state │
    └────────────────────┘  └──────────────────┘
              │                       │
              └───────────┬───────────┘
                          ▼
             Normalized LLM response

    HistoryStore ──> ContextBuilder ──> context for every LLM step
```

`LLMRouter` is an application policy service, not a third credential manager.
It chooses between the two concrete managers and keeps provider selection out
of agent code.

## LLM routing policy

The initial routing policy is:

1. Build a provider-neutral context envelope for the step.
2. Select a compatible subscription route when policy prefers subscription.
3. Ask `SubscriptionManager` to choose Codex or Claude Code.
4. On a classified quota or availability error, put that route into cooldown.
5. Submit the same logical request to `ApiModelManager`.
6. Persist the selected route, attempt number, usage, result, and error class.

Fallback must not happen blindly. Authentication errors, invalid prompts,
policy violations, and malformed tool calls should fail explicitly. A fallback
is appropriate for quota exhaustion, rate limiting, temporary provider
unavailability, or a route disabled by health policy.

### SubscriptionManager

Responsibilities:

- Own Codex and Claude Code adapters.
- Check executable availability and authentication state.
- Normalize CLI output into the common LLM response model.
- Classify quota and transient errors.
- Maintain route health, cooldown, timeout, and concurrency state.
- Never rely on an opaque provider conversation as durable memory.

### ApiModelManager

Responsibilities:

- Maintain a model catalog and model capabilities.
- Resolve API keys by environment-variable reference or a secret backend.
- Rotate keys according to provider, model, quota, rate limit, health, and cost.
- Keep per-key circuit-breaker and cooldown state.
- Never write secret values to logs, history, traces, or config files.
- Normalize provider-specific responses and usage into the common model.

## History and context

There are two different concepts:

- Provider checkpoint: an internal session owned by Codex, Claude Code, or an
  API provider. The architecture does not depend on it.
- Application state: task state, messages, tool results, decisions, summaries,
  and step status stored by this repository.

Each LLM step receives a `ContextEnvelope` assembled from:

- Agent system instructions.
- Current objective and task constraints.
- Relevant parent-agent messages.
- Selected conversation history.
- Tool results and artifacts referenced by the task.
- The latest durable summary.
- Available tool schemas for that agent.

Raw history should be append-only. Context is a projection of that history,
not necessarily every raw message. When history exceeds a model's context
window, `ContextBuilder` selects relevant events and uses a persisted summary;
it must not silently discard the original events.

A workflow may later resume from application state by rebuilding context. That
is different from resuming an opaque provider-side checkpoint.

## Repository structure

```text
.
├── .mcp.json                         # MCP server manifest for the runtime
├── .env.example                      # Secret variable names only
├── TODO.md                           # Implementation checklist
├── config/
│   └── README.md                     # Planned runtime configuration files
├── docs/
│   └── adr/                          # Architecture decision records
├── scripts/                          # Development and operational scripts
├── src/
│   └── agent_system/
│       ├── bootstrap.py              # Composition root (planned)
│       ├── core/
│       │   ├── models/               # Provider-neutral domain models
│       │   └── ports/                # Interfaces implemented by adapters
│       ├── application/
│       │   ├── orchestration/        # Coordinator, scheduler, task graph
│       │   ├── context/              # History selection and context building
│       │   ├── llm/                  # LLMRouter and routing policy
│       │   └── tools/                # Tool policy, approval, and audit flow
│       ├── agents/                   # Agent definitions and role prompts
│       ├── infrastructure/
│       │   ├── llm/
│       │   │   ├── api/              # ApiModelManager and API adapters
│       │   │   └── subscription/     # SubscriptionManager and CLI adapters
│       │   ├── mcp/                  # MCP lifecycle, registry, and gateway
│       │   ├── persistence/          # History/run-state repositories
│       │   └── observability/        # Logs, metrics, traces, audit records
│       └── entrypoints/              # CLI, API, and worker entrypoints
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

## Dependency direction

```text
entrypoints ──> application ──> core
                    ▲
                    │
              infrastructure
```

- `core` imports no provider SDK, MCP SDK, CLI adapter, or persistence library.
- `application` depends on interfaces declared in `core/ports`.
- `infrastructure` implements those interfaces.
- `bootstrap.py` is the only composition root allowed to wire concrete
  implementations together.
- Agents call application services. They do not call provider or MCP managers
  directly.

## Configuration boundaries

- `.mcp.json`: MCP connection definitions only.
- `config/agents.yaml`: agent roles, prompts, model requirements, and tool
  allow-lists (planned).
- `config/providers.yaml`: subscription routes and provider/model metadata
  (planned).
- `config/api_keys.csv`: local API key/provider/model catalog loaded through
  pandas. The real file is Git-ignored; only its example schema is committed.
- `config/policies.yaml`: fallback, retries, cooldown, approval, budget, and
  concurrency limits (planned).
- `.env`: local secret values, never committed.

The VS Code file `.vscode/mcp.json` remains a development convenience. The
Python runtime will load root `.mcp.json` through its own validated config
loader.

## API credential DataFrame

API credentials are loaded from the local, Git-ignored
`config/api_keys.csv`. The committed template is
`config/api_keys.example.csv`.

```csv
key,provider,model,enabled,priority
YOUR_API_KEY,openai,MODEL_NAME,true,100
```

`ApiKeyCatalog` validates and normalizes the DataFrame at startup. Application
code receives immutable `ApiCredential` objects; diagnostic code receives only
a safe DataFrame without the raw `key` column. The catalog derives `key_id`
from a one-way SHA-256 fingerprint of provider and key so the future
`ApiModelManager` can track health without logging credentials.

The CSV approach is intended for a local single-user deployment. Before a
multi-user or remote deployment, replace the CSV storage adapter with a secret
manager while preserving the same core credential interface.

## Development workflow

1. Pick the next unchecked item in `TODO.md`.
2. Add or update its acceptance criteria before implementation.
3. Implement through a core port where an external system is involved.
4. Add unit tests and, where applicable, integration tests with fake adapters.
5. Mark the item complete only after its acceptance criteria pass.
6. Record architectural changes in `docs/adr/`.

## Security rules

- Never commit API keys, subscription tokens, browser profiles, or MCP tokens.
- Redact prompts and tool results according to the configured logging policy.
- Treat model output as untrusted input before tool execution.
- Enforce tool authorization server-side in `ToolService`, not only by hiding
  tools from a prompt.
- Require explicit confirmation for destructive SSH operations.
- Use a step ID and idempotency policy to prevent duplicated work after retry or
  fallback.
