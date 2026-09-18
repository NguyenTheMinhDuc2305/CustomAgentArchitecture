# ADR 0001: Local API credential CSV

## Status

Accepted for the initial local, single-user implementation.

## Context

The runtime needs to route requests across multiple API keys, providers, and
models. The initial deployment is local and the operator requested one CSV file
that can be loaded as a DataFrame.

## Decision

- Store local credentials in `config/api_keys.csv`.
- Ignore the real file in Git and commit only `api_keys.example.csv`.
- Require `key`, `provider`, and `model`; allow `enabled` and `priority`.
- Load and validate the file with pandas at application startup.
- Never expose the raw credential DataFrame outside the infrastructure adapter.
- Derive a stable `key_id` from a one-way fingerprint for health and quota
  tracking.

## Consequences

- Local setup is simple and supports bulk editing and inspection.
- Anyone who can read the file can read every API key in it.
- File permissions, backups, malware, and accidental screen sharing remain
  risks outside application control.
- Multi-user or remote deployment must replace this adapter with a secret
  manager; core and application layers should not change.
