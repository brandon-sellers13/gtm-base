---
date: 2026-09-04
topic: gtm-base-scope
focus: GTM Base scope v1 (the core plugin, the company repo convention, shared skills and plugins)
---

# Ideation: GTM Base scope v1

## Codebase Context

There is no GTM Base repository yet. Grounding came from four sources: the scope document (`~/Obsidian/Vault/Work/GTM-Base/2026-09-04-gtm-base-scope-v1.md`), the donor codebase being archived (`~/Build/profile-base-app`, whose transcript prompts, ICP schema, seed skills, and March 29 proposal rules carry over), the reference plugin layout (`compound-engineering` 2.60.0 in the local plugin cache, especially the `ce-compound` writeback pattern and `ce-compound-refresh` as a stale-check analog), and the doctrine block in `~/Personal/CLAUDE.md` (five kinds of place, three arrows back, human approves in v1, reads are local files). The Gridwise `weekly-planning` skill served as the model company skill.

Past learnings that shaped the critique: distribution is the product; the per-read MCP model was the regretted decision; approve exactly what the reviewer saw; pull and rebase before proposing; agents surface gaps and humans write copy; hold v1 at six skills; three prior scope reviews accepted every expansion and the product was archived five months later; every outward label must pass a no-jargon test for a marketer.

### Mechanics facts found during critique (verified against code.claude.com docs and the local plugin cache)

1. Branch protection and rulesets on private repos require GitHub Team or Enterprise. On GitHub Free, enforced owner approval does not exist. The scope assumed it was free.
2. Marketplace plugins are always copied to `~/.claude/plugins/cache`. A marketplace pointing at the local working clone still produces two copies, and a merged skill change reaches a seat only after a plugin update. Background refresh of a private HTTPS marketplace cannot authenticate by default; SSH remotes avoid that.
3. A SessionStart hook is output-only. It cannot ask the user anything. Conversational steps must be injected instructions Claude acts on at the first turn. SessionStart also fires on resume, clear, compact, and fork, so a pull on every SessionStart would run mid-session.
4. The docs describe no precedence or override rule between a dependent plugin's skill and a same-named core skill. Use distinct names, or have core skills read company overrides from context files.
5. A company plugin's `hooks/hooks.json` runs on every seat at every session start. Merge rights to `plugins/` are remote code execution on every laptop.

## Ranked Ideas

### 1. Current without integrations
**Description:** A `context/work/decisions.md` ledger where each entry carries date, decided_by, source link, the context paths it affects, and a review_by date. `stale-check` starts from this ledger and flags any affected file whose `last_confirmed` is older than the decision, with no transcript or Slack access required. Transcripts and pasted threads are dropped into a gitignored `context/work/inbox/` and consumed by `learn-from-call`, which is the optional pass that populates the ledger. Owner confirmation ("is the ICP still true as written?") is a skill or a hook-injected instruction answered at the first turn, never a hook prompt.
**Rationale:** Two of the six v1 skills depended on integrations nobody had designed. This makes both usable on day one, keeps every read local, and turns the article's own example (the ICP file that predates Tuesday's meeting) into a deterministic check. All three critics kept it.
**Downsides:** A dropped file is still a person carrying context in, so it must be framed as the on-ramp to connectors or it undercuts the series' own definition. The ledger is hand-maintained and can itself go stale.
**Confidence:** 85%
**Complexity:** Low
**Status:** Explored

### 2. The series module is the seed
**Description:** Every STEAL THIS artifact and every module output in the `ai-native-marketing` repository ships in GTM Base frontmatter shape, ready to propose into a company base. The ICP and positioning module (Oct 19) fills `context/strategy/`; the agent roster module (Nov 9) fills `plugins/<company>-gtm/agents/`.
**Rationale:** Zero code. It is the only idea that produces users, it ties the free article, the paid repository, and the consulting sprint into one motion, and the Oct 19 date forces the schema to lock.
**Downsides:** Frontmatter must not make STEAL THIS read as a teaser or cost the artifact its standalone use.
**Confidence:** 90%
**Complexity:** Low
**Status:** Unexplored

