"""Final step: add the binder amino acid sequence to the minibinder table.

Reads minibinders_to_validate/minibinders_to_validate.csv, pulls the chain A
sequence out of each design's PDB, and writes
minibinders_to_validate/minibinders_to_validate_seqs.csv.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_args
import pdb_utils

MINIBINDERS_DIR = "minibinders_to_validate"
INPUT_CSV = os.path.join(MINIBINDERS_DIR, "minibinders_to_validate.csv")
OUTPUT_CSV = os.path.join(MINIBINDERS_DIR, "minibinders_to_validate_seqs.csv")
PDBS_DIR = os.path.join(MINIBINDERS_DIR, "pdbs")


def main(args):
    if not os.path.exists(INPUT_CSV):
        print(f"No minibinder table at {INPUT_CSV}; nothing to do.")
        return

    with open(INPUT_CSV, newline="") as infile:
        reader = csv.DictReader(infile)
        if reader.fieldnames is None:
            print(f"{INPUT_CSV} is empty; nothing to do.")
            return
        if "design_name" not in reader.fieldnames:
            raise SystemExit(
                f"{INPUT_CSV} has no 'design_name' column "
                f"(found: {reader.fieldnames})."
            )
        rows = list(reader)
        fieldnames = reader.fieldnames + ["sequence"]

    written = 0
    missing = 0
    with open(OUTPUT_CSV, "w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            pdb_path = os.path.join(PDBS_DIR, row["design_name"] + ".pdb")
            if not os.path.exists(pdb_path):
                print(f"PDB file not found, skipping: {pdb_path}")
                missing += 1
                continue
            row["sequence"] = pdb_utils.extract_sequence_from_pdb(pdb_path, chain="A")
            writer.writerow(row)
            written += 1

    print(f"Wrote {written} minibinder sequences to {OUTPUT_CSV}.")
    if missing:
        print(f"{missing} design(s) had no PDB file and were skipped.")

    # The table without sequences is superseded by the one we just wrote.
    os.remove(INPUT_CSV)


if __name__ == "__main__":
    main(cli_args.parse("Add binder sequences to the minibinder table."))
