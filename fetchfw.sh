#!/bin/sh
# POSIX counterpart of fetchfw.bat; requires Python 3 in PATH.
OUT=$(CDPATH= cd -P "$(dirname "$0")" && pwd) || exit 1
exec python3 "$OUT/fetchfw.py" "$@"
