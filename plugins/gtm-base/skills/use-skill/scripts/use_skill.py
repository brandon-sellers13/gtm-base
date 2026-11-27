#!/usr/bin/env python3
"""Run a skill kept in a company base through the thin runner.

Everything this script does lives in `gtmbase.runner`; this file exists only
to find the library, read the arguments, and print what the runner hands
back.
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

from gtmbase import machine, moment, paths, runner, skill_install, wordsfile  # noqa: E402
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is no "
    "skill here to run."
)
COULD_NOT_READ_FILE = (
    "GTM Base could not read one of the files it was handed, so nothing was "
    "recorded."
)
NOTHING_OPEN = "Every run of a skill on this computer was finished."


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--start", metavar="SKILL", help="check a skill and hand back its instructions")
    actions.add_argument("--finish", metavar="RUN", help="check the work product of a run and close it")
    actions.add_argument("--check", metavar="SKILL", help="run a skill's examples through the contract check")
    actions.add_argument(
        "--incomplete", action="store_true", help="list runs that were started and never finished"
    )
    actions.add_argument(
        "--new-words-file", help="hand out a file to put somebody's own words in, of one kind"
    )
    actions.add_argument(
        "--prepare-install", metavar="SKILL", help="prepare a whole skill, new or changed, to be shown"
    )
    actions.add_argument(
        "--approve-install", metavar="PREPARED", help="give one yes to a prepared skill"
    )
    actions.add_argument(
        "--show", metavar="SKILL", help="show who approved a skill this computer does not trust yet"
    )
    actions.add_argument(
        "--accept", metavar="SKILL", help="trust here a version somebody with authority approved"
    )
    parser.add_argument(
        "--from", dest="source_folder", help="with --prepare-install: the folder the skill is written in"
    )
    parser.add_argument(
        "--reason-file", help="with --prepare-install: a file this script handed out, holding why"
    )
    parser.add_argument("--shown", help="with --approve-install or --accept: the value the showing printed")
    parser.add_argument(
        runner.UNATTENDED_WORD,
        dest="unattended",
        action="store_true",
        help="with --start: nobody is watching this run",
    )
    parser.add_argument("--output", help="with --finish: the file holding the work product")
    parser.add_argument(
        "--built-from",
        dest="source",
        action="append",
        default=[],
        help="with --finish: a file the work product was built from; give each one",
    )
    return parser


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main(argv=None):
    options = build_parser().parse_args(argv)
    if not (
        options.start or options.finish or options.check or options.incomplete
        or options.new_words_file or options.prepare_install or options.approve_install
        or options.show or options.accept
    ):
        build_parser().print_help()
        return EXIT_ERROR
    resolution = paths.resolve_base(os.getcwd(), machine.load_machine_state())
    if not resolution.active or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR
    root, base_id = resolution.root, resolution.base_id

    if options.start:
        try:
            result = runner.start(
                root,
                base_id,
                options.start,
                unattended=options.unattended,
                conversation=runner.conversation_id(base_id),
            )
        except GtmBaseError as failure:
            sys.stderr.write(str(failure) + "\n")
            return EXIT_REFUSED
        sys.stdout.write(result.render() + "\n")
        return EXIT_DONE if result.hands_back else EXIT_REFUSED

    if options.finish:
        if not options.output:
            build_parser().print_help()
            return EXIT_ERROR
        try:
            output = _read(options.output)
            sources = {item: _read(item) for item in options.source}
        except (OSError, UnicodeDecodeError):
            sys.stderr.write(COULD_NOT_READ_FILE + "\n")
            return EXIT_ERROR
        done = runner.finish(base_id, options.finish, output, sources)
        sys.stdout.write(done.render() + "\n")
        return EXIT_DONE if done.accepted else EXIT_REFUSED

    if options.new_words_file:
        if options.new_words_file not in wordsfile.KINDS:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        wordsfile.ensure_words_dir(base_id)
        sys.stdout.write("words=%s\n" % wordsfile.new_words_path(base_id, options.new_words_file))
        return EXIT_DONE

    if options.prepare_install:
        if not options.source_folder or not options.reason_file:
            build_parser().print_help()
            return EXIT_ERROR
        claim = wordsfile.claim_words(options.reason_file, base_id)
        if claim is None:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        try:
            files = skill_install.files_from_folder(options.source_folder, options.prepare_install)
            prepared = skill_install.prepare(
                root, base_id, options.prepare_install, files, claim.text
            )
        except GtmBaseError as failure:
            wordsfile.release_words(claim)
            sys.stdout.write(str(failure) + "\n")
            return EXIT_REFUSED
        wordsfile.consume_claim(claim)
        sys.stdout.write(moment.fenced(prepared.artifact) + "\n")
        sys.stdout.write(
            "[for the assistant] prepared=%s shown=%s\n" % (prepared.prepared_id, prepared.shown)
        )
        return EXIT_DONE

    if options.approve_install:
        done = skill_install.approve(root, base_id, options.approve_install, options.shown or "")
        sys.stdout.write(done.sentence + "\n")
        return EXIT_DONE if done.done or done.code == skill_install.CODE_WAITING else EXIT_REFUSED

    if options.show:
        showing = skill_install.approval_of(root, base_id, options.show)
        sys.stdout.write("\n".join(showing.sentences()) + "\n")
        if showing.acceptable:
            sys.stdout.write("[for the assistant] shown=%s\n" % showing.shown)
            return EXIT_DONE
        return EXIT_DONE if showing.trusted else EXIT_REFUSED

    if options.accept:
        done = skill_install.accept(root, base_id, options.accept, options.shown or "")
        sys.stdout.write(done.sentence + "\n")
        return EXIT_DONE if done.done else EXIT_REFUSED

    if options.check:
        contract = runner.check_examples(root, base_id, options.check)
        for problem in contract.problems:
            sys.stdout.write(problem + "\n")
        return EXIT_DONE if contract.passed else EXIT_REFUSED

    open_runs = runner.incomplete(base_id)
    if not open_runs:
        sys.stdout.write(NOTHING_OPEN + "\n")
        return EXIT_DONE
    for row in open_runs:
        sys.stdout.write(
            "- %s started on %s and never finished, stopping point unknown.\n"
            % (row.get("job"), row.get("date"))
        )
    return EXIT_DONE


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
