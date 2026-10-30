"""Partial diffusion filter: run filter_pdbs_modified_pd.sh for every AF2 score file.

MATCH_SUFFIX picks which score files belong to this stage; STRIP_SUFFIX is
removed to recover the run id used to name the silent and output files.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cli_args
import serrans_config

FOLDER = "Binder_design_outputs"
# Absolute path, because this script chdirs into {FOLDER} before running it.
SHELL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filter_pdbs_modified_pd.sh")
MATCH_SUFFIX = "af2pred_out.sc"
STRIP_SUFFIX = "_out.sc"
STAGE = "partial diffusion"


def main(args):
    if not os.path.isdir(FOLDER):
        raise SystemExit(f"'{FOLDER}' not found; the previous step produced nothing.")

    threshold = serrans_config.get("SERRANS_PREFILTER_PAE", "30")
    os.chdir(FOLDER)

    score_files = sorted(f for f in os.listdir(".") if f.endswith(MATCH_SUFFIX))
    if not score_files:
        print(f"No '{MATCH_SUFFIX}' score files in '{FOLDER}'; nothing to filter.")
        return

    print(f"Filtering {len(score_files)} {STAGE} score file(s).")

    failures = []
    for filename in score_files:
        run_id = filename[: -len(STRIP_SUFFIX)]
        print(f"Filtering {run_id}")
        try:
            subprocess.run(
                ["bash", SHELL_SCRIPT, "-r", run_id, "-t", str(threshold)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error filtering {filename}: {e}")
            failures.append(run_id)

    if failures:
        raise SystemExit(f"Filtering failed for: {', '.join(failures)}")


if __name__ == "__main__":
    main(cli_args.parse(f"Filter the {STAGE} designs."))
