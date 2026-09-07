## 1. Attack the candidate

**Use a separate default location if you want, but reject the claim that a `content_root` link makes the location disappear.** It creates a second activation boundary with its own identity, recovery, permissions, and consent problems.

These findings come from read-only code inspection and official documentation. Failure scenarios below are inferred from those mechanisms, not reproduced in a live Claude Code session.

First, the current implementation differs from the stated rule. After rejecting a repository parent, it tries `~/<Company>/gtm-base`; only when that company folder is also inside a repository does it try `~/GTM Bases/<Company>/gtm-base`. See [location.py:235](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/location.py:235).

| Failure mode | What breaks or becomes a new obligation |
|---|---|
| **The new field silently disappears.** | Adding `content_root` at creation is insufficient. [machine.py:32](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/machine.py:32) permits only `root`, `base_id`, and `remote`; loading discards unknown fields at line 145, saving reconstructs those three fields at line 255, and `append_joined` creates only those fields at line 348. Every path must preserve and validate the addition, including future migration. |
| **Renaming the content folder silently disables activation.** | An exact stored path will no longer match. Existing move recovery works because the relocated **base** carries an identifier, which [session_start.py:459](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/session_start.py:459) uses to rewrite its old root. An ordinary content folder carries no equivalent identity. Recovering by company name or basename would risk selecting another client. You need an explicit relinking flow. |
| **Deleting and recreating the content folder can activate the wrong company.** | Deletion leaves an orphaned association. If another project later occupies the same path, path equality activates the old base. Validating the base’s identifier does not validate the identity of the content folder. [paths.py:340](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/paths.py:340) currently authenticates the actual candidate base through its root and identifier; the proposed alias has no comparable evidence. |
| **Two companies name the same content folder.** | A consultant names `~/Clients` for both companies. Two valid bases now match one `cwd`. Current ambiguity handling counts physical `gtm-base` children, not matching joined entries, at [paths.py:329](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/paths.py:329). First-match selection would leak one company’s context into another’s session. Registration must reject collisions, and resolution must fail closed on legacy or forged collisions. A physical base and an alias matching the same folder also need an explicit conflict rule. |
| **An external content drive is unavailable.** | The central base remains usable, which is a benefit. But the user cannot normally start in an absent directory, so the advertised shortcut is unavailable. A different drive later mounted at the same path introduces the reuse problem above. Do not invalidate the joined base merely because its source folder is absent. Existing raw-state loading deliberately preserves unavailable roots across unrelated writes at [machine.py:176](/Users/brandonsellers/Build/gtm-base/plugins/gtmbase/machine.py:176); alias handling needs the same distinction between unavailable and forgotten. |
| **Two people share one computer account.** | They share `machine.json`, the joined list, and per-base seat state. A content association cannot distinguish them. The plan already acknowledges shared account state at [plan:97](/Users/brandonsellers/Build/gtm-base/docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md:97). Central placement adds a company-name collision if they independently create bases for the same company. This is account-scoped behavior, not person-scoped isolation. |
| **Creation succeeds but recording the association fails.** | The base becomes real at the rename, then the joined entry is written at [create_base.py:310](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/create_base.py:310). Opening the original content folder after that failure reveals no child base and provides no recovery evidence. The existing recovery promise assumes the person opens somewhere the resolver can discover the base. Hiding its location makes this failure harder to recover from. |

**Opening `~/GTM Bases/<Company>/` already works without the link.** The parent itself need not be base-shaped. The resolver enumerates its `gtm-base` child, checks the child’s shape, and checks its joined identity. A joined child gets the daily block; an unjoined child reaches the trust check and base-shaped question. Opening `~/GTM Bases/` does not recursively select a company. That is useful isolation, not a discovery bug. See [paths.py:266](/Users/brandonsellers/Build/gtm-base/plugins/gtmbase/paths.py:266) and [session_start.py:384](/Users/brandonsellers/Build/gtm-base/plugins/gtmbase/session_start.py:384).

