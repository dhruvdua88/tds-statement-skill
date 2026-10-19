#!/bin/sh
# Double-click on a Mac (or run from a terminal) to open the TDS statement page.
cd "$(dirname "$0")" && exec python3 scripts/tds.py ui
