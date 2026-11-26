#!/usr/bin/env python3
"""Create documents, and change one settings line, each shown first and approved once.

Everything this script does lives in `gtmbase.operations` (Plan 1, Unit 4.2a);
this file exists only to find the library, read the arguments, and print the
answer. Preparing shows the whole of what would be written and writes nothing
into the base; approving is a separate run, put to the person by Claude Code.
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

from gtmbase import machine, moment, operations, paths, wordsfile  # noqa: E402
from gtmbase.errors import GtmBaseError  # noqa: E402

EXIT_DONE = 0
EXIT_REFUSED = 1
EXIT_ERROR = 2

NOT_JOINED = (
    "This folder is not a company base you have joined yet, so there is "
    "nothing here to change."
)
NEEDS_THE_WORDS = (
    "Say where each piece is, with the files this script handed out for them."
)
NOT_THAT_KIND = (
    "That prepared change is not the kind this command approves, so nothing "
    "was written. Use the command the showing printed."
)
WENT_WRONG = "GTM Base could not finish that step, so nothing was written."


def build_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--new-words-file",
        help="hand out a file to put a document, a value or a reason in",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="prepare new documents to be written, to show before any yes",
    )
    parser.add_argument(
        "--set",
        choices=operations.SETTINGS_OPERATIONS,
        help="prepare one settings line to change, to show before any yes",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="where a new document goes, or the document whose line changes",
    )
    parser.add_argument(
        "--document-file",
        action="append",
        default=[],
        help="a file this script handed out, holding one new document",
    )
    parser.add_argument(
        "--value-file", help="a file this script handed out, holding the new value"
    )
    parser.add_argument(
        "--reason-file", help="a file this script handed out, holding the reason"
    )
    parser.add_argument(
        "--approve-creation",
        help="write the new documents that were shown, by their prepared name",
    )
    parser.add_argument(
        "--approve-setting",
        help="write the settings change that was shown, by its prepared name",
    )
    parser.add_argument(
        "--operation",
        choices=operations.SETTINGS_OPERATIONS,
        help="with --approve-setting, the operation the showing printed",
    )
    parser.add_argument("--shown", help="the value the showing printed")
    return parser


def _words(path, base_id, claims):
    """Somebody's words, from a file this script handed out, held until the work is done."""
    if not path:
        raise LookupError(NEEDS_THE_WORDS)
    claim = wordsfile.claim_words(path, base_id)
    if claim is None:
        raise LookupError(wordsfile.NOT_OURS)
    claims.append(claim)
    return claim.text


def _show(prepared, operation=None):
    sys.stdout.write(moment.fenced(prepared.artifact) + "\n")
    sys.stdout.write(
        "   [for the assistant] prepared=%s shown=%s%s\n"
        % (
            prepared.prepared_id,
            prepared.shown,
            " operation=%s" % operation if operation else "",
        )
    )


def main(argv=None):
    options = build_parser().parse_args(argv)
    here = os.getcwd()
    resolution = paths.resolve_base(here, machine.load_machine_state())
    if not resolution.active or not resolution.root or not resolution.base_id:
        sys.stderr.write(NOT_JOINED + "\n")
        return EXIT_ERROR
    root, base_id = resolution.root, resolution.base_id

    if options.new_words_file:
        if options.new_words_file not in wordsfile.KINDS:
            sys.stdout.write(wordsfile.NOT_OURS + "\n")
            return EXIT_REFUSED
        wordsfile.ensure_words_dir(base_id)
        sys.stdout.write(
            "words=%s\n" % wordsfile.new_words_path(base_id, options.new_words_file)
        )
        return EXIT_DONE

    if options.approve_creation or options.approve_setting:
        prepared_id = options.approve_creation or options.approve_setting
        kind = operations.KIND_CREATE if options.approve_creation else operations.KIND_SETTING
        try:
            done = operations.approve(
                root,
                base_id,
                prepared_id,
                options.shown or "",
                kind=kind,
                operation=options.operation if options.approve_setting else None,
            )
        except GtmBaseError as failure:
            sys.stdout.write(str(failure) + "\n")
            return EXIT_REFUSED
        sys.stdout.write(done.sentence + "\n")
        return EXIT_DONE if done.done else EXIT_REFUSED

    if options.create or options.set:
        claims = []
        try:
            reason = _words(options.reason_file, base_id, claims)
            if options.create:
                if not options.path or len(options.path) != len(options.document_file):
                    raise LookupError(NEEDS_THE_WORDS)
                files = [
                    (path, _words(document, base_id, claims))
                    for path, document in zip(options.path, options.document_file)
                ]
                prepared = operations.prepare_creation(root, base_id, files, reason)
            else:
                if len(options.path) > 1:
                    raise LookupError(NEEDS_THE_WORDS)
                value = _words(options.value_file, base_id, claims).strip()
                prepared = operations.prepare_setting(
                    root,
                    base_id,
                    options.set,
                    reason,
                    path=options.path[0] if options.path else None,
                    value=value,
                )
        except LookupError as missing:
            for claim in claims:
                wordsfile.release_words(claim)
            sys.stdout.write(str(missing.args[0]) + "\n")
            return EXIT_REFUSED
        except GtmBaseError as failure:
            for claim in claims:
                wordsfile.release_words(claim)
            sys.stdout.write(str(failure) + "\n")
            return EXIT_REFUSED
        except Exception:
            for claim in claims:
                wordsfile.release_words(claim)
            sys.stderr.write(WENT_WRONG + "\n")
            return EXIT_ERROR
        for claim in claims:
            wordsfile.consume_claim(claim)
        _show(prepared, options.set)
        return EXIT_DONE

    sys.stderr.write(NEEDS_THE_WORDS + "\n")
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
