# Changelog

## 0.2.2 (2026-09-06)

- Join, the list of what will be read: the yes is asked as a yes to read those documents in order to draft the three files, saying that none is copied into the base or changed. It had read as a list of files about to be imported. Found on Brandon's first real setup run.

## 0.2.1 (2026-09-06)

- Location: when the folder named for the company is itself the folder just turned down (a company called Gridwise working in ~/Gridwise, which keeps its own history), the base goes to a folder kept for bases inside the home folder instead of the refused place. Found on Brandon's first real setup run. The sentence now says the folder keeps its own change history rather than that it is looked after by another tool.

## 0.2.0 (2026-09-06)

- Setup now drafts your ideal customer profile, one decision entry, and your positioning, one at a time, and shows each one to you whole before anything is written. Each draft is a complete document rather than a set of questions, so you read it and say yes, change it, skip it, or ask what is wrong with it, and nothing is asked of you one field at a time. The profile always carries who these companies are, what they already know they need, what they do with the product, and what they use today; the four other sections appear only when what you named actually said something about them, because a heading with nothing behind it is worse than no heading.

- Nothing a draft says is written down until it has been read for the things that must not be written down. A character a reader of the file would never see, somebody's email address, somebody's phone number, and anything shaped like a key all send the step back to be drafted again, and what you are told is the kind of thing that was found and never the value itself. The one exception is the settings line carrying the address of the base's own owner, which this plugin writes there itself a moment later.

- A draft is refused outright when it uses a long dash, when it reaches for one of the fourteen words that say nothing, or when it leaves a placeholder such as "TBD" where an answer should be. The refusal is one short reason and the same step is offered again. Your own note to yourself, written in square brackets as a call for you to make, is not a placeholder and is kept.

- Each file you approve is written into the base together with the line recording that you approved it, as one piece of saved work, dated today and carrying the identifier of the setup run. The decision entry is named by GTM Base rather than by the assistant, so the rest of the plugin can find it again, and it says it came from setting the base up. A file you skip is written saying so, with nothing in it, and the next session offers to finish what is missing.

- Setting up only ever writes files that were not there. A file the base already holds is refused rather than edited, a folder with unsaved changes in it stops the next file until they are dealt with, and a decision entry naming a file outside the base's own context folder is refused before anything is written.

- Setup now reads the folder you name, and it shows you the list before it opens anything. The list has the files it would read on one side and, on the other, what it left out and why, counted by class, so you can see that four names said they held keys and two documents were of a kind this plugin does not open. Links are listed and never followed, whether they point at a file or at a folder, and a file whose first line says it holds a key is left out even when its name says nothing. A folder that is your home folder or anything above it needs a second yes in so many words, and a folder that looks like it holds work for two different companies stops and asks which one this is for.

- Saying yes to that list is now the moment nothing more may leave your computer. The set of files is fixed at that point, so a file dropped into the folder a minute later is refused until a new list has been shown and agreed to, and the safeguard refuses every send and refuses the GitHub tool for the rest of the session.

- Everything read is wrapped and screened before it reaches the assistant. Each piece of text is checked for anything a reader of the file would not see, refused if it writes the wrapper's own lines, and then labelled with one sentence saying that what follows is something you wrote down rather than instructions to follow. Word processor files and slide files are named with the request to save them as a PDF or paste the part that matters, because this release opens only writing, plain text, and rows of values itself.

- Saying yes to the offer now builds a base. The first file you approve is written into a new folder called `gtm-base` beside the material you named, together with the record of your approval, and both are saved as one piece of work. Everything is built in a folder named `gtm-base.partial-` plus a random ending, and the single rename of that folder to `gtm-base` is the moment your base exists, so a run that stops early leaves your approved draft sitting safely in that half built folder and never leaves half a base behind.

- Your base gets its own work email address, written inside the base and nowhere else. The address already on the machine is used when there is one, and when there is none you are asked for one and it is checked before it is used. The machine's own git settings file is never written to, and the machine's setting for what a new repository's first line of work is called is ignored, so every base starts the same way whatever the machine is set to.

- The base is built from the template, with the placeholder owner address in the map, in the ideal customer profile, and in the list of text the outgoing check lets through all replaced with the real address. The settings file that installs and pins the plugin for the team is written with exactly two settings. **Before a second person joins any base, the release step has to put a real forty character identifier in that settings file in place of the row of zeros that ships today.** A base created before that happens will install nothing for the person who joins it.

