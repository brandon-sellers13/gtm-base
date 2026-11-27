#!/usr/bin/env python3
"""Write the fixtures that hold the web app's moment-of-use port to the plugin.

For each scenario this builds a real git repository with commits by the
document's owner and by a teammate, reads it with the plugin's own reader
(`base_reader.read_base`), works out what is out of date with the plugin's own
rules (`stale.compute`), and writes three things to
`web/scripts/fixtures/stale-parity.json`:

- the snapshot the web app's port reads (the files' text, who added each
  confirmation line, and the facts about each accepted record's commit),
- which open change, if any, the plugin says has overtaken each document,
- and, for each flagged document, the exact words the plugin's moment of use
  says, for an owner and for anybody else.

`web/scripts/stale-parity.mjs` then runs the port on the same snapshots and
fails on any difference. Run this whenever the plugin's rules change:

    PYTHONPATH=plugins/gtm-base/lib python3 tests/stale_parity.py
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

from gtmbase import authority, base_reader, ids, moment, stale

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "scripts", "fixtures", "stale-parity.json")

TODAY = datetime.date(2026, 11, 20)
OWNER = "owner@example.com"
SECOND = "second@example.com"
TEAMMATE = "teammate@example.com"
BASE_ID = "0123456789abcdef0123456789abcdef"

A = "stg-aaaaaaaaaaaaaaaa"
B = "stg-bbbbbbbbbbbbbbbb"
RUN = "run-2026-11-01-abcdef12"
FOLDERS = ("context/", "learning/changes/", "learning/corrections/", "work/confirmations/", "standards/", "access/")
ADMIN = "admin@example.com"
FORMER = "former@example.com"
NEWCOMER = "newcomer@example.com"


def git(args, cwd, author=OWNER, day=None):
    env = dict(os.environ)
    env.update(
        GIT_TERMINAL_PROMPT="0",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Someone",
        GIT_AUTHOR_EMAIL=author,
        GIT_COMMITTER_NAME="Someone",
        GIT_COMMITTER_EMAIL=author,
    )
    if day:
        env["GIT_AUTHOR_DATE"] = day + "T12:00:00"
        env["GIT_COMMITTER_DATE"] = day + "T12:00:00"
    done = subprocess.run(["git"] + args, cwd=cwd, env=env, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), done.stderr))
    return done.stdout


def write(root, path, text):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)


def map_doc(owner=OWNER, administrators=None):
    admins = "administrators: [%s]\n" % ", ".join(administrators) if administrators else ""
    return (
        "---\nkind: map\nowner: %s\n%ssources: []\nstatus: draft\n---\n\n# Map\n\n"
        "## Settings\n\nconfirmation_threshold_days: 30\nnot_now_days: 7\n" % (owner, admins)
    )


def doc(kind, owner, title, body="Companies of any size.", status="draft"):
    return (
        "---\nkind: %s\nowner: %s\nsources: []\nstatus: %s\n---\n\n# %s\n\n## Part\n\n%s\n"
        % (kind, owner, status, title, body)
    )


def change(entry_id, happened, written, affects, status="open", run_id=None, body=None):
    lines = [
        "---",
        "id: %s" % entry_id,
        "kind: change",
        "happened_on: %s" % happened,
        "written_on: %s" % written,
        "noted_by: %s" % OWNER,
        "source: a note from the sales call",
        "affects: [%s]" % ", ".join(affects),
        "review_by: 2026-12-15",
        "origin: manual",
    ]
    if run_id:
        lines.append("run_id: %s" % run_id)
    lines.append("status: %s" % status)
    lines.append("---")
    text = "\n".join(lines) + "\n\n"
    text += body if body is not None else (
        "We now sell to companies over 50 people.\nThe small ones churned within a quarter.\n"
    )
    return text


def line(day, path="context/positioning.md", trigger="threshold", entry="-", run="-"):
    return "date=%s time=10:00:00Z file=%s trigger=%s entry=%s question=- run=%s\n" % (
        day, path, trigger, entry, run
    )


def confirmations_path(path):
    return "work/confirmations/" + path.replace("/", "--")


def corrections_record(entry_id, staging_id, content_hash, touched):
    return (
        "---\nkind: correction\ndate: 2026-11-09\nstaging_id: %s\nentry_id: %s\n"
        "source_id: -\nintake_path: ledger\nmode: decision\nthird_party: false\n"
        "content_hash: %s\ntouched_paths: [%s]\ncorrection_class: new-decision\n"
        "marker: gtm-base proposal %s entry %s source -\n---\n\n"
        "## What changed\n\nPositioning now names companies over 50.\n\n## Why\n\nThe change.\n"
        % (staging_id, entry_id, content_hash, ", ".join(touched), staging_id, entry_id)
    )


class Base(object):
    """One scenario's repository, built commit by commit."""

    def __init__(self, map_text=None):
        self.root = tempfile.mkdtemp(prefix="gtm-parity-")
        git(["init", "-b", "main", "-q"], cwd=self.root)
        git(["config", "--local", "user.email", OWNER], cwd=self.root)
        git(["config", "--local", "user.name", "Owner"], cwd=self.root)
        self.save(
            {
                "context/map.md": map_text or map_doc(),
                "context/icps.md": doc("icp", OWNER, "Customer profile"),
                "context/positioning.md": doc("positioning", OWNER, "Positioning"),
                "context/messaging.md": doc("messaging", "[%s, %s]" % (OWNER, SECOND), "Messaging"),
            },
            day="2026-10-01",
        )

    def save(self, files, author=OWNER, day="2026-10-02", append=False):
        for path, text in files.items():
            if append and os.path.exists(os.path.join(self.root, path)):
                with open(os.path.join(self.root, path), "a", encoding="utf-8") as handle:
                    handle.write(text)
            else:
                write(self.root, path, text)
        git(["add", "-A"], cwd=self.root)
        git(["commit", "-q", "-m", "save"], cwd=self.root, author=author, day=day)

    def confirm(self, text, path="context/positioning.md", author=OWNER):
        self.save({confirmations_path(path): text}, author=author, append=True)

    def accept_record(self, entry_id, merged_by, merged_on, good_hash=True, change_doc=True,
                      path="context/positioning.md", owner=OWNER, extra=""):
        """A proposal written by a teammate on a side branch, merged onto main."""
        staging = "stg-cccccccccccccccc"
        git(["checkout", "-q", "-b", "proposal"], cwd=self.root)
        new_text = doc("doc", owner, "Fixed", body="Companies over 50 people.")
        files = {}
        if change_doc:
            files[path] = new_text
        current = new_text if change_doc else open(
            os.path.join(self.root, path), encoding="utf-8"
        ).read()
        digest = ids.content_hash(current) if good_hash else "0" * 64
        record = corrections_record(entry_id, staging, digest, [path])
        if extra:
            record = record.replace("marker:", extra + "marker:", 1)
        files["learning/corrections/%s.md" % staging] = record
        self.save(files, author=TEAMMATE, day="2026-11-08")
        git(["checkout", "-q", "main"], cwd=self.root)
        git(
            ["merge", "-q", "--no-ff", "-m", "accept", "proposal"],
            cwd=self.root,
            author=merged_by,
            day=merged_on,
        )

    def snapshot_and_verdict(self):
        os.environ["GTM_BASE_HOME"] = tempfile.mkdtemp(prefix="gtm-parity-seat-")
        tracked = git(["ls-files"], cwd=self.root).split("\n")
        files = {}
        for path in tracked:
            if path and path.startswith(FOLDERS) or path.startswith(("work/decisions/", "work/changes/", "corrections/")):
                with open(os.path.join(self.root, path), encoding="utf-8") as handle:
                    files[path] = handle.read()
        runner = base_reader.runner_or_default(None)
        authors = {}
        revisions = set()
        for path in sorted(files):
            if path.startswith("work/confirmations/") and path.endswith(".md"):
                found = base_reader.line_authors_and_revisions(self.root, path, runner)
                authors[path] = dict(
                    (str(k), {"email": email, "revision": revision}) for k, (email, revision) in found.items()
                )
                revisions.update(revision for _email, revision in found.values() if revision)
        corrections = {}
        paths = [p for p in base_reader.correction_files(self.root)]
        records = base_reader.corrections(self.root, runner, "main")
        parseable = []
        from gtmbase import formats

        for path in paths:
            try:
                formats.CorrectionsFile.parse(files[path])
                parseable.append(path)
            except Exception:
                pass
        for path, record in zip(parseable, records):
            corrections[path] = {
                "coModified": list(record.co_modified_paths),
                "hashAtCommit": record.content_hash_at_commit,
                "mergedBy": record.merged_by_email,
                "mergedOn": record.merged_on.isoformat() if record.merged_on else None,
                "mergedIn": base_reader.accepted_at(self.root, path, "main", runner)[2],
            }
            if corrections[path]["mergedIn"]:
                revisions.add(corrections[path]["mergedIn"])
        # The map and every document as each revision above saved them, which
        # is what the plugin's authority check reads (authority.at).
        documents = sorted(
            set(p for p in files if p.startswith(("context/", "standards/", "access/")))
            | set(t for r in records for t in (r.file.touched_paths or []) if isinstance(t, str))
        )
        saved = {}
        for revision in sorted(revisions):
            saved[revision] = {
                "map": authority._saved(self.root, revision, "context/map.md", runner),
                "documents": dict(
                    (d, authority._saved(self.root, revision, d, runner)) for d in documents
                ),
            }
        snapshot = {
            "today": TODAY.isoformat(),
            "files": files,
            "confirmationAuthors": authors,
            "corrections": corrections,
            "revisions": saved,
        }
        try:
            inputs = base_reader.read_base(
                self.root, BASE_ID, runner=runner, today=TODAY, record_dropped=False
            )
            report = stale.compute(
                today=TODAY,
                settings=inputs.settings,
                files=inputs.files,
                ledger=inputs.ledger,
                confirmations=inputs.confirmations,
                corrections=inputs.corrections,
                seat=inputs.seat,
                owner_email=None,
            )
        except Exception as failure:  # the plugin's check fails as a whole
            return snapshot, {"unreadable": type(failure).__name__}, {}
        verdict = {}
        words = {}
        for path in sorted(report.files):
            verdict[path] = None
        for flag in report.file_flags:
            if flag.trigger != stale.TRIGGER_LEDGER:
                continue
            entry_id = flag.entry_ids[0]
            verdict[flag.path] = entry_id
            entry = base_reader.entry_by_id(inputs, entry_id)
            for owned in (True, False):
                said = moment.Moment(
                    flag.path,
                    flagged=True,
                    entry_id=entry_id,
                    entry=entry,
                    happened_on=entry.decided_on,
                    fix_ready=False,
                    today=TODAY,
                    owned=owned,
                )
                words.setdefault(flag.path, {})["owned" if owned else "notOwned"] = said.block()
        return snapshot, verdict, words

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


