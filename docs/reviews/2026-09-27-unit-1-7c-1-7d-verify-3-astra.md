Reviewed `d2bdfa7..fa7d9ca` read-only. All five original cases are closed, but the markup fix introduces one ordinary-prose regression. Evidence combines source inspection and executed in-memory probes; filesystem-writing tests were not rerun.

| Finding | Status | Evidence | Does the test fail without its fix? |
|---|---|---|---|
| Lock namespace splits between sessions | **Closed** | `fsutil.py:109–126` derives locks from the seat folder. In-memory probes produced identical paths under different temporary directories. Both seat and `locks/` undergo ownership, permission and symlink checks. | **Yes** for the namespace test, corroborated against baseline code. The three directory tests **error** on the baseline because `_lock_home` did not exist, rather than reaching their security assertions. |
| Writer proceeds without its lock | **Closed** | `fsutil.py:157–174` refuses writers after open or `flock` failure. Injected failures returned `no-writing-lock`; failed `flock` also closed the handle. | **Yes**, by inspection. Baseline probe reproduced `held=True, handle=None` after an open failure. |
| Malformed claim names acted on | **Closed** | `review.py:716–741` requires ASCII digits, exactly 16 lowercase hexadecimal characters and a supported basename. All six malformed examples returned `None`; valid page and confirmation names remained accepted. | **Yes** for malformed names, corroborated against baseline parsing. The well-formed-claim test passes without the fix and is a preservation check. |
| Blank line inside quoted attribute bypasses markup rule | **Closed, with regression below** | Both supplied markup tests passed in memory, including the multiline quoted attributes. | **Yes** for the two blank-line payloads, executed with the old rule restored in memory. Oversized-tag cases and standalone comparisons pass with either rule. |
| Redundant kept-aside copy after restoration | **Closed** | `review.py:761–790` recognizes matching device/inode pairs. A simulated retry removed only the claim; baseline code instead allocated `original.kept-aside-1.md` and returned failure. | **Yes**, by inspection and the baseline retry probe. |

The other requested checks found no defect. Owner-held `0700` and ordinary `0755` directories are accepted; `0775`, `0777`, foreign ownership and symlinks are refused. Without `fcntl`, writers proceed and sweeps remain disabled. Source inspection found no remaining test writing to the real seat folder, including inherited environments in writer subprocesses.

**New finding, medium: paragraph-separated comparisons and quoted replies are refused.** At [adopt.py:619](/Users/brandonsellers/Build/gtm-base/.claude/worktrees/agent-adb18d6bfdbbaf313/plugins/gtm-base/lib/gtmbase/adopt.py:619), feeding the entire document to `HTMLParser` lets a comparison consume a later paragraph’s `>` as its closing delimiter. This ordinary text passes the previous rule but now raises `AdoptionRefused("screened")`:

```markdown
CAC<LTV.

> Our customers want faster reporting.
```

The same failure occurs with `Keep CAC<LTV at all times.` followed by a quoted reply, or with a later paragraph containing `Win rate >20%.`. Prices, comparisons and quoted replies tested separately pass.

**Smallest fix:** make residual-markup recognition distinguish paragraph-separated comparison prose from tags while preserving detection across quoted attribute values. Add these combined cases to the comparison test and retain the blank-line attribute regressions.

**Verdict: ready with the listed changes.**