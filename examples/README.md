# examples — worked plans

Real plans you can load, check, edit, and (from M2) braid. Each is also a test
fixture: `tests/test_example_apiguard.py` holds the repo to the promise that
the shipped examples validate clean and order deterministically.

- **apiguard/** — the PLAN.md §3.3 worked example: seven nodes, all five
  engineering kinds, one milestone grouping, one annotation edge with a
  relation label, and a layout sidecar. Try:

```bash
uv run kumihimo check examples/apiguard
```
