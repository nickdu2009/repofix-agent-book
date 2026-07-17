# RepoFix companion guide

## Purpose

This directory contains the executable companion project for the RepoFix book.

## Commands

- `make bootstrap`
- `make test`
- `make lint`
- `make contract-test`
- `make fixture-baseline`
- `make fake-e2e`
- `make eval-unit`

## Safety

- Never execute commands or modified code proposed by a live model on the development host.
- Before the Daytona checkpoint, pair AgentRunner only with FakeModelClient and FakeToolExecutor.
- Keep OpenAI and Daytona credentials out of fixtures, sandbox payloads, logs, events, and artifacts.
- A model selects a semantic test target; Go maps it to a trusted command ID. The model never provides shell commands.
- Hidden evaluation tests are never mounted in the Agent's working sandbox.

## Contracts

- `contracts/*.schema.json` is the source of truth for cross-language wire values.
- Go owns Run state, cancellation, persistence, and the Daytona lifecycle.
- Python owns the model decision loop but cannot decide the final Run status.

## Done means

- Deterministic tests pass without cloud credentials or network access.
- `AgentStatus.CANDIDATE_READY` proves only that visible tests passed on the current revision; Go requires independent verification before final success.
- New failure paths have tests.
- Documentation commands match the executable Makefile targets.
