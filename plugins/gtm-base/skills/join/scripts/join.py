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
import io
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
    approval,
    adopt,
    constants,
    create_base,
    drafting,
    folder_identity,
    join_flow,
    location,
    machine,
    moment,
    names,
    offer_answer,
    paths,
    review,
    segments,
    sources,
    wordsfile,
)
from gtmbase.errors import (  # noqa: E402
    ConsentError,
    DraftError,
    GtmBaseError,
    IdentityNeeded,
    LocationError,
    PathError,
    ReviewError,
    StateError,
    ValidationError,
)

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NO_BASE_HERE = (
    "That folder is not a company base yet, so there is nothing there to add "
    "to."
)
WENT_WRONG = "GTM Base could not finish that step, so nothing was written."
CHANGE_NOT_IN_THE_BASE = (
    "That context change is not in this base, so there is nothing to ask "
    "about. Approve the change first, then run this again."
)
RECONCILE_ANSWER_UNKNOWN = (
    "That answer has to be yes or no, so nothing was recorded. Ask again and "
    "run this with the answer they gave."
)
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
NARROW_FIRST = (
    "That folder is large enough that nobody could read the list through, so "
    "the yes was not taken. Ask which of its folders hold the marketing "
    "material, then show the list for those folders and ask again."
)
SCOPE_CHANGED = (
    "What the base is for changed after the list was shown, so the yes was "
    "not taken. Run list-sources again, show the new list, and ask again."
)
NO_SUCH_FOLDER = (
    "That is not one of the folders in the list, so nothing was shown. Name "
    "one of the folders the counts above name instead."
)
NO_SURVEY_YET = (
    "Nothing has been proposed for this run yet, so there is nothing to list. "
    "Run survey first, say what it found, and ask whether that is it."
)
NO_FOLDERS_CHOSEN = (
    "Every place was dropped and none was added, so there is nothing left to "
    "show. Ask which folder holds the marketing material and name that one."
)
NOT_ON_THE_LIST = (
    "That is not on the list you agreed to, so nothing was read. Name one of "
    "the files or folders from that list instead."
)
ASK_AGAIN = (
    "A different list was shown after the yes, so nothing was read. Ask for a "
    "yes to the list as it is now before anything is drafted."
)
WILL_BE_LINKED = (
    "Your base will be linked to %s, so opening Claude Code in that folder "
    "brings the base with it."
)
LINKED = (
    "That folder and your base are now linked. Opening Claude Code in that "
    "folder brings the base with it."
)
UNLINKED = (
    "That folder and your base are no longer linked. The base itself is exactly "
    "as it was, and you can still open it in its own folder."
)
FOLDER_TAKEN = (
    "That folder already belongs with the base at %s, and a folder can belong "
    "with only one base. Name a different folder, or unlink that one first."
)
FOLDER_INSIDE_BASE = (
    "That folder is a base, sits inside one, or is the folder GTM Base keeps "
    "for itself, so it cannot be linked to a base. Name a folder of your own "
    "instead."
)
FOLDER_MISSING = "That folder is not on this computer, so nothing was linked."
NO_LINKS = "This account has no bases yet."
NO_BASE_OF_THAT_NAME = (
    "There is no base of that name on this computer. Say: show my linked "
    "folders, to see every base there is and the folder each one belongs with, "
    "then name one of those."
)
NO_BASE_AT_ALL = (
    "There is no base on this computer yet, so there is nothing to connect a "
    "folder to. Say: set up my company base, to make one."
)
MORE_THAN_ONE_BASE = (
    "There is more than one base this could mean, the one at %s and the one at "
    "%s, so nothing was changed. Name the base you want by the company it is "
    "for, or by its folder."
)
NAME_ALREADY_USED = (
    "There is already a folder for a company of that name, so a base built "
    "there could write over one you already have. Give me a name that tells "
    "the two apart and I will use that instead."
)
PLACE_KEEPS_HISTORY = (
    "That folder already keeps its own change history, and a base inside it "
    "would get tangled up with it, so the base cannot go there. Name a "
    "different folder, or let the base go in the folder kept for bases inside "
    "your home folder."
)
PLACE_IS_COPIED = (
    "Another program copies that folder off this computer by itself, and a "
    "base holds raw notes and the context you approve, so the base cannot go "
    "there. Name a different folder, or let the base go in the folder kept for "
    "bases inside your home folder."
)
PLACE_MIGHT_BE_COPIED = (
    "GTM Base cannot tell whether that folder is copied off this computer. "
    "Does any app copy this folder, or your whole home folder, to cloud "
    "storage automatically? If it does, the base should go somewhere else."
)
PLACE_IS_A_BASE = (
    "That folder is a base or sits inside one, so a second base cannot go "
    "there. Name a folder of your own instead."
)
PLACE_TAKEN = (
    "There is already something at that place, so nothing was built. Name a "
    "different folder."
)
LINK_NOT_RECORDED = (
    "Your base was built, but it was not linked to %s. The base is fine. Say: "
    "link this folder to my base, to finish that one step."
)
# The one sentence said for each way a place can be turned down. A refusal the
# person cannot act on is a dead end, so every one of these names what to do
# next.
PLACE_REFUSALS = {
    location.CODE_COMPANY_FOLDER_EXISTS: NAME_ALREADY_USED,
    location.CODE_INSIDE_REPOSITORY: PLACE_KEEPS_HISTORY,
    location.CODE_SYNCED: PLACE_IS_COPIED,
    location.CODE_SYNC_UNKNOWN: PLACE_MIGHT_BE_COPIED,
    location.CODE_INSIDE_BASE: PLACE_IS_A_BASE,
    location.CODE_INSIDE_SEAT_HOME: PLACE_IS_A_BASE,
    location.CODE_TARGET_EXISTS: PLACE_TAKEN,
    location.CODE_STRAY_BASE: PLACE_TAKEN,
}

# Most labels the preview names one by one before it stops naming them.
PREVIEW_LABELS_SHOWN = 20
# Why a document is not going into this draft.
REASON_OVER_THE_CAP = "over-the-cap"
REASON_UNUSABLE = "unusable:%s"

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


def plain_value(value):
    """One value, made safe to put inside a sentence a person reads.

    It is the same treatment as a name and value line without the quotation
    marks, because a sentence naming three of somebody's own documents reads
    badly with quotation marks around each of them and there is no line for
    them to break out of.
    """
    text = "" if value is None else str(value)
    text = "".join(
        CONTROL_STAND_IN if (ord(character) < 32 or ord(character) == 127) else character
        for character in text
    )
    if len(text) > VALUE_MAX:
        text = text[:VALUE_MAX] + "..."
    return text


def held_apart(out, lines):
    """Lines that can carry a name somebody typed.

    Everything a step prints is held apart as data in one fence by `main`,
    because the name of a file, a folder or a segment is whatever somebody
    typed, a slug made from one still reads as words, and chasing each line
    that might carry one missed some twice (Astra's review of Release B and
    its confirmations, finding 5). This only keeps the lines together.
    """
    for text in lines:
        if text:
            out.write(text + "\n")


def line(out, name, value):
    """Write one name and value line, with the value made safe first."""
    out.write("%s=%s\n" % (name, safe_value(value)))


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("mode", help="which step of setting a base up to run")
    parser.add_argument("--run", help="the identifier of this setup run")
    parser.add_argument(
        "--step", help="icp, umbrella, segment, change-entry, or positioning"
    )
    parser.add_argument(
        "--segment",
        help="the file name the segments step printed for one segment to draft",
    )
    parser.add_argument(
        "--questions-open",
        action="store_true",
        help="they chose to approve the draft with its questions left open",
    )
    parser.add_argument("--company", help="the company the base is for")
    parser.add_argument("--content-folder", help="the folder holding their material")
    parser.add_argument(
        "--content-folder-file",
        help="a file holding the folder that holds their material",
    )
    parser.add_argument("--folder", help="the folder to list or to fix the list of")
    parser.add_argument(
        "--folder-file", help="a file holding the folder to list or to fix"
    )
    parser.add_argument("--session", help="the identifier of this session")
    parser.add_argument("--label", help="a short name for one piece of text")
    parser.add_argument(
        "--label-file", help="a file holding a short name for one piece of text"
    )
    parser.add_argument(
        "--for",
        dest="for_kind",
        help="which kind of words a file is being asked for",
    )
    parser.add_argument(
        "--company-file", help="a file holding the company the base is for"
    )
    parser.add_argument("--from", dest="from_file", help="the file the text is in")
    parser.add_argument(
        "--paste-file",
        action="append",
        default=[],
        help="text held for this run, once per piece",
    )
    parser.add_argument("--draft", help="the file the draft was written to")
    parser.add_argument(
        "--only",
        help="only these files from the list, by their numbers, separated by commas",
    )
    parser.add_argument(
        "--from-survey",
        action="store_true",
        help="list the places the finding step proposed, with their changes",
    )
    parser.add_argument(
        "--add",
        action="append",
        default=[],
        dest="added",
        help="one more folder to list alongside the places proposed",
    )
    parser.add_argument(
        "--add-file",
        action="append",
        default=[],
        dest="added_files",
        help="a file holding one more folder to list, once per folder",
    )
    parser.add_argument(
        "--drop",
        action="append",
        default=[],
        dest="dropped",
        help="the number of one place proposed to leave out, once per place",
    )
    parser.add_argument(
        "--keep",
        action="append",
        default=[],
        dest="kept",
        help="the number of one place proposed that the person named to use, "
        "once per place; every place not named is left out",
    )
    parser.add_argument(
        "--only-folder",
        action="append",
        default=[],
        help="only the files in this numbered folder of the list, once each",
    )
    parser.add_argument("--answer", help="what the person said, in their own words")
    parser.add_argument(
        "--answer-file", help="a file holding what the person said, in their own words"
    )
    parser.add_argument(
        "--got-in-the-way-file",
        help="a file holding what got in the way, in their own words",
    )
    parser.add_argument("--entry", help="the context change this step is about")
    parser.add_argument("--file", dest="file", help="the one document to record an answer about")
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
    parser.add_argument(
        "--beside",
        action="store_true",
        help="they asked for the base to sit inside the folder they named",
    )
    parser.add_argument(
        "--scope-file",
        help="a file holding the part of the company the base is for",
    )
    parser.add_argument(
        "--whole",
        action="store_true",
        help="they said the base is for the whole company",
    )
    parser.add_argument(
        "--segments-file",
        help="a file holding one line per segment: the answer, a number, a name",
    )
    parser.add_argument(
        "--hash",
        help="the hash adopt-show printed for the page the person said yes to",
    )
    return parser


COULD_NOT_READ = (
    "GTM Base could not read the file holding their words, so nothing was "
    "done. Write it again and run this with the path to it."
)
# Said when the draft being approved still asks the person something and they
# have not said to leave it open (Unit 1.7b).
QUESTIONS_NOT_ANSWERED = (
    "That draft still leaves questions for you to answer, so nothing was "
    "written. Answer them, or say to approve it with them left open."
)
# Said when a step is asked for that the segments this run settled rule out.
UMBRELLA_INSTEAD = (
    "Your base holds several segments, so the customer profile is drafted "
    "across all of them rather than as one. Draft that instead."
)
NOT_SEVERAL_SEGMENTS = (
    "This run settled one segment or none, so the customer profile is drafted "
    "in full as one document. Draft that instead."
)
NOT_THIS_SEGMENTS_DRAFT = (
    "That draft is not the one written for this segment, so nothing was done. "
    "Use the draft file the assemble step named for it."
)
CANNOT_SKIP_THIS = (
    "Only the customer profile and the positioning are ever written down as "
    "skipped. A segment you do not want now is simply not approved, and "
    "nothing is written."
)
NOT_A_SEGMENT_TO_DRAFT = (
    "That is not a segment this run settled to be drafted, so nothing was "
    "done. Draft one of the segments you said to draft."
)
NEEDS_A_RUN_OR_SESSION = (
    "This step needs to know which setup run it belongs to, so nothing was "
    "done. Run it again and say which run it is."
)
ONLY_BY_NUMBER = (
    "Name the files by the number beside each one on the list, separated by "
    "commas, because a file name is not something to put in a command."
)
FOLDERS_BY_NUMBER = (
    "Name the folders by the number beside each one on the list, because a "
    "folder name is not something to put in a command."
)
NO_SUCH_FOLDER_NUMBER = (
    "That is not one of the numbers beside the folders on the list, so "
    "nothing was shown. Read the list out again and ask which of those."
)


def chosen_folders(options, out):
    """Which folders of the list the person picked, by their numbers.

    A folder name is whatever somebody called their folder, and quotation
    marks are not a fix: a folder called "Brandon's Docs" breaks the command
    that carries it. So the listing prints a number beside each folder and the
    number is what comes back (finding F6 of the third look).
    """
    asked = [str(item).strip() for item in (options.only_folder or []) if str(item).strip()]
    if not asked:
        return [], True
    if not all(item.isdigit() for item in asked):
        out.write(FOLDERS_BY_NUMBER + "\n")
        return None, False
    shown = join_flow.folders_shown(options.run) if options.run else []
    found = []
    for item in asked:
        number = int(item)
        if number < 1 or number > len(shown):
            out.write(NO_SUCH_FOLDER_NUMBER + "\n")
            return None, False
        found.append(shown[number - 1])
    return found, True


def dropped_places(options, out):
    """Which of the places the finding step proposed the person dropped.

    They are named by the number the finding step printed beside each place,
    for the same reason every other folder is (finding R9 of Astra's third
    look, which found the places still named by name).
    """
    return places_by_number(options.dropped, options, out)


def kept_places(options, out):
    """Which of the places the finding step proposed the person named to use.

    Named by number, like a place dropped. Naming the places to use is an
    explicit choice, which is not asked to be narrowed again (Unit 1.6).
    """
    return places_by_number(options.kept, options, out)


def places_by_number(numbers, options, out):
    """The proposed places a list of numbers means, or a refusal said once."""
    asked = [str(item).strip() for item in (numbers or []) if str(item).strip()]
    if not asked:
        return [], True
    if not all(item.isdigit() for item in asked):
        out.write(FOLDERS_BY_NUMBER + "\n")
        return None, False
    found = join_flow.load_survey(options.run) if options.run else None
    places = found["places"] if found else []
    chosen = []
    for item in asked:
        number = int(item)
        if number < 1 or number > len(places):
            out.write(NO_SUCH_FOLDER_NUMBER + "\n")
            return None, False
        chosen.append(places[number - 1])
    return chosen, True


def added_places(options, out):
    """The folders the person named to add, read out of the files they are in."""
    added = list(options.added or [])
    for path in options.added_files or []:
        text = words_from(path, options, out)
        if text is None:
            return None, False
        added.append(text)
    return added, True


def the_content_folder(options, out):
    """The folder somebody keeps their material in, from a file when one is named.

    A folder is never put on a command line by the skill, because a folder
    called Brandon's Docs breaks the command that carries it (finding F6 of
    the third look, which this one flag was left out of until R9).
    """
    if options.content_folder_file:
        text = words_from(options.content_folder_file, options, out)
        return text, text is not None
    return options.content_folder, True


def the_folder(options, out):
    """The folder this step works on, read out of a file when one is named."""
    if options.folder_file:
        return words_from(options.folder_file, options, out)
    return need(options, "folder", out)


def words_key(options, out):
    """Which run or base a words file belongs to, or nothing at all.

    A setup run has a run identifier and nothing else, because there is no
    base yet. Every step after that is run inside a base, and the base is what
    a words file belongs to there: a session moves the moment a second window
    opens, and an answer somebody had just typed stopped being readable
    (finding L3 of the third look).
    """
    key = options.run or options.session
    if key:
        return key
    try:
        resolution = paths.resolve_base(
            options.base or os.getcwd(), machine.load_machine_state()
        )
        if resolution.base_id:
            return resolution.base_id
    except Exception:
        pass
    out.write(NEEDS_A_RUN_OR_SESSION + "\n")
    return None


