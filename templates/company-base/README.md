# Your company base

This folder is your company's marketing context in one place. It holds what your
AI assistant needs to read before it can do real marketing work for you, and it
holds the record of how that context stays current as the business moves.

## What each folder holds

The folders follow the five parts of the CLASS framework, and one more holds
the approvals.

**context** is what is true about the business, and everything the assistant
reads for meaning. It holds one file for each subject: your goals, your
product, your ideal customer profiles, your buyer personas, your positioning,
your messaging, your voice, your design, and your metric definitions. Each
customer segment gets its own file in `context/icps`. `context/map.md` is the
map, which says where everything lives and carries two settings you can change.

**learning** is how the base gets better. `learning/changes` holds one dated
entry for each context change, which is anything that happened that makes a
document here no longer true. `learning/corrections` holds what each approved
fix changed, and why. `learning/lessons` is kept for lessons from results,
which arrive later.

**access** holds `stack.md`, which says where your material lives, which tools
read it, and where finished work is saved. It never holds a password, a key,
or a token.

**skills** is kept empty for now. It will hold the written steps for each
recurring job once your team has settled who may approve a change to one.

**standards** holds what good work looks like for each job, and what needs
approval before it is used.

**work** holds the approvals. `work/confirmations` holds the record of the
owner saying that a file is still right. `work/inbox` is where you drop meeting
notes and transcripts for the assistant to read. `work/proposals` holds
suggested changes while they are being prepared.

**CODEOWNERS** lists the files that need the owner's review before a change to
them is accepted. **gate-allowlist.txt** lists the exact pieces of text the
outgoing-content check is allowed to let through.

## Two things to know

The owner address in these files is a placeholder. When your base is created,
the setup step replaces it everywhere with your own work email address.

Everything in this folder is shared with everyone you invite to the base, so
treat it as a document your whole team can read. The two exceptions are
`work/inbox` and `work/proposals`, which stay on your own computer and are never
shared.
