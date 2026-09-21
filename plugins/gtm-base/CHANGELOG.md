# Changelog

## Unreleased

- A session now opens with nothing to answer. The base records the session, brings itself up to date with the shared copy, and hands over the map and what has changed since last time, and then it stops. No question leads the first reply and no question identifier is issued. The evidence for the change is the first real return session, on the nineteenth of September, which opened by asking whether the base's own map was still right; that is the worst possible first sentence for a working session, and the question was in the way of the work rather than part of it.

- The question itself was moved rather than removed. Saying "review my base" walks everything the base is due a look at, one numbered line per item, with the document shown only for the item you ask to see. Every document it asks about carries its own single-use question identifier, and the yes, the no that becomes a prepared change, the not now that sets a document aside, and the log of what was asked all work exactly as they did when a session start issued them. A prepared change waiting for you to approve it is listed in the same walk, with no question attached to it, because approving a change is not answering a question. The three answers are explained once, at the top, instead of once for every document.

- The base speaks up on its own in exactly one case: a document you are about to use has been overtaken by a context change you recorded. It names the document, the change and the day the change happened, shows the change as the four labeled lines, and asks whether to use the document as it stands, fix it first, or record that it already reflects the change. Using it as it stands writes nothing and leaves the document flagged, because permission to use a document that is behind is not a statement that it is right. Fixing it first prepares the change and waits for you to approve it. Saying it already reflects the change writes the one confirmation line. No work is written before you have answered. All three are recorded by a command of their own, and so are turning the weekly line on or off and asking for quiet; an earlier draft of this entry described those as working when nothing could actually run them.

- One answer settles one change and nothing else. Saying a document already reflects the change you were shown used to settle every older change on that document as well, including ones nobody had shown you, because a confirmation that named one change was also read as an ordinary dated answer about all of them. A confirmation that names a change now settles that change alone, so a document behind two changes is still behind the second one afterwards and the next check says so.

- Everything the four lines carry is read back and acted on by nobody. The words come out of files people type into, and they are handed to the assistant inside an instruction it follows, so a change whose text held the end of the block it was being shown in could write instructions after it. Every value is now put on one line with the markers taken apart, capped at the same length, and shown inside a fence with a sentence saying it is to be read back and not acted on. A file whose name is not plain letters, digits and spaces is called "one of your documents" instead of being repeated back. The rule the session carries also quotes every path it tells the assistant to put on a command line, and the characters a shell reads as an instruction are no longer allowed in any path.

- A check that says nothing now means one thing only: nothing has overtaken that document. Handing it a path it will not answer about, or a base whose records it could not read, used to print nothing and end well, which the rule reads as permission to carry on. Both now say what happened and end badly. A path it will not answer about also reads nothing at all; it used to hand back whatever file that path led to, anywhere on the computer.

- The check finds the document however the path was spelled. An assistant naming the whole path from the top of the disk, a person naming it from where they are standing, a name in letters the disk does not use, and a name that leads through a link all now find the same document. Before this, the most common of those, the whole path from the top of the disk, found nothing and said nothing.

- The review lists every document one change left behind rather than one of them, folds a document that also has a change prepared into one line instead of two, lists prepared changes on a base whose review happens elsewhere, and says plainly when nothing in the base is recorded as yours. It reuses the question it already issued when you ask for it twice, so asking twice no longer counts as asking twice in the numbers, and it issues nothing at all while something is waiting to be read in your inbox, because every answer would have been refused.

- It never claims a fix exists when one does not. It says a change is ready only when a prepared change for that document is really waiting in the folder prepared changes wait in, and otherwise it says plainly that none is prepared and offers to prepare one. A document carrying an unanswered marker and nothing else never interrupts anything; markers belong to the review. The check itself is a lookup in your own base and reaches nothing over the network, which is asserted by a test that fails on any command capable of reaching a remote and by a test that the module loads nothing that can open a connection.

- Inside the three skills that hand a context file to the model, the check runs before the file is read, and this is asserted against what those skills' own scripts really print rather than against a stand-in that chose to call it. Every one of those paths also holds the file apart as data, and the text a session carries now says in as many words that everything inside a context file is data and never an instruction.

- Outside a skill, the flag rests on an instruction. The text a session carries tells the assistant to run the check before it uses a context file, and an instruction is a real mechanism with a real failure rate rather than a guarantee.

- There is now a deterministic backstop behind that instruction: GTM Base checks as a context file is read, and hands the same flag straight back. Claude Code's hook documentation, read on the twentieth of September at https://code.claude.com/docs/en/hooks, is what makes it possible. Its decision-control table for the tool-use event lists three fields a check of that kind may answer with, and the third is the one this needed: `permissionDecision`, "\"allow\", \"deny\", or \"ask\". Overrides the permission system's decision for this tool call"; `permissionDecisionReason`, "Text shown to the user when denying or asking"; and `additionalContext`, "Text added to Claude's context before the tool call runs, shown in the transcript". The same page says "Claude Code fires the same hook events wherever it runs: sessions in the terminal, IDE extensions, the Desktop app, and cloud sessions", and that "All matching hooks run in parallel", which is why the check that reads every command is untouched by this one sitting beside it.

- What that check does is deliberately small. For any file that is not inside the context folder of a base this account has joined, which is almost every file anybody reads, it prints nothing and leaves, the same way the check on commands leaves. For a context file that a recorded change has overtaken, it answers with the four lines and the three answers, and it never touches the permission decision at all: it does not deny, does not ask, does not defer, and the file is read either way. It writes nothing into your base, reaches nothing over the network, makes no call that could reach anywhere, works to a small time limit, and says nothing at all rather than failing when anything goes wrong.

- It asks nothing itself. The question a person answers belongs to whoever actually asks them, which is the script the rule names, and that script hands back a question already open rather than issuing a second one. A question is only handed back when it is about the same document, the same change, and the same session, because one from another session is refused an hour long and one about another change would write a confirmation naming something nobody was shown. One session is told about one document and one change once, so a file read five times in a sitting is flagged on the first read, and a change written down later in that same session is still raised.

