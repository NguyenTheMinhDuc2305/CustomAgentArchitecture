# Implementation TODO

This file is the source of truth for implementation progress. Check an item
only when its acceptance criteria and relevant tests pass.

Status legend:

- `[x]` complete
- `[ ]` not started or in progress
- `(blocked: reason)` cannot proceed yet

## Phase 0 — Repository foundation

- [x] Define the repository architecture and dependency direction.
- [x] Create Python package, configuration, documentation, and test folders.
- [x] Document subscription/API routing and application-owned history.
- [x] Add ignore rules for secrets, runtime state, browser profiles, and
  generated dependencies.
- [ ] Replace the placeholder root `main.py` with a real CLI entrypoint.
- [ ] Add linting, formatting, type-checking, and test commands to
  `pyproject.toml`.
- [ ] Add CI for unit and integration tests.

## Phase 1 — Core contracts and configuration

- [ ] Define provider-neutral `Message`, `ToolCall`, `ToolResult`, `Usage`,
  `LLMRequest`, and `LLMResponse` models.
- [ ] Define `Run`, `Task`, `Step`, `AgentIdentity`, and step-status models.
- [ ] Define `LLMGateway`, `ToolGateway`, `HistoryRepository`, `RunRepository`,
  `ApprovalPort`, and `EventBus` protocols.
- [ ] Implement typed loading and validation for `.mcp.json`.
- [ ] Design and implement `config/agents.yaml` schema.
- [ ] Design and implement `config/providers.yaml` schema.
- [ ] Design and implement `config/policies.yaml` schema.
- [ ] Ensure configuration contains secret references, never secret values.

Acceptance criteria:

- Invalid configuration fails at startup with a field-specific error.
- Core modules import no MCP or provider SDK.
- Configuration tests cover missing, malformed, and unknown fields.

## Phase 2 — History and context pipeline

- [ ] Implement an append-only history repository.
- [ ] Persist agent messages, LLM attempts, tool calls, tool results, routing
  decisions, and errors as typed events.
- [ ] Implement `ContextBuilder` to construct one context envelope per LLM
  step.
- [ ] Add token-budget estimation per target model.
- [ ] Implement relevance selection and deterministic truncation rules.
- [ ] Add durable summaries without deleting raw history.
- [ ] Implement sensitive-field redaction before persistence and logging.
- [ ] Add reconstruction tests proving that the same stored step produces the
  same logical context envelope.

Acceptance criteria:

- No adapter depends on provider-owned conversation state.
- Every LLM attempt references a persisted context-envelope ID.
- A run can reconstruct its next step after process restart.

## Phase 3 — API key and model manager

- [ ] Implement `ApiModelManager`.
- [ ] Implement model catalog and capability matching.
- [x] Define the local API credential CSV schema.
- [x] Implement pandas DataFrame loading, normalization, and validation.
- [x] Implement secret-safe credential IDs and redacted diagnostic views.
- [x] Add unit tests for valid, malformed, duplicate, and disabled rows.
- [ ] Build the API-key pool on top of `ApiKeyCatalog`.
- [ ] Track key health, rate limits, quota errors, cooldowns, and concurrency.
- [ ] Define key rotation policy; do not rotate on invalid-request errors.
- [ ] Add provider adapters incrementally behind the common LLM port.
- [ ] Normalize responses, usage, finish reasons, and errors.
- [ ] Add per-key and per-model budget controls.

Acceptance criteria:

- Logs never contain raw API keys.
- The real `config/api_keys.csv` is ignored by Git.
- Exhausting one key can select another eligible key.
- An invalid prompt is returned to the caller and does not burn every key.

## Phase 4 — Subscription manager

