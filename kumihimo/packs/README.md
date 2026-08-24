# packs — shipped kind definitions

Data, not code: each subfolder is a kind pack a manifest can pull in with
`kinds: {from: <name>}`. Schemas live in `kinds.yaml` (loaded by
`core/kinds.py`); render templates join them at M2 (used by `compile/`). Packs
live here — outside both `core/` and `compile/` — precisely so `core` can load
schemas without importing template machinery.