- The template every base is built from now ships inside the plugin as well, at `plugins/gtm-base/templates/company-base`. That copy is the one a real run uses, because an installed plugin is fetched on its own and the repository's copy is not there beside it. A test holds the two copies identical file for file.

- New: `location.py` decides where a base goes. It proposes the folder you named, warns and proposes a folder named for your company inside your home folder when the folder you named is already looked after by another tool, and refuses your home folder itself unless you say yes a second time, a folder that already holds something named like a base, and anywhere inside the folder GTM Base keeps for itself. The company name is checked so it can never become a hidden folder or a path.

- New: `create_base.py` also carries the recovery rules. A half built folder is listed and deleted only after you are asked. A folder that got as far as being renamed is left to the question the session start already asks about a folder shaped like a base. A base the account has a record of with no safeguard installed is repaired. A seat folder for a base whose folder never got anything saved in it is cleared away before a new base is built.

- Saying "set up my company base" now runs the whole first session. One skill takes it from the first sentence to the last: what setting a base up does, the one line saying you can stop at any time, the notice that files you approve may later be shared with everyone invited to the base, the single question about where your marketing context lives today, the folder your base will go in shown before anything is created, the list of what would be read shown before anything is opened, and then the three documents one at a time. Every step says what is about to happen before it happens, nothing is ever asked of you one field at a time, and nothing anywhere says how long it will take.

- Every session now ends with one true thing about your base and the way back to it. The closing works out the finding from the base as it stands, in a fixed order: a document you have not written yet, then no decision at all, then a document written from material older than the decision it is meant to reflect, then the plain statement that nothing is out of date yet and the first date GTM Base will watch. It is worked out again every time, so a date you corrected a moment ago changes it. It never claims more than the dates show.

- The closing also says where the base lives, that it is on this computer and nowhere else, and how to open it next time, including that `/cd` moves you there now on recent versions of Claude Code. Keeping a copy of your base somewhere off this computer and inviting somebody else onto it are named honestly as arriving with the next release, and reading a sales call into the base as arriving later than that. Asking for any of them today gets one sentence and nothing more.

- Anything that got in the way while you were setting the base up is written into the base itself, in your own words, in the `corrections` folder, so the next session can see it. It is read for contact details and anything else that must not be saved first, and it is left unwritten rather than cleaned up if it holds any.

- A base is no longer flagged as behind itself. A decision you made in August, written down today, approved alongside the document it affects in the same sitting, now counts as settled by that document's own approval, whatever the two dates are. Before this the first run of a brand new base reported its own ideal customer profile as out of date against the decision that had just been written with it, which was true to the letter of the rule and useless to a person reading it.

- Each setup run now works in a folder of its own inside the folder GTM Base keeps for you, readable by nobody else. It holds what you pasted in and the requests built from it, because the steps that use them happen one after another rather than all at once, and it is deleted at the closing. Nothing in it is ever written into the base and nothing in it ever leaves the computer.

- Security review fixes: join-01, the yes you give to the list of files is now taken against the list you were actually shown. The list is written down when it is shown to you, and saying yes looks at the folder once more and compares the two. If anything changed while you were reading, the yes is refused, you are shown the new list, and you are asked again, so a file that appeared a moment ago can never ride in on a yes that was never about it. join-02, a note you type at the closing is now read from the first character to the last. The one settings line GTM Base writes your own address onto is let through in a document GTM Base itself read back, and nothing else ever is, so a note that merely happens to start with three dashes no longer buys itself an exemption. join-03, every value the setup script prints for the assistant to read is now made safe first, because a file name is whatever somebody typed when they saved the file. A name holding a line break has it replaced, a very long name is shortened, and a name holding a space or an equals sign comes back inside quotation marks, so one line is always one value and a file name can never write a line of its own. join-04, every settings line that is let through the check is now written over with your own address, and the one line setting a base up never fills in is taken off the document rather than kept. Your ideal customer profile and your positioning now carry exactly the five settings this plugin writes and reads, and a draft that invents a sixth is refused by name. join-05, the folder your base is going into is checked again at the moment it is built, not only when it was proposed, because the two happen at different moments and anything could have changed in between. Setting up also refuses to write into a folder this account has not joined, however much that folder looks like a base. join-06, a file that holds a key is now caught when the key sits a few lines down rather than only on the first line, so a key file that opens with a blank line, a comment, or a mark some editors put at the start is no longer offered as an ordinary document. join-07, handing over a paste, a PDF, a web page, or anything a connected tool returned now tells the safeguard this session has read your own material, exactly as saying yes to a folder does. Somebody who never names a folder is now covered by the same rule as everybody else. join-08, the company name is checked everywhere it is used, not only where the folder is named, because it is also written into the request that drafts your documents and it sits outside every wrapper there. join-09, text that writes the wrapper's own lines is refused whatever letter case it is written in.

