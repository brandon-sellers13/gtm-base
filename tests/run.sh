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

# No test may write into the seat folder of whoever runs the suite. Every test
# module starts with the seat folder pointed at this temporary one (see
# tests/support.py), so a test that makes no seat folder of its own writes
# here instead, and the run fails if anything did. The real seat folder is
# never read, listed or touched by this check.
UNOWNED_SEAT=$(mktemp -d "${TMPDIR:-/tmp}/gtm-base-unowned-seat.XXXXXX")
GTM_BASE_TESTS_UNOWNED_SEAT="$UNOWNED_SEAT"
export GTM_BASE_TESTS_UNOWNED_SEAT

nothing_written_to_a_seat_nobody_made() {
  if [ -n "$(ls -A "$UNOWNED_SEAT")" ]; then
    echo "A test wrote into a seat folder it did not make for itself:" >&2
    find "$UNOWNED_SEAT" >&2
    rm -rf "$UNOWNED_SEAT"
    exit 1
  fi
}

python3 -m unittest discover -s tests -p 'test_*.py' -v
nothing_written_to_a_seat_nobody_made

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
  test_words_files.TestTheDraftFileToo \
  test_os_clutter.TestTheApprovalScriptPastClutter \
  test_record_change.TestTheWholeFlowThroughTheScript \
  test_record_change.TestNothingIsWrittenBeforeTheYes \
  test_record_change.TestTheAsk \
  test_record_change.TestTheDocuments \
  test_record_change.TestTheWords \
  test_record_change.TestTheIdentifier \
  test_record_change.TestBothLayouts \
  test_record_change.TestABaseWithASharedCopy \
  test_record_change.TestWhatStandsInTheWay \
  test_record_change.TestFromALinkedFolderEveryTime
nothing_written_to_a_seat_nobody_made
rm -rf "$UNOWNED_SEAT"