def words_from(path, options, out):
    """What somebody typed, read out of a file this script itself handed out.

    Their words go in a file and the path goes on the command line, because a
    sentence somebody wrote with a dollar sign and a bracket in it becomes a
    shell instruction the moment it is written into a command. What is read
    here is text and nothing in it is ever run.

    The path has to be one this script handed out, which is finding V6 of the
    2026-09-20 verification round: any path at all used to be read this way, so
    a document could have somebody's private notes read into their base with
    nobody asked. Reading somebody's own documents is a step of its own, with
    its own question and its own record, and a flag on a command is not that
    step.
    """
    key = words_key(options, out)
    if key is None:
        return None
    text = wordsfile.read_words(path, key)
    if text is None:
        out.write(wordsfile.NOT_OURS + "\n")
        return None
    return text


def a_draft_of_this_run(path, options, out):
    """Whether one draft file is the one this run named, and nothing else."""
    key = words_key(options, out)
    if key is None:
        return False
    if not wordsfile.named_for_a_draft(path, key):
        out.write(wordsfile.NOT_A_DRAFT + "\n")
        return False
    return True


def run_words_file(options, out):
    """Hand out one path for somebody's own words, and make nothing else."""
    kind = options.for_kind
    if not kind:
        out.write("This step needs --for.\n")
        return EXIT_ERROR
    key = words_key(options, out)
    if key is None:
        return EXIT_ERROR
    if kind not in wordsfile.KINDS:
        out.write(wordsfile.NOT_OURS + "\n")
        return EXIT_REFUSED
    wordsfile.ensure_words_dir(key)
    line(out, "words", wordsfile.new_words_path(key, kind))
    return EXIT_DONE


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
    if not resolution.active or not resolution.root:
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
    content_folder, read = the_content_folder(options, out)
    if not read:
        return EXIT_REFUSED
    options.content_folder = content_folder
    try:
        proposal = join_flow.propose_location(
            company,
            content_folder=options.content_folder,
            confirmed_home=options.confirmed_home,
            beside=options.beside,
        )
    except LocationError as refusal:
        sentence = PLACE_REFUSALS.get(refusal.code)
        if sentence is None:
            raise
        out.write(sentence + "\n")
        line(out, "codes", refusal.code)
        return EXIT_REFUSED
    out.write(location.describe(proposal) + "\n")
    line(out, "target", proposal.target_path)
    line(out, "parent", proposal.parent)
    line(out, "reason", proposal.reason_code)
    if options.content_folder and not options.beside:
        held_apart(out, ["belongs-with=%s" % safe_value(options.content_folder)])
        out.write(WILL_BE_LINKED % plain_value(options.content_folder) + "\n")
    if proposal.warning_code:
        line(out, "warning", proposal.warning_code)
    return EXIT_DONE


def run_survey(options, out):
    folder = the_folder(options, out)
    run_id = need(options, "run", out)
    if not folder or not run_id:
        return EXIT_ERROR
    found = join_flow.survey_sources(run_id, folder)
    out.write(found.sentence() + "\n")
    # The number is what a place is dropped by afterwards, in the order the
    # places were written down (finding R9 of Astra's third look).
    listed = []
    for number, place in enumerate(found.places, start=1):
        counts = " ".join(
            "%s=%d" % (safe_value(kind), place.counts_by_kind[kind])
            for kind, _words in constants.MARKETING_KINDS
            if place.counts_by_kind.get(kind)
        )
        listed.append(
            "place=%s number=%d score=%d%s mostly=%s"
            % (
                safe_value(place.relative_folder),
                number,
                place.score,
                " " + counts if counts else "",
                safe_value(place.mostly),
            )
        )
    # Each file a place was proposed for, and each set of files whose names
    # say they are versions of one document, for the assistant only. Nothing
    # here was read past a name and a first heading (Unit 1.6).
    for number, place in enumerate(found.places, start=1):
        for relative, kind in place.candidates:
            listed.append(
                "candidate=%s place=%d kind=%s"
                % (safe_value(relative), number, safe_value(kind))
            )
    for group in found.version_sets:
        for other in group[1:]:
            listed.append(
                "version-set=%s other=%s" % (safe_value(group[0]), safe_value(other))
            )
    held_apart(out, listed)
    for note in found.notes:
        line(out, "note", note)
    # Two or more places that each hold a customer profile and a positioning
    # of their own: the material plainly splits, so the scope question is
    # asked before the places are settled (Unit 1.7a).
    split = join_flow.places_that_split(run_id)
    if split:
        numbers = [
            str(number)
            for number, place in enumerate(found.places, start=1)
            if place.relative_folder in split
        ]
        line(out, "splits", ",".join(numbers))
        out.write(
            constants.SCOPE_SPLITS_SENTENCE
            % {
                "places": plain_value(
                    and_list([sources.place_label(place) for place in split])
                )
            }
            + "\n"
        )
    return EXIT_DONE


def and_list(names):
    """Names joined the way a sentence joins them."""
    names = list(names)
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


SCOPE_NOT_A_NAME = (
    "That is not a short name for part of the company, so nothing was held. "
    "Write it as a short name, such as the name of a product line, and run "
    "this again."
)
SCOPE_AFTER_THE_YES = (
    "The list of files was already agreed to, or the customer profile already "
    "approved, so what the base is for cannot change in this run. Carry on."
)
SCOPE_NEEDS_AN_ANSWER = (
    "This step needs either --scope-file with the part of the company, or "
    "--whole, so nothing was held."
)


def run_scope(options, out):
    """Hold what the base is for, and say it back in one sentence."""
    run_id = need(options, "run", out)
    if not run_id:
        return EXIT_ERROR
    covers = None
    if options.scope_file:
        covers = words_from(options.scope_file, options, out)
        if covers is None:
            return EXIT_REFUSED
    if (covers is None) == (not options.whole):
        out.write(SCOPE_NEEDS_AN_ANSWER + "\n")
        return EXIT_ERROR
    try:
        label = join_flow.hold_scope(run_id, covers=covers, whole=options.whole)
    except ValidationError as refusal:
        line(out, "codes", refusal.code)
        if refusal.code == join_flow.CODE_SCOPE_AFTER_THE_YES:
            out.write(SCOPE_AFTER_THE_YES + "\n")
        else:
            out.write(SCOPE_NOT_A_NAME + "\n")
        return EXIT_REFUSED
    if label:
        held_apart(
            out,
            [
                "covers=%s" % safe_value(label),
                constants.SCOPE_HELD_SENTENCE % {"covers": plain_value(label)},
            ],
        )
    else:
        line(out, "covers", "whole")
        out.write(constants.SCOPE_WHOLE_SENTENCE + "\n")
    return EXIT_DONE


NO_YES_YET = (
    "There is no agreed list of files for this run yet, so there are no "
    "documents to ask about. Take the yes first."
)
SEGMENTS_UNREADABLE = (
    "That list of segments could not be read, so nothing was kept. Write one "
    "line per segment: adopt, draft, or leave-out, then the number of its "
    "document or a hyphen, then its name."
)
SEGMENTS_NO_SUCH_DOCUMENT = (
    "One of those numbers is not beside any document on the list, so nothing "
    "was kept. Read the list out again and ask which document they meant."
)
SEGMENTS_ADOPT_NEEDS_A_DOCUMENT = (
    "A segment can be taken from a finished document only when the number of "
    "that document is given, so nothing was kept. Give its number, or draft it."
)