- Security review fixes, two smaller ones. The reading rules said that anything you paste is never saved anywhere, which was not true. It is held in the run's own folder inside the folder GTM Base keeps for you, nobody else can read it, and the closing deletes it, and that is what the rules say now. And a decision entry naming a file it may not name now comes back as a plain refusal with its own short reason, rather than as the sentence that says something went wrong.

- Correctness review fixes: C1, one document that cannot be used no longer ends the session. A single character a reader would never see, in one file out of five, used to stop every step after it. The rest are read as normal now and you are told which one was left out and why. C2, a step with nothing left to draft from is refused instead of handing back a request with your company name and no material in it. You are told which documents were left out and asked for a shorter paste. C3, skipping is now offered from the second document onward. It was offered on the first one and could never work there, because a skipped document is written into the base saying it was skipped and until the first document is approved there is no base to write it into. C4, a computer with no work email address recorded on it now says so in one sentence and asks for the address, instead of stopping with nothing you can do about it. C5, saying yes to the offer is recorded the moment your base exists rather than at the closing, so somebody who approves their first document and closes the window is not asked again the next morning whether they would like to set one up. C6, closing a second time with the same note no longer throws away the finding and the message that says where your base is. C7, a run that stopped part way now has what it was holding cleared away the next time you start one on a later day, rather than sitting in the folder GTM Base keeps for you forever. C8, a file that says it was changed on a day still to come has its date pulled back to today, and now you are told that happened rather than the pulled back date being shown as though it were the file's own. C9, a document approved or skipped while you are working in the company folder is written into the base inside it rather than into the folder you happened to name.

- Correctness review fixes, two smaller ones. A file is never written with an empty owner line, because a file nobody owns is a file the currency check has nobody to compare against; you are asked for the address instead. And the closing note now goes through the same checks every other write into your base goes through.


## 0.1.5 (2026-09-06)

- Saying "not now" is now remembered. Seen live on 2026-09-06: the assistant said the right sentence back and the account still recorded no answer at all, so the offer returned the next session. The plan had put the recording step in the join skill, which is not built yet, so nothing in the shipped plugin could write the answer down. A new script, `scripts/offer_answer.py`, records it, and the text the assistant is given at the start of a session now names that script by its full path so it is run before the sentence is said. Set up and join are still left to the step that makes a base or joins one, because an account that said yes and then stopped halfway has not set anything up.

- The reply to a greeting now reads as one reply rather than two unrelated blocks. Seen live on 2026-09-06: the offer, then the sentence that starts setup again, then "Hello. What are you working on today?" with nothing joining them. The branch for a greeting or a question now ends with one sentence that turns to what the person asked, which is "That can wait, so here is what you asked for," and the reply carries on from there.

## 0.1.4 (2026-09-06)

- The setup offer now keeps asking until the person answers in words. It is made once a session, as part of the first reply, in whatever folder they are working in, for as long as the answer is unset. Being shown the offer and hearing nothing back used to count as "not now", which meant a person who read the offer inside a reply and carried on with their day never saw it again anywhere. Brandon's decision of 2026-09-06.

- Only three things are an answer: set up, join, and not now. After an explicit not now nothing changes from before, so the offer stays out of the projects the person works in and comes back only in an empty folder or in a folder that already looks like a base. Nothing changes for a base already joined or for the question a base-shaped folder asks.

- Every reply to "not now" carries the one sentence that starts setup again, and the offer inside a reply now ends with that sentence too, so a person who reads it and does nothing still has the way back in front of them. The text the assistant is given also tells it to say the offer once and not to repeat it later in the same session.

