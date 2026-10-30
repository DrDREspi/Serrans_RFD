"""Round 0 selection: pick the parents for round 1 and the first minibinders.

The work happens in selection.py; this file just supplies the round 0 column
layout and output folder.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_args
import selection

if __name__ == "__main__":
    args = cli_args.parse("Select the best round 0 designs.")
    selection.run_stage(selection.ROUND0, "top10binders", args)
