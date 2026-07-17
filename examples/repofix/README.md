# RepoFix companion workspace

This directory is the executable companion project for the RepoFix book. The
book lives in `docs/`; all commands shown in implementation chapters run from
this directory unless a chapter says otherwise.

## Start here

```bash
make bootstrap
make help
make test
make contract-test
```

`make bootstrap` creates a local `.venv` and installs the pinned Python and Web
tooling. `make test` covers the Python Agent/API, Go Fake control plane,
TypeScript contract layer, deterministic Eval, and shared Schemas. Intentionally
broken fixture repositories are excluded from that target. No default target
contacts a live model or cloud sandbox.

To prove that the first fixture starts in a broken state, run:

```bash
make fixture-baseline
```

This target requires pytest exit code `1`, exactly one pass and one failure, and
the known failing node. Import and collection errors are not accepted as a valid
baseline.

Read the matching chapters before changing files:

- [Cloud workspace](../../docs/foundations/cloud-workspace.md)
- [Buggy calculator fixture](../../docs/foundations/fixture.md)

## Safety boundary

Before the Daytona chapter, the companion project uses only deterministic
`FakeModel` and `FakeExecutor` test doubles. Do not run a live model's commands,
or code written by a live model, in this workspace. Codespaces and a local
checkout may contain credentials; they are development hosts, not sandboxes.

## Checkpoints

The whole repository is versioned together. Published chapter checkpoints use
the following tag convention:

```text
chapter-04-start
chapter-04-complete
```

First list the tags that are actually included in the current release:

```bash
git fetch --tags
git tag --list 'chapter-*'
```

If the target start tag exists, create your own branch from it instead of
committing on a detached tag:

```bash
git fetch --tags
git switch -c work/chapter-04 chapter-04-start
```

The names above illustrate the convention; they do not guarantee that every
chapter tag has already been published. If a target tag is absent, follow the
chapter from your own branch at the current `main` baseline and do not invent
the tag locally.