- A miss costs almost nothing now, which is what makes a check on every file read affordable. It reads the account's own record without running anything, compares the path as text, and only then asks about the one folder the file could be in. Measured on this computer on the twentieth of September, with one base joined: the lookup went from 11.0 milliseconds to 0.3 at the median, and from 201 to 4.4 at its worst. With five bases joined and four of their folders gone, from 10.5 milliseconds to 0.2. The whole thing end to end, wrapper and all, is 58 milliseconds at the median, nearly all of it starting Python.

- A check that runs out of time says nothing rather than guessing. Who wrote each line of a confirmations file is how a confirmation gets an owner, and when that read timed out every confirmation came back unowned, every settled document looked out of date, and the backstop raised a flag on a document its owner had already confirmed. That read now says plainly that it could not answer, and everything above it treats that as unknown rather than as nobody.

- An older Claude Code gets the instruction and not the backstop. Carrying text back from a check of this kind is something Claude Code gained in a release of its own, and a seat on anything older simply sees a check that says nothing, which costs it nothing. The rule the session carries is written to stand in front of the backstop rather than behind it, for that reason and because a document handed to the assistant earlier in a session was read before the backstop had anything to say about it.

- Recorded as still open, and not fixed here. Two sessions open in one base at the same time bind a question to whichever started last. The backstop writes down that it has told a session about a document before the client has actually delivered the text. The paths it writes down are hashed without a salt, which is enough to keep a customer's name out of a file that is read back in plain sight and not enough to stop somebody who already guessed the path from confirming the guess.

- What is still unmeasured is how often the instruction is followed on its own, outside a skill and without the backstop. The trial that would measure it is ten real prompts that each use a flagged document, with the count of times the flag fired written down, and that trial is the owner's to run. No number about it appears here because none has been measured.

- A one-line weekly nudge exists and ships switched off. Turned on, it is said once in a week and not twice. The base can also be asked to stay quiet for a month, and while it is quiet neither the weekly line nor the flag says anything, while a review you ask for still works exactly as usual.

- A prepared change can now be approved by its owner in Claude, on a base that has no shared copy. Until now it could not be approved anywhere. Two things were true at once on the one real base, and both were verified on the nineteenth of September: that base has no shared copy, so there was nowhere to send a proposed change, and nothing in the shipped code ever marks a first backup as reviewed, so the second condition on sending could not be satisfied either. Every answer that turns into a prepared change, including saying no when asked whether a document is still right, therefore ended at a refusal with nothing the person could do about it. The owner now reads the whole change, in the four labeled lines with the before and after of every part of every file it touches, and one yes applies it, records their approval against each file, and writes the record of what changed that the four-week numbers count exactly as they count a change accepted on a shared copy.

- Nothing about what may leave the computer changed to make that work. The check on commands and the two conditions that hold everything back are untouched, the first backup is still unreviewed afterwards, and nothing in this path can reach anywhere off the computer. The yes is bound to exactly what was shown, so a prepared change or a file that moved in between is shown again rather than applied. Only an owner of every file a change touches may approve it. A run that stops halfway is either finished off or undone on the next run, and a path holding your own words is left exactly as you left it and stops the run instead.

- A proposed change can no longer reach your base's map by calling it something else. Comparing the name an edit gives a file against the map's own name let two things through, both of them reproduced: the same name written in different letters, which is one file on most Macs, and a folder link inside the context folder, which makes one folder readable as two. An edit is now followed to the file it really means, that file has to sit at the very name the edit gave, and the map is recognised as the same file rather than as the same spelling. This holds for every proposed change, not only for one approved here.

- A prepared change is only ever read from the folder they wait in. Throwing one away used to delete whatever path it was handed, so a mistyped path could have deleted a document. A dropped change is now moved into a folder of changes nobody wanted rather than deleted, which also stops tomorrow's check preparing the same one all over again.

- A run that stopped halfway no longer writes over your own work while tidying up after itself. The note it leaves now records the exact content it was going to put at each path, and a path is put back only when what is on the disk is exactly that. A path holding your own words is left alone and the run stops and says so, a path that could not be put back keeps the note so the run can be finished later, and the note itself is read as data with every path and value in it checked before anything is touched.

- What you are shown is now the whole of what would be written. The context change a prepared change carries is shown exactly as it will be written down rather than as its first sentence, the reason is shown in full, what the change affects includes the documents the change itself names, and a part being added, or a second edit to the same file, is shown as the file will really read. The screens now also read the headings an edit names, which get written into the file when the part is not there yet, and the note the work is saved under.

- Three smaller things a base would have noticed. Not being able to read whether a base has a shared copy is no longer treated as not having one. A change already recorded here is refused rather than recorded twice. And the four-week numbers count one context change once, however many records name it.

- Residual, and not fixed here. The turned down rate is still counted only from proposals on a shared copy, so approving or dropping a change here never reaches either the accepted or the turned down number. The check that reads every command reads commands only, so a tool that writes files could still write this account's own seat files directly; that is wider than this unit and belongs to the security pass before the release.

- Setting up a base now finishes on two documents, your customer profile and your positioning. Writing down something that changed about your business is no longer a required step of setting up, so a base that has nothing recorded against it yet is a finished base rather than a half made one, and a later session never offers to finish setting it up again.

- The sentence that ends setting up now tells the truth about a base with nothing recorded against it. It names each document and the day you confirmed it, says plainly that no context change is recorded and that GTM Base therefore cannot yet check whether a change has made either document out of date, and names the day each document comes back to you. On the third real setup run that sentence said there was no date to watch, which was wrong twice over: nothing had been checked, and both confirmations already had a date of their own.

- Your base's map is never asked about. It holds the settings and the note of where things live, so nothing you decide about your business can make it wrong, and it is now left out of the flags, the questions, and the review by what it is rather than by a confirmation line, which would only have brought it back a month later. The first real return session opened by asking whether the map was still right, which is the worst possible first sentence for a working session. A base created before this change is covered too, and the placeholder date the map template carried is gone.

- The finding about a document written from material older than the change it should reflect now looks at the documents that change actually names, and only while the change is still open. It used to match on the setup run the document was drafted in, which would have gone quiet as soon as changes recorded outside setup arrived, and which would have raised one finding per document in a base holding many of them instead of one per document the change affects.

