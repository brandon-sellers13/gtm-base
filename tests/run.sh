#!/bin/sh
# Run the GTM Base test suite with the fakes ahead of the real tools on PATH.
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PATH="$ROOT/tests/fakes:$PATH"
export PATH

if [ -n "$PYTHONPATH" ]; then
  PYTHONPATH="$ROOT/plugins/gtm-base/lib:$PYTHONPATH"
else
  PYTHONPATH="$ROOT/plugins/gtm-base/lib"
fi
export PYTHONPATH

# The tests fix a moment and the day it fell on, and the library reads the day
# where the person is sitting. One zone for every run keeps the two in step on
# any machine, wherever it happens to be that week.
TZ="America/Los_Angeles"
export TZ

python3 -m unittest discover -s tests -p 'test_*.py' -v

# The test classes that start a skill's scripts, run a second time with every
# script started from a folder linked to the base rather than from inside it.
# Every script refused that folder in 0.3.0 and no test saw it, because every
# test started every script from inside the base (finding 1 of the release A
# live check). Only the classes that start a script are run again, because
# running the rest again proves nothing new and nearly doubles the time;
# tests/test_linked_folder.py fails when a class that starts a script is
# missing from this list. The walk through the skills' own commands, and the
# tests written for that finding, already run from a linked folder above.
cd "$ROOT/tests"
TESTS_FROM_A_LINKED_FOLDER=1
export TESTS_FROM_A_LINKED_FOLDER
python3 -m unittest -v \
  test_moment_of_use.TestEveryPathThatHandsOverADocument \
  test_moment_of_use.TestTheReview \
  test_moment_of_use.TestOneWholeSitting \
  test_moment_of_use.TestTheUnitReview \
  test_approve_local.TestTheScriptRunsEveryAnswer \
  test_compose_proposal.TestTheHandEditHabitThroughTheScript \
  test_compose_proposal.TestAHandEditToADocumentWithAnUnusualName \
  test_changes_migration.TestTheOlderNameOfTheDismissOption \
  test_changes_migration.TestTheMoveStepOfTheSkill \
  test_changes_migration.TestTheDeclineCanActuallyBeGiven \
  test_changes_migration.TestTheReadOnlyCheck \
  test_first_draft_marker.TestTheOneWayToClearIt \
  test_first_draft_marker.TestTheObsoleteClaimIsGone \
  test_first_draft_marker.TestOneOrdinaryEditOfThePreparedChange \
  test_first_draft_marker.TestTheWordingCanBeRevisedAgain \
  test_first_draft_marker.TestARevisionThatLandsWhileApprovalReads \
  test_names_with_a_space.TestApprovingHere \
  test_names_with_a_space.TestTheMomentOfUse \
  test_third_look.TestAWordsFileSurvivesASecondWindow \
  test_words_files.TestAPathTheScriptsDidNotHandOut \
  test_words_files.TestThePathTheScriptsDoHandOut \
  test_words_files.TestTheDraftFileToo
exit $?