### 3. One schema, and a skill is context with a procedure
**Description:** One frontmatter schema across context files and skills (`kind`, `owner`, `last_confirmed`, `sources`, `status`, plus `correction_class` on corrections). Rubrics such as drift-grade's five messaging dimensions live in `context/strategy/messaging-rubric.md`, and the skill is a thin runner that reads them, so a company customizes behavior by proposing a change to a context file, never by forking a skill. Corrections are one dated file per merged proposal under `corrections/`, not an append-only log. Each skill carries an `examples/` folder with one or two owner-approved input and output pairs.
**Rationale:** It is Brandon's published position ("better CLAUDE.md, not more skills") made structural. It keeps the skill count flat as companies customize, removes the hottest-file conflict from the corrections log, and sidesteps mechanics fact 4 because nothing needs to shadow a core skill.
**Downsides:** Claude Code ignores custom frontmatter fields, so schema validation is a script the plugin owns. The examples folder is a convention only until a bench exists.
**Confidence:** 80%
**Complexity:** Medium
**Status:** Unexplored

### 4. The hook contract and the safety floor
**Description:** The SessionStart hook runs only on startup and resume, never on compact. It prints which base loaded and one line of "since your last session: N changes," pulls fast-forward only after a dirty-tree check, and on any failure (conflict, dirty tree, expired token, offline) prints exactly one plain sentence naming the state and the one command that fixes it, then injects the last-known-good map with an "as of <date>" stamp. Dirty local edits are offered as a proposal, never discarded. Raw transcripts live only in a gitignored folder. A PreToolUse gate on push and PR creation scans the diff for keys, tokens, emails, and phone numbers. `plugins/` has stricter ownership than `context/`, and `propose-change` refuses to touch it by default.
**Rationale:** The hook is the only surface a marketer sees, so plainness there is the whole user experience. Three data-loss and security risks close for the cost of design rules.
**Downsides:** None material. Revocation removes repo access but cannot recall clones already on laptops; the join guide must say so.
**Confidence:** 85%
**Complexity:** Low
**Status:** Unexplored

### 5. One proposal, three approval channels
**Description:** The pull request body is the frozen artifact: before and after in plain prose, evidence, confidence, and the rule being changed. It renders identically in Claude through `review-proposals`, on the GitHub PR page or mobile app, and as an email or Slack message the owner answers "approve" or "reject: reason" to, with a Claude Code seat applying the decision and crediting the owner. Given mechanics fact 1, enforcement is advisory on GitHub Free regardless, so the channel matters more than the gate.
**Rationale:** Resolves the one open conflict in the critique. The scope guardian wanted GitHub as the only approve screen; the marketer lens said the founder never opens GitHub. Both are right about different people. The body format is v1 work; the email and Slack channels are the first v2 slice.
**Downsides:** Email or Slack approval means a seat merges on the owner's behalf, so the audit trail records the operator unless the body records the approver. Sender verification needs care.
**Confidence:** 75%
**Complexity:** Medium
**Status:** Unexplored

### 6. Capture the paste
**Description:** A mode of `propose-change` for the moment someone had to paste context into a session by hand. It files a missing-context proposal (which kind of place, suggested path, the pasted text as a draft, the asker credited). The count of open missing-context proposals per kind is the base's coverage number.
**Rationale:** It instruments the wedge itself, the step whose context was not pasted. It gives a consulting sprint and the newsletter's THE RESULT section an honest before-and-after number.
**Downsides:** Depends on people remembering to invoke it. Not a seventh skill; a mode of an existing one.
**Confidence:** 70%
**Complexity:** Low
**Status:** Unexplored