def run_segments(options, out):
    """Show the documents that each describe one segment, numbered, and ask."""
    run_id = need(options, "run", out)
    if not run_id:
        return EXIT_ERROR
    try:
        found = join_flow.segment_candidates(run_id)
    except ConsentError as refusal:
        if refusal.code != join_flow.CODE_NO_CONSENT:
            raise
        line(out, "codes", refusal.code)
        out.write(NO_YES_YET + "\n")
        return EXIT_REFUSED
    line(out, "documents", len(found))
    if len(found) < 2:
        # One document, or none, is one segment or none: the profile covers it
        # in full and there is nothing to ask, unless the person has said they
        # sell to several groups, which the next step still takes.
        line(out, "codes", "one-or-none")
        return EXIT_DONE
    held_apart(
        out,
        [
            "candidate=%s number=%d" % (safe_value(candidate.path), candidate.number)
            for candidate in found
        ],
    )
    out.write(segments.FOUND_SENTENCE % {"count": names.counted(len(found))} + "\n")
    # A document's name is whatever somebody typed when they saved it, so the
    # numbered list is held apart as data like the documents themselves
    # (Astra's review of the merged Units 1.7c and 1.7d, finding 7).
    out.write(
        moment.fenced(
            "\n".join(
                "%d. %s" % (candidate.number, plain_value(candidate.label))
                for candidate in found
            )
        )
        + "\n"
    )
    out.write(segments.ASK_SENTENCE + "\n")
    return EXIT_DONE


SEGMENT_REFUSALS = {
    segments.CODE_UNREADABLE: SEGMENTS_UNREADABLE,
    segments.CODE_NO_SUCH_DOCUMENT: SEGMENTS_NO_SUCH_DOCUMENT,
    segments.CODE_ADOPT_NEEDS_A_DOCUMENT: SEGMENTS_ADOPT_NEEDS_A_DOCUMENT,
}


def run_segments_settle(options, out):
    """Keep the inventory the person gave, and read it back to them."""
    run_id = need(options, "run", out)
    path = need(options, "segments-file", out)
    if not run_id or not path:
        return EXIT_ERROR
    text = words_from(path, options, out)
    if text is None:
        return EXIT_REFUSED
    try:
        inventory = join_flow.settle_segments(run_id, text)
    except segments.InventoryRefused as refusal:
        line(out, "codes", refusal.code)
        sentence = refusal.sentence or SEGMENT_REFUSALS.get(
            refusal.code, SEGMENTS_UNREADABLE
        )
        # A refusal can name the segment it is about.
        held_apart(out, [sentence])
        return EXIT_REFUSED
    for segment in inventory.segments:
        out.write(
            "segment=%s answer=%s number=%s\n"
            % (
                safe_value(segment.slug),
                safe_value(segment.answer),
                safe_value("-" if segment.number is None else segment.number),
            )
        )
    # Every name in these was checked as it was settled: one line, no
    # control character, and no longer than the cap. A name is still
    # whatever somebody typed, so the read-back is held apart as data
    # (Astra's confirmation of the Release B fixes, finding 5).
    held_apart(out, segments.readback(inventory))
    return EXIT_DONE


LIST_REFUSALS = {
    join_flow.CODE_NO_SUCH_FOLDER: NO_SUCH_FOLDER,
    join_flow.CODE_ADDED_NOT_DIRECTLY_INSIDE: join_flow.ADDED_NOT_DIRECTLY_INSIDE,
    join_flow.CODE_NO_SURVEY: NO_SURVEY_YET,
    join_flow.CODE_NO_FOLDERS_CHOSEN: NO_FOLDERS_CHOSEN,
}