- What your base tracks is called a context change everywhere you read it, and the word decision is gone. The word was the problem: on the live setup run the step that records one needed three separate explanations before it was understood, and it was still too narrow afterwards, because a competitor's launch, a price change, and something you learned about how customers describe the problem are all things that make a document wrong and none of them is a decision anybody made. Inside the base the folder `work/decisions` is now `work/changes`, each entry says `kind: change`, and its settings keep their meanings under plainer names: `happened_on` for the day it happened, and `noted_by` for whoever wrote it down, because there is not always somebody who decided it. Every identifier is untouched, which is what keeps confirmations, records, and prepared changes pointing at the same things they always pointed at.

- Both layouts are read, and only the new one is ever written. A base still holding `work/decisions`, an entry still written with the older settings, a copy restored from a backup, and a base holding both folders at once are all read exactly as they always were, and one entry comes back per identifier. Where the same identifier sits in both folders saying two different things, that is reported as a problem by name and neither version is used, because choosing between two things you wrote is not a reader's call. A prepared change that names the older folder is still accepted, so nothing already waiting is thrown away by the rename.

- Moving an existing base is offered rather than done to you. GTM Base says so when you ask to review your base, and nothing moves until you say yes. The move is one recorded piece of work, with a note kept outside your base while it runs, and it happens in two saved changes on purpose: the files move first without one character of them changing, and only then are the settings rewritten. That order is what keeps the four-week numbers right, because the count of what GTM Base caught is worked out from which saved change first added each file, and a move saved together with a rewrite reads as a brand new file. Before anything is written it checks that every entry can be read and that no identifier appears twice saying two different things, and it refuses with a plain sentence when either is wrong, or when you have edits you have not saved. A run that stops partway is finished or put back on the next run, and it tells its own unfinished work from your edits by the exact content it recorded, so a path holding your own words stops the run rather than being written over.

- Measured on a sandbox base built the shape the one real base is, with one context change, no correction records, and no prepared changes waiting: twelve runs, each on a fresh copy, gave a median of 0.211 seconds and a slowest run of 0.294 seconds, against the fifteen seconds a session start has to work in. The cost is not what decides it. It is offered and never automatic because nothing is applied to a base without the owner's yes.

- The words ledger and decision are now checked for in every sentence a person reads, alongside the version-control words that were already banned, and the check runs over the sentences held in code as well as over the documents. The option that stopped GTM Base mentioning a quiet record was called `--dismiss-ledger-behind` and is now `--dismiss-quiet-record`. One older sentence that can still be reached, the one saying there is no date to watch, said less than it knew: it now says that every context change the base holds is either closed or carries no date to look at it again, and that the next one you record will give it a date.

- Two outside reviews of the update above found seven ways it could lose work, every one of them reproduced on a sandbox base, and all of them are fixed. The rule the recovery now follows is one sentence: work out what every single file is before touching any of them, and if one of them holds words you have not saved, stop there, change nothing, and name that file. The two worst were a run that took one context change away and only then noticed the next file was yours, leaving that change in neither folder and coming back to the same place on every retry; and a put-back that wrote over an unsaved edit to a change it had not reached yet and then reported that everything said what it said before. Alongside those: a copy of a base restored on top of itself wedged the update and deleted the committed copy from the working folder; a moment when GTM Base could not read what had already been saved was treated as nothing having been saved, which took a finished move apart and left the base reading as empty; and finishing an interrupted run saved your half written sentence as though GTM Base had written it. The note it keeps while it works is now read as warily as everything else it did not write.

- The rewrite no longer rewrites your file. It renames the two settings and the one word that changed, line by line, and leaves every other byte exactly as it was, your line endings and your blank lines included. Before this it read the file, threw it away, and wrote a fresh one in its place, which quietly reformatted whatever you had written. A file that gives one setting under both its old and its new name and says two different things in them is now refused by name rather than having one of the two quietly kept, and a required value that is missing is a plain refusal rather than a crash that took the whole check down with it.

- One context change written down twice is never silent. Two files saying they are the same change and not saying the same thing used to make every document that change was about look settled, with the run reporting that the base had nothing recorded in it at all. The run, the review, and the check made as a document is about to be used all now name the change, name both files, and say plainly that GTM Base cannot vouch for those documents until the two agree. Every file also has to be named after the change inside it, so one change can never end up spread across two names, and anything that writes a change down asks where that change already is first rather than writing a second copy of it.

- The offer is an offer. It is not made when saying yes would be refused: not while anything is unsaved, not while one change is written down twice, and not on a base other people can reach, where GTM Base states the condition instead and waits for you to say that everyone who opens it is on the current version. Saying not now stops it being mentioned for a month. A look only really writes nothing, and there is one way out of an update that stopped somewhere nothing can finish from, which puts back only what GTM Base still recognises as its own and names whatever it left alone.

- The four-week numbers no longer rest on the words in a saved note. The count of what GTM Base caught asks about both of a change's names together and takes the older answer, so tidying your own history no longer drops the number to zero. The option that stops a quiet record being mentioned answers to both its old and its new name, so a session holding the older instructions is not refused and your answer is not lost. And the sentence about a quiet record now says the day the last change was written down, which is the day the rule behind it actually compares.

- The check for words a person should never read was reading less than it looked like. Any line of three dashes switched it off for the rest of the file, and the description line of every skill, which is the first thing anybody reads about one, was skipped entirely. Both are fixed, and the one sentence a person reads before they have installed anything, the plugin's own description, is checked now too and no longer says the older word.

- A second data-safety pass reran every fix above and confirmed them, then found that the rename itself had introduced one critical, three highs and four mediums. All are fixed, all were reproduced first. The rule that closes most of them is one invariant: every renamed context change is read back before anything is written to your base, and unless it says exactly what it said before, with every field and the whole body equal, the file is named and nothing happens. A file that starts with an invisible mark some editors add, a file whose lines end the oldest way, a file giving one setting under both its old and its new name, and a quoted word where a plain one was expected were all cases where the rename produced something your base could not read back. Each of them is now a sentence naming that file, before one thing has been saved.