### 7. Notes as evidence, not truth
**Description:** `context/notes/<person>.md`, append-only, `status: personal`, never treated as company truth. Proposals cite lines from it as evidence; `stale-check` and `learn-from-call` read it for "the owner already expected this" before flagging. No Obsidian or Plaud bridge in v1.
**Rationale:** The fifth kind of place had no read or propose path in the scope, and it is the one layer no vendor can supply.
**Downsides:** Author-only is a convention on GitHub Free. A per-person path rule needs a paid plan to enforce.
**Confidence:** 75%
**Complexity:** Low
**Status:** Unexplored

### Accepted into existing skill specifications, not standalone ideas
- `drift-grade` also reads `context/work/` for sibling pieces in flight and reports contradictions between them (the "across" argument).
- `join` creates the repository, CODEOWNERS, and plugin skeleton through `gh`, with a plain-English handoff note for the settings that need an org admin or a paid plan.
- Multi-change runs use a set-id branch prefix so a bad run can be found and reverted as a unit.
- The hook prints which base loaded; a PreToolUse deny on paths outside the resolved base is a v1.1 item for multi-client operators.

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Generated map.md that prints only when changed | Suppressing the map breaks "loaded every run"; the generator is a build step v1 does not need. The "since last session" line survives in idea 4. Defer the generator. |
| 2 | Read-through telemetry (local receipts, citation footer, heartbeat ref) | A per-session push is a fourth arrow back; usage counts on a private repo have no line to pipeline. A citation footer per run may return later as a proof device. |
| 3 | Guest seat via signed tarball and invite code | Rebuilds the v3 hosted tier inside v1 with a shared long-lived token, and validated invite codes need a server. |
| 4 | Proposal sets with "approve all high-confidence" and auto-downgrade | A workflow engine that hollows out human-approves-everything before any run has produced thirty changes. Set-id prefix kept. |
| 5 | Ownership modes config (solo, org, agency) | New state and a new devil's-advocate agent for a user who has not made one proposal. Revisit with the first multi-owner team. |
| 6 | One clone, not two | Infeasible. The plugin cache copy is mandatory (mechanics fact 2). |
| 7 | Claims as the unit, files as compiled views | A database and a compiler between the human and readable files. This is ProfileBase again. |
| 8 | Context inside the product monorepo with drift-grade as CI | Puts marketers under engineering's repo rules and access; destroys the per-company repo that is also the marketplace. |
| 9 | Agent-portable mirrors (AGENTS.md, .cursorrules generators) | Three adapters before one has a user. The constraint "no Claude-only syntax in SKILL.md bodies" is free and kept. |
| 10 | /sanitize with upstream flow into the public starter | Needs a human gate and consent language; a client-wall leak into a public starter fails the board-review test. Defer. |
| 11 | /recalibrate and /rebench | Both feed on a corrections log and fixtures that do not exist yet. The correction-class tag and the examples folder ship now inside idea 3. |
| 12 | Email as the git remote (format-patch) | Abandons the shared store and branch review entirely; the email approval channel survives inside idea 5 without this. |
| 13 | Traveling personal base across client bases | Crosses client walls the moment a client session reads it. |
| 14 | GitHub PR page as the only approve screen, drop review-proposals | Right for engineers, hostile to the founder approver, and enforcement is plan-gated anyway. Folded into idea 5 as one of three channels. |
| 15 | Owner confirms via a hook yes/no | Infeasible as stated (mechanics fact 3). Reshaped inside idea 1 as a skill or injected instruction. |
| 16 | Scores history file for drift-grade trends | A store, and v1 has no store. The sibling read is kept in the drift-grade spec. |

## Session Log
- 2026-09-04: Initial ideation. 48 raw ideas from six framed agents, merged to 26 unique plus 5 cross-cutting syntheses, critiqued by three agents (scope, mechanics, doctrine and marketer). 7 survived. Five mechanics facts recorded above and folded into the scope document the same day.
- 2026-09-04: Brainstorm started on idea 1, Current without integrations, with a stress test of whether v1 should launch with the integrations instead.