def run_list_sources(options, out):
    folder = the_folder(options, out)
    run_id = need(options, "run", out)
    if not folder or not run_id:
        return EXIT_ERROR
    only_folders, read = chosen_folders(options, out)
    if not read:
        return EXIT_REFUSED
    dropped, read = dropped_places(options, out)
    if not read:
        return EXIT_REFUSED
    added, read = added_places(options, out)
    if not read:
        return EXIT_REFUSED
    kept, read = kept_places(options, out)
    if not read:
        return EXIT_REFUSED
    try:
        listing = join_flow.list_sources(
            folder,
            run_id,
            only_folders=only_folders,
            from_survey=options.from_survey,
            added=added,
            dropped=dropped,
            kept=kept,
        )
    except ConsentError as refusal:
        sentence = LIST_REFUSALS.get(refusal.code)
        if sentence is None:
            raise
        line(out, "codes", refusal.code)
        out.write(sentence + "\n")
        return EXIT_REFUSED
    if sources.CODE_NARROW_FIRST in listing.codes:
        out.write(
            constants.CONSENT_NARROW_SENTENCE
            % {
                "files": names.counted(len(listing.readable)),
                "folders": names.counted(len(listing.by_folder)),
            }
            + "\n"
        )
    # Every listing prints the folder numbers, in the order they are written
    # down, and so the order a number is taken back against. A small listing
    # printed none, and a narrowed one printed numbers that chose a folder it
    # had just left out (finding R9 of Astra's third look). Each folder says
    # what it mostly holds, from the paths of its files alone (Unit 1.6).
    mostly = sources.folder_mostly(listing.root, listing.readable)
    for number, name in enumerate(join_flow.folders_in_order(listing), start=1):
        out.write(
            "folder=%s number=%d count=%d mostly=%s\n"
            % (
                safe_value(name),
                number,
                listing.by_folder[name],
                safe_value(mostly.get(name, constants.MOSTLY_OTHER_LABEL)),
            )
        )
    shown = join_flow.load_listing(run_id) or {}
    choice = shown.get("choice", constants.CHOICE_PLAIN_YES)
    line(out, "choice", choice)
    if choice == constants.CHOICE_EXPLICIT:
        out.write(
            explicit_count(
                len(join_flow.files_in_order(listing)),
                len(shown.get("folders") or listing.by_folder),
            )
            + "\n"
        )
    out.write("These are the files GTM Base would read.\n")
    # The number is what the skill names a file by later, because a file name
    # is somebody else's text and a number is not (finding N2), and it is the
    # number of the file written down in that place (finding R9).
    held_apart(
        out,
        [
            "read=%s number=%d kind=%s date=%s"
            % (
                safe_value(entry.path),
                number,
                safe_value(entry.kind),
                safe_value(entry.modified_date or "none"),
            )
            for number, entry in enumerate(join_flow.files_in_order(listing), start=1)
        ],
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
        held_apart(
            out, ["company-hint=%s" % safe_value(hint) for hint in listing.company_hints]
        )
    return EXIT_DONE


def run_freeze_sources(options, out):
    folder = the_folder(options, out)
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
        if refusal.code == join_flow.CODE_NARROW_FIRST:
            line(out, "codes", refusal.code)
            out.write(NARROW_FIRST + "\n")
            return EXIT_REFUSED
        if refusal.code == join_flow.CODE_SCOPE_CHANGED:
            line(out, "codes", refusal.code)
            out.write(SCOPE_CHANGED + "\n")
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
    session = need(options, "session", out)
    if options.label_file:
        label = words_from(options.label_file, options, out)
        if label is None:
            return EXIT_REFUSED
    else:
        label = need(options, "label", out)
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
    # A label is the name of their file, so it is held apart as data (Astra's
    # confirmation of the Release B fixes, finding 5).
    held_apart(
        out,
        [
            "Left out: %s (%s)" % (safe_value(label), safe_value(reason))
            for label, reason in left_out or ()
        ],
    )


def say_removed(out, removed):
    """Say what was taken out of each document, in one sentence for each."""
    held_apart(
        out,
        [sources.removed_sentence(label, counts) for label, counts in removed or ()],
    )


def explicit_count(files, folders):
    """The count a person confirms after naming their folders themselves."""
    return constants.EXPLICIT_COUNT_SENTENCE % {
        "files": names.how_many(files, "file", "files"),
        "folders": (
            "folder" if folders == 1 else names.how_many(folders, "folder", "folders")
        ),
    }


# Which sentence says why one version of a document was not used.
VERSION_SENTENCES = {
    join_flow.VersionLeftOut.FINAL: constants.VERSION_NOT_USED_FINAL,
    join_flow.VersionLeftOut.FINAL_OVER_NEWER: constants.VERSION_NOT_USED_FINAL_OVER_NEWER,
    join_flow.VersionLeftOut.SET_ASIDE: constants.VERSION_NOT_USED_SET_ASIDE,
    join_flow.VersionLeftOut.LATER_NUMBER: constants.VERSION_NOT_USED_LATER_NUMBER,
    join_flow.VersionLeftOut.NEWER: constants.VERSION_NOT_USED_NEWER,
    join_flow.VersionLeftOut.SAME_DAY: constants.VERSION_NOT_USED_SAME_DAY,
}


def say_versions(out, superseded):
    """Say which version of each document was left out and why, and any conflict.

    Unit 1.6: a version is never left out in silence, and two versions that
    say different things are said to, rather than one quietly chosen.
    """
    for version in superseded or ():
        names = {
            "older": plain_value(version.older),
            "winner": plain_value(version.winner),
        }
        out.write(VERSION_SENTENCES[version.reason] % names + "\n")
        if version.differs:
            out.write(constants.VERSION_CONFLICT % names + "\n")


def say_how_much(out, previewed):
    """Say how much this draft reads, what it leaves out, and why at all.

    The person hears the count every time. When the cap left anything out,
    they hear why a draft reads a limited amount at all, which the preview
    never used to say. Only a plain yes is then asked whether to narrow it;
    folders the person named are not asked about again (ruling 2).
    """
    read = len(previewed.included_labels)
    left = (
        list(previewed.dropped_labels)
        + [label for label, _reason in previewed.left_out]
        + [version.older_line for version in previewed.superseded]
    )
    chosen = previewed.narrowed
    if left:
        out.write(
            (constants.PREVIEW_READS_SOME_CHOSEN if chosen else constants.PREVIEW_READS_SOME)
            % {
                "read": names.counted(read),
                "total": names.counted(previewed.total),
                "left": names.counted(len(left)),
                "labels": ", ".join(plain_value(label) for label in left),
            }
            + "\n"
        )
    elif read == 0:
        # Nothing was named for this draft at all, so there is no count to
        # say, and the step after this says there is nothing to draft from.
        return
    elif read == 1:
        out.write(
            (constants.PREVIEW_READS_THE_ONE_CHOSEN if chosen else constants.PREVIEW_READS_THE_ONE)
            + "\n"
        )
    else:
        out.write(
            (constants.PREVIEW_READS_ALL_CHOSEN if chosen else constants.PREVIEW_READS_ALL)
            % {"read": names.counted(read)}
            + "\n"
        )
    if previewed.dropped_labels:
        out.write(constants.PREVIEW_WHY_LIMITED + "\n")
    say_versions(out, previewed.superseded)
    # Only a plain yes is asked, and only before it has been narrowed: a
    # draft the person narrowed has had its question answered.
    if previewed.choice != constants.CHOICE_EXPLICIT and not chosen:
        if previewed.dropped_labels:
            out.write(constants.PREVIEW_NARROW_ASK_SOME + "\n")
        else:
            out.write(constants.PREVIEW_NARROW_ASK_ALL + "\n")


def narrowing(options, out):
    """The two ways one draft may be narrowed to part of the agreed list.

    Files are named by the number beside them on the list this run printed, and
    never by their names. Finding N2 of the 2026-09-20 verification round: a
    name comes off a file on the disk, and a file may be named anything at all,
    so a name written into a command is somebody else's text in a command.
    """
    numbers = None
    if options.only:
        pieces = [piece.strip() for piece in options.only.split(",") if piece.strip()]
        if not pieces or not all(piece.isdigit() for piece in pieces):
            out.write(ONLY_BY_NUMBER + "\n")
            return None, None, False
        numbers = [int(piece) for piece in pieces]
    folders, read = chosen_folders(options, out)
    if not read:
        return None, None, False
    return numbers, folders or None, True


def a_reading_refusal(refusal, out):
    """Say one of the two refusals a draft's reading can meet, or say nothing.

    Returns whether it said one. A number or folder that is not on the agreed
    list is one; a different list shown after the yes is the other, and it
    stops everything until that list has a yes of its own (Unit 1.6).
    """
    sentence = {
        join_flow.CODE_NOT_CONSENTED: NOT_ON_THE_LIST,
        join_flow.CODE_ASK_AGAIN: ASK_AGAIN,
    }.get(refusal.code)
    if sentence is None:
        return False
    line(out, "codes", refusal.code)
    out.write(sentence + "\n")
    return True


def older_version_lines(superseded):
    """One line for the assistant for each version a draft leaves out."""
    return [
        "left-out=%s reason=%s"
        % (safe_value(version.older_line), safe_value(constants.REASON_OLDER_VERSION))
        for version in superseded or ()
    ]


def say_older_versions(out, superseded):
    """The lines for the versions a draft leaves out, held apart as data."""
    held_apart(out, older_version_lines(superseded))


STEP_REFUSALS = {
    join_flow.CODE_UMBRELLA_INSTEAD: UMBRELLA_INSTEAD,
    join_flow.CODE_NO_SEVERAL_SEGMENTS: NOT_SEVERAL_SEGMENTS,
    segments.CODE_NOT_TO_DRAFT: NOT_A_SEGMENT_TO_DRAFT,
    join_flow.CODE_NOT_THIS_SEGMENTS_DRAFT: NOT_THIS_SEGMENTS_DRAFT,
    join_flow.CODE_NO_RUN: NEEDS_A_RUN_OR_SESSION,
    "cannot-skip": CANNOT_SKIP_THIS,
    join_flow.CODE_DRAFT_NOT_AGREED: join_flow.DRAFT_NOT_AGREED,
}


def a_step_refusal(refusal, out):
    """Say why a step the settled segments rule out was refused, when it was."""
    sentence = STEP_REFUSALS.get(getattr(refusal, "code", None))
    if sentence is None:
        return False
    line(out, "codes", refusal.code)
    out.write(sentence + "\n")
    return True


def run_preview(options, out):
    step = need(options, "step", out)
    run_id = need(options, "run", out)
    if not step or not run_id:
        return EXIT_ERROR
    only, only_folder, read = narrowing(options, out)
    if not read:
        return EXIT_REFUSED
    try:
        previewed = join_flow.preview_step(
            run_id,
            step,
            paste_files=options.paste_file,
            only_index=only,
            only_folder=only_folder,
            segment=options.segment,
        )
    except ConsentError as refusal:
        if not a_reading_refusal(refusal, out):
            raise
        return EXIT_REFUSED
    except ReviewError as refusal:
        if not a_step_refusal(refusal, out):
            raise
        return EXIT_REFUSED
    line(out, "step", previewed.step)
    line(out, "choice", previewed.choice)
    line(out, "going-in", len(previewed.included_labels))
    line(
        out,
        "left-out-count",
        len(previewed.dropped_labels)
        + len(previewed.left_out)
        + len(previewed.superseded),
    )
    line(out, "total", previewed.total)
    # Every line here names one of their files, so all of it is held apart as
    # data (Astra's confirmation of the Release B fixes, finding 5).
    held_apart(
        out,
        ["included=%s" % safe_value(label) for label in previewed.included_labels[:PREVIEW_LABELS_SHOWN]]
        + [
            "left-out=%s reason=%s" % (safe_value(label), safe_value(REASON_OVER_THE_CAP))
            for label in previewed.dropped_labels
        ]
        + [
            "left-out=%s reason=%s" % (safe_value(label), safe_value(REASON_UNUSABLE % reason))
            for label, reason in previewed.left_out
        ]
        + older_version_lines(previewed.superseded),
    )
    for code in previewed.codes:
        line(out, "note", code)
    say_removed(out, previewed.removed)
    say_how_much(out, previewed)
    return EXIT_DONE


def run_assemble(options, out):
    step = need(options, "step", out)
    run_id = need(options, "run", out)
    company = need(options, "company", out)
    if not step or not run_id or not company:
        return EXIT_ERROR
    only, only_folder, read = narrowing(options, out)
    if not read:
        return EXIT_REFUSED
    try:
        assembled = join_flow.assemble_step(
            step,
            run_id,
            company,
            options.email or "",
            paste_files=options.paste_file,
            only_index=only,
            only_folder=only_folder,
            segment=options.segment,
        )
    except ConsentError as refusal:
        if not a_reading_refusal(refusal, out):
            raise
        return EXIT_REFUSED
    except ReviewError as refusal:
        if not a_step_refusal(refusal, out):
            raise
        return EXIT_REFUSED
    except DraftError as refusal:
        if refusal.code != drafting.CODE_NO_SOURCES:
            raise
        say_left_out(out, getattr(refusal, "left_out", []))
        line(out, "codes", refusal.code)
        out.write(NO_SOURCES_LEFT + "\n")
        return EXIT_REFUSED
    line(out, "prompt", assembled.path)
    settled = (
        join_flow.segment_to_draft(run_id, options.segment)
        if step == drafting.STEP_SEGMENT
        else None
    )
    line(out, "draft", join_flow.draft_path(run_id, step, settled))
    held_apart(
        out,
        ["included=%s" % safe_value(label) for label in assembled.included_labels]
        + ["dropped=%s" % safe_value(label) for label in assembled.dropped_labels]
        + older_version_lines(assembled.superseded),
    )
    for code in assembled.codes:
        line(out, "note", code)
    say_left_out(out, assembled.left_out)
    say_removed(out, assembled.removed)
    # The count, the reason, and any narrowing question were said at the
    # preview, and the person has answered them by now. Saying them again here
    # asked a second time what had just been settled (Unit 1.6).
    return EXIT_DONE


def run_review(options, out):
    step = need(options, "step", out)
    draft = need(options, "draft", out)
    if not step or not draft:
        return EXIT_ERROR
    if not a_draft_of_this_run(draft, options, out):
        return EXIT_REFUSED
    try:
        reviewed = join_flow.review_step(
            step,
            draft,
            base_root=options.base,
            run_id=options.run,
            segment=options.segment,
        )
    except ReviewError as refusal:
        if not a_step_refusal(refusal, out):
            raise
        return EXIT_REFUSED
    if reviewed.ready:
        out.write("ready\n")
        if reviewed.questions:
            # The questions themselves are in the draft, where the person
            # reads them; only how many there are is said here.
            line(out, "questions", reviewed.questions)
            out.write(join_flow.draft_questions_sentence(reviewed.questions) + "\n")
        return EXIT_DONE
    line(out, "codes", ",".join(reviewed.codes))
    out.write(
        "That draft holds something that must not be written down, so write it "
        "again from the same request.\n"
    )
    return EXIT_REFUSED


def run_what_is_wrong(options, out):
    step = need(options, "step", out)
    if options.answer_file:
        answer = words_from(options.answer_file, options, out)
        if answer is None:
            return EXIT_REFUSED
    else:
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
    if not a_draft_of_this_run(draft, options, out):
        return EXIT_REFUSED
    root = None
    if options.base:
        root = base_folder(options, out)
        if root is None:
            return EXIT_ERROR
    content_folder, read = the_content_folder(options, out)
    if not read:
        return EXIT_REFUSED
    options.content_folder = content_folder
    try:
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
            content_folder=options.content_folder,
            beside=options.beside,
            segment=options.segment,
            questions_open=options.questions_open,
        )
    except ReviewError as refusal:
        return an_approval_refusal(refusal, options, out)
    line(out, "base", result.root)
    line(out, "file", result.path)
    if drafting.step_named(step) == drafting.STEP_CHANGE:
        # The two steps after this one are about this one change, and they
        # need its name rather than the file it landed in.
        line(out, "change", os.path.basename(result.path)[: -len(".md")])
    for code in result.codes:
        line(out, "note", code)
    if create_base.CODE_LINK_FAILED in (result.codes or []):
        out.write(LINK_NOT_RECORDED % plain_value(options.content_folder) + "\n")
    out.write("That is written down, together with the record that you said yes.\n")
    return EXIT_DONE


