#!/usr/bin/env python3
"""Serrans_RFD - automated pipeline for de novo minibinder design.

Round 0 runs RFdiffusion, ProteinMPNN and AF2 over every target PDB in
targets/. Each following round takes the best designs so far and re-diffuses
them (partial diffusion), keeping anything that passes the ipAE and pLDDT cuts.
The loop stops when enough minibinders have been collected or the round limit
is reached.

Run from the repository root:

    python3 Serrans_RFD.py -r 5 -m 200 -hs A27

See README.md for the full argument list, and config.sh for the paths to your
RFdiffusion / ProteinMPNN / AF2 installations.
"""

import csv
import os
import shutil
import stat
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import cli_args

# Pipeline steps, in the order they run.
STEP_RF_DIFFUSION = "src/run_rf_dif.py"
STEP_FILTER = "src/call_filter_pdbs.py"
STEP_SELECT = "src/select_best_designs.py"
STEP_PARTIAL_DIFFUSION = "src/run_partial_diff_2.py"
STEP_FILTER_PD = "src/call_filter_pdbs_for_partial_diff.py"
STEP_SELECT_PD = "src/select_best_designs_pd.py"
STEP_EXTRACT_SEQ = "src/extract_seq.py"

MINIBINDERS_CSV = "minibinders_to_validate/minibinders_to_validate.csv"

# Working folders removed once the run finishes.
SCRATCH_FOLDERS = ["partial_outputs", "RFdiffusion_outputs", "outputs"]


def delete_folder(folder_path):
    """Delete a folder and its contents, including read-only files."""
    if not os.path.exists(folder_path):
        return

    def remove_readonly(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        shutil.rmtree(folder_path, onerror=remove_readonly)
        print(f"Removed working folder '{folder_path}'.")
    except OSError as e:
        print(f"Could not remove '{folder_path}': {e}")


def move_folders_by_prefix(prefix, target_location, exclude=None):
    """Move every folder in the current directory starting with `prefix`."""
    os.makedirs(target_location, exist_ok=True)

    for item in sorted(os.listdir(".")):
        if not os.path.isdir(item) or not item.startswith(prefix):
            continue
        if exclude and exclude in item:
            continue
        if os.path.abspath(item) == os.path.abspath(target_location):
            continue
        shutil.move(item, os.path.join(target_location, item))
        print(f"Moved {item} to {target_location}")


def move_folders_to_new_folder(folder_names, new_folder_name):
    """Group the named folders under a new folder, for a tidy output tree."""
    os.makedirs(new_folder_name, exist_ok=True)

    for folder_name in folder_names:
        if os.path.exists(folder_name):
            shutil.move(folder_name, os.path.join(new_folder_name, folder_name))
            print(f"Moved {folder_name} into {new_folder_name}")
        else:
            print(f"Folder {folder_name} not found; nothing to move.")


def validate_hotspots(hotspot_str):
    """Check a hotspot string like 'A23,B254' and return it as a list."""
    if not hotspot_str or hotspot_str == "False":
        return []

    hotspots = [x.strip() for x in hotspot_str.split(",")]
    for h in hotspots:
        if not h or len(h) < 2 or not h[0].isalpha() or not h[1:].isdigit():
            raise ValueError(
                f"Invalid hotspot format: '{h}'. Expected a chain letter "
                "followed by a residue number, e.g. 'A23'."
            )
    return hotspots


def run_step(script_path, round_num, args):
    """Run one pipeline step as a subprocess, streaming its output."""
    command = ["python3", script_path, "-rn", str(round_num)]
    command += cli_args.as_cli_args(args, exclude={"rn"})

    print(f"--> {' '.join(command)}", flush=True)
    result = subprocess.run(command)

    if result.returncode != 0:
        raise SystemExit(
            f"Pipeline step '{script_path}' failed in round {round_num} "
            f"(exit code {result.returncode}). Stopping."
        )

    print(f"<-- Finished {script_path} (round {round_num}).", flush=True)


def count_csv_rows(csv_file_path):
    """Count the data rows (excluding the header) in a CSV file."""
    if not os.path.exists(csv_file_path):
        return 0
    with open(csv_file_path, "r", newline="") as csv_file:
        return max(sum(1 for _ in csv.reader(csv_file)) - 1, 0)


def tidy_round_outputs(round_num):
    """Collect a round's raw outputs into one per-round folder."""
    move_folders_to_new_folder(
        ["best_designs", "Binder_design_outputs"],
        f"Serrans_RFD_outputs{round_num}",
    )


def cleanup():
    """Remove scratch folders and group the results into tidy directories."""
    for folder in SCRATCH_FOLDERS:
        delete_folder(folder)
    move_folders_by_prefix("top10", "TOP10_designs_per_round")
    move_folders_by_prefix("Serrans", "Serrans_int_files", exclude="int")


def main():
    args = cli_args.parse(
        "Serrans_RFD - automated pipeline for de novo minibinder design."
    )

    try:
        hotspots = validate_hotspots(args.hs)
    except ValueError as e:
        raise SystemExit(f"Error: {e}")

    if hotspots:
        print(f"Targeting hotspots: {', '.join(hotspots)}")
    else:
        print("No hotspots given; RFdiffusion will choose the interface.")

    print("Starting the pipeline...")

    # --- Round 0: de novo design against each target ------------------------
    print("Round 0: RFdiffusion, ProteinMPNN and AF2.")
    run_step(STEP_RF_DIFFUSION, 0, args)
    run_step(STEP_FILTER, 0, args)
    run_step(STEP_SELECT, 0, args)

    round_num = 0
    tidy_round_outputs(round_num)

    # --- Partial diffusion rounds -------------------------------------------
    while round_num <= args.r:
        print(f"Starting partial diffusion round {round_num + 1}...")

        run_step(STEP_PARTIAL_DIFFUSION, round_num, args)
        run_step(STEP_FILTER_PD, round_num, args)

        round_num += 1

        run_step(STEP_SELECT_PD, round_num, args)

        row_count = count_csv_rows(MINIBINDERS_CSV)
        print(f"{row_count} minibinder(s) collected after round {round_num}.")

        tidy_round_outputs(round_num)

        if row_count >= args.m:
            print(
                f"Reached the target of {args.m} minibinders. "
                "Ending the pipeline loop."
            )
            break
    else:
        print(f"Reached the round limit of {args.r} rounds.")

    # --- Final step: write out the binder sequences --------------------------
    run_step(STEP_EXTRACT_SEQ, round_num, args)

    print("Minibinder design pipeline completed.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # Tidy up even if a step failed, so a crashed run is still navigable.
        cleanup()
