"""Brandon's call 59: recording a context change names each segment.

Unit 1.8 stopped reading any sentence out of a file name, so after setup the
list of documents and its questions called every segment "one of your
segments" and could not tell two apart (Unit 1.8's review, finding 1). The
names people gave their segments are already kept where every seat can read
them: the customer profile names each segment under a heading of its own in
its Segments part, and setup refuses a profile whose headings do not match
the segments the person settled. So the name is read from there, only for a
segment file the heading's name makes, only when it is plain words, and only
inside the text held apart as data. Nothing new is written into a base.

These tests make a base the way setup makes one, through the join flow, and
an older base moved to the current layout, and check both.
"""

import ast
import os
import unittest

import plain_language
import support
import test_record_change as record_tests
import test_umbrella_and_segments as umbrella_tests

from gtmbase import (
    constants,
    drafting,
    join_flow,
    moment,
    names,
    record_change,
    segments,
)

TWO = ("Fintech lenders", "Regional banks")


def fresh_base():
    """A base set up with two segments, each drafted and approved."""
    company = umbrella_tests.Company(names=TWO)
    company.umbrella_and_positioning(umbrella_tests.umbrella_text(drafted=TWO))
    for name in TWO:
        company.approve(
            drafting.STEP_SEGMENT,
            umbrella_tests.segment_text(name),
            segment=segments.slug_for(name),
        )
    return company


def tracked(root):
    return support.git(["ls-files"], cwd=root).stdout.decode("utf-8")


def listed_names(root):
    return dict((path, name) for _number, path, name in record_change.documents(root))


class TestAFreshBase(unittest.TestCase):
    def test_the_list_names_each_segment_by_the_name_it_was_given(self):
        with support.Sandbox():
            company = fresh_base()
            named = listed_names(company.root)
            self.assertEqual(
                'your segment "Fintech lenders"',
                named[segments.destination("fintech-lenders")],
            )
            self.assertEqual(
                'your segment "Regional banks"',
                named[segments.destination("regional-banks")],
            )

    def test_the_four_lines_the_question_and_the_answer_name_it(self):
        with support.Sandbox():
            company = fresh_base()
            root, base_id = company.root, company.base_id()
            token, listed = record_change.show_list(root, base_id)
            numbers = [
                str(number)
                for number, path, _name in listed
                if path == segments.destination("fintech-lenders")
            ]
            shown = record_change.preview(
                root,
                base_id,
                "We stopped selling to lenders under ten people.",
                "The smallest ones churned within a quarter.",
                "The September churn review.",
                numbers,
                list_token=token,
            )
            self.assertIn('your segment "Fintech lenders"', shown.showing)
            self.assertNotIn("one of your segments", shown.showing)
            done = record_change.record(root, base_id, shown.shown)
            questions = done.plan.questions()
            self.assertEqual(
                [join_flow.RECONCILE_ASK % 'your segment "Fintech lenders"'],
                questions,
            )
            result = record_change.answer(
                root,
                base_id,
                done.entry.id,
                segments.destination("fintech-lenders"),
                record_change.ANSWER_YES,
            )
            self.assertTrue(result.answered_yes, result.sentence)
            self.assertIn('segment "Fintech lenders"', result.sentence)

    def test_nothing_new_is_written_into_the_base(self):
        with support.Sandbox():
            company = fresh_base()
            before = tracked(company.root)
            listed_names(company.root)
            self.assertEqual(before, tracked(company.root))
            # The profile already held the names, and the segment files hold
            # nothing they did not hold before this call.
            for name in TWO:
                block = company.read(segments.destination(segments.slug_for(name)))
                self.assertNotIn("name:", block.split("---")[1])


