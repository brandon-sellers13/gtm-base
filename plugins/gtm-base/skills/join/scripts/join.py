#!/usr/bin/env python3
"""Set a company base up, one step at a time, and say in plain lines how it went.

Everything this script does lives in `gtmbase.join_flow`; this file exists only
to find the library, read the arguments, and print the answer. What it prints is
of two kinds: whole sentences, which are for the person to read, and single
lines of the form name=value, which are for the assistant to read back.

Every value on one of those lines goes through `safe_value` first. Some of them
are file names, and a file name is whatever somebody typed when they saved the
file, which can hold a line break, a tab, or thousands of characters. Written
out as they are, one such name would look like several lines and could say
whatever its author wanted the assistant to read. So a value with a control
character in it has that character replaced, a value longer than the cap is
shortened, and a value holding a space, an equals sign, or a quotation mark is
put in quotation marks with its backslashes and quotation marks marked off.
"""

# --- gtm-base shim (copy from here) ---
import os
import sys


def locate_lib(start):
    """Find the folder holding `gtmbase`: beside the script, then the plugin."""
    here = os.path.dirname(os.path.abspath(start))
    while True:
        candidate = os.path.join(here, "lib")
        if os.path.isfile(os.path.join(candidate, "gtmbase", "__init__.py")):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    for folder in (
        os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "lib"),
        os.environ.get("GTM_BASE_LIB", ""),
    ):
        if folder and os.path.isfile(os.path.join(folder, "gtmbase", "__init__.py")):
            return folder
    return None


_lib = locate_lib(__file__)
if _lib is None:
    sys.stderr.write(
        "GTM Base could not find its library; reinstall the plugin with: "
        "claude plugin install gtm-base@gtm-base\n"
    )
    raise SystemExit(3)
if _lib not in sys.path:
    sys.path.insert(0, _lib)
# --- end of shim ---


import argparse  # noqa: E402

from gtmbase import (  # noqa: E402
    drafting,
    join_flow,
    location,
    machine,
    offer_answer,
    paths,
)
from gtmbase.errors import (  # noqa: E402
    ConsentError,
    DraftError,
    GtmBaseError,
    IdentityNeeded,
    ReviewError,
)

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NO_BASE_HERE = (
    "That folder is not a company base yet, so there is nothing there to add "
    "to."
)
WENT_WRONG = "GTM Base could not finish that step, so nothing was written."
NEEDS_EMAIL = (
    "GTM Base needs your work email address for this base. Ask for it, then "
    "run approve again with --email <address>."
)
BAD_COMPANY = (
    "That company name holds something a folder name may not carry, so "
    "nothing was run."
)
CANNOT_SKIP_FIRST = (
    "There is no base yet, so this first document cannot be skipped. Approve "
    "it, edit it, or ask what is wrong with it."
)
NO_SOURCES_LEFT = (
    "None of the material you named could be used for this step, so there was "
    "nothing to draft from and nothing was written."
)
LISTING_CHANGED = (
    "That folder is not what it was when the list was shown, so the yes was "
    "not taken. Show the list again and ask again."
)
NO_LISTING_YET = (
    "No list has been shown for this run yet, so there is no yes to take. Run "
    "list-sources first."
)

# Most characters one value on a name and value line may carry.
VALUE_MAX = 300
# What a control character in a value is replaced with.
CONTROL_STAND_IN = "?"