- The critical was a folder named with a capital letter, which most Macs cannot tell from the same name in lower case but git can. An update stopped before its first save left every context change in neither folder, on every retry, because the note recorded a name git did not hold, every question about it came back no, and the recovery deleted what it had copied anyway. The note now records the name git really holds, and the rule behind it is written into the code and tested: no recovery takes a file away unless another readable copy of that same change is confirmed to be there at that moment. Putting things back now also restores before it removes, so there is no instant in which a change is in neither place.

- A context change written down twice, with the two copies disagreeing, can no longer be answered around. GTM Base already said it could not vouch for the documents that change is about; it now also asks no question about them, refuses a yes about them, refuses "it already reflects this", and refuses to apply a prepared change to them, each with a sentence naming the change and both files. Saying "use it as it stands" is still allowed and still writes nothing. Before this a yes given while the two copies disagreed settled the document for good, and the change stayed hidden even after the copies were sorted out. No setting hides one of these either: asking GTM Base to stay quiet, saying not now, and declining the update all leave it visible, because quiet was never permission to hide something GTM Base cannot vouch for. A copy nothing can read, sitting beside a copy it can, is now named as the same thing rather than counted as one unreadable file.

- Giving up on an unfinished update tells the truth about what it left. It no longer puts an older copy back beside a file holding your own words, which used to manufacture exactly the disagreement above. When the first half had already been saved it says so plainly, that the base is half updated and reads no differently, and the rest can still be offered and finished later. When something stops it from putting work back, it keeps its note and says it could not, rather than reporting a clean base. A note it cannot read is kept and named, never deleted.

- Putting work back now knows about everything a run removes, not only about what it moves, so an update that stopped no longer leaves a staged deletion that made every later run report edits you never made. The note is never taken away while anything that run touched still differs from what was saved. A failed first run puts things back before it says your base is as it was, and says something else when it could not.

- Two things you can now actually do: tell GTM Base not now about the update, which it records and respects for a month, and ask it to check the update, which reads your base, writes nothing, and says what it would do and whether it would offer it. The skill also now states that two of these steps carry your own words and that the assistant may never supply either itself, which matters most for the one about every seat being on the current version, because GTM Base cannot find out who else opens your base.

- Two more ways an unfinished update could leave you stuck, both fixed, neither of which ever lost anything. If an update stopped before it had saved anything and you then saved the half done move yourself, which is an ordinary thing to do with a staged change sitting in front of you, every retry refused and told you to save your base, on a base with nothing left to save. GTM Base now asks the base rather than its own note: if every file it moved is gone from what you last saved and every copy it made is there instead, the move has landed, whoever saved it, and it simply finishes. And the sentence that refuses when a moved file really cannot be put back now names the one step that gets you out of it.

- Giving up on an unfinished update now clears up after itself. It used to leave behind the dated record it had already written but not saved, and because that record is not a context change, the rule about never deleting the last copy of something kept it there. Every run afterwards said you had unsaved edits you had never made. That rule is about context changes, which are the thing that cannot be got back, so it no longer applies to the record of a run being undone. Giving up also keeps its note until there really is nothing of its own left, which is the rule putting work back already followed.

- The sentence about a half updated base no longer says which half. How far an update got before it stopped is not the same every time, and the older wording said your settings still carried their older names, which was true in one of the two states it covered and wrong in the other.

- Recorded, and not fixed here: a seat running 0.2.6 reads a migrated base as empty. Its parser requires the older settings and the older kind, so every entry in the new layout is simply not there for it, and it will report nothing out of date rather than reporting a problem. There is a test that pins that behaviour, so it is a known limit rather than a surprise. The condition that follows is that every seat updates before a base is migrated, which matters from the moment a second person is invited to one.

- Setting a base up no longer makes you draft a context change as a required step. It asks one question about the business instead, once, at the closing. The evidence for the change is the third real setup run on the nineteenth of September: the step that drafted an entry was not understood by the product's own designer after three explanations, and on the day it was written it changed nothing the person could see. The question now comes after three plain sentences saying what a context change is, why the base wants one, and what it does with one, with one example, and it is worded: tell me if anything about the context of the business changed that we should account for, one sentence is enough, or say skip.

- Skip is a whole answer. It writes nothing at all into the base, and it puts off the reminder that the record of context changes looks quiet for as long as that base lets a confirmation stand, which is thirty days unless the map says otherwise. Nothing about it reaches the rate at which the base's own questions are answered yes, because it is not an answer to a question the base asked, and there is a test on that number itself.

- A sentence you give is shown whole before a word of it is written. The day it happened, who noted it, which documents it affects and when it comes back for a look are all worked out rather than given, so every one of them is yours to correct, through the same four answers every draft gets: approve it, correct it, skip it, or say what is wrong with it.

- The other half of why that step changed nothing visible is gone too. An entry written at the closing used to carry the name of the setup run, and the currency rules read a matching run on a document and on a change as the owner having been shown both together, so documents drafted minutes earlier counted as already caught up. Nothing setup writes carries a run any more. If your approved profile says you sell to small fleets and your sentence says you stopped selling to small fleets, the base asks you about the profile rather than deciding for you.

- It asks about one document at a time. For each of the two documents a base needs, you are asked separately whether that document already says what the change says. Yes writes that down against that one change and nothing else. No leaves the document flagged and prepares a change for it, which waits for you to approve it, because setting a base up never edits a document it has already written for you. Anything else the change affects is left flagged and counted in one line, so a change touching a dozen files is still two questions at the closing rather than a dozen.

- The closing finding for a brand new base is three short lines instead of one long sentence: what you confirmed and when, that nothing is recorded yet to check either document against, and when the base will ask about them again. When both documents were confirmed on the same day, which is what setting up in one sitting produces, that day is named once.

- Editing a context file by hand now asks what changed and why, once, on top of where the edit came from. An answer about the business travels with the prepared change and is written into the base when that change is accepted. An answer about a spelling mistake records nothing, and the proposal is exactly the one you would have had before you were asked. Nobody is made to invent a change to get a typo fixed.

- The note that your record of context changes looks quiet has moved out of the way. It used to be said by the run that prepares changes; it is said only inside a review you asked for now, at most once a session, never at the start of one. A record with nothing in it is behind at once, which it always was. Saying there is nothing to write down rests it for the same thirty days, and then it returns, once.

