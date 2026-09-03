# Security policy

## Reporting

Report vulnerabilities privately via
[GitHub security advisories](https://github.com/tzavislan/kumihimo/security/advisories/new)
— not in public issues. You should hear back within a week.

## Supported versions

No version has been released to a package index yet; `main` is the only
supported line. Once versions ship, the latest release is the supported one.

## Scope worth knowing

Kumihimo's library makes no network calls and runs no LLMs (a repo
invariant, enforced by tests). The editor (`kumihimo edit`) serves
localhost only. The braid preview renders user-authored Markdown with raw
HTML escaped and link/image URL schemes allow-listed — findings in that
sanitizer are in scope and very welcome.