def safe_value(value):
    """One value, made safe to write onto a name and value line.

    Control characters are replaced, the value is shortened to the cap, and a
    value holding a space, an equals sign, or a quotation mark is quoted.
    """
    text = "" if value is None else str(value)
    text = "".join(
        CONTROL_STAND_IN if (ord(character) < 32 or ord(character) == 127) else character
        for character in text
    )
    if len(text) > VALUE_MAX:
        text = text[:VALUE_MAX] + "..."
    if text == "" or any(mark in text for mark in (" ", "=", '"', "\\")):
        text = '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def line(out, name, value):
    """Write one name and value line, with the value made safe first."""
    out.write("%s=%s\n" % (name, safe_value(value)))


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("mode", help="which step of setting a base up to run")
    parser.add_argument("--run", help="the identifier of this setup run")
    parser.add_argument("--step", help="icp, ledger-entry, or positioning")
    parser.add_argument("--company", help="the company the base is for")
    parser.add_argument("--content-folder", help="the folder holding their material")
    parser.add_argument("--folder", help="the folder to list or to fix the list of")
    parser.add_argument("--session", help="the identifier of this session")
    parser.add_argument("--label", help="a short name for one piece of text")
    parser.add_argument("--from", dest="from_file", help="the file the text is in")
    parser.add_argument(
        "--paste-file",
        action="append",
        default=[],
        help="text held for this run, once per piece",
    )
    parser.add_argument("--draft", help="the file the draft was written to")
    parser.add_argument("--answer", help="what the person said, in their own words")
    parser.add_argument("--base", help="the base folder to write into")
    parser.add_argument("--parent", help="the folder the base will be created in")
    parser.add_argument("--email", help="the address this base records work under")
    parser.add_argument("--name", help="the name this base records work under")
    parser.add_argument(
        "--got-in-the-way", help="what got in the way, in their own words"
    )
    parser.add_argument(
        "--confirmed-home",
        action="store_true",
        help="they said yes a second time to their home folder",
    )
    return parser


def need(options, name, out):
    value = getattr(options, name.replace("-", "_"), None)
    if not value:
        out.write("This step needs --%s.\n" % name)
        return None
    return value


def base_folder(options, out):
    """The base this step writes into, or nothing when there is not one.

    A folder only counts when this account has joined it. A folder that merely
    looks like a base, or one that was left half built by a run that stopped,
    is not somewhere setting a base up may write.
    """
    root = options.base or os.getcwd()
    resolution = paths.resolve_base(root, machine.load_machine_state())
    if resolution.code != paths.CODE_JOINED or not resolution.root:
        out.write(NO_BASE_HERE + "\n")
        return None
    return resolution.root


def run_new_run(options, out):
    run_id = join_flow.new_run()
    line(out, "run", run_id)
    line(out, "scratch", join_flow.scratch_dir(run_id))
    return EXIT_DONE


def run_propose_location(options, out):
    company = need(options, "company", out)
    if not company:
        return EXIT_ERROR
    proposal = join_flow.propose_location(
        company,
        content_folder=options.content_folder,
        confirmed_home=options.confirmed_home,
    )
    out.write(location.describe(proposal) + "\n")
    line(out, "target", proposal.target_path)
    line(out, "parent", proposal.parent)
    if proposal.warning_code:
        line(out, "warning", proposal.warning_code)
    return EXIT_DONE


def run_list_sources(options, out):
    folder = need(options, "folder", out)
    run_id = need(options, "run", out)
    if not folder or not run_id:
        return EXIT_ERROR
    listing = join_flow.list_sources(folder, run_id)
    out.write("These are the files GTM Base would read.\n")
    for entry in listing.readable:
        out.write(
            "read=%s kind=%s date=%s\n"
            % (
                safe_value(entry.path),
                safe_value(entry.kind),
                safe_value(entry.modified_date or "none"),
            )
        )
    out.write("These were left out, and this is why.\n")
    for reason in sorted(listing.excluded_counts):
        out.write(
            "left-out=%s count=%d\n"
            % (safe_value(reason), listing.excluded_counts[reason])
        )
    for code in listing.codes:
        line(out, "note", code)
    if listing.needs_second_yes:
        out.write("needs-second-yes=true\n")
    if listing.appears_multi_company:
        out.write("appears-multi-company=true\n")
        for hint in listing.company_hints:
            line(out, "company-hint", hint)
    return EXIT_DONE


