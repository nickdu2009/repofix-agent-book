# RepoFix companion workspace

This directory is the executable companion project for the RepoFix book. The
book lives in `docs/`; all commands shown in implementation chapters run from
this directory unless a chapter says otherwise.

## Start here

```bash
make bootstrap
make chapter-list
make chapter-prepare CHAPTER=chapter-01
make chapter-check CHAPTER=chapter-01
```

`make bootstrap` creates a local `.venv` and installs the pinned Python and Web
tooling. Chapter preparation copies the read-only `start/` skeleton to
`.work/chapter-NN/`; it refuses to overwrite existing work. The first structural
check normally fails until the TODO and completion marker are resolved.

After the chapter-specific behavior command passes, compare your choices with
`labs/chapter-NN/solution/`. The solution is a review aid, not the starting
point. Run the full deterministic suite with `make test`; no default target
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

## Chapter labs and checkpoints

Every chapter uses the same layout:

```text
labs/chapter-04/start/       read-only skeleton
.work/chapter-04/            your ignored working copy
labs/chapter-04/solution/    reference for later comparison
```

`chapter-check` performs structural checks and never executes learner code.
Practical chapters also list an explicit Python, Go, or TypeScript behavior
command. See `make help` and the matching book chapter for the exact sequence.

Stable releases may additionally publish immutable tags using this convention:

```text
chapter-04-start
chapter-04-solution
```

Tags are optional snapshots, not a prerequisite for the checked-in labs. Never
invent a missing tag or modify a detached tag directly.