- The join guide is rewritten around what the app actually does: open Claude Code anywhere, type anything at all, and the reply opens with the offer.

- The check that reads what a command would send now only reads it when the send comes from a base you have joined, from a folder inside one, or from a working folder GTM Base made for itself. In every other repository on the machine the change, the notes saved with it, the file a GitHub command would send, and the command line itself are no longer read at all. Reading every repository refused ordinary work, including work on this plugin, whose own test files carry addresses and whose commit notes name a second author, and a check people turn off protects nothing. The refusals that need nothing read still hold everywhere: the GitHub commands no skill uses, skipping the safeguard, overwriting the branch the team shares, pointing git at other safeguards, handing git another program to run, naming GTM Base's own records folder, a command that cannot be read, and the rule that nothing may leave a session that has read your own documents. A folder named with `-C` or `--git-dir` that is not a base is no longer refused outright; it is simply not read. Brandon's decision of 2026-09-06.

## 0.1.3 (2026-09-06)

- Live finding: the desktop app renders neither a hook's combined output nor its systemMessage alone; only the assistant's context arrives. A first message that is not an answer to the offer (a greeting, a question) now gets the offer text in the reply instead of the restart sentence. The on-screen half of J1 is recorded as a platform limitation for now.

## 0.1.2 (2026-09-06)

- The check now follows a command that moves itself into another folder before it sends anything: a folder change before a send, or a send from a folder that is not a base at all, was not read. What a send would carry is read in the folder in force at that point, a folder change the check cannot follow refuses everything after it, and a send whose folder cannot be read is refused rather than allowed.

- The refusal sentence shows the plugin's own fixed phrases as written; only file names taken from a diff are sanitized (the live gate had printed "the?command").

- Manifest no longer names hooks/hooks.json; Claude Code loads that file on its own and refused the plugin when it was named twice (found on the first live install, 2026-09-06). The offer and the join guide now say to type the answer as the first message.

- The work done at the start of a session is now declared as two hook entries rather than one, because the single object carrying both halves did not show the person anything. On the first live session (2026-09-06) the offer was recorded as shown, with the session it belonged to, and nothing appeared on screen. The first entry prints only the sentence the person reads, as one object holding that message, and writes nothing at all and reaches nothing over the network. The second prints only the text the assistant reads, as plain text, and is the one that records the session, brings the base up to date, issues the question id, and installs the safeguard. Both work the same decision out from the same inputs, and the combined form is kept for a client that renders it.

- Claude Code runs the two entries at the same time rather than one after the other, so neither may wait on the other. The part that prints what a person sees takes a record carrying this session's own id, on a session that has only just begun, as the other part making the offer right now, and says its half of it. The one sentence that cannot be worked out without reaching the shared copy, the one saying an update carried files GTM Base does not take on its own, is left as a fixed code in this seat's own settings and said at the start of the next session, and the code is cleared only once a later run finds nothing left to refuse.

- An owner accepting a prepared change now counts as that owner saying the
  affected document is right, on the day they accepted it, so the clock starts
  again rather than the same document being asked about next session. When the
  person who accepted it does not own the document, nothing changes: the record
  settles the decision it names and the document still waits on its owner.
  Brandon's decision of 2026-09-05.
- Session-start update refuses anything under the settings folder (`.claude/`), including the one file the join-time trust check allows, because a changed settings file would re-point the plugin itself.

Correctness review fixes (C1, C2, C3, C4, C5, C6, C7, and SEC-5).

- An owner's answer that names the decision it was given about now settles that
  decision whatever day the answer carries, which is what a yes on the day the
  decision was written down looks like (C1).
- A question is used up only when the answer is recorded. Asking the owner what
  changed, refusing something in what they said that must never leave, and an
  inbox with items still waiting are all decided first, so the answer the
  sentence asks for can be given to the same question (C2).
- Answers waiting to be sent are held as a list rather than one at a time, so a
  morning offline can hold several and none is written over. Sending them again
  clears each one on its own and keeps only the ones that still cannot go (C3).
- A run repeated after its own review opened now finishes and tidies up rather
  than reporting the seat's own review as somebody else's (C4).
- Every date compared with a date in the base is the day it is where the person
  is sitting. Only the time on a confirmation line and the moments in this
  seat's own files stay in coordinated universal time (C5).
- A path a decision names that GTM Base will not write is recorded once rather
  than on every reading, and a run that is only looking records nothing at
  all (C6).
