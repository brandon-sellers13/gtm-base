---
title: "Moved: brand design system plan"
type: feat
status: superseded
date: 2026-09-05
---

# Moved

This plan now lives in the personal website repository, which owns the shared design language as of
2026-09-05:

`~/Personal/Brandon_Sellers_Website/docs/plans/2026-09-05-001-feat-brand-design-system-plan.md`

It moved because the website is the only surface that consumes CSS today, it is already a git
repository with its own plans directory, and Netlify deploys from it, so the brand checks the plan
adds can gate the real deploy path. Keeping it here would also have coupled a live site and a
published newsletter to the direction of an unreleased product.

This repository stays the read-only source for the approved palette (`brandkit/approve-palette.json`)
and the brand constraints (`brandkit/brand-lock.json`, `brandkit/brand-lock-b4-refinement.json`).
Nothing in the moved plan writes to `brandkit/`.