def an_approval_refusal(refusal, options, out):
    """Say why an approval wrote nothing, for the refusals a person can act on."""
    code = getattr(refusal, "code", None)
    if a_step_refusal(refusal, out):
        return EXIT_REFUSED
    if code == join_flow.CODE_QUESTIONS_OPEN:
        line(out, "codes", code)
        out.write(QUESTIONS_NOT_ANSWERED + "\n")
        return EXIT_REFUSED
    if code == segments.CODE_FOLDER_NOT_ORDINARY:
        line(out, "codes", code)
        out.write(segments.FOLDER_NOT_ORDINARY + "\n")
        return EXIT_REFUSED
    if code == segments.CODE_FILE_TAKEN:
        line(out, "codes", code)
        # The segment is not named here: the step's own line already says
        # which one it is, and a name can have come out of their material.
        out.write(segments.FILE_TAKEN + "\n")
        return EXIT_REFUSED
    if code in join_flow.DRAFT_SENTENCES:
        # A segment drafted in a later session is written only after a yes to
        # read its material (call 29).
        line(out, "codes", code)
        out.write(join_flow.DRAFT_SENTENCES[code] + "\n")
        return EXIT_REFUSED
    if code in join_flow.BASE_REFUSALS:
        # A segment is written the way a finished page is, so it meets the
        # same refusals from the base, each with its one sentence.
        line(out, "codes", code)
        out.write(join_flow.BASE_REFUSALS[code] + "\n")
        return EXIT_REFUSED
    raise refusal


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
    try:
        result = join_flow.skip_step(step, root, run_id=options.run)
    except ReviewError as refusal:
        if not a_step_refusal(refusal, out):
            raise
        return EXIT_REFUSED
    if getattr(result, "sentence", None):
        # Skipping a context change writes nothing at all, so there is no file
        # to name and nothing for a later session to finish.
        out.write(result.sentence + "\n")
        return EXIT_DONE
    line(out, "file", result.path)
    out.write(
        "That one is written down as skipped, and the next session will offer "
        "to finish it.\n"
    )
    return EXIT_DONE


def an_adoption_refusal(refusal, out):
    """Say why a page was not taken in: the code, then the one sentence.

    The sentence names the class of what was found and never the value, and
    a refusal about the page itself ends in the offer to draft it instead.
    """
    line(out, "codes", refusal.code)
    if refusal.code in adopt.OFFERS_A_DRAFT:
        line(out, "draft-instead", "yes")
    # The refusal about a reserved name names the segment.
    held_apart(out, [refusal.sentence])
    return EXIT_REFUSED


ADOPTION_BASE_REFUSALS = join_flow.BASE_REFUSALS


def an_adoption_base_refusal(refusal, out):
    """Say why the base would not take a page, or hand the failure on."""
    sentence = ADOPTION_BASE_REFUSALS.get(getattr(refusal, "code", None))
    if sentence is None:
        raise refusal
    line(out, "codes", refusal.code)
    out.write(sentence + "\n")
    return EXIT_REFUSED


def run_adopt_show(options, out):
    """Clean one finished page and show what was removed and how it starts."""
    run_id = need(options, "run", out)
    slug = need(options, "segment", out)
    if not run_id or not slug:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_REFUSED
    try:
        shown = join_flow.adoption_show(run_id, slug, root, email=options.email)
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    line(out, "segment", shown.segment.slug)
    line(out, "hash", shown.digest)
    if shown.cleaned.questions:
        line(out, "questions", shown.cleaned.questions)
    for sentence in shown.sentences():
        if shown.segment.name in sentence:
            held_apart(out, [sentence])
        else:
            out.write(sentence + "\n")
        if sentence == adopt.OPENING_SAID:
            # The first lines are the person's own writing, so they are held
            # apart as data, however they are fenced themselves.
            out.write(moment.fenced("\n".join(shown.cleaned.opening())) + "\n")
    return EXIT_DONE


def run_adopt_read(options, out):
    """Show the whole cleaned page, held apart as data, if it is the one shown."""
    run_id = need(options, "run", out)
    slug = need(options, "segment", out)
    if not run_id or not slug:
        return EXIT_ERROR
    try:
        text = join_flow.adoption_read(run_id, slug)
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    out.write(moment.fenced(text.rstrip("\n")) + "\n")
    return EXIT_DONE