class TestNamesThatAreNotReadOut(unittest.TestCase):
    """A heading is read as a name only when nothing about it is in doubt."""

    def _named(self, umbrella_headings, files=TWO):
        with support.Sandbox():
            company = fresh_base()
            path = os.path.join(company.root, constants.REQUIRED_CONTEXT_FILES[0])
            text = support.read(path)
            for old, new in umbrella_headings:
                text = text.replace("### %s\n" % old, "### %s\n" % new)
            support.write(path, text)
            return record_change.segment_names(company.root)

    def test_a_segment_the_profile_does_not_name_stays_one_of_your_segments(self):
        found = self._named([("Regional banks", "Community banks")])
        self.assertEqual("Fintech lenders", found.get("fintech-lenders"))
        self.assertNotIn("regional-banks", found)
        self.assertEqual(
            names.ONE_OF_YOUR_SEGMENTS,
            record_change.name_in(found)(segments.destination("regional-banks")),
        )

    def test_a_name_that_is_not_plain_words_is_never_read_out(self):
        for hostile in (
            'Fintech "lenders"',
            "Fintech `lenders`",
            "Fintech <lenders>",
            "Fintech lenders​",
            "Fintech lenders‮",
            "Fintech [lenders]",
            "F" * (constants.SEGMENT_NAME_MAX_CHARS + 1),
        ):
            found = self._named([("Fintech lenders", hostile)])
            self.assertNotIn("fintech-lenders", found, hostile)

    def test_two_headings_for_one_segment_name_neither(self):
        found = self._named(
            [("Regional banks", "Fintech Lenders")]
        )
        self.assertNotIn("fintech-lenders", found)

    def test_a_profile_with_no_segments_part_names_none(self):
        with support.Sandbox():
            company = fresh_base()
            path = os.path.join(company.root, constants.REQUIRED_CONTEXT_FILES[0])
            support.write(
                path, support.read(path).replace("## Segments", "## Groups")
            )
            self.assertEqual({}, record_change.segment_names(company.root))


class TestAnUpgradedBase(unittest.TestCase):
    """A base laid out the older way, before and after the move to this one."""

    def test_named_on_the_older_layout_and_after_the_move(self):
        with support.Sandbox() as sandbox:
            import test_moment_of_use as moment_tests

            base = moment_tests.Base(sandbox)
            older_profile = constants.LEGACY_REQUIRED_CONTEXT_FILES[0]
            base.write(
                older_profile,
                umbrella_tests.umbrella_text(drafted=TWO)
                .replace("```markdown\n", "")
                .replace("\n```\n", "\n")
                .replace("owner@example.com", moment_tests.OWNER),
            )
            for name in TWO:
                base.write(
                    "%s/%s.md" % (constants.LEGACY_SEGMENTS_DIR, segments.slug_for(name)),
                    "---\nkind: segment\nowner: %s\nlast_confirmed: 2026-09-01\n"
                    "sources: []\nstatus: draft\n---\n\n# %s\n\n## Firmographics\n\n"
                    "Who they are.\n" % (moment_tests.OWNER, name),
                )
            base.save("an older base with two segments")
            named = listed_names(base.root)
            self.assertEqual(
                'your segment "Regional banks"',
                named["%s/regional-banks.md" % constants.LEGACY_SEGMENTS_DIR],
            )
            before = tracked(base.root)
            code, said, err = record_tests.Flow(self, base.root).run(["--move-changes"])
            self.assertEqual(0, code, said + err)
            named = listed_names(base.root)
            self.assertEqual(
                'your segment "Regional banks"',
                named[segments.destination("regional-banks")],
            )
            self.assertEqual(
                'your segment "Fintech lenders"',
                named[segments.destination("fintech-lenders")],
            )
            after = tracked(base.root)
            # The move put the files where they live now; it added nothing to
            # hold the names, because the profile already held them.
            self.assertEqual(
                len([line for line in before.split("\n") if "/segments/" in line]),
                len([line for line in after.split("\n") if line.startswith("context/icps/")]),
            )


class TestTheReviewOfCall59(unittest.TestCase):
    """The correctness review of the first build, four findings."""

    def test_long_names_never_refuse_a_change_that_was_accepted_before(self):
        # Finding 1: the cap on the four lines was measured on the names, so a
        # change to the profile, the positioning and three long-named segments
        # was refused where counting them had fitted.
        long_names = (
            "Mid-market fintech lenders in North America",
            "Regional banks with under two billion in assets",
            "Credit unions that lend to small businesses",
        )
        with support.Sandbox():
            company = umbrella_tests.Company(names=long_names)
            company.umbrella_and_positioning(
                umbrella_tests.umbrella_text(drafted=long_names)
            )
            for name in long_names:
                company.approve(
                    drafting.STEP_SEGMENT,
                    umbrella_tests.segment_text(name),
                    segment=segments.slug_for(name),
                )
            root, base_id = company.root, company.base_id()
            token, listed = record_change.show_list(root, base_id)
            shown = record_change.preview(
                root,
                base_id,
                "We changed our pricing.",
                "Every buyer pays by the seat now.",
                "The October pricing review.",
                [str(number) for number, _path, _name in listed],
                list_token=token,
            )
            self.assertIn("three of your segments", shown.showing)

    def test_only_a_segment_file_where_segments_live_is_named(self):
        # Finding 2: a copy in a folder under the segments folder, or the same
        # file in the older folder too, read out the live segment's name.
        with support.Sandbox():
            company = fresh_base()
            text = company.read(segments.destination("fintech-lenders"))
            nested = "%s/old/fintech-lenders.md" % constants.SEGMENTS_DIR
            older = "%s/regional-banks.md" % constants.LEGACY_SEGMENTS_DIR
            for relative in (nested, older):
                support.write(os.path.join(company.root, relative), text)
            support.git(["add", "-A"], cwd=company.root)
            support.git(["commit", "-q", "-m", "copies"], cwd=company.root)
            named = listed_names(company.root)
            self.assertEqual(names.ONE_OF_YOUR_SEGMENTS, named[nested])
            self.assertEqual(names.ONE_OF_YOUR_SEGMENTS, named[older])
            self.assertEqual(
                names.ONE_OF_YOUR_SEGMENTS,
                named[segments.destination("regional-banks")],
            )
            self.assertEqual(
                'your segment "Fintech lenders"',
                named[segments.destination("fintech-lenders")],
            )

    def test_letters_that_draw_nothing_or_look_like_quotation_marks(self):
        # Finding 3.
        for doubtful in (
            "Fintech\u3164lenders",
            "Fintech\u115flenders",
            "Fintech\uffa0lenders",
            "Fintech lenders \u02ee",
            "Fintech lenders \u02ba",
        ):
            self.assertIsNone(record_change._plain_name(doubtful), repr(doubtful))