- A working folder left with no line of work on it is put back on its own
  before anything is sent, and a failure preparing one is reported as a refusal
  rather than raised (C7).
- The file a change is written to is checked in the folder it is written in, so
  a name that is an ordinary file in one copy of a base and a link to somewhere
  else in another is refused (SEC-5).
- Also: a no about the calendar names the question it answers, so two answers
  about one file weeks apart are two changes; the report window is the 28 days
  it says it is; a reminder put off comes back on the day it says, the same
  boundary a document put off for now uses; and a joined base cannot be pointed
  at a folder another base already claims.

## 0.1.0 (2026-09-05)

Security review fixes (SEC-1, SEC-2, SEC-3, SEC-4, SEC-6, SEC-7, SEC-8, SEC-9,
SEC-10, SEC-11, SEC-12, and C8): the check that reads a command now strips
quotes and backslashes before it looks for git, accounts for every part of a
command that names git, follows a command written inside another one, reads a
send against the folder the command names, refuses the settings and options
that hand git another program to run, and refuses any command that touches the
folder holding this seat's own records. The update from the shared copy now
refuses the same set of names the folder check refuses, compared the same way,
and refuses an update carrying a link. A file name from the shared copy is
checked before it is repeated back, the map is held apart by marks the map
itself cannot end, and the safeguard folder is only made once every reason to
refuse has been ruled out.

Unit 10, the confirmation flow: the owner's answer to the one question a
session asks.

- Added the `confirm` skill and its script. The skill is not one a person calls
  by name. It carries the instructions for showing the document, showing the
  decision behind the question when there is one, asking in plain words, saying
  what each answer does before it is given, and calling the script in the same
  turn as the answer. The assistant never writes in the confirmations folder
  itself.
- Added `lib/gtmbase/confirm.py`, the only thing that ever writes a
  confirmation line. It requires a question this session was given, that has
  not been answered and is less than an hour old, and it refuses while anything
  is still waiting to be read in the inbox, without using the question up, so
  the same question can be answered once those items have been read.
- A yes writes one line carrying the file, the date, the time, the reason it was
  asked, the decision when there is one, and the question, and no address at
  all. Identity is read back from the saved work that added the line. The line
  is prepared in a working folder of its own, read by the same check every send
  passes, and added to the shared copy. The person's own folder is left exactly
  as it is.
- A yes that cannot reach the shared copy is never lost. When the shared copy
  moves underneath it, the answer is written again from where the shared copy
  is now and sent once more; when that fails too, the answer is held in this
  seat's own settings and the next session or the next check sends it.
- A base with no shared copy of its own moves the person's own folder forward by
  that one answer, and only when there is nothing unsaved in it.
- A base where somebody reads every change before it reaches the shared line
  gets a review for the answer instead, and the skill says so.
- A "not now" leaves the document alone for the days the map sets and writes
  nothing anywhere. A no becomes a prepared change: for a question about a
  decision it is the same prepared change the stale check writes, carrying the
  owner's words as evidence; for a question about the calendar the owner is
  asked what changed first, and their answer becomes the change.
- Added a setup path for the answer given when a document is written for the
  first time. It adds the line and stages it, saves nothing, is allowed once per
  document, and only for a document that is not part of the base yet.
- Added the list of questions still waiting for an answer, which the script
  prints when it is run without one.
- The question the hook adds to a session now names the script and says the
  confirmations folder is never written by hand.


Unit 9b, the stale check a person runs and the four week report.

- Added the `stale-check` skill, its script, and `references/rules.md`, which
  states every rule the check follows in plain words: how a decision and a
  document are compared, what counts as a confirmation, the one exemption for
  the day a base is set up, when an accepted record settles a decision, what a
  decision that names no files leads to, and the identifier that stops the same
  work being done twice.
- Added `lib/gtmbase/stale_check.py`. It asserts the base is on the main line of
  work the team shares, brings it up to date when it has a shared copy and
  treats a base with none as up to date, prepares nothing while items are
  waiting to be read in the inbox but still lists what is out of date, reads the
  base, runs the rules, and writes one prepared change for every document a
  decision has moved past. For a decision that names no files it prepares the
  list of files instead, for the owner to approve. It lists the decisions that
  have come up for review and keeps them for the next session, reports a quiet
  ledger with the way to stop it being mentioned, and lists what could not be
  read. A look only run says what it would prepare and writes nothing.
