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

It imports nothing of the plugin itself. It waits for the script to load the
approval module from wherever the script's own shim finds the library, and
marks it held then, so a test that starts a broken copy of the plugin still
starts the broken copy.
"""

import importlib.abc
import importlib.util
import os
import sys

_NAME = "gtmbase.approval"


class _EveryWrite(frozenset):
    def __contains__(self, name):
        return True

    def __bool__(self):
        return True


class _HoldWhenLoaded(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != _NAME:
            return None
        sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(name)
        finally:
            sys.meta_path.insert(0, self)
        if spec is None or spec.loader is None:
            return spec
        load = spec.loader.exec_module

        def exec_module(module):
            load(module)
            module._held = _EveryWrite()

        spec.loader.exec_module = exec_module
        return spec


if os.environ.get("GTM_BASE_TESTS_HOLD_APPROVAL") == "1":
    sys.meta_path.insert(0, _HoldWhenLoaded())