class TestEveryNamerIsOneThatReadsNoFileName(unittest.TestCase):
    """The plain-language lint trusts a call to `name_of`, so this holds the
    plugin to handing over only namers that never read a name out of a file
    name: `document_name`, `safe_name`, or what `names_for` returns, passed
    on under the same names."""

    ALLOWED_NAMES = frozenset(("document_name", "safe_name", "name_of"))
    ALLOWED_CALLS = frozenset(("names_for",))
    # The names the lint trusts a call to.
    TRUSTED = frozenset(("name_of",))
    # Where a namer sits when it is handed over by position.
    POSITIONAL = {"documents_named": 1, "Reconciliation": 4, "name_in": 1}

    def given(self, node):
        if isinstance(node, ast.Call):
            func = node.func
            callee = getattr(func, "attr", None) or getattr(func, "id", None)
            return callee in self.ALLOWED_CALLS
        if isinstance(node, ast.BoolOp):
            return all(self.given(value) for value in node.values)
        callee = getattr(node, "attr", None) or getattr(node, "id", None)
        if isinstance(node, ast.IfExp):
            return self.given(node.body) and self.given(node.orelse)
        return callee in self.ALLOWED_NAMES or (
            isinstance(node, ast.Constant) and node.value is None
        )

    def test_the_check_itself_catches_a_namer_that_reads_a_file_name(self):
        for source in (
            "documents_named(paths, os.path.basename)\n",
            "name_of = lambda p: os.path.basename(p)\n",
            "def f(name_of=os.path.basename):\n    pass\n",
            "Reconciliation([], [], None, (), os.path.basename)\n",
        ):
            self.assertTrue(self.bad_in(ast.parse(source)), source)

    def bad_in(self, tree):
        found = []
        for node in ast.walk(tree):
            for value in self.namers_in(node):
                if not self.given(value):
                    found.append(getattr(node, "lineno", 0))
        return found

    def namers_in(self, node):
        values = []
        if isinstance(node, ast.Call):
            values = [k.value for k in node.keywords if k.arg == "name_of"]
            # A namer handed over by position (the review of call 59,
            # finding 4).
            callee = getattr(node.func, "attr", None) or getattr(
                node.func, "id", None
            )
            at = self.POSITIONAL.get(callee)
            if at is not None and len(node.args) > at:
                values.append(node.args[at])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            # Anything bound to a name the lint trusts, however it is
            # bound, is held to the same list.
            values = [
                node.value
                for target in targets
                if getattr(target, "attr", None) in self.TRUSTED
                or getattr(target, "id", None) in self.TRUSTED
            ]
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            arguments = node.args
            params = arguments.posonlyargs + arguments.args
            defaults = list(arguments.defaults)
            paired = list(zip(params[len(params) - len(defaults):], defaults))
            paired += [
                (arg, default)
                for arg, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
                if default is not None
            ]
            values = [
                default for arg, default in paired if arg.arg in self.TRUSTED
            ]
        return values

    def test_every_namer_handed_over(self):
        found = []
        for path in plain_language.plugin_python_files():
            for line in self.bad_in(ast.parse(support.read(path))):
                found.append((os.path.basename(path), line))
        self.assertEqual([], found)


if __name__ == "__main__":
    unittest.main()