def run_adopt(options, out):
    """Write one page the person said yes to, bound to the hash they were shown."""
    run_id = need(options, "run", out)
    slug = need(options, "segment", out)
    digest = need(options, "hash", out)
    if not run_id or not slug or not digest:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_REFUSED
    try:
        result = join_flow.adoption_approve(
            run_id,
            slug,
            root,
            digest,
            questions_open=options.questions_open,
            email=options.email,
        )
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    except (ReviewError, PathError) as refusal:
        return an_adoption_base_refusal(refusal, out)
    line(out, "base", result.root)
    line(out, "file", result.path)
    out.write(adopt.TAKEN_IN + "\n")
    return EXIT_DONE


def run_adopt_leave(options, out):
    """Write down that the person left one finished page out."""
    run_id = need(options, "run", out)
    slug = need(options, "segment", out)
    if not run_id or not slug:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_REFUSED
    try:
        sentence = join_flow.adoption_leave_out(run_id, slug, root)
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    except (ReviewError, PathError) as refusal:
        return an_adoption_base_refusal(refusal, out)
    held_apart(out, [sentence])
    return EXIT_DONE


def run_resume(options, out):
    """Finish an import that stopped, and name the pages still to be shown."""
    run_id = need(options, "run", out)
    session = need(options, "session", out)
    if not run_id or not session:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_REFUSED
    try:
        resumed = join_flow.resume_import(run_id, root, session, email=options.email)
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    except (ReviewError, PathError) as refusal:
        return an_adoption_base_refusal(refusal, out)
    if resumed.stopped is not None:
        line(out, "codes", resumed.stopped[1])
    for segment in resumed.to_show:
        line(out, "segment", segment.slug)
    for segment in resumed.to_draft:
        line(out, "to-draft", segment.slug)
    for segment in resumed.unreadable:
        line(out, "unreadable", segment.slug)
    held_apart(out, resumed.sentences())
    return EXIT_REFUSED if resumed.stopped is not None else EXIT_DONE


def a_draft_refusal(refusal, out):
    """Say why a segment still to draft was not listed, agreed to, or left out."""
    code = getattr(refusal, "code", None)
    sentence = getattr(refusal, "sentence", "") or join_flow.DRAFT_SENTENCES.get(code)
    if not sentence:
        raise refusal
    line(out, "codes", code)
    held_apart(out, [sentence])
    return EXIT_REFUSED


def file_numbers(options, out):
    """The numbers of the files to drop from the list, or a refusal said once."""
    asked = [str(item).strip() for item in (options.dropped or []) if str(item).strip()]
    if not all(item.isdigit() and item.isascii() for item in asked):
        out.write(ONLY_BY_NUMBER + "\n")
        return None, False
    return [int(item) for item in asked], True


def run_draft_list(options, out):
    """Show the files a segment still to draft would read, before any yes."""
    run_id = need(options, "run", out)
    slug = need(options, "segment", out)
    if not run_id or not slug:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_REFUSED
    dropped, read = file_numbers(options, out)
    if not read:
        return EXIT_REFUSED
    added, read = added_places(options, out)
    if not read:
        return EXIT_REFUSED
    try:
        shown = join_flow.draft_list(run_id, slug, root, added=added, dropped=dropped)
    except ConsentError as refusal:
        return a_draft_refusal(refusal, out)
    except (ReviewError, PathError) as refusal:
        return an_adoption_base_refusal(refusal, out)
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    line(out, "segment", shown.segment.slug)
    if shown.code:
        line(out, "codes", shown.code)
    held_apart(out, shown.sentences())
    # The number is what a file is dropped by, because a file name is
    # somebody else's text and a number is not.
    held_apart(
        out,
        [
            "read=%s number=%d kind=%s date=%s"
            % (
                safe_value(entry.path),
                number,
                safe_value(entry.kind),
                safe_value(entry.modified_date or "none"),
            )
            for number, entry in enumerate(shown.entries, start=1)
        ],
    )
    for reason in sorted(shown.left_out):
        out.write(
            "left-out=%s count=%d\n" % (safe_value(reason), shown.left_out[reason])
        )
    if shown.needs_second_yes:
        out.write("needs-second-yes=true\n")
    if shown.appears_multi_company:
        out.write("appears-multi-company=true\n")
    return EXIT_REFUSED if shown.code else EXIT_DONE


def run_draft_freeze(options, out):
    """Take the yes to the list a segment still to draft would read."""
    run_id = need(options, "run", out)
    session = need(options, "session", out)
    if not run_id or not session:
        return EXIT_ERROR
    try:
        consent = join_flow.draft_freeze(run_id, session)
    except ConsentError as refusal:
        return a_draft_refusal(refusal, out)
    out.write(
        "The list is fixed. Nothing leaves this computer for the rest of this "
        "session.\n"
    )
    out.write("frozen=%d\n" % len(consent.paths))
    return EXIT_DONE


def run_draft_leave(options, out):
    """Write down that the person left a segment still to draft out."""
    slug = need(options, "segment", out)
    if not slug:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_REFUSED
    try:
        sentence = join_flow.draft_leave_out(slug, root)
    except ConsentError as refusal:
        return a_draft_refusal(refusal, out)
    except (ReviewError, PathError) as refusal:
        return an_adoption_base_refusal(refusal, out)
    except adopt.AdoptionRefused as refusal:
        return an_adoption_refusal(refusal, out)
    held_apart(out, [sentence])
    return EXIT_DONE


def base_and_id(options, out):
    """The base this step works in, and the name this account knows it by."""
    root = options.base or os.getcwd()
    resolution = paths.resolve_base(root, machine.load_machine_state())
    if not resolution.active or not resolution.root or not resolution.base_id:
        out.write(NO_BASE_HERE + "\n")
        return None, None
    return resolution.root, resolution.base_id


def run_closing_question(options, out):
    """Print the three sentences, the example, and the one request."""
    del options
    out.write(join_flow.closing_question())
    return EXIT_DONE


def run_preview_change(options, out):
    """Show the whole of what would be written down, before writing any of it."""
    draft = need(options, "draft", out)
    if not draft:
        return EXIT_ERROR
    if not a_draft_of_this_run(draft, options, out):
        return EXIT_REFUSED
    reviewed = join_flow.review_step(
        drafting.STEP_CHANGE, draft, base_root=options.base
    )
    if not reviewed.ready:
        line(out, "codes", ",".join(reviewed.codes))
        out.write(
            "That draft holds something that must not be written down, so write "
            "it again from the same request.\n"
        )
        return EXIT_REFUSED
    if not need(options, "base", out):
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_ERROR
    try:
        proposed = join_flow.preview_change(reviewed.draft, base_root=root)
    except ReviewError as refusal:
        if refusal.code != join_flow.CODE_NEEDS_THE_BASE:
            raise
        out.write(join_flow.NEEDS_THE_BASE + "\n")
        return EXIT_REFUSED
    out.write(proposed.summary + "\n\n")
    out.write(join_flow.NOTED_BY_IS_THE_BASES_RECORD + "\n")
    out.write("\n" + proposed.artifact + "\n")
    out.write(join_flow.ENTRY_PREVIEW_ASK + "\n")
    return EXIT_DONE


def run_reconcile(options, out):
    """Say which documents to ask about, and how many are left flagged."""
    entry_id = need(options, "entry", out)
    if not entry_id:
        return EXIT_ERROR
    root, base_id = base_and_id(options, out)
    if root is None:
        return EXIT_ERROR
    entry, _file = join_flow.entry_in_base(root, base_id, entry_id)
    if entry is None:
        out.write(CHANGE_NOT_IN_THE_BASE + "\n")
        return EXIT_REFUSED
    plan = join_flow.reconcile_plan(root, base_id, entry.affects)
    for path, question in zip(plan.ask_about, plan.questions()):
        line(out, "file", path)
        out.write(question + "\n")
    if plan.sentence:
        out.write(plan.sentence + "\n")
    return EXIT_DONE


