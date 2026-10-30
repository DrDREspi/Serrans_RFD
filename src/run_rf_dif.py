"""Round 0: run RFdiffusion -> ProteinMPNN -> AF2 for every target PDB.

One call to src/RF_diff.sh per PDB file found in the targets folder.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_args
import pdb_utils

TARGETS_FOLDER = "targets"
BASH_SCRIPT = "src/RF_diff.sh"


def main(pdb_folder, bash_script, args):
    if not os.path.isdir(pdb_folder):
        raise SystemExit(
            f"Targets folder '{pdb_folder}' not found. Put your target PDB "
            "files there and run the pipeline from the repository root."
        )

    pdb_files = sorted(f for f in os.listdir(pdb_folder) if f.endswith(".pdb"))
    if not pdb_files:
        raise SystemExit(f"No .pdb files found in '{pdb_folder}'.")

    print(f"Found {len(pdb_files)} target(s) in '{pdb_folder}'.")

    for pdb_file in pdb_files:
        pdb_path = os.path.join(pdb_folder, pdb_file)
        basename = os.path.splitext(pdb_file)[0]

        residues = pdb_utils.get_residue_info(pdb_path)
        if residues is None:
            print(f"Skipping {pdb_file}: no residue information could be read.")
            continue

        contigs = pdb_utils.format_residue_ranges(residues)

        result = subprocess.run(
            ["bash", bash_script, pdb_path, basename, contigs,
             args.hs, str(args.sc), str(args.seq)]
        )
        if result.returncode != 0:
            raise SystemExit(
                f"{bash_script} failed for {pdb_file} "
                f"(exit code {result.returncode})."
            )


if __name__ == "__main__":
    main(TARGETS_FOLDER, BASH_SCRIPT,
         cli_args.parse("Round 0 RFdiffusion/ProteinMPNN/AF2 for each target."))