- Added the first run mode: one honest finding, looked for in a fixed order and
  worked out fresh every time, saying either a document the person skipped, that
  no decision has been written down, that a document is older than the decision
  it should reflect, or that nothing is out of date yet and naming the first
  date it will watch.
- Added `lib/gtmbase/report.py`, the four numbers for the last four weeks, all
  of them labelled as this seat's own: what GTM Base caught, how often a
  question was answered yes with every question asked in the denominator, how
  often a proposal was turned down, and how the material read into the base
  arrived. Nothing is estimated, and a zero is written out as a zero.
- Added `lib/gtmbase/base_reader.py`, the one way a base is read into the values
  the stale library works on. The hook at the start of a session and the stale
  check now share it, so two readings of the same folder can never disagree.
- Fixed the rule for the hash an accepted record carries, which had two forms
  and so could never match for a proposal touching more than one file. There is
  now one rule: the hash is taken over every path in the `context` folder the
  record lists, in the order it lists them, read as the accepted change left
  them and joined end to end. `references/pr-body-rules.md` says the same thing.
- Allowed a proposal to name a decision the base already holds without writing a
  second copy of it. A marker naming the proposal's own identifier as the
  decision still means a new decision the proposal has to carry.
- Moved the record of an update this seat refused out of a file of its own and
  into this seat's own settings, as a date, one fixed code, and the refused
  paths as hashes.
- Made the check on the command tool and the check a skill runs before it
  prepares anything ask the same question in one place, so they cannot disagree
  about whether the first send from a base has been reviewed.


Unit 7, turning a staged change into a review the team can read.

- Added the `propose-change` skill, its script, and
  `references/pr-body-rules.md`, which says what the text of a proposal has to
  contain, in what order, and how the hash it carries can be worked out again
  from the change itself.
- Added `lib/gtmbase/compose_proposal.py`: it reads the staged file, refuses a
  change to the map, to the settings at the top of a file, or to anything
  outside the context folder, asks the two conditions that stop anything
  leaving the computer, reads everything the proposal would carry for contact
  details, keys, links, and hidden text, searches for the same change
  everywhere it might already be, applies the change in a working folder of its
  own, writes the decision and the record of what changed beside it, sends it,
  and opens the review. Every step is safe to repeat: a run that stopped
  halfway picks up the folder it left, never saves the same work twice, and
  never opens a second review.
- Added the path for a change somebody made by hand: their own file is left
  exactly as they left it, the source they state becomes the evidence, and the
  same checks run before anything is sent.
- Added `lib/gtmbase/worktree.py`, the working folders under the seat
  directory, one per staged change and one for confirmations. The person's own
  folder never changes what it is on and never loses what they were doing.
- Added `lib/gtmbase/duplicate_check.py`, which finds the one marker line a
  proposal carries in the reviews on the shared copy and in the records already
  accepted, so the same change is never raised twice and one that was turned
  down comes back only when the person says so.
- Added `lib/gtmbase/ghcmd.py`, the one way this plugin runs the GitHub tool,
  and `lib/gtmbase/push_conditions.py`, which asks the same two questions the
  check on the command tool asks, so a skill can say why nothing will be sent
  before it prepares anything.
- Added the decision itself to `templates/proposal-staging.md`, which carried
  only its settings before and so could never have produced a usable entry.


Unit 3, what happens at the start of a session.

- Added `hooks/session-start.sh`, declared in `hooks/hooks.json` as a
  SessionStart hook with no matcher and a 15 second limit, so every kind of
  session start is seen. It checks the prerequisites itself before Python runs,
  because on a fresh Mac the git and python3 names exist as stubs that pass a
  plain lookup, so it asks `xcode-select` instead and prints one install
  sentence when that fails. It exits 0 on every path and writes nothing to the
  error stream.
- Added `scripts/session_start.py` and `lib/gtmbase/session_start.py`. In a base
  this account has opened, every session records its session id and the client,
  and a session that is starting or being picked up again also brings the base
  up to date with the shared copy, adds the map with a trust note and a length
  cap, and asks at most one owner one question with a single use id. An update
  whose incoming files touch the settings folder, an instruction file, or any
  code file is refused with one fixed sentence and the last known good map. A
  base with no shared copy skips the update, says nothing about it, and still
  asks its question. A base still missing a required file offers to finish
  setting it up instead, issues no question id, and writes nothing to the
  asked log.
