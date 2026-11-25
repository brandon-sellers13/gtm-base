---
title: "feat: The GTM Base web app, version one (a team on one base)"
date: 2026-11-24
status: draft, waiting for Brandon's check-in before any code
origin: Brandon's decisions of 2026-11-24 (build the web app now, productize from the start, keep review cycles short); the v2 decision of 2026-09-05 in the scope doc
---

# The GTM Base web app, version one

## What this builds

A small web app that lets a whole marketing team work on one company base. A person signs in with GitHub, creates the company's base (or connects one that already exists), invites teammates, reads every document laid out by the five CLASS parts, and accepts or discards the changes that teammates' Claude Code sessions propose. It also catches any change that reached the base without going through an approval and offers a one-click undo.

The app is a view onto the company's GitHub repository and never a second copy of it. Everything it shows is read from the repository, and everything it does is a commit, a pull request, or a pull request decision in that repository. If the app went away tomorrow, the base would still be complete and still work in Claude Code.

Two kinds of people use it:

1. **People who work in Claude Code.** They get onto the base from a link the app gives them, and their proposals show up in the app.
2. **People who never open Claude Code,** usually the founder or the head of marketing who owns the positioning. For them the app is the only screen they need.

## Why now, and what it is for

Brandon decided on 2026-11-24 to build the app before a real second team exists, because it is cheap to build and it makes the idea visible to a buyer in a way a command-line plugin cannot. GTM Base is a product from the start, and setting up a base for a client team is part of what Brandon sells, not the only route to revenue. The path to pipeline is direct: the app is what a prospective client sees in a demo, and it is what the client's executive uses after a consulting sprint ends.

The app also replaces the hardest part of the join plan's second release. Units 6 and 7 of that plan (back up a base to GitHub, invite a teammate, join from a link) were designed around the GitHub command-line tool on each person's computer, with warnings about sign-in tokens and an install step. The app's GitHub App can create the repository and add teammates itself, so those two units shrink to two small plugin changes.

## What version one includes

1. Sign in with GitHub.
2. Create a new base repository from the GTM Base template, or connect an existing repository that already holds a base.
3. Read the base: every document grouped by CLASS part, rendered as a page, with its owner, the date it was last confirmed, and the open context changes that name it.
4. A proposals inbox: every open pull request that carries GTM Base's proposal line, shown as its "What changed, Why, Evidence, Confidence" sections, with Accept and Discard. Only the document's owner can accept.
5. Invite a teammate, and give them the one line to say in Claude Code to join.
6. Changes that skipped approval: any commit on the main branch that did not come through an accepted proposal is listed with Keep or Undo.
7. The GTM Base look, taken from `brandkit/brand-lock.json` (the overlap mark, DM Sans).

## What version one leaves out

| Left out | Why |
|---|---|
| Sign-in without a GitHub account (email) | The scope doc's v3. Every person still needs a free GitHub account in version one. |
| Editing a document in the browser | Changes come from Claude Code as proposals with evidence. A browser editor would be a way around the proposal and approval flow, which is the product's core. |
| Blocking direct edits outright | See "Approval on GitHub Free" below. Version one catches and undoes instead. |
| Working out which documents are out of date | That logic lives in the plugin. Repeating it in the app risks two answers that disagree. Version one shows the facts the plugin wrote (open changes, last confirmation) and leaves the verdict to the plugin. |
| Billing and pricing | A decision for Brandon after the app exists (see "For Brandon"). |
| Slack, email notices, scheduled runs, company skills | Later releases. |
| A database | The repository is the only store. A signed cookie holds the session. |

## Approval on GitHub Free

Private repositories on GitHub's free plan cannot enforce branch protection, so anyone added to the repository can change any file on the main branch directly. GitHub's documentation says protection on private repositories needs GitHub Pro for a personal account, or GitHub Team for an organization (Team lists at four dollars per person per month as of November 2026).

Version one handles this by catching and undoing. A change that skipped approval is visible in the app and one click reverses it, and git keeps the full history either way. For a small team that trusts each other, the realistic risk is a mistake, not misconduct.

Later, the app should not rebuild what GitHub already sells. When the repository's plan supports protection, the app offers to turn it on with one click. When it does not, the app says plainly which upgrade turns it on. A second option, where teammates get read-only access and the GitHub App is the only thing that writes, may work on the free plan but is not verified and would change how Claude Code sessions send their proposals. It stays a later decision.

## How it is built

| Choice | Decision | Reason |
|---|---|---|
| Framework | Next.js with Tailwind, deployed on Vercel | Matches the ProfileBase app, whose layout and components can be reused as a starting point. |
| Where the code lives | A `web/` folder in this repository | One place for the template, the fixtures, and the app. Can move to its own repository later. Brandon to confirm (see "For Brandon"). |
| GitHub access | One GitHub App with the narrowest permissions that do the job (contents, pull requests, administration only if creating repositories needs it) | The app acts as the GitHub App, never with a person's own token stored anywhere. |
| Who owns a document | The `owner:` email in the document's front matter, matched against the signed-in person's verified GitHub emails | No second list of owners. When Plan 1's Unit 4.2a merges, the app reads the map's settings block instead. |
| Secrets | The GitHub App's private key, its client secret, and the cookie secret are stored as sensitive variables in Vercel | These can act on people's repositories, which meets the bar for marking them sensitive. |

## Units

There are nine units: six in the web app and three in the plugin. The web app units can start now, built against the CLASS layout that Release B ships. The three plugin units wait until Release B is merged, because they change code Release B also changes.

### Web app

- [x] **W1. The skeleton, sign-in, and a short spike.** Done 2026-11-24: live at https://gtm-base-app.netlify.app on Brandon's personal Netlify team, with its own GitHub App ("GTM BaseLive"); sign in checked there. Register the GitHub App, set up the Next.js app on Vercel, and add sign in with GitHub. The spike answers two questions before any other unit starts: whether the GitHub App can create a repository in a personal account (if not, the person makes an empty repository in one click and the app fills it), and whether an organization on the free plan can give a teammate read-only access. Done when Brandon can sign in on the deployed app and the two answers are written into this plan.
  - *Spike answer 1 (from GitHub's documentation, 2026-11-24):* yes. The "create a repository for the authenticated user" endpoint accepts a GitHub App user token that has the narrow "Repository creation" permission (or "Administration"), and the app gets access to the repositories it creates. W2 adds "Repository creation" to the app.
  - *Spike answer 2:* not settled. GitHub's documentation on repository roles, individual access and base permissions names no plan for the built-in Read role (only custom roles are marked Enterprise Cloud), which suggests Read is available on the free plan, but nothing says so. It gets tested live in W5 with a free organization.
  - *Built so far (2026-11-24, branch `claude/web-app-w1`):* the Next.js app in `web/` with the GTM Base look, a development-only "Connect to GitHub" page that registers the GitHub App through GitHub's manifest flow (the app's credentials go straight from GitHub into `web/.env.local`), sign in with GitHub with an encrypted session cookie, an invite-only allowlist, sign out, and a home page listing the accounts the app is installed on. Brandon created the development app ("GTM Base Dev 744f") the same day after a fix (GitHub refuses a webhook address on localhost, and refuses the account-level email permission in a manifest, so W4 adds that permission in the app's settings). Sign in, the accounts list (empty, the app is not installed yet), the session cookie being unreadable from the page, and sign out were all checked in the browser. Not done: the Vercel deployment and its own GitHub App for the live address.
- [x] **W2. Create or connect a base.** Done 2026-11-24 (PR #10): create from the template; connecting is giving the app access to a repository that holds context/map.md. Create a repository from the base template (`plugins/gtm-base/templates/company-base`), or connect an existing repository that has `context/map.md`. Done when both work against a test account.
- [x] **W3. Read the base.** Done 2026-11-24: the base page by CLASS part and a page per document, checked on brandon-sellers13/gtm-base-test. Show the documents grouped by CLASS part, render each one, and show its owner, its last confirmation (from `work/confirmations`), and the open context changes that name it (from `learning/changes`). Done when Brandon's Gridwise base, once backed up in unit P1, reads correctly in the app.
- [x] **W4. The proposals inbox.** Done 2026-11-24. The plugin (Release B) opens proposals but never merges or closes them, and counts a merge as the owner's confirmation when the commit that lands the change on the main line (first parent) is authored with an owner's email; the app builds that merge commit itself, authored with the owner's verified email, and discarding closes the pull request. Checked on gtm-base-test: the plugin's own query returns the accept commit with the owner's email. List open pull requests carrying the proposal line, render their sections, and let the document's owner accept (merge, and record the owner's confirmation the way the plugin already does for an accepted proposal) or discard (close, with an optional reason). Before building, check exactly how the plugin records that confirmation (decided 2026-09-06), so the app writes the same thing. Done when a proposal made in Claude Code is accepted in the app and the plugin then treats the document as confirmed.
- [ ] **W5. Invite a teammate.** Built 2026-11-24 (in the app, per Brandon; both apps now hold Administration: write, the only permission that adds collaborators). Teammates sign in when they can reach a base on an allowed account. The first security review ran on the whole app and its eight findings were fixed. Open: the real invite test with a second GitHub account. Known limit, stated on the team page: on GitHub's free plan an invited teammate can push straight to main; W6 flags it, and the plugin should not treat a commit's author email alone as an owner's confirmation (a teammate can set any author). Add a teammate to the repository through the GitHub App, and show them the one line that joins the base from Claude Code. Done when a second GitHub account is invited and joins.
- [ ] **W6. Changes that skipped approval.** List commits on main that did not come through an accepted proposal, with Keep (recorded in the repository) or Undo (a revert commit). Done when an edit made directly on GitHub.com shows up and Undo reverses it.

### Plugin (after Release B merges)

- [ ] **P1. Back up a base to its repository.** Replace today's refusal of every push from a base (the first-backup review was never built) with a short review that shows what will go up and screens it for anything that looks like a credential, then pushes to the repository the app created. Done when Brandon's Gridwise base is in its repository.
- [ ] **P2. Join a base from a link.** A teammate says the line the app gave them, and the plugin copies the base onto their computer in the usual place and sets them up as a seat. Done when the second account's Claude Code reads the base.
- [ ] **P3. Working on a shared base.** Recording a context change, and the setup closing, stop refusing a base that has a shared copy and send their writes as proposals instead. The push check refuses a direct push to main from a seat, so everything a Claude Code session changes arrives in the app's inbox. Done when a context change recorded by the second account appears in Brandon's inbox.

## Review standard for this build

Following Brandon's rule of 2026-11-24, units get no review of their own. The end-to-end run below is the main check. There are two security reviews in the whole build, one pass each: the first before anyone other than Brandon signs in to the app (covering sign-in, the GitHub App's permissions and invites), and the second before the plugin units P1 and P2 are released (covering what a backup sends and what joining writes onto a teammate's computer). A second round happens only if a review finds something critical. Tests check what each piece does, not the exact wording of every sentence.

## How we know it is done

One run from start to finish, with Brandon and a second GitHub account:

1. Brandon signs in and creates the Gridwise base's repository in the app.
2. Brandon backs up his existing Gridwise base from Claude Code (P1).
3. Brandon invites the second account, which joins from Claude Code (W5, P2).
4. The second account records a context change in Claude Code, and it appears in Brandon's inbox (P3, W4).
5. Brandon accepts it in the app, and the plugin then treats the document as confirmed (W4).
6. Someone edits a document directly on GitHub.com, the app lists it, and Undo reverses it (W6).

## For Brandon

1. **Where the code lives.** Recommended: a `web/` folder in this public repository. The alternative is a separate private repository, if you want the app's code kept private for the product.
2. **Who can sign up in version one.** Recommended: invite-only, from a short list you control, until the end-to-end run above passes.
3. **The domain and the app's name** on GitHub (the GitHub App needs a public name and a callback address).
4. **Pricing,** after version one exists and you have shown it to someone.

## What else is still open in GTM Base (for context)

- **Release B:** no units left to build. It needs the re-run of the fidelity replay on the summarize-first build, then a merge. It ships as 0.5.0, because main used 0.4.0 for the settings guard.
- **Plan 1 (company skills and the Meta ads skill):** nine units, four of them built (4.1 signed, 2.1, 2.5a and 4.2a on a branch, not merged). Five are left: 3.1, 4.2b, 2.4a, 3.5 and 3.6.
- **The rest of the roadmap after Phase 1:** about eight more units (messaging and voice, design, the remaining context files, the sources-of-truth file, updating GTM Base, drift grade, content brief, outbound sequence), not planned in detail yet.
- **The join plan's Units 6 and 7** are replaced by this plan (W2, W5, P1, P2).