def run_reconcile_answer(options, out):
    """Record one answer about one document, and say what it led to."""
    entry_id = need(options, "entry", out)
    relative = need(options, "file", out)
    answer = need(options, "answer", out)
    if not entry_id or not relative or not answer:
        return EXIT_ERROR
    if answer not in ("yes", "no"):
        out.write(RECONCILE_ANSWER_UNKNOWN + "\n")
        return EXIT_REFUSED
    root, base_id = base_and_id(options, out)
    if root is None:
        return EXIT_ERROR
    if answer == "yes":
        result = join_flow.reconcile_yes(root, base_id, relative, entry_id)
    else:
        result = join_flow.reconcile_no(root, base_id, relative, entry_id)
    if result.staging_path:
        line(out, "prepared", result.staging_path)
    for code in result.codes:
        line(out, "note", code)
    out.write(result.sentence + "\n")
    return EXIT_DONE


def run_skip_change(options, out):
    """Skip is a whole answer, so nothing is written and the reminder rests."""
    root, base_id = base_and_id(options, out)
    if root is None:
        return EXIT_ERROR
    out.write(join_flow.skip_the_closing_question(root, base_id) + "\n")
    return EXIT_DONE


def run_close(options, out):
    run_id = need(options, "run", out)
    if not run_id:
        return EXIT_ERROR
    root = base_folder(options, out)
    if root is None:
        return EXIT_ERROR
    got_in_the_way = options.got_in_the_way
    if options.got_in_the_way_file:
        got_in_the_way = words_from(options.got_in_the_way_file, options, out)
        if got_in_the_way is None:
            return EXIT_REFUSED
    result = join_flow.close_run(
        root, run_id, got_in_the_way=got_in_the_way, email=options.email
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
    if result.drafts_unfinished:
        # One sentence either way: segments still to draft are said with the
        # yes the next session will ask again for (call 29).
        out.write(join_flow.CLOSING_DRAFTS_UNFINISHED + "\n")
    elif result.import_unfinished:
        out.write(join_flow.CLOSING_IMPORT_UNFINISHED + "\n")
    return EXIT_DONE


def named_base(options, out):
    """The base the person named, by its folder or by the company it is for.

    Connecting a folder happens from the folder being connected, which is not a
    base and never will be, so this step cannot ask the resolver what base the
    session is in the way every other step does.
    """
    try:
        return join_flow.find_base(options.base, cwd=os.getcwd())
    except GtmBaseError as refusal:
        if refusal.code == join_flow.MORE_THAN_ONE_BASE:
            roots = list(getattr(refusal, "roots", []) or []) + ["", ""]
            out.write(
                MORE_THAN_ONE_BASE % (plain_value(roots[0]), plain_value(roots[1]))
                + "\n"
            )
            line(out, "codes", refusal.code)
            return None, None
        out.write((NO_BASE_OF_THAT_NAME if options.base else NO_BASE_AT_ALL) + "\n")
        line(out, "codes", join_flow.NO_SUCH_BASE)
        return None, None


def run_link(options, out):
    folder = the_folder(options, out)
    if not folder:
        return EXIT_ERROR
    root, base_id = named_base(options, out)
    if root is None:
        return EXIT_REFUSED
    try:
        join_flow.link_folder(root, folder)
    except StateError as refusal:
        if refusal.code == machine.CODE_CONTENT_TAKEN:
            out.write(FOLDER_TAKEN % plain_value(getattr(refusal, "other_root", "")) + "\n")
            line(out, "codes", refusal.code)
            return EXIT_REFUSED
        if refusal.code == machine.CODE_CONTENT_INSIDE_BASE:
            out.write(FOLDER_INSIDE_BASE + "\n")
            line(out, "codes", refusal.code)
            return EXIT_REFUSED
        if refusal.code in (
            folder_identity.CODE_NOT_A_FOLDER,
            folder_identity.CODE_UNSTABLE,
        ):
            out.write(FOLDER_MISSING + "\n")
            line(out, "codes", refusal.code)
            return EXIT_REFUSED
        raise
    line(out, "base", root)
    held_apart(out, ["belongs-with=%s" % safe_value(folder)])
    out.write(LINKED + "\n")
    return EXIT_DONE


def run_unlink(options, out):
    root, base_id = named_base(options, out)
    if root is None:
        return EXIT_REFUSED
    join_flow.unlink_folder(root)
    line(out, "base", root)
    out.write(UNLINKED + "\n")
    return EXIT_DONE


def run_links(options, out):
    listed = join_flow.linked_folders()
    if not listed:
        out.write(NO_LINKS + "\n")
        return EXIT_DONE
    for base_root, content_root in listed:
        # The name is the folder the base sits in, which is the name the person
        # can hand back to link or unlink without knowing any path at all.
        name = os.path.basename(os.path.dirname(str(base_root or "").rstrip(os.sep)))
        out.write(
            "name=%s base=%s belongs-with=%s\n"
            % (
                safe_value(name),
                safe_value(base_root),
                safe_value(content_root or "none"),
            )
        )
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
    "words-file": run_words_file,
    "propose-location": run_propose_location,
    "survey": run_survey,
    "list-sources": run_list_sources,
    "freeze-sources": run_freeze_sources,
    "scope": run_scope,
    "segments": run_segments,
    "segments-settle": run_segments_settle,
    "add-paste": run_add_paste,
    "preview": run_preview,
    "assemble": run_assemble,
    "review": run_review,
    "what-is-wrong": run_what_is_wrong,
    "approve": run_approve,
    "skip": run_skip,
    "adopt-show": run_adopt_show,
    "adopt-read": run_adopt_read,
    "adopt": run_adopt,
    "adopt-leave": run_adopt_leave,
    "resume": run_resume,
    "draft-list": run_draft_list,
    "draft-freeze": run_draft_freeze,
    "draft-leave": run_draft_leave,
    "closing-question": run_closing_question,
    "preview-change": run_preview_change,
    "reconcile": run_reconcile,
    "reconcile-answer": run_reconcile_answer,
    "skip-change": run_skip_change,
    "close": run_close,
    "link": run_link,
    "unlink": run_unlink,
    "links": run_links,
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
    if options.company_file:
        # The run has to be on the command, because it is what says which
        # setup the file belongs to. Finding H3 of the third look: without it
        # this said the file was not one GTM Base handed out, which is not
        # what was wrong and left nobody anywhere to go.
        if not (options.run or options.session):
            sys.stdout.write(NEEDS_A_RUN_OR_SESSION + "\n")
            return EXIT_ERROR
        company = wordsfile.read_words(
            options.company_file, options.run or options.session
        )
        if company is None:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        options.company = company
    if options.company:
        try:
            location.validate_company_name(options.company)
        except GtmBaseError:
            sys.stdout.write(BAD_COMPANY + "\n")
            return EXIT_REFUSED
    # Everything the step prints goes out in one fence, as data, so no name
    # it carries reaches the assistant as words around the data, whatever
    # line it is on (Astra's review of Release B and its confirmations,
    # finding 5). What goes to the error stream never names anything.
    printed = io.StringIO()
    try:
        return step(options, printed)
    except IdentityNeeded:
        printed.write(NEEDS_EMAIL + "\n")
        return EXIT_REFUSED
    except approval.ApprovalRefused as refusal:
        # Said as it is, so the person hears why and what to do, rather than
        # the sentence for a step that could not be finished (the correctness
        # review of Unit 1.7e, finding 1).
        printed.write("codes=%s\n" % safe_value(refusal.code))
        printed.write(str(refusal) + "\n")
        return EXIT_REFUSED
    except (DraftError, ReviewError) as refusal:
        printed.write("codes=%s\n" % safe_value(",".join(_codes_of(refusal))))
        printed.write(
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
    finally:
        said = printed.getvalue().rstrip("\n")
        if said:
            sys.stdout.write(moment.fenced(said, note=moment.NAMES_NOTE) + "\n")


def _codes_of(failure):
    found = list(getattr(failure, "codes", []) or [])
    code = getattr(failure, "code", None)
    if code and code not in found:
        found.insert(0, code)
    return found or ["refused"]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
