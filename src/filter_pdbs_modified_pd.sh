#!/bin/bash
# ---------------------------------------------------------------------------
# Partial diffusion filter: pull the promising designs out of the AF2 silent file.
#
# Reads the AF2 score file for one run, keeps the rows whose pae_interaction is
# below the loose prefilter cut, and unpacks just those designs from the silent
# file into best_designs/<RUN_ID>/pdbs.
#
# Usage: filter_pdbs_modified_pd.sh -r RUN_ID [-t threshold]
# Must be run from inside Binder_design_outputs (the callers do this).
# ---------------------------------------------------------------------------
set -eo pipefail

SERRANS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$SERRANS_ROOT/config.sh"

usage() {
    echo "Usage: $0 -r RUN_ID [-t threshold]" >&2
    exit 1
}

threshold="$SERRANS_PREFILTER_PAE"

while getopts ":r:t:" opt; do
  case $opt in
    r) RUN_ID="$OPTARG" ;;
    t) threshold="$OPTARG" ;;
    \?) echo "Invalid option -$OPTARG" >&2; usage ;;
  esac
done

[ -z "$RUN_ID" ] && usage
[ -z "$threshold" ] && usage

serrans_init_modules
serrans_load dl_binder_design

out_dir="../best_designs/${RUN_ID}"
mkdir -p "$out_dir/pdbs"

input_file="${RUN_ID}_out.sc"
output_file="${out_dir}/${RUN_ID}_filtered_out.csv"

if [ ! -f "$input_file" ]; then
    echo "ERROR: score file not found: $input_file" >&2
    exit 1
fi

# pae_interaction sits in column 4 of the score file produced by this stage.
pae_col=4
kept=0

{
    IFS= read -r header
    echo "$header" | sed 's/ \+/,/g' > "$output_file"

    while IFS= read -r line; do
        [ -z "$line" ] && continue
        pae_interaction=$(echo "$line" | awk -v c="$pae_col" '{print $c}')
        case "$pae_interaction" in
            ''|*[!0-9.eE+-]*) continue ;;   # skip malformed rows
        esac
        if (( $(echo "$pae_interaction < $threshold" | bc -l) )); then
            echo "$line" | sed 's/ \+/,/g' >> "$output_file"
            description_line=$(echo "$line" | awk '{print $NF}')
            silentextractspecific "../Binder_design_outputs/${RUN_ID}_af2.silent" "$description_line"
            # Move only what this extraction produced, and tolerate a miss.
            if [ -f "${description_line}.pdb" ]; then
                mv "${description_line}.pdb" "$out_dir/pdbs/"
                kept=$((kept + 1))
            else
                echo "WARNING: silentextractspecific produced no PDB for $description_line" >&2
            fi
        fi
    done
} < "$input_file"

echo "$RUN_ID: kept $kept designs with pae_interaction < $threshold"