POS = ["context/positioning.md"]


def scenarios():
    def s(name, build):
        base = Base()
        try:
            build(base)
            snapshot, verdict, words = base.snapshot_and_verdict()
        finally:
            base.close()
        return {"name": name, "snapshot": snapshot, "expected": verdict, "words": words}

    yield s("an open change and no confirmation", lambda b: b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)}))

    def owner_after(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.confirm(line("2026-11-03"))
    yield s("the owner confirms after the change", owner_after)

    def teammate_after(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.confirm(line("2026-11-03"), author=TEAMMATE)
    yield s("a teammate confirms after the change", teammate_after)

    def same_day(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.confirm(line("2026-11-01"))
    yield s("the owner confirms on the day it happened", same_day)

    def between(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-05", POS)})
        b.confirm(line("2026-11-03"))
    yield s("a confirmation before the change was written down", between)

    def naming(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.confirm(line("2026-10-15", trigger="ledger", entry=A))
    yield s("a confirmation naming the change, dated earlier", naming)

    def naming_other(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.confirm(line("2026-11-10", trigger="ledger", entry=B))
    yield s("a confirmation naming a different change", naming_other)

    def drafted(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-01", POS, run_id=RUN)})
        b.confirm(line("2026-11-01", trigger="drafted", run=RUN))
    yield s("setup's own line in the same run", drafted)

    def done(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS, status="done")})
    yield s("a change that is done", done)

    def two(b):
        b.save({
            "learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS),
            "learning/changes/%s.md" % B: change(B, "2026-11-03", "2026-11-04", POS, body="We raised prices by ten percent.\n"),
        })
        b.confirm(line("2026-11-05", trigger="ledger", entry=A))
    yield s("two open changes, the owner answered the first", two)

    def question(b):
        b.save({
            "learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS),
            "context/positioning.md": doc("positioning", OWNER, "Positioning", body="Which segment? [your call: pick one]"),
        })
        b.confirm(line("2026-11-03"))
    yield s("a document still holding an open question", question)

    def skipped(b):
        b.save({
            "learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS),
            "context/positioning.md": doc("positioning", OWNER, "Positioning", status="skipped"),
        })
    yield s("a skipped document", skipped)

    def the_map(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", ["context/map.md"])})
    yield s("a change that names the map", the_map)

    def accepted_owner(b):
        b.save({
            "learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS),
            "learning/changes/%s.md" % B: change(B, "2026-11-05", "2026-11-06", POS, body="We raised prices by ten percent.\n"),
        })
        b.accept_record(A, OWNER, "2026-11-10")
    yield s("the owner accepts a record for one change", accepted_owner)

    def accepted_teammate(b):
        b.save({
            "learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS),
            "learning/changes/%s.md" % B: change(B, "2026-11-05", "2026-11-06", POS, body="We raised prices by ten percent.\n"),
        })
        b.accept_record(A, TEAMMATE, "2026-11-10")
    yield s("a teammate accepts a record for one change", accepted_teammate)

    def bad_hash(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.accept_record(A, OWNER, "2026-11-10", good_hash=False)
    yield s("an accepted record whose hash does not match", bad_hash)

    def record_alone(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
        b.accept_record(A, OWNER, "2026-11-10", change_doc=False)
    yield s("an accepted record that did not change the document", record_alone)

    def second_owner(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", ["context/messaging.md"])})
        b.confirm(line("2026-11-03", path="context/messaging.md"), path="context/messaging.md", author=SECOND)
    yield s("the second of two owners confirms", second_owner)

    def future(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-12-01", "2026-12-01", POS)})
    yield s("a change that says it happened in the future", future)

    def several(b):
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS + ["context/icps.md", "context/icps/enterprise.md"])})
    yield s("one change naming several documents", several)

    VOICE = ["context/voice.md"]

    def voice_base(admins=None, map_owner=OWNER):
        def make():
            b = Base(map_doc(map_owner, admins))
            b.save({"context/voice.md": doc("voice", SECOND, "Voice")})
            b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", VOICE)})
            return b
        return make

    def scenario_with(name, make, then):
        base = make()
        try:
            then(base)
            snapshot, verdict, words = base.snapshot_and_verdict()
        finally:
            base.close()
        return {"name": name, "snapshot": snapshot, "expected": verdict, "words": words}

    yield scenario_with("the base owner confirms a document someone else owns", voice_base(),
                        lambda b: b.confirm(line("2026-11-03", path="context/voice.md"), path="context/voice.md", author=OWNER))
    yield scenario_with("an administrator confirms", voice_base(admins=[ADMIN]),
                        lambda b: b.confirm(line("2026-11-03", path="context/voice.md"), path="context/voice.md", author=ADMIN))
    yield scenario_with("a teammate who is no administrator confirms", voice_base(admins=[ADMIN]),
                        lambda b: b.confirm(line("2026-11-03", path="context/voice.md"), path="context/voice.md", author=TEAMMATE))
    yield scenario_with("a map naming two owners names no base owner", voice_base(map_owner="[%s, %s]" % (OWNER, TEAMMATE)),
                        lambda b: b.confirm(line("2026-11-03", path="context/voice.md"), path="context/voice.md", author=OWNER))

    def former(b):
        b.save({"context/voice.md": doc("voice", FORMER, "Voice")})
        b.confirm(line("2026-11-03", path="context/voice.md"), path="context/voice.md", author=FORMER)
        b.save({"context/voice.md": doc("voice", SECOND, "Voice")})
    yield scenario_with("an owner at the time who no longer owns it", voice_base(), former)

    def newcomer(b):
        b.confirm(line("2026-11-03", path="context/voice.md"), path="context/voice.md", author=NEWCOMER)
        b.save({"context/voice.md": doc("voice", NEWCOMER, "Voice")})
    yield scenario_with("an owner today who did not own it then", voice_base(), newcomer)

    def role_token(b):
        b.confirm(line("2026-11-03", path="context/voice.md").replace("run=-", "run=- role=owner"), path="context/voice.md", author=SECOND)
    yield scenario_with("a confirmation line carrying its role", voice_base(), role_token)

    yield scenario_with("the base owner accepts a fix to a document someone else owns", voice_base(),
                        lambda b: b.accept_record(A, OWNER, "2026-11-10", path="context/voice.md", owner=SECOND))
    yield scenario_with("a record carrying approved roles and hashes", voice_base(),
                        lambda b: b.accept_record(A, SECOND, "2026-11-10", path="context/voice.md", owner=SECOND,
                                                  extra="approved_roles: [context/voice.md=owner]\napproved_hashes: [context/voice.md=%s]\n" % ("a" * 64)))

    def standard(b):
        b.save({"standards/cold-email.md": doc("standard", OWNER, "Cold email standard")})
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", ["standards/cold-email.md"])})
    yield s("a change naming a standard", standard)

    def standard_confirmed(b):
        standard(b)
        b.confirm(line("2026-11-03", path="standards/cold-email.md"), path="standards/cold-email.md")
    yield s("a standard its owner confirmed", standard_confirmed)

    def stack(b):
        b.save({"access/stack.md": doc("stack", OWNER, "Source map")})
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", ["access/stack.md"])})
    yield s("a change naming the source map", stack)

    def not_a_standard(b):
        b.save({"standards/Bad_Name.md": doc("standard", OWNER, "Not a standard")})
        b.save({"learning/changes/%s.md" % A: change(A, "2026-11-01", "2026-11-02", ["standards/Bad_Name.md"])})
    yield s("a file in standards whose name is not a job", not_a_standard)

    def bad_id(b):
        b.save({"learning/changes/stg-short.md": change("stg-short", "2026-11-01", "2026-11-02", POS)})
    yield s("a change whose identifier is malformed", bad_id)

    def older(b):
        b.save({"work/decisions/%s.md" % A: change(A, "2026-11-01", "2026-11-02", POS)})
    yield s("a base still holding the older layout", older)


def main():
    if "gtmbase" not in sys.modules:
        raise SystemExit("Run with PYTHONPATH=plugins/gtm-base/lib")
    fixtures = list(scenarios())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(fixtures, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print("wrote %d scenarios to %s" % (len(fixtures), os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