- Two reviewers went through the closing before it shipped and found eight things wrong with it. All eight are fixed here and every one of them now has a test, four of which run the command a skill actually tells the assistant to run rather than the library behind it. That gap is how four of the eight got in.

- A yes at the closing used to save more than the one line it wrote. Adding a line stages the whole file it sits in, so a line about another change that somebody had written and not saved was saved along with it and counted as the owner's yes about that other change too. The closing's yes now refuses on a folder with anything unsaved in it, the way every other write into a base already did, and it refuses when the base is not on its main line.

- That yes also checked almost nothing before it wrote. It now requires the change to be one the base really holds, in either folder; the change to say it affects that document; the document to be one of the two a base needs; and this computer's own address to be recorded as owning the document. When the save itself fails, the line is taken back off the disk rather than left there looking like words you never saved.

- Words somebody typed no longer go on a command line anywhere. A sentence with a dollar sign, a bracket or a pair of backticks in it is an instruction to the shell the moment it is written into a command, and four of the skills told the assistant to do exactly that with what a person said. Their words go in a file now and the path goes on the command line. Every command that takes words this way ends in `-file`.

- The hand-edit habit could not actually be used. The script the skill names took neither the answer nor the flag that carries it, so it refused every attempt, and on a base with no shared copy the local approval refused the edit as unsaved work, which is exactly what a hand edit is. Both are fixed, and the whole habit is proved end to end on a base with no shared copy: the edit, the question, an answer about the business, one approval, the document saved and confirmed, and the change written down.

- Nothing about what may leave the computer changed to make that work. The only thing narrowed is which unsaved files stop a local approval: the files the change itself is about are allowed to be unsaved, because the yes is already bound to their exact bytes, and any other unsaved work anywhere in the base still stops the run with the sentence it always did.

- Every context change written at a closing used to get the same name. The name was worked out from four fixed things, so it was identical on every base and for every closing. A second closing was either refused outright or, on a base still keeping its changes in the older folder, wrote a second entry under the same name in the newer one, which is the one state nothing can resolve and which quietly unflags every document that change is about. A closing now takes the first name neither folder already holds.

- The closing no longer reports an all-clear over a document it has just flagged. Saying no to "does this already say what the change says" leaves the document flagged, and the finding immediately afterwards said nothing was out of date. It says which document has not caught up. A context change written down twice stops any claim either way, rather than being read as a base with nothing recorded in it.

- The change shown before it is written is held apart as data, so a heading inside it cannot read as an instruction, and every one of the four lines is put on one line with anything that could end the block taken apart first. It also stops offering to let you correct who noted the change: that address is the one your base records your work under, it was written over a moment later anyway, and saying so plainly is better than taking a correction and throwing it away.

- Skip works after you have been shown what you would be skipping. It used to be refused from the moment the change had been drafted, which is the one moment somebody is most likely to want it.

- Nothing an assistant writes can reach GTM Base's own records any more. Both reviewers of this release found the same hole and reproduced it the same way: the check that runs before a command reads commands, and a file-writing tool writes a file without any command being typed, so one plain write over one small file in the records folder undid what somebody had agreed to. Writing an empty object over the account's record of joined bases made a joined base read as no base at all, which allowed a send carrying something shaped like a key and took away the first backup rule with it. Writing yes into this seat's record of the first backup turned a refused send into an allowed one, and no shipped code ever writes that yes, so every one of them was put there by something else. Writing over the record of having read somebody's own documents took away the rule that such a session may send nothing. Writing "until they ask again" into the quiet setting silenced the flag on a document with no end date, and a date in the year nine thousand in the record of what was put off silenced a reminder for ever.

- So a check now runs before every file write, and it refuses three places: anything at all under GTM Base's own records folder, a joined base's own repository folder, and the folder an assistant reads its settings from inside a joined base. A settings file in that last one could point the records folder somewhere else through a setting, and a file there could run something, which is why it is on the list. A base's context files are not on it and never will be: a person edits those by hand, the assistant edits them too, and proposing a change from a hand edit is a path this plugin supports. The path is compared after every link is followed and after letter case and Unicode form are folded on both sides, so a name written in other letters or in the other Unicode form is the same name it opens.

- Claude Code's hook documentation, read on the twentieth of September at https://code.claude.com/docs/en/hooks, is what that rests on. The shape a check of this kind refuses with is `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "Destructive command blocked by hook"}}`, and the page says that for that event "`permissionDecision: "deny"` blocks the tool call when returned with exit code 0 and valid JSON". Naming several tools at once is documented as well: "`Edit|Write` and `Edit, Write` each match either tool exactly", and "`Edit.*` matches both `Edit` and `NotebookEdit`". The field a file tool carries its path in is documented as `file_path`. The field names the notebook tool uses are not documented anywhere on that page, so this reads `notebook_path` and anything else whose name ends the same way as a precaution rather than on the documentation's word, and it refuses nothing for their absence.

- The check costs about what the one before a file read costs, measured the same way on the same computer on the twentieth of September: two hundred runs of the real wrapper as a real process, on a file in none of the three places, discarding the first twenty. The check before a file read came in at 53 milliseconds at the median and this one at 43, nearly all of it starting Python in both cases. Neither runs any command at all on the path where it says nothing, and this one runs none on the path where it refuses either.

- Setting a base up now writes its drafts somewhere else. The assistant used to write them into the run's own folder inside the records folder, beside the record of what that person agreed could be read, and allowing writes there would have meant allowing writes beside the consent records. The scripts make a folder for each run under the folder this computer keeps temporary work in, readable by that person and nobody else, and print the path for the assistant to write to, so the assistant never chooses where the file goes. The folder goes when the run's own folder goes.

