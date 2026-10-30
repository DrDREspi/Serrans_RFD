"""Partial diffusion round: re-diffuse each of the surviving top designs.

One call to src/partial_diff_2.sh per PDB in the current round's TOP10 folder.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_args

BASH_SCRIPT = "src/partial_diff_2.sh"


def main(pdb_folder, bash_script, args):
    pdbs_folder = os.path.join(pdb_folder, "TOP10", "pdbs")

    if not os.path.isdir(pdbs_folder):
        print(
            f"No designs to re-diffuse: '{pdbs_folder}' does not exist. "
            "The previous round produced nothing that passed the filters."
        )
        return

    pdb_files = sorted(f for f in os.listdir(pdbs_folder) if f.endswith(".pdb"))
    if not pdb_files:
        print(f"No .pdb files in '{pdbs_folder}'; nothing to re-diffuse.")
        return

    print(f"Re-diffusing {len(pdb_files)} design(s) from '{pdbs_folder}'.")

    for pdb_file in pdb_files:
        pdb_path = os.path.join(pdbs_folder, pdb_file)
        basename = os.path.splitext(pdb_file)[0]
        print(f"Partial diffusion on {pdb_path}")

        result = subprocess.run(
            ["bash", bash_script, pdb_path, basename,
             str(args.psc), str(args.pseq)]
        )
        if result.returncode != 0:
            raise SystemExit(
                f"{bash_script} failed for {pdb_file} "
                f"(exit code {result.returncode})."
            )


if __name__ == "__main__":
    args = cli_args.parse("Partial diffusion round over the surviving designs.")

    # Round 0 reads the folder produced by the de novo step; later rounds read
    # the folder produced by the previous partial diffusion round.
    if args.rn == 0:
        pdb_folder = "top10binders"
    else:
        pdb_folder = f"top10binders_PD{args.rn}"

    main(pdb_folder, BASH_SCRIPT, args)
