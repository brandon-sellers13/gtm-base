"""Plan 1, Unit 4.2a: the script that creates documents and changes one setting.

Run as the person runs it: words arrive in files the script handed out, the
showing prints the whole of what would be written held apart as data, and the
yes is a second run named the way Claude Code's question names it. Every
fixture is written from scratch.
"""

import contextlib
import importlib.util
import io
import os
import re
import unittest

import support
import test_operations as operating

from gtmbase import constants

SCRIPT = os.path.join(
    support.PLUGIN_DIR, "skills", "propose-change", "scripts", "operations.py"
)


def script():
    spec = importlib.util.spec_from_file_location("gtm_base_operations_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_in(root, arguments):
    module = script()
    was = os.getcwd()
    os.chdir(support.where_a_script_runs(root))
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = module.main(arguments)
    finally:
        os.chdir(was)
    return code, out.getvalue()


def handed_out(root, kind, words):
    code, said = run_in(root, ["--new-words-file", kind])
    assert code == 0, said
    path = said.strip().split("=", 1)[1]
    support.write(path, words)
    return path


def prepared_from(said):
    match = re.search(r"prepared=(\S+) shown=(\S+)", said)
    assert match, said
    return match.group(1), match.group(2)


def operation_from(said):
    match = re.search(r"operation=(\S+)", said)
    assert match, said
    return match.group(1)


class TestTheScript(unittest.TestCase):
    def test_a_business_line_shown_then_approved(self):
        with support.Sandbox() as sandbox:
            root, _base_id = operating.a_base(sandbox)
            operating.as_address(root, operating.WRITER)
            code, said = run_in(
                root,
                [
                    "--set", "business", "--path", operating.POSITIONING,
                    "--value-file", handed_out(root, "value", "insights\n"),
                    "--reason-file", handed_out(root, "reason", "It is about Insights.\n"),
                ],
            )
            self.assertEqual(0, code, said)
            self.assertIn("```data", said)
            self.assertIn("business: insights", said)
            prepared, shown = prepared_from(said)
            self.assertNotIn("business:", support.read(os.path.join(root, operating.POSITIONING)))
            # Approving it as the other kind writes nothing.
            code, _said = run_in(root, ["--approve-creation", prepared, "--shown", shown])
            self.assertEqual(1, code)
            self.assertEqual("business", operation_from(said))
            # Named as another operation than the one prepared, nothing is written.
            code, _said = run_in(
                root, ["--approve-setting", prepared, "--operation", "map-owner", "--shown", shown]
            )
            self.assertEqual(1, code)
            code, said = run_in(
                root, ["--approve-setting", prepared, "--operation", "business", "--shown", shown]
            )
            self.assertEqual(0, code, said)
            self.assertIn("business: insights", support.read(os.path.join(root, operating.POSITIONING)))

    def test_a_new_document_shown_then_approved(self):
        with support.Sandbox() as sandbox:
            root, _base_id = operating.a_base(sandbox)
            code, said = run_in(
                root,
                [
                    "--create", "--path", "context/goals.md",
                    "--document-file", handed_out(root, "document", operating.GOALS),
                    "--reason-file", handed_out(root, "reason", "We need goals.\n"),
                ],
            )
            self.assertEqual(0, code, said)
            prepared, shown = prepared_from(said)
            code, said = run_in(root, ["--approve-creation", prepared, "--shown", shown])
            self.assertEqual(0, code, said)
            self.assertTrue(os.path.isfile(os.path.join(root, "context", "goals.md")))

    def test_words_from_a_file_it_did_not_hand_out_are_refused(self):
        with support.Sandbox() as sandbox:
            root, _base_id = operating.a_base(sandbox)
            stray = support.write(os.path.join(sandbox.path, "mine.txt"), "insights\n")
            code, said = run_in(
                root,
                ["--set", "business", "--path", operating.POSITIONING,
                 "--value-file", stray, "--reason-file", stray],
            )
            self.assertEqual(1, code)
            self.assertNotIn("prepared=", said)

    def test_a_refused_preparation_keeps_the_words_for_another_try(self):
        with support.Sandbox() as sandbox:
            root, _base_id = operating.a_base(sandbox)
            value = handed_out(root, "value", "wholesale\n")
            reason = handed_out(root, "reason", "Why.\n")
            code, _said = run_in(
                root,
                ["--set", "business", "--path", operating.POSITIONING,
                 "--value-file", value, "--reason-file", reason],
            )
            self.assertEqual(1, code)
            self.assertTrue(os.path.exists(reason))

    def test_outside_a_base_it_says_so(self):
        with support.Sandbox() as sandbox:
            code, _said = run_in(sandbox.path, ["--create"])
            self.assertEqual(2, code)

    def test_the_map_is_reached_only_through_its_three_operations(self):
        with support.Sandbox() as sandbox:
            root, _base_id = operating.a_base(sandbox)
            operating.as_address(root, operating.OWNER)
            code, said = run_in(
                root,
                ["--set", "administrators",
                 "--value-file", handed_out(root, "value", operating.WRITER + "\n"),
                 "--reason-file", handed_out(root, "reason", "Helps run it.\n")],
            )
            self.assertEqual(0, code, said)
            prepared, shown = prepared_from(said)
            code, said = run_in(
                root,
                ["--approve-setting", prepared, "--operation", operation_from(said), "--shown", shown],
            )
            self.assertEqual(0, code, said)
            self.assertIn(
                "administrators: [%s]" % operating.WRITER,
                support.read(os.path.join(root, constants.MAP_PATH)),
            )


if __name__ == "__main__":
    unittest.main()