- The check on commands now fails closed, because no rule about the text of a command can catch every way a folder can be named. A folder is a base to the check when it is shaped like one, whether or not any record says so, and the first backup is unreviewed in this release always and without reading anything: the first backup review is not shipped, so there is nothing honest to read, and when it ships it will record the address it reviewed and the saved work it reviewed rather than a bare yes. Said the other way round, so nobody has to work it out: nothing leaves a base in this release at all. Every send from one is refused before anything in it is read, by the check on commands and by the safeguard inside the base alike, and an answer that would have been sent is kept on this computer and the person is told in one sentence that it is safe here and will go the next time a send is possible. A question about the first backup that cannot be answered now answers that it is unreviewed; it used to answer that it was reviewed, so anything that broke the question let a send through. The record of having read somebody's own documents grew a second half. A record standing there that cannot be read stops a send, wherever the send comes from, because that is the shape a record takes after somebody has written over it and there is nothing left in it to say whose session it was. A record this very session wrote stops a send from every repository on the machine, exactly as it always has, because the text this session is holding could be pasted into any of them. And a record some other session wrote, young enough to still be about now, stops a send only from a base or from a working folder GTM Base made for itself. That last line was drawn deliberately. A record lasts twelve hours and nothing in this release clears one, so asking for its age everywhere refused every push from every repository on the machine for half a day after any setup run, which is not a thing somebody working across a dozen client repositories in a day can live with. It bought little, besides: somebody who can write that file can delete it just as easily as they can put another session's name in it, and deleting it defeats the age rule just as well. The safeguard the base itself runs keeps the age rule whole, because it runs inside git with no session to compare against and is only ever installed in a base. Quiet asked for until somebody asks again is held to the same thirty days as every other quiet, and a date in the record of what was put off further out than that is not honoured.

- What did not change is what the check leaves alone. A repository with no map where a base keeps one is still not read at all: not the change, not the notes saved with it, not the command line. That was settled on the sixth of September because reading every repository on a consultant's machine refused ordinary work, and a check people turn off protects nothing. This plugin's own repository is one of those, and there are tests that say so about both.

- The rule about naming the records folder on a command line was tightened where tightening it is cheap. Another letter case is caught now, and so are two names finished off with the characters a shell expands. Two of the spellings the reviewers wrote are still not caught and cannot be: a name built up out of a variable, and a name joined together inside another program. That is said here plainly rather than left for somebody to discover, and it is survivable for one reason only, which is that nothing the check decides is read out of that folder any more.

- Seat files are not checked for tampering in this release, and that is a decision rather than an oversight. The assistant runs as the same person the plugin does, so it could read any key kept to sign them and sign whatever it liked. A check that can be defeated by reading one file beside it is a check that reads as protection and is not, which is worse than none. What replaces it is that the records no longer decide anything about what leaves this computer.

- A note GTM Base leaves while it is applying a change is now read the way the older one always was. A reviewer wrote one naming a change somebody was waiting to read, giving it words that matched some saved work, and listing no files at all; the run read that as its own work having landed, dropped the prepared change, and said it had been applied. A note listing no files is refused, because a run that wrote nothing leaves no note. The saved point in a note has to be written the one way a saved point is written, because it goes onto a command line and the same reviewer put an option there instead and had a file written. And saved work only counts as this run's work when it touched the files the note names, not merely when it carries the same words.

- The first draft GTM Base writes into a prepared change can no longer be approved as though it were the correction. That draft opens with "Update needed" and then repeats the change back; it is a note asking the assistant for the real wording, and approving it used to put that note into the document, clear the flag, and leave the claim that had gone out of date sitting exactly where it was. A prepared change still carrying it is refused, on a base with no shared copy and on one with a shared copy alike, with one sentence saying what to do instead. The skills say what to do: read the document and the change, write what that part of the document should say now in the document's own voice, put it into the prepared change, show what the document says today beside what it would say instead, and only then ask.

- A change about a document that is written down twice, with the two copies disagreeing, is now said as a file is read. The check inside the base has always refused to be quiet about that, on the grounds that nothing can be said about whether the document is behind one of them, and the check that runs as a file is read answered on the flag alone, so the one case nothing is allowed to quiet was the one case it said nothing about.

- Asking for a document to be fixed first now answers the question it was asked. It used to leave the question unanswered for ever, which said the person had never replied when they had, and moved the count of how often somebody said a document was still right against a seat whose person had in fact answered. It has an answer of its own now, and that answer is left out of that count, because asking for a fix says nothing about whether the document is right.

- Answering a question about a document issues nothing. The answer path used to run the ordinary check first, which issues a question and writes it down, so answering a question that had run out left behind a fresh one nobody had ever been shown, unanswered, in the count. The answer path now looks without asking, and the question somebody hands it is checked against what was really asked rather than believed: a question nobody issued, and a question about another document, are both refused.

- Two outside reviewers re-checked the fixes above on the twentieth of September. Four of the findings were still open and the fixes themselves had introduced three defects of their own, including a guard that could be made to disable itself and a way for a local approval to destroy the very edit it was approving. Everything below is that round.

- A failed approval can no longer throw away the change you made by hand. Approving a hand edit means approving something you have not saved, and when the save at the end failed, for instance because something in your own repository refused it, the tidy-up put the file back the way it was last saved, which is the way it was without your change in it. The exact bytes that were in front of you are now kept beside the note before one byte of the run's own work is written, those are what comes back, and the file is read back and measured against them before the note is cleared. A copy that has gone missing stops the run and keeps the note rather than guessing.

- Approving a hand edit shows the whole of what saying yes writes down. Approval saves the whole file, and what you were shown was only the part the change was about, so an unrelated edit further down the same document went in unread. You now see everything in each document that is different from the last time it was saved, all of it, and the yes is bound to it. Every other kind of prepared change goes back to the old rule: nothing unsaved anywhere in a target file, because a change that came from somewhere else has no business finding its own file already edited.

- A second change you make by hand to the same document can be proposed. It never could before: the name a hand edit is filed under was worked out from three fixed things and the number zero, so the second one always asked for the name the first one already had and was refused as something already recorded. The first free name is taken now, looking in every place a name is remembered.

- Somebody's own words reach a script only through a file the script itself handed out. Putting their words in a file rather than on a command line fixed one thing and left another wide open: the readers took any path at all, so a document could have told the assistant to hand over the path of your private notes, and those notes would have been read into your base and written down with nobody asked and no record that anything private had been read. A command prints a path now, inside a folder only you can open, the readers accept nothing else, the file is read once and taken away, and a folder somebody else on a shared computer stood up first is not used. The same rule holds for the drafts a setup run writes, and drafts whose run is gone are swept.

- The company name, the label on a piece of pasted text, and the files to draft from no longer stand on command lines. All three can come out of a document or off a file name, where whoever wrote the name chooses what the shell does. The first two travel in words files like every other answer, and the files to draft from are named by the number the listing prints beside each one. A command naming a file rather than a number is refused outright.

- A first draft is tracked rather than recognised by its words. The note GTM Base writes asking for the real wording used to be caught by matching its exact text, and dropping the full stop, using lower case, putting in a double space, rewrapping the line, or keeping only the first half all got past that. The prepared change now carries a marker saying it is a first draft, written by GTM Base itself, and the only thing that takes it off is the one command that writes the wording in, which refuses wording that is the note over again however it is spaced or capitalised.

- The wording replaces the part of the document that went out of date. When the change does not say which part it is about, the wording used to be added in a part of its own, which cleared the flag while the claim the change made obsolete went on standing above it. The command lists the parts of the document, the assistant asks which one this is about, and the wording replaces that part. Without an answer it refuses.

- The check before a file write no longer tidies the path up first. A link named with a space in front of it pointed at the records folder while the check looked at a name nothing on the disk answered to. The name is used exactly as given, both the name and the name with every link followed are checked, and the folder a base keeps its own history in is protected as an entry rather than only as a folder, which matters because a working folder keeps that entry as a file.

- The check can no longer be turned off by writing over it. Plugin code sat outside every protected place, so an ordinary file write could replace the check's own code, the next run would fail to start, a failure used to mean silence, and the write after that went wherever it liked. The installed plugin's own folder is protected, from the place the client says it installed it and from the place the code answering is actually running from, and so are the settings that decide whether it loads. Working on the plugin in a checkout of your own somewhere else is untouched.

- When the check cannot run at all, the wrapper does a much smaller one of its own. It reads the request as text and refuses anything that so much as names the records folder, the plugin's own folder, or a version-control or assistant-settings folder, with one fixed sentence saying the check could not run. Everything else goes through, because a plugin that is broken must never stop somebody working on their own machine.

- A base's own two folders are protected by the shape of the folder rather than by a record. The protection used to be read off this account's list of joined bases, and emptying that list with one write took the protection with it. The folder tree is walked upwards instead, with no program started, and the same holds for the folder a base belongs with, which is the folder a session is usually opened in.

- What counts as a base no longer rests on one file nobody has saved. Renaming the map in the working folder took a base out of the safety check's reach entirely, and the opposite error was there too: an ordinary repository that happened to hold a file of that name was held to a base's rules for ever. Three things decide now, any one of them enough: the folder's own settings carry the name GTM Base knows the base by, this account's list names the folder, or the history the folder has saved holds all of a base's fixed entries. A question that cannot be answered leaves a base in reach rather than out of it.

- Whether the first backup has been reviewed is asked of the folder the send is from. Naming the base with a folder of its own, or moving into it earlier in the same command line, went round the rule while the send itself was read against the base exactly as it should have been. Every folder a command would send from is asked now.

- The summary of the closing preview is held apart as data. The whole change underneath it was fenced and the four lines and three facts above it were not, and those are read straight out of a file somebody typed into.

- The documented preview command carries the base. Without it the preview skipped finishing the change off and showed who noted it as a draft address that approving then replaced, and every test supplied the argument by hand, so the shipped command was the one nobody ran. The base is now required, the command is corrected, and the skill no longer offers who noted the change as something to correct. A test now reads every command out of every skill and puts it to the parser of the script it names, which is the class of miss this was.

- Two caps that turned down days far enough in the past now turn down days far enough in the future as well. Quiet asked for until somebody asks again was recorded with the day it was asked for, and a day in the year nine thousand, or simply tomorrow, kept a base quiet for ever. The day has to be a real day on a real calendar, and it has to be today or earlier.

- Putting the reminder off works on a base whose confirmation window is longer than the cap. The person was told a day, and the record was thrown away the next time it was read, so skipping did nothing at all. The day is brought back to the cap when it is written, and the day somebody is told is the day that is kept.

- A settings file with a second name is not read. A file anybody can also write from somewhere this seat never looks is not a file to believe.

- Still open, and honestly. A command can still build a path to the records folder, or to the installed plugin's own code, in spellings no pattern reads, and nothing is going to close that by pattern: what stands behind it is the safety check failing closed and the client's own permission prompt in front of every command. File tools from a connected server, and any tool whose name this does not know, are not matched by the check before a file write at all, and the same two things stand behind that. No check is made that this account's own settings files were written by GTM Base rather than by something running as the same person, which was decided in the round before this one and has not changed.

## 0.2.6 (2026-09-12)

- You are no longer asked to work out which of your folders holds your marketing material. The one opening question now asks where your company's material is roughly, a whole company folder is a fine answer, and GTM Base looks through the folder you named and proposes the places inside it that look like marketing material, naming each one with a count of what it found there and asking whether that is it. You say yes, name a folder to add, or name one to drop, and only then are you shown the list of files and asked whether they may be read. The old rule asked for the narrowest folder you could name, which put the finding on the person least likely to know where their own material sits.

- To find those places GTM Base reads the name of every file and the first heading line of every document, and nothing else. The heading is looked for no further than forty lines into a file and kept no longer than two hundred characters, a file of rows says nothing but its own name, and everything the list already refuses is refused here too, including lists of people. You are told this in the same sentence that asks whether the files may be read, so what has already been looked at is said before the yes rather than after it.

- A folder is proposed when the files inside it look like customer profiles, personas, positioning, brand voice, plans, strategy, campaigns, or metrics, by the words in their names and headings. A folder whose marketing-shaped files are both fewer than a quarter of what it holds and fewer than three is left out as thin, which is what keeps a folder of somebody's code out of the proposal when one file in it happens to be called a plan. A folder left out that way can still be added by name.

- The rule that a large spread out folder is narrowed before the yes is still there, as the backstop behind the new step rather than as the thing you meet first.

## 0.2.5 (2026-09-12)

- Lists of people are now left out of everything GTM Base offers to read. A file of rows is treated as a contact list, and never offered, when its heading row names a column only a list of people has, such as an email address, a phone number, a mobile number, or a social profile, or when most of its rows hold something shaped like an email address. Only the start of the file is looked at. Naming one of those files by hand afterwards does not bring it back either. The second real setup run named a working repository and the list that came back held twenty three files of prospect names, companies, and email addresses, all offered for a single yes. A prospect list is other people's personal information, not a document about your business, so it is left out on purpose and counted with its own reason.

- A folder that turns out to be large and spread out is now narrowed before you are asked to say yes to anything. When the list holds more than forty files across more than three folders, you are told how many files there are and how many folders they sit in, each folder is named with its count, and you are asked which of those folders hold your customer profiles, your positioning, your messaging, or your plans. The list for just those folders is then shown to you, and the yes is taken over that. Saying yes to the long list is refused rather than allowed, because a list of a hundred and fifty files offered for one yes is a list nobody reads, and a yes nobody read is not really a yes. The folders you picked are written down with the list you agreed to.

- The one opening question now asks for the narrowest folder rather than for wherever your context lives. It asks for the folder holding your customer profiles, positioning, messaging, or plans, rather than a whole company or project folder, and it still offers pasting the material in or reading it through a tool you already have connected.

## 0.2.4 (2026-09-07)

- Every new base now goes in one place, a folder called GTM Bases inside your home folder with one folder per company. It used to go inside the folder you named, which meant it landed wherever your material happens to live, and that is often a folder some other tool already looks after or some other program already copies to the internet on its own. A base holds raw notes and approved company context, so it is put somewhere GTM Base can make a promise about instead. You can still ask for it beside your material, and the same checks then run on the folder you named.

- A folder GTM Base cannot make that promise about is now refused rather than warned about, because a warning does not stop an upload. Refused: anywhere inside a folder another tool already keeps a history for, the folders Apple's cloud storage keeps, the folders other cloud storage is connected through, any folder whose name starts with Google Drive, Dropbox, or OneDrive, anything inside a base you have already joined, and the folder GTM Base keeps for itself. When your Desktop or Documents folder might be kept in the cloud and it cannot be established either way, you are asked instead of being told. All of these run again at the moment the base is built, on the real folders the path leads to, before anything you approved is written anywhere.

- Your base is now linked to the folder your marketing material lives in, so opening Claude Code in that folder brings the base with it: the map, the one question, and the day's update, exactly as if you had opened the base itself. The link is a record GTM Base keeps for itself. It never writes a thing into your folder and never reads your documents again.

- The link survives you renaming or moving that folder, and it does not survive the folder being deleted and a different one being made in its place. It keeps enough about the folder itself, from the operating system, to tell those two apart. A folder on an external disk that comes back as a different disk is reported as that rather than guessed at, and you are asked to connect it again.

- One folder belongs with one base. A folder another base already belongs with is refused, and you are told which base has it. If two bases somehow both claim one folder, neither is opened and both are named, so no company's context can arrive in a session opened for another.

- Three new things you can say: link this folder to my base, unlink this folder from my base, and show my linked folders. You can name the base by the company it is for rather than by its folder, so "link this folder to my Acme base" is enough, and none of the three needs a base to be open, which matters because the folder you want to connect is your own folder and is never a base. Show my linked folders lists every base with its name, its folder, and the folder it belongs with.

- When you are told where your base will go, the sentence now names the folder you named as the one to open from then on, so the two folders are put to you together rather than the base's own folder being the only one mentioned. The message that ends setting up does the same, and it gives the base's own folder as well so nothing about where it lives is hidden from you.

- A company name that already has a folder in GTM Bases is now turned down with a request for a name that tells the two apart, rather than a second base being built where one already is.

- Every way a place can be turned down now comes back as a sentence saying what to do next instead of a bare failure, including the one case GTM Base cannot settle on its own, where it asks you whether any app copies that folder to cloud storage automatically.

- A folder that cannot be linked is now said so before your base is built rather than after, and when a base is built the base and the folder it belongs with are written down together in one go, so there is no moment where you have a base and no record of which folder it belongs with. If that one write is refused anyway, you keep the base and are told the single step that is left.

- A base whose folder is not plugged in today keeps its link. A record of a link that cannot be read is switched off and reported on its own, and the base itself is kept.

- Everything the session start does with the version tool now shares one time budget, so a slow network or a stuck lock ends in a sentence you can read rather than a start that hangs.

## 0.2.3 (2026-09-06)

- A document that holds a comment, a tag, or a character a reader of the file would never see is now read with those parts taken out of it, rather than turned away whole. Brandon's first real setup run named a folder of a hundred and four files and seven of them were refused outright, all of them ordinary marketing templates carrying notes the author had written to themselves inside comment marks. You are told which document something was taken out of and how much of each kind went, in one sentence for each document. Text that writes the wrapper's own lines is still refused, and that check now runs after the removal, so nothing can be hidden inside a tag and appear once the tag is gone.

- Each draft now reads the documents it is actually about first. The material for one draft used to be read in whatever order the folder happened to hold it, so when there was more than one request could take, the files at the end were dropped whether or not they were the ones the document was about. On the first real run the file that sorted first filled the request on its own, ninety-six of the hundred and four were dropped, and all fourteen files describing who the company sells to were among them, so the ideal customer profile was drafted from one file about messaging. The profile now reads the files named or headed for customers, segments, personas, and buyers first, the positioning reads the ones about positioning, messaging, and voice first, and the decision entry reads the most recent material first. Nothing is thrown away by the ordering itself; it only decides what the cap reaches last.

- How much material one draft can read has gone up fourfold, so an ordinary folder of somebody's marketing material now goes in whole and the ordering only decides the rare case.

- Before each of the three drafts you are now shown what it will read and what it will leave out, by name, with the reason for each one. Nothing is written at that point. You are then asked whether to draft from that or to narrow it to the files or the folder that matter for that one document, and you can answer with either. Narrowing only ever takes part of the list you already agreed to; a file or folder that was not on that list is refused rather than looked for.

- When there is more material than one draft can read, what you are told now says how many of your files it will read, how many it will leave out, which ones those are, and that you can name the files or the folder that matter most for this document instead. It used to say only that the sources listed as dropped were left out whole, which was true and gave you nothing to do about it.

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
