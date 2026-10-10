1. **Blocker, CS11 and User Flows. Acceptance can bypass approval authority.**

   CS11 lets “a person” accept an untrusted manifest, and the diagram then proceeds to execution. It does not distinguish an approved version this computer has never accepted from bytes nobody approved. This matters because [Unit 4.2b explicitly includes a change that no approval covers](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:566). The document neither establishes who may authorize those bytes nor explains what “who approved it” displays when nobody did.

   **Smallest fix.** Separate consent to run an already approved version from approval of previously unapproved bytes. The latter must pass CS3 and Unit 1.7e, record a new approval of the complete manifest, and only then establish trust. The display must explicitly identify missing approval.

2. **High, CS3 and CS22. The restriction on changing ordinary documents has no corresponding file-write boundary.**

   CS3 says only the authority set may make a document change, but CS22 restricts direct writes only under `skills/`. On `release-b`, `write_hook.py:23` expressly permits assistant edits to context documents, and `:835` allows ordinary context writes through. Unit 4.2a changes approval and confirmation checks; Unit 4.2b’s write-hook changes remain skill-specific. A normal file-writing tool therefore remains an uncovered path, without requiring the hostile command access excluded by CS14.

   **Smallest fix.** Require supported file-writing tools to enforce CS3 for ordinary documents and refuse base-content writes in unattended conversations. Define how existing unapproved hand edits are handled, and assign the necessary hook changes and refusal tests to Unit 4.2a. This implements the fixed ownership decision rather than weakening it.

3. **High, CS30. “A conversation started as unattended” is narrower than the approved rule.**

   [Unit 4.2a marks a conversation when the runner starts an unattended run](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:398), including an existing conversation. CS30 can instead be implemented as a check of how the conversation originally started. An attended conversation that later starts unattended work would escape that wording. Option D does not supply the missing behavior automatically; `unit-1-7e-d:approval.py:694` still creates an approval ticket and asks.

   **Smallest fix.** Say that any unattended runner invocation marks its conversation before work begins. Every subsequent approval path must refuse before creating a ticket or question, and a later attended invocation must not clear that mark.

4. **High, CS23. The blanket `.claude/` ban rejects the required base configuration.**

   CS23 refuses `.claude/` “everywhere in a base, exactly as today.” The actual rule requires root `.claude/settings.json` and permits that precise exception, subject to configuration validation (`release-b:trust_surface.py:127` and `:181`). The company-base template contains it. Implementing CS23 literally makes a standard base invalid.

   **Smallest fix.** Preserve the existing validated root `.claude/settings.json` exception and refuse every other `.claude/` entry. Describe the existing restriction accurately.

5. **Medium, CS21 and CS15 to CS17. The settings contract prevents the planned business assignment.**

   CS21’s exhaustive list excludes `business`. Yet [Unit 2.1 reads skills as documents and derives their business from their folder or settings](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:435). `skills/meta-ads/SKILL.md` has no business folder. Adding `business: driver-app` would make it fail CS21. CS15 to CS17 also omit the document business-setting operation, the fifth operation explicitly required by Unit 4.2a.

   **Smallest fix.** Admit `business` with a value validated against the map, and restore the narrowly defined, authority-approved operation for changing it. Preserve the plan’s preview, approval binding and recording requirements.

6. **Medium, CS28 to CS30. The unattended answer omits an already decided behavior and overstates the write prohibition.**

   The document explains what happens to an untrusted skill, but not a trusted skill whose context is flagged. P43 and [Unit 3.1’s outcome table](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/plan-1-meta-skill-3d436e/docs/plans/2026-10-10-002-feat-plan-1-company-skills-and-meta-skill-plan.md:510) require unattended work to report the flag, hold dependent work, and continue independent spend-protecting work without asking. “Nothing is written” also reads as prohibiting the runner’s required start/completion records and the engine’s separately authorized work.

   **Smallest fix.** Incorporate Unit 3.1’s outcomes and precedence explicitly. Limit “nothing is written” to the refused approval, confirmation, settings, creation and acceptance operations. Preserve operational records and authorized engine work.

7. **Medium, CS19 and CS20. The exhaustive file rules reject their own required files.**

   CS19 requires `SKILL.md` while requiring every filename to be lowercase. CS20 refuses every hidden file, but existing bases contain the explicitly permitted empty `skills/.gitkeep` (`release-b:layout.py:191`). No migration removes it. “Files under” an example directory also leaves the permitted depth less precise than the promise of “exactly three shapes.”

   **Smallest fix.** Exempt the exact filename `SKILL.md`. Preserve the empty root placeholder outside skill manifests, or specify its removal. State the complete example-file shape, including its final filename and permitted depth.

8. **Low, CS2, CS9 to CS12, CS26 and Deferred to Planning. Several terms obscure what Brandon is signing.**

   “Map” and “source map” identify different files without naming them. “Hash,” “seat,” “contract check,” and “settings grammar” require technical interpretation; the trust guarantee depends on understanding several of them.

   **Smallest fix.** Identify the ownership/settings map as `context/map.md` and the source map as `access/stack.md`. Define a hash as a file fingerprint, use “computer” consistently, and explain the contract check as an automatic check of the supplied example outputs. Keep parser and merge terminology in implementation notes.

**Verdict: not ready.**