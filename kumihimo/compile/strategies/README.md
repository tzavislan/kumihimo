# strategies — how a braid gets its shape

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The strategy registry: Section (the unit every strategy produces), the built-in registrations, and third-party loading via the kumihimo.strategies entry-point … |
| `grouped.py` | Sections by membership: each in-target becomes a titled section introduced by its own node, ungrouped prerequisites lead, ungrouped leftovers trail, and sectio… |
| `linear.py` | The simplest braid: every selected node in one numbered sequence, already in deterministic topological order. |
<!-- END GENERATED INDEX -->

## What this is

A strategy turns the deterministic global order into sections: `linear` is one
numbered sequence; `grouped` (the engineering default) makes each in-target a
titled section introduced by its own node, with ungrouped prerequisites
leading and leftovers trailing, sections ordered by the real dependencies
between their members. Third parties register through the
`kumihimo.strategies` entry-point group — packaging metadata alone, no config.
A strategy promises order; rendering is weave's job.