def run_freeze_sources(options, out):
    folder = need(options, "folder", out)
    session = need(options, "session", out)
    run_id = need(options, "run", out)
    if not folder or not session or not run_id:
        return EXIT_ERROR
    try:
        consent = join_flow.freeze_sources(folder, session, run_id)
    except ConsentError as refusal:
        if refusal.code == join_flow.CODE_LISTING_CHANGED:
            line(out, "codes", refusal.code)
            out.write(LISTING_CHANGED + "\n")
            return EXIT_REFUSED
        if refusal.code == join_flow.CODE_NO_LISTING:
            line(out, "codes", refusal.code)
            out.write(NO_LISTING_YET + "\n")
            return EXIT_REFUSED
        raise
    out.write(
        "The list is fixed. Nothing leaves this computer for the rest of this "
        "session.\n"
    )
    out.write("frozen=%d\n" % len(consent.paths))
    return EXIT_DONE


def run_add_paste(options, out):
    run_id = need(options, "run", out)
    label = need(options, "label", out)
    session = need(options, "session", out)
    if not run_id or not label or not session:
        return EXIT_ERROR
    if options.from_file:
        with open(options.from_file, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    line(out, "paste", join_flow.write_paste(run_id, label, text, session))
    out.write(
        "That is held for this run. Nothing leaves this computer for the rest "
        "of this session.\n"
    )
    return EXIT_DONE


def say_left_out(out, left_out):
    """Say which of the person's own documents could not be used, and why."""
    for label, reason in left_out or ():
        out.write("Left out: %s (%s)\n" % (safe_value(label), safe_value(reason)))


def run_assemble(options, out):
    step = need(options, "step", out)
    run_id = need(options, "run", out)
    company = need(options, "company", out)
    if not step or not run_id or not company:
        return EXIT_ERROR
    try:
        assembled = join_flow.assemble_step(
            step,
            run_id,
            company,
            options.email or "",
            paste_files=options.paste_file,
        )
    except DraftError as refusal:
        if refusal.code != drafting.CODE_NO_SOURCES:
            raise
        say_left_out(out, getattr(refusal, "left_out", []))
        line(out, "codes", refusal.code)
        out.write(NO_SOURCES_LEFT + "\n")
        return EXIT_REFUSED
    line(out, "prompt", assembled.path)
    line(out, "draft", join_flow.draft_path(run_id, step))
    for label in assembled.included_labels:
        line(out, "included", label)
    for label in assembled.dropped_labels:
        line(out, "dropped", label)
    for code in assembled.codes:
        line(out, "note", code)
    say_left_out(out, assembled.left_out)
    if assembled.dropped_labels:
        out.write(
            "There was more material than one request holds, so the sources "
            "listed as dropped were left out whole.\n"
        )
    return EXIT_DONE


def run_review(options, out):
    step = need(options, "step", out)
    draft = need(options, "draft", out)
    if not step or not draft:
        return EXIT_ERROR
    reviewed = join_flow.review_step(step, draft, base_root=options.base)
    if reviewed.ready:
        out.write("ready\n")
        return EXIT_DONE
    line(out, "codes", ",".join(reviewed.codes))
    out.write(
        "That draft holds something that must not be written down, so write it "
        "again from the same request.\n"
    )
    return EXIT_REFUSED


def run_what_is_wrong(options, out):
    step = need(options, "step", out)
    answer = need(options, "answer", out)
    if not step or not answer:
        return EXIT_ERROR
    out.write(join_flow.what_is_wrong(step, answer))
    return EXIT_DONE


def run_approve(options, out):
    step = need(options, "step", out)
    draft = need(options, "draft", out)
    run_id = need(options, "run", out)
    if not step or not draft or not run_id:
        return EXIT_ERROR
    root = None
    if options.base:
        root = base_folder(options, out)
        if root is None:
            return EXIT_ERROR
    result = join_flow.approve_step(
        step,
        draft,
        run_id,
        base_root=root,
        parent=options.parent,
        company=options.company,
        email=options.email,
        name=options.name,
        confirmed_home=options.confirmed_home,
    )
    line(out, "base", result.root)
    line(out, "file", result.path)
    for code in result.codes:
        line(out, "note", code)
    out.write("That is written down, together with the record that you said yes.\n")
    return EXIT_DONE


def run_skip(options, out):
    step = need(options, "step", out)
    if not step:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        # Skipping writes a file saying the step was skipped, and there is
        # nowhere to write it until the first document has been approved.
        out.write(CANNOT_SKIP_FIRST + "\n")
        return EXIT_REFUSED
    result = join_flow.skip_step(step, root)
    line(out, "file", result.path)
    out.write(
        "That one is written down as skipped, and the next session will offer "
        "to finish it.\n"
    )
    return EXIT_DONE


def run_close(options, out):
    run_id = need(options, "run", out)
    if not run_id:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_ERROR
    result = join_flow.close_run(
        root, run_id, got_in_the_way=options.got_in_the_way, email=options.email
    )
    out.write(result.finding + "\n")
    if result.note_path:
        line(out, "note", result.note_path)
    if result.note_codes:
        if join_flow.NOTE_NOT_SAVED in result.note_codes:
            out.write(join_flow.NOTE_NOT_SAVED_MESSAGE + "\n")
        else:
            out.write(join_flow.NOTE_NOT_WRITTEN + "\n")
        line(out, "note-code", ",".join(result.note_codes))
    out.write(result.closing)
    return EXIT_DONE


def run_not_now(options, out):
    return offer_answer.main(["--answer", offer_answer.NOT_NOW])


def run_refusal(name):
    def run(options, out):
        out.write(join_flow.refuse_mode(name, options.session) + "\n")
        return EXIT_REFUSED

    return run


MODES = {
    "new-run": run_new_run,
    "propose-location": run_propose_location,
    "list-sources": run_list_sources,
    "freeze-sources": run_freeze_sources,
    "add-paste": run_add_paste,
    "assemble": run_assemble,
    "review": run_review,
    "what-is-wrong": run_what_is_wrong,
    "approve": run_approve,
    "skip": run_skip,
    "close": run_close,
    "not-now": run_not_now,
    "backup": run_refusal(join_flow.MODE_BACKUP),
    "invite": run_refusal(join_flow.MODE_INVITE),
    "join-link": run_refusal(join_flow.MODE_JOIN_LINK),
}


def main(argv=None):
    options = build_parser().parse_args(argv)
    step = MODES.get(options.mode)
    if step is None:
        sys.stderr.write("That is not a step of setting a base up.\n")
        return EXIT_ERROR
    # The company name is checked here rather than in each step, because it is
    # written into a folder name in one step and into a request in another, and
    # both of those need it to be a name and nothing else.
    if options.company:
        try:
            location.validate_company_name(options.company)
        except GtmBaseError:
            sys.stdout.write(BAD_COMPANY + "\n")
            return EXIT_REFUSED
    try:
        return step(options, sys.stdout)
    except IdentityNeeded:
        sys.stdout.write(NEEDS_EMAIL + "\n")
        return EXIT_REFUSED
    except (DraftError, ReviewError) as refusal:
        sys.stdout.write("codes=%s\n" % safe_value(",".join(_codes_of(refusal))))
        sys.stdout.write(
            "That step could not be finished, so nothing was written. Go back "
            "to the same step and try it again.\n"
        )
        return EXIT_REFUSED
    except GtmBaseError as failure:
        sys.stderr.write(str(failure) + "\n")
        return EXIT_REFUSED
    except Exception:
        sys.stderr.write(WENT_WRONG + "\n")
        return EXIT_ERROR


def _codes_of(failure):
    found = list(getattr(failure, "codes", []) or [])
    code = getattr(failure, "code", None)
    if code and code not in found:
        found.insert(0, code)
    return found or ["refused"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
