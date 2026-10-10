"""For the test suite only: a script a test starts holds its approval.

Every library function that writes an approval refuses unless the process
was started by a command the person allowed through Claude Code's own
question (Unit 1.7e). In the suite a test is the person, so tests/support.py
puts this folder first on the path every script it starts inherits, with the
variable below set, and Python imports this file as each of those processes
starts. Nothing in the plugin reads that variable or knows this file exists,
so a base's own owner never has a way past the question that a test has.
tests/test_approval_ask.py starts its scripts without either, to prove the
refusal.
"""

import os

if os.environ.get("GTM_BASE_TESTS_HOLD_APPROVAL") == "1":
    try:
        from gtmbase import approval

        class _EveryWrite(frozenset):
            def __contains__(self, name):
                return True

            def __bool__(self):
                return True

        approval._held = _EveryWrite()
    except Exception:
        pass
