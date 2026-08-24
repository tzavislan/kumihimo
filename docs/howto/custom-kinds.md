# Custom kinds and templates

The core is domain-agnostic; kinds carry the domain. Three moves, all in
`kumihimo.yaml`.

## Extend a pack kind

```yaml
kinds:
  from: engineering
  task:
    fields:
      component: {type: str}
      reviewed: {type: bool, default: false}
```

Pack fields survive the merge; same-named fields are replaced.

## Define kinds from scratch

Skip `from:` entirely and the manifest is the whole kind system — this is the
shipped `examples/fieldnotes` plan, a research/essay graph:

```yaml
kinds:
  source:
    fields:
      cite: {type: str, required: true}
      stance: {type: choice, options: [supporting, opposing, mixed]}
  claim:
    fields:
      confidence: {type: choice, options: [low, medium, high], default: medium}
```

Field types: `str`, `int`, `bool`, `list` (of strings), `choice` (with
`options`). `required: true` without a `default` makes omission a check
error; a `default` is applied in memory (templates and filters see it) but
never written into your files.

## Give a kind a template

A kind's `template` is Jinja2 (sandboxed), either inline in the manifest or a
path to a file under the plan root:

```yaml
  source:
    template: |
      {% if number %}
      ### {{ number }}. Source: {{ node.title }}

      {% endif %}
      Cite as: {{ node.fields.cite }}

      {{ node.body }}
```

Resolution order: manifest template → the pack's `templates/<kind>.j2` → a
built-in generic that renders title, *After* line, fields, and body. The
context a template sees:

| Variable | Contents |
|---|---|
| `node` | `id`, `kind`, `title`, `body`, `fields` (effective — defaults applied), `priority` |
| `number` | the item's global number, or none for section intros |
| `after` | the composed prerequisite line ("2. v2 endpoint surface; …") |
| `deps` / `dependents` | lists of `{id, title, number}` |
| `group` | `{id, title}` of the section's group, when sectioned |
| `in_others` | titles of other memberships |
| `links` | `{to, rel, title}` annotations |
| `independent` | true when the item doesn't depend on the one above it |
| `plan` | `{name, description}` |

The whole document wrapper (the *cord*) is also a template you can replace:
set `compile: {cord: my-cord.j2}` and the file under your plan root receives
`plan`, `preamble`, `epilogue`, `diagram`, `stubs`, `sections` (each with
`title`, `intro`, `entries`), and `warnings`.
