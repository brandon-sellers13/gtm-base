# MKT1 "multiplayer AI" compared with GTM Base

Date: 2026-09-19. Source: newsletter.mkt1.co/p/multiplayer-ai-team-mkt1, read through a fetch-and-summarize tool. The page is partly paywalled, so this covers the visible part only, and the details below are a summary by a small model that was not checked line by line against the page.

## What they built

A three-person marketing team (Emily Kramer owns it) shares its AI setup through GitHub repositories installed as Claude Code plugins: one personal repository, one team repository, and one public repository that ships skills to paying subscribers through an MCP server on Cloudflare, with access synced to the Substack subscriber list. They report more than a hundred internal skills and more than thirty scheduled routines, most of them run in the cloud.

Two tests frame it. The vacation test asks whether the work runs when someone is offline. The new computer test asks whether someone is fully productive quickly on a new machine.

Instructions and context are kept apart. Skills and one CLAUDE.md hold instructions and rules (including voice). Context stays in the tools it lives in (Airtable, Asana, Drive, Obsidian, Attio) and is read through MCP connections only when a skill needs it. One "sources of truth" skill maps where each dataset lives and what the fallback is.

Skills have a lifecycle: a duplicate check before building, a review that runs the skill against three real inputs, a publish step, an update step after a session where Claude proposes edits and a person approves, and weekly and monthly audits for stale or duplicate skills and rules. Changes are posted to Slack in a fixed format.

Problems they name: context and skills that lived on one person's laptop, long context pasted into skills, plugins that do not refresh on their own, and thin usage data from GitHub.

## Where the two systems differ

| | MKT1 | GTM Base today |
|---|---|---|
| Shared skills and routines | The core of the system | Not built. Ruled out of the current release |
| Strategy context (who we sell to, positioning, voice) | A voice skill and rules in CLAUDE.md. No owner, no confirmation, no record of what changed | The core of the system: owned files, confirmations, context changes, proposed fixes |
| Where context lives | In the source tools, read live through MCP | Markdown in the base, read locally. Source tools are read only to learn what changed |
| Keeping things current | Audits of skills and rules | Staleness detected from recorded context changes, fix drafted, owner approves |
| Safety | None described. A team repository of skills is code that runs on every seat | A check on what leaves the machine, a refusal to pull code or instruction files, a trust check before a folder is treated as a base |
| Who can set it up | A technical founder who builds in Claude Code daily | Meant for a marketing lead who never sees git |
| A map of where data lives | Yes, a dedicated skill | The map holds two settings and a description of folders |

## What to take from it

1. Shared skills are what the market is already building by hand. Move "skills that use the base" and "company skills shared across seats" up the roadmap. GTM Base's addition is the trust model and the approval flow.
2. Adopt the vacation test and the new computer test as success criteria. The new computer test is the second-seat join plus a backup. The vacation test needs scheduled runs, which are out of scope today.
3. Grow the map into a real sources-of-truth file: where each kind of data lives outside the base, which connected tool reads it, and the fallback. This is the "mapped" property in the definition.
4. A skill lifecycle: examples as tests (the scope already called for an examples folder per skill), an update-after-session step that proposes edits for approval, and audits. This is propose-a-change applied to skills.
5. Plugins do not refresh on their own. We hit the same thing. A plain "update GTM Base" step is needed.
6. A fixed-format note when something in the base changes, posted through the person's own Slack connection, so a team sees changes without opening anything.

## What not to take

Reading strategy context live from source tools on every use. It is slower, it costs more, and nothing confirms it is still true. Their data and work context fit that pattern. Strategy does not.

## A separate idea, not GTM Base

They ship skills to paying newsletter subscribers through an MCP server gated by the subscriber list. That is a distribution model for the paid series repository, and it is worth its own look.
