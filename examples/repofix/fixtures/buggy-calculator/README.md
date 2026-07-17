# Buggy calculator fixture

This repository fixture contains one intentional bug: `divide(5, 2)` returns `2`
because `calculator.py` uses floor division.

From `examples/repofix`, run:

```bash
.venv/bin/python -m pytest -q fixtures/buggy-calculator/tests
```

The baseline must report exactly one passing and one failing test. The repair may
change `calculator.py`, but must not change the tests. After replacing floor division
with true division, both tests must pass.