- Added the setup offer: the first session on an account with no base shows it
  on screen and primes the assistant to act on the answer, once per session id,
  and after a not now it comes back only in an empty folder or a folder that
  looks like a base.
- Added `lib/gtmbase/trust_surface.py`: before a folder that looks like a base
  is offered as one, its whole tree is checked for instruction files, agent
  folders, code files, a folder of plugins, anything under the settings folder
  other than the settings file itself, and links, with every name compared after
  case folding and Unicode composition, and the settings file itself checked for
  exactly two keys, the GTM Base repository, a pinned forty character version,
  and this plugin.
- Added `templates/injection.md`, `templates/offer.md`,
  `templates/base-shaped-question.md`, and `templates/continue-setup.md`, so
  every sentence a person reads sits in one reviewable place.
- Unverified assumption: that one hook may return both the text the assistant
  reads and the text the person sees in a single object. It has not yet been
  seen render in a real session. `render_output` in `session_start.py` is the
  one place that changes if the fallback of two hook entries is needed.

Unit 4, the check before anything leaves the computer.

- Added `hooks/pre-push-gate.sh` and declared it in `hooks/hooks.json` as a
  PreToolUse hook on the command tool with a 20 second limit. It finds python3,
  hands the request over, and refuses when either step cannot be done.
- Added `scripts/push_gate.py` and `lib/gtmbase/gate.py`: it reads any command
  holding `git` or `gh`, works out whether the command would send anything,
  refuses the GitHub commands no skill uses, and reads what a send would carry
  before it runs.
- Added `lib/gtmbase/scan.py` and `lib/gtmbase/redaction_patterns.py`: the added
  lines of a change, the notes saved with it, the command itself, and any file a
  GitHub command would send are read for addresses, phone numbers, key shapes,
  web addresses carrying a key, links to shared documents, paths from inside a
  home folder, and text that would be hidden from a reader. A refusal names the
  file and the kind of thing found, never the thing itself.
- Added the allowed-words file rules: exact words only, comments allowed, caps
  on how many and how long, the whole file thrown away if any line holds pattern
  syntax, and no word can ever excuse a key or a folder that is yours alone.
- Added `lib/gtmbase/marker.py`, the record of a session having read the
  person's own documents, and the two session conditions the check enforces:
  nothing leaves while that record matches, and nothing leaves a base whose
  first backup has not been reviewed.
- Added `lib/gtmbase/install_git_hook.py`, which puts the same check in the
  folder git looks in, moves an existing one aside and still runs it, follows a
  folder named in the account settings, never writes a file the team shares, and
  records a fixed code when it could not be installed.

Unit 1, the scaffold. Nothing acts yet.

- Added the marketplace manifest and the plugin manifest. The plugin manifest
  declares no MCP servers.
- Added `hooks/hooks.json` as an empty event map, so the plugin installs and no
  hook fires.
- Added `lib/gtmbase/constants.py` with the folder paths, size caps, time
  windows, refusal sets, and placeholders the later units share.
- Added the shared library the later units build on: `formats.py` for every
  file the plugin reads or writes, `ids.py` for identifiers that stay the same
  across runs, `paths.py` for the seat folder and for keeping a path inside the
  base, `state.py` for what one seat remembers, `machine.py` for the one record
  of what this account joined, `validate.py` for the map's settings and owner
  addresses, `gitcmd.py` for the single way this plugin runs git, `fsutil.py`
  for writes that either happen or do not, `errors.py`, and `shim.py` for the
  loader every script copies.
- Added the six file templates under `templates/` and a fixture of every
  artifact under `tests/fixtures/`, each one parsed by a test.
- Added `scripts/_shim_template.py` and `scripts/gtmbase_version.py`, the
  smallest script that uses the loader and the target of the packaging test.
- Added the `company-base` template, the join guide, the test runner, and a fake
  GitHub command line tool for tests.
- Added `lib/gtmbase/stale.py`, the stale-check library: it works out which
  context files a decision has moved past, which have gone too long without
  the owner's yes, and the one honest finding a first run reports, from values
  the caller hands in and nothing it fetches itself.