**Plugin activation is not Claude Code workspace activation.** Matching `content_root` does not change Claude’s working directory, load the external base’s project settings, or grant access to it. Claude documents separate workspace permissions and project settings; out-of-scope operations can require additional approval. The external base’s `.claude/settings.json` does not become the content folder’s settings because Python returned its path. [Claude security](https://code.claude.com/docs/en/security), [Claude settings](https://code.claude.com/docs/en/settings).

Consequently:

- A globally enabled plugin may resolve the alias, but a plugin enabled only through the base’s project settings cannot rely on that alias to start itself.
- Passing `trust_surface.check(base_root)` checks the base, not the content folder’s instructions, settings, or surrounding workspace. The check starts at the supplied root in [trust_surface.py:275](/Users/brandonsellers/Build/gtm-base/plugins/gtmbase/trust_surface.py:275).
- Opening a new base still entails Claude’s trust process. Relocation does not remove it. The plan specifically anticipates a separate prompt for a nested repository at [plan:84](/Users/brandonsellers/Build/gtm-base/docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md:84); the exact current prompt sequence needs a live walkthrough.
- Copying settings or instructions into the content folder to make this work would violate J14’s prohibition on those writes.

**The cloud risk is real, but the proposed guarantee is too strong.** The template excludes `work/inbox/` from Git at [.gitignore:1](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/templates/company-base/.gitignore:1). That controls Git tracking, not a separate synchronization service. A push gate cannot stop a cloud client uploading files. [Git ignore documentation](https://git-scm.com/docs/gitignore).

Ordinary `~/GTM Bases` is outside the Desktop and Documents folders covered by Apple’s iCloud feature. It therefore escapes **that particular setting**, assuming it is a normal directory with no redirection. Apple explicitly documents automatic synchronization of new files within Desktop and Documents. [Apple’s iCloud documentation](https://support.apple.com/en-us/109344).

It does not escape a service configured to synchronize the home directory, a redirected ancestor, or a later change in sync settings. Moreover, [location.check_parent:165](/Users/brandonsellers/Build/gtm-base/plugins/gtmbase/location.py:165) checks neither synchronization nor repository ancestry. The proposal-time repository check is not repeated by the creation-time guard. Even today’s final fallback can sit beneath an existing `~/GTM Bases` repository.

Synchronization can produce inconsistent repository files; **“will corrupt Git state” is not established by this review**. The stronger, sufficient objection is that raw transcripts and approved confidential material can leave through a channel the plugin never reviews.

**Backups expose another missing distinction.** The base holds documents, history, and the inbox. `~/.gtm-base` holds machine associations and per-base working state, including worktrees, as [paths.py:128](/Users/brandonsellers/Build/gtm-base/plugins/gtmbase/paths.py:128) shows.

- Restoring only the base does not restore the account’s joined association or seat state.
- Restoring only the seat directory does not restore the base’s documents.
- Restoring both under different paths still requires recovery.
- A backup can retain transcripts after their working copies are deleted.

Time Machine exclusions are separate settings; Apple also notes that excluded items remain in local snapshots. Central placement is not a backup exclusion or a promise of permanent deletion. [Apple’s Time Machine documentation](https://support.apple.com/guide/mac-help/exclude-files-from-a-time-machine-backup-mh15622/26/mac/26).

**Release two makes the association explicitly machine-local.** The private remote backs up tracked base history, not `machine.json`, raw inbox files, or the original marketing folder. A second person chooses their own destination under [plan:115](/Users/brandonsellers/Build/gtm-base/docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md:115). Their content folder may be different or nonexistent. Never transport the first person’s `content_root` through the remote; ask separately if aliases become a supported feature. Remote-ID migration must preserve local associations through every intermediate state.

Finally, the amendment cost is understated. Beyond J14 and J15, central placement changes **J16’s build-beside promise**, J19’s return instructions, the folder-scoped Key Decision, and R5’s literal “inside the working folder” wording when the session runs in external content. See [requirements:73](/Users/brandonsellers/Build/gtm-base/docs/brainstorms/2026-09-05-join-and-onboarding-requirements.md:73) and [R5:62](/Users/brandonsellers/Build/gtm-base/docs/brainstorms/2026-09-04-current-without-integrations-requirements.md:62).

Amendment r2.2 does not justify persistent content access. Its preview and narrowing rules explicitly preserve the frozen consent list at [plan:581](/Users/brandonsellers/Build/gtm-base/docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md:581). Naming a source folder once must not become permission to reread it whenever an alias activates.

## 2. The strongest case for keeping the base beside the content

**The company folder is the person’s existing unit of work.** Keeping its base there makes the product understandable through Finder, preserves their filing system, and avoids a second registry of relationships.

This argument is particularly strong for consultants who already organize everything by client. A central `GTM Bases` folder organizes by software instead of ownership. It makes bases easy to enumerate while splitting every engagement across two places.

The current design also has useful recovery properties:

- Moving the company folder moves its base with it. The base identifier enables existing relocation recovery when the old root disappears.
- The physical `gtm-base` child makes the association visible and naturally limits a content folder to one base.
- A second person can choose their own company folder without reproducing someone else’s path.
- A source-folder rename does not require maintaining a separate source-to-base mapping.

**Repository nesting is a tooling inconvenience, not proof of inevitable corruption.** Git explicitly recognizes embedded repositories and warns when they are added. The plan already requires operations to use the resolved base root, which addresses accidental execution against the parent repository. [Git add documentation](https://git-scm.com/docs/git-add), [plan:104](/Users/brandonsellers/Build/gtm-base/docs/plans/2026-09-05-001-feat-join-and-onboarding-plan.md:104).

The strongest warning-only policy would let an informed person accept the parent-tooling interference and additional trust prompt. It would preserve location consistency rather than making “this folder happens to contain history” determine where the product lives.

**Its fatal weakness is synchronization.** A warning does not prevent a transcript upload. Nor can the plugin quietly add parent exclusions without breaking its no-existing-file-edits promise. Someone accepting a warning does not make R5’s “never synced” statement true.

Warning-only placement is defensible only if R5 is explicitly weakened to a user-managed condition. That is a privacy-contract change, not a small onboarding adjustment.

## 3. Recommendation and smallest implementation

**Default new bases to `~/GTM Bases/<Company>/gtm-base`, retain physical folder activation, and defer `content_root` activation.** Allow another suitable location when requested, including beside content, but refuse known synchronized locations and repository nesting.

The trade-off is explicit: users must learn where their base lives and open it. In exchange, release one avoids an alias lifecycle, ambiguous client selection, and the false promise that resolving a path also configures Claude’s workspace.

The runner-up is beside-content placement for verified local, non-repository folders, with the central location as fallback. It preserves existing organization but adds more location-dependent onboarding behavior.

The smallest coherent changes are:

| Area | Change |
|---|---|
| **Location proposal** | Change [location.py:198](/Users/brandonsellers/Build/gtm-base/plugins/gtm-base/lib/gtmbase/location.py:198) to propose the central path directly. Preserve company-name validation and existing-target refusal. If names collide, ask for a distinguishing company folder name; never silently reuse a base. |
| **Actual destination guard** | Extend `check_parent`, which creation already calls, to check repository ancestry and known sync locations through resolved ancestors, including when the target parent does not exist yet. Recheck before creating the partial folder. Unknown sync configuration must remain explicitly unknown, not be labeled safe. |
| **Activation and state** | Leave `paths.resolve_base` and the joined schema unchanged. Preserve activation from the base and its direct parent. Do not relocate existing bases automatically. |
| **Creation and recovery** | Keep the sibling partial folder and rename sequence. Validate its parent too, because approved content exists in the partial folder before the final rename. Continue showing the actual destination so interrupted setup remains recoverable. |
| **Requirements and guide** | Amend J15 and J16, the build-beside decision, location copy, and closing instructions. J14 and J19 retain their physical activation rule. Clarify R5 to mean the inbox is inside the base, excluded from shared history, and unsupported in synchronized locations. State separately that user-managed backups may retain it. Preserve r2.2’s source consent and previews unchanged. |
| **Release two** | Offer the same default while allowing the second person to name another suitable parent. Apply identical destination checks before the partial download. Explain that the private backup covers approved base history, not original sources, raw inbox files, or local seat state. |

No folder convention can enforce an absolute “never synced” promise against arbitrary backup software or future user changes. If that wording remains absolute, neither candidate satisfies it. The plan must define the enforceable boundary instead of treating `~/GTM Bases` as one.

The exact location proposal should be:

> “May I create your company’s base at `~/GTM Bases/<Company>/gtm-base`, where you’ll open Claude Code to use it?”

When sync coverage cannot be established, ask separately:

> “Does any app automatically copy this folder, or your whole home folder, to cloud storage?”

The trust explanation should be:

> “Claude Code will ask whether you trust this new folder before using its project settings.”

Before calling the change complete, verify central placement, both physical activation paths, company-name collisions, synchronized or repository ancestors, interrupted creation, moved-base recovery, and an unavailable external destination. Then observe one marketing lead return to the base in a second session. That last check tests the actual cost of the recommendation: whether the explicit location is understandable enough to use again.
