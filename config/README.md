# Configuration

Planned configuration boundaries:

- `agents.yaml`: roles, prompts, model requirements, and tool allow-lists.
- `providers.yaml`: subscription routes and provider/model capabilities.
- `policies.yaml`: fallback, retries, cooldown, approval, budget, timeout, and
  concurrency rules.
- `api_keys.csv`: local API credential catalog loaded into a pandas DataFrame.
  This file is ignored by Git.
- `api_keys.example.csv`: committed schema example with no real credential.

Only example or non-secret configuration belongs in Git. Actual credentials
in `api_keys.csv` must never be copied into issues, logs, test fixtures, or
committed configuration.

## API key CSV schema

Required columns:

- `key`: the raw provider API key.
- `provider`: normalized to lowercase by the loader.
- `model`: exact provider model identifier.

Optional columns:

- `enabled`: `true` by default. Accepted values are `true`, `false`, `1`, `0`,
  `yes`, and `no`.
- `priority`: non-negative integer; lower values are selected first and the
  default is `100`.

Use one row for each provider/model combination. The same key may occur on
multiple model rows; the loader derives the same secret-safe `key_id` for those
rows so quota and health can later be tracked per credential.