- [ ] Implement `SubscriptionManager`.
- [ ] Implement a Codex subscription adapter.
- [ ] Implement a Claude Code subscription adapter.
- [ ] Detect executable availability and authentication state.
- [ ] Pass a complete context envelope on every invocation.
- [ ] Normalize CLI output into `LLMResponse`.
- [ ] Classify quota, authentication, timeout, transient, and permanent errors.
- [ ] Add route cooldown and concurrency controls.
- [ ] Add fake-process integration tests for stdout, stderr, exit codes, and
  timeouts.

Acceptance criteria:

- Subscription adapters do not require provider checkpoint IDs.
- Quota errors are distinguishable from authentication and prompt errors.
- A cancelled step terminates its child process without leaking descendants.

## Phase 5 — LLM router and fallback

- [ ] Implement application-level `LLMRouter`.
- [ ] Define routing order by agent, task type, capability, cost, and policy.
- [ ] Prefer eligible subscription routes where configured.
- [ ] Fall back to `ApiModelManager` only for explicitly classified conditions.
- [ ] Carry the same logical context envelope across fallback attempts.
- [ ] Add attempt IDs and step-level idempotency protection.
- [ ] Persist why each route was selected or rejected.
- [ ] Prevent infinite retry/fallback loops.

Acceptance criteria:

- A simulated subscription quota error falls back to an eligible API model.
- Authentication and invalid-request errors do not silently fall back.
- The final step record contains every attempt in order.

## Phase 6 — MCP tool layer

- [ ] Complete root `.mcp.json` with Playwright, Chrome DevTools, and SSH MCP.
- [ ] Implement MCP config models and secret interpolation.
- [ ] Implement MCP connection lifecycle for stdio and Streamable HTTP.
- [ ] Implement namespaced tool registry.
- [ ] Implement `MCPToolGateway` behind the core tool port.
- [ ] Implement per-agent tool allow-lists.
- [ ] Inject `actor` into supported SSH tool calls.
- [ ] Implement destructive-tool confirmation flow.
- [ ] Serialize browser calls and define browser-session ownership.
- [ ] Add health checks, timeouts, reconnect policy, and graceful shutdown.

Acceptance criteria:

- All configured servers initialize and list tools in an integration test.
- Unauthorized agents cannot call a hidden tool by name.
- Browser profile conflicts cannot occur under the default policy.

## Phase 7 — Agents and orchestration

- [ ] Implement base agent contract and lifecycle.
- [ ] Implement planner/coordinator agent.
- [ ] Implement browser operator and browser debugger roles.
- [ ] Implement infrastructure observer and operator roles.
- [ ] Implement task graph, dependencies, cancellation, and timeout semantics.
- [ ] Define agent-to-agent message envelopes.
- [ ] Implement bounded parallel execution.
- [ ] Add loop detection and maximum-step budgets.
- [ ] Add human approval and intervention points.

Acceptance criteria:

- A coordinator can delegate a browser and infrastructure subtask.
- Each agent sees only its configured tools and relevant history.
- Failed agents return typed failure state instead of stalling the run.

## Phase 8 — Persistence, observability, and operations

- [ ] Choose the initial persistent store and write an ADR.
- [ ] Implement run, task, step, history, and artifact repositories.
- [ ] Add structured logs with run/task/step/agent correlation IDs.
- [ ] Add metrics for latency, usage, quota failures, fallback, and tool calls.
- [ ] Add distributed trace propagation where supported.
- [ ] Add crash recovery based on application state and history reconstruction.
- [ ] Add retention, redaction, and cleanup policies.
- [ ] Add operational CLI commands for inspecting and cancelling runs.

## Phase 9 — End-to-end validation

- [ ] Test subscription-first success path.
- [ ] Test subscription-quota-to-API fallback path.
- [ ] Test multiple API keys with rate-limit rotation.
- [ ] Test history reconstruction across provider changes.
- [ ] Test MCP browser workflow.
- [ ] Test SSH read-only and destructive approval workflows.
- [ ] Test restart during an in-progress run.
- [ ] Run security review for secrets, command execution, and prompt/tool input.
