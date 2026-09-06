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

python3 -m unittest discover -s tests -p 'test_*.py' -v
exit $?
