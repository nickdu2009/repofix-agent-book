# RepoFix shared contracts

These JSON Schemas are the source of truth for values exchanged by Go, Python, and TypeScript. Application code may generate types or validate hand-written adapters from them, but it must not invent a separate status or event enum.

Run the deterministic structural check from the companion root after
`make bootstrap` has installed the pinned JSON Schema validator:

```bash
make contract-test
```

The validator checks each Draft 2020-12 schema, representative positive and
negative payloads, and the RunStatus/RunEvent string constants declared by Go
and TypeScript. Service-level boundary tests additionally prove that adapters
reject malformed payloads before they enter domain state.
