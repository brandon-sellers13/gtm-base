| Finding | Status | Evidence |
|---|---|---|
| N1, saved content receives working-copy flag results | Closed | CS3 requires the same saved revision for checks and returned documents; Plan 1 assigns the changes to Unit 2.1 and requires the unsaved `status: skipped` regression test at line 532. |
| N2, persistent mark conflicts with runner classification | Closed | Plan 1, lines 519 and 531, makes an existing mark override omission of the unattended word and requires no question or wait. |
| N3, Plan 1 omits preserved file exceptions | Closed | Plan 1, lines 142 and 359, preserves validated root `.claude/settings.json`; line 359 also preserves empty `skills/.gitkeep`. |
| Astra 2, ordinary-document write boundary | Closed | CS3 retains authority-checked saves and excludes unsaved edits; the corresponding saved-revision reader and check changes now have an assigned unit and regression test. |
| Astra 3, unattended marking starts too narrowly | Closed | CS30 marks any unattended invocation before work begins and treats every later run in that conversation as unattended. |
| Astra 4, blanket `.claude/` ban | Closed | CS23 and Plan 1 now agree on the validated root settings exception, matching `release-b:trust_surface.py:127` and `:181`. |
| Astra 7, file rules reject required files | Closed | CS19 exempts `SKILL.md`, fixes example depth and admits the empty placeholder; Plan 1 now preserves that placeholder, matching `release-b:layout.py:191`. |
| Fable M5, unattended marking | Closed | CS30 requires the scheduled prompt to start with the runner; Plan 1 explicitly tests subsequent starts without the unattended word. |

No new findings. The changes introduce no identified contradiction with the requirements, Plan 1 revision 2.6 or release-b, and leave no unbuildable requirement for Units 4.2a, 4.2b or 3.1.

**Verdict: ready for Brandon's signature as written.**