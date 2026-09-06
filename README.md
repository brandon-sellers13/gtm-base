# GTM Base

GTM Base is a Claude Code plugin plus a per-company folder of context files that
an AI assistant can read and keep current on its own. The folder holds your
strategy, your numbers, your plan, and your notes. The plugin reads meeting
notes and decisions you drop into it, proposes changes to those files with the
evidence attached, and asks the person who owns a file to confirm that it is
still right when it starts to go stale. Every accepted change is recorded, so
the record of why a file says what it says lives beside the file itself.

## Repository layout

```
.claude-plugin/marketplace.json   the marketplace manifest
plugins/gtm-base/                 the plugin itself
templates/company-base/           the template a new base is built from
docs/                             requirements, plans, and the join guide
tests/                            the test suite and its fakes
```

## Running the tests

```
sh tests/run.sh
```

The runner puts `tests/fakes` at the front of `PATH` so the tests never reach
the network, adds `plugins/gtm-base/lib` to `PYTHONPATH`, and runs
`python3 -m unittest` over everything under `tests/`. Python 3 standard library
only, and everything must import on Python 3.9.

## Status

Version 0.1.0 is the scaffold. The plugin installs and nothing acts yet. No
hooks, no skills, no agents, and no MCP servers.

## Joining

See [docs/join-guide.md](docs/join-guide.md).
