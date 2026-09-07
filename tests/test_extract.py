"""Turning the three kinds of file the plugin reads itself into plain text."""

import os
import shutil
import tempfile
import unittest

import support
from support import write

from gtmbase import constants, extract
from gtmbase.errors import SourceRejected

SOURCES_FIXTURES = os.path.join(support.FIXTURES_DIR, "sources")


class TempFolder(object):
    def __enter__(self):
        self.path = os.path.realpath(tempfile.mkdtemp(prefix="gtm-base-extract-"))
        return self

    def __exit__(self, kind, value, trace):
        shutil.rmtree(self.path, ignore_errors=True)
        return False

    def file(self, name, text):
        return write(os.path.join(self.path, name), text)

    def bytes(self, name, payload):
        path = os.path.join(self.path, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        return path


class TestMarkdownAndText(unittest.TestCase):
    def test_markdown_comes_back_as_it_was_written(self):
        path = os.path.join(SOURCES_FIXTURES, "icp.md")
        text, notes = extract.extract(path, "markdown")
        self.assertIn("Ideal customer profile", text)
        self.assertIn("one marketer doing everything", text)
        self.assertEqual([], notes)

    def test_plain_text_comes_back_as_it_was_written(self):
        path = os.path.join(SOURCES_FIXTURES, "notes.txt")
        text, notes = extract.extract(path, "text")
        self.assertIn("lead with the monthly", text)
        self.assertEqual([], notes)

    def test_a_byte_order_mark_is_taken_off_the_front(self):
        with TempFolder() as folder:
            path = folder.bytes("bom.md", "﻿# Heading\n".encode("utf-8"))
            text, _notes = extract.extract(path, "markdown")
            self.assertEqual("# Heading\n", text)
            self.assertFalse(text.startswith("﻿"))

    def test_line_endings_are_all_made_the_same(self):
        with TempFolder() as folder:
            path = folder.bytes("mixed.txt", b"one\r\ntwo\rthree\n")
            text, _notes = extract.extract(path, "text")
            self.assertEqual("one\ntwo\nthree\n", text)

    def test_a_character_that_will_not_decode_is_replaced_and_noted(self):
        with TempFolder() as folder:
            path = folder.bytes("odd.txt", b"good \xff bad\n")
            text, notes = extract.extract(path, "text")
            self.assertIn("characters-replaced", notes)
            self.assertIn("good", text)


class TestSpreadsheetStyleFiles(unittest.TestCase):
    def test_rows_come_back_as_a_table_with_its_heading_row(self):
        path = os.path.join(SOURCES_FIXTURES, "customers.csv")
        text, notes = extract.extract(path, "csv")
        lines = text.strip().split("\n")
        self.assertEqual("company | segment | plan | started", lines[0])
        self.assertEqual("Northwind | mid-market | team | 2026-01-14", lines[1])
        self.assertEqual(4, len(lines))
        self.assertEqual([], notes)

    def test_more_rows_than_we_read_is_said_out_loud(self):
        with TempFolder() as folder:
            rows = ["name,value"]
            for number in range(constants.CSV_MAX_ROWS + 5):
                rows.append("row%d,%d" % (number, number))
            path = folder.file("big.csv", "\n".join(rows) + "\n")
            text, notes = extract.extract(path, "csv")
            self.assertIn("rows-capped", notes)
            body = [line for line in text.strip().split("\n") if line]
            self.assertEqual(constants.CSV_MAX_ROWS + 1, len(body))

    def test_a_line_break_inside_a_cell_does_not_break_the_table(self):
        with TempFolder() as folder:
            path = folder.file("wrapped.csv", 'name,note\nAcme,"one\ntwo"\n')
            text, _notes = extract.extract(path, "csv")
            lines = text.strip().split("\n")
            self.assertEqual(2, len(lines))
            self.assertEqual("Acme | one two", lines[1])

    def test_an_empty_file_comes_back_empty(self):
        with TempFolder() as folder:
            path = folder.file("empty.csv", "")
            text, notes = extract.extract(path, "csv")
            self.assertEqual("", text.strip())
            self.assertIn("empty", notes)


class TestWhatIsRefused(unittest.TestCase):
    def test_a_file_of_bytes_rather_than_words_is_refused(self):
        with TempFolder() as folder:
            path = folder.bytes("binary.txt", b"words\x00and then a zero byte")
            with self.assertRaises(SourceRejected) as caught:
                extract.extract(path, "text")
            self.assertEqual("binary", caught.exception.code)

    def test_a_zero_byte_far_into_the_file_is_not_looked_for(self):
        with TempFolder() as folder:
            payload = b"a" * 5000 + b"\x00"
            path = folder.bytes("late.txt", payload)
            text, _notes = extract.extract(path, "text")
            self.assertTrue(text.startswith("aaaa"))

    def test_a_file_over_the_size_cap_is_refused(self):
        with TempFolder() as folder:
            path = folder.bytes(
                "huge.txt", b"a" * (constants.SOURCE_MAX_BYTES + 1)
            )
            with self.assertRaises(SourceRejected) as caught:
                extract.extract(path, "text")
            self.assertEqual("too-large", caught.exception.code)

    def test_a_kind_the_plugin_does_not_read_itself_is_refused(self):
        path = os.path.join(SOURCES_FIXTURES, "plan.pdf")
        with self.assertRaises(SourceRejected) as caught:
            extract.extract(path, "pdf")
        self.assertEqual("unsupported", caught.exception.code)

    def test_a_file_that_is_not_there_is_refused(self):
        with TempFolder() as folder:
            with self.assertRaises(SourceRejected) as caught:
                extract.extract(os.path.join(folder.path, "gone.md"), "markdown")
            self.assertEqual("unreadable", caught.exception.code)

    def test_a_link_is_never_opened(self):
        with TempFolder() as folder:
            real = folder.file("real.md", "hello\n")
            link = os.path.join(folder.path, "link.md")
            os.symlink(real, link)
            with self.assertRaises(SourceRejected) as caught:
                extract.extract(link, "markdown")
            self.assertEqual("unreadable", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
