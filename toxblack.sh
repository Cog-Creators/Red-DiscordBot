#!/bin/sh
black  -l 99 --check `git ls-tree $(git status | awk '{print $NF; exit}') -r --name-only | grep -E "py$"`
exit $?