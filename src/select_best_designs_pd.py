"""Partial diffusion selection: pick the parents for the next round.

The work happens in selection.py; this file just supplies the partial
diffusion column layout and the per-round output folder.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_args
import selection

if __name__ == "__main__":
    args = cli_args.parse("Select the best partial diffusion designs.")

    # Round 0 of the loop writes to top10binders; later rounds get their own
    # folder so each round's parents stay separate.
    if args.rn == 0:
        output_folder = "top10binders"
    else:
        output_folder = f"top10binders_PD{args.rn}"

    selection.run_stage(selection.partial_diffusion(args.rn), output_folder, args)
