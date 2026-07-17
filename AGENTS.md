# Repository guide

## Purpose

This repository contains the Chinese RepoFix AI Agent practice book and its MkDocs Material site.

## Commands

- `pip install -r requirements.txt`
- `mkdocs serve`
- `mkdocs build --strict`
- `make -C examples/repofix bootstrap`
- `make -C examples/repofix test`

## Editing rules

- Keep the main text organized by system capability, not by week.
- Put calendar-based learning plans only under `docs/appendix/`.
- Teach Python and TypeScript features where RepoFix first needs them.
- Prefer minimal examples that can be tested and explained.
- Never suggest running model-generated commands on the development host.
- Before Daytona integration, use only FakeModel and FakeExecutor for agent-loop tests.
- Keep shared Run, Event, Error, and Artifact values aligned with `examples/repofix/contracts/`.
- Keep navigation in `mkdocs.yml` aligned with files under `docs/`.

## Done means

- `mkdocs build --strict` succeeds.
- Companion tests succeed without cloud credentials.
- New pages are reachable from navigation.
- Code fences specify a language where practical.
- Cross-page links remain valid.
