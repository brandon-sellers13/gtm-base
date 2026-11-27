"""C2's security review, the borderline pattern Brandon closed on 2026-11-27.

A proposal whose commits edit a document, add a record for it, and then undo
the edit changes records only, so it can be accepted as records only. Before
this, the record still settled the change for that document, because the
commit that added the record had also changed it. A record now settles a
document only when the change that brought it onto the main line changed that
document too. Every fixture is written from scratch; the company is made up.
"""

import os
import unittest

import support  # noqa: F401  (puts the library on the path)
import stale_parity as sp

POSITIONING = "context/positioning.md"


class TestARecordsOnlyAccept(unittest.TestCase):
    def setUp(self):
        self.home = os.environ.get("GTM_BASE_HOME")

    def tearDown(self):
        if self.home is None:
            os.environ.pop("GTM_BASE_HOME", None)
        else:
            os.environ["GTM_BASE_HOME"] = self.home

    def verdict(self, undo):
        base = sp.Base()
        try:
            base.save({"learning/changes/%s.md" % sp.A: sp.change(sp.A, "2026-11-01", "2026-11-02", sp.POS)})
            base.accept_record(sp.A, sp.OWNER, "2026-11-10", undo=undo)
            _snapshot, verdict, _words = base.snapshot_and_verdict()
        finally:
            base.close()
        return verdict

    def test_an_edit_undone_inside_the_proposal_settles_nothing(self):
        self.assertEqual(sp.A, self.verdict(undo=True).get(POSITIONING))

    def test_the_same_proposal_with_its_edit_kept_still_settles_it(self):
        self.assertIsNone(self.verdict(undo=False).get(POSITIONING))


if __name__ == "__main__":
    unittest.main()
