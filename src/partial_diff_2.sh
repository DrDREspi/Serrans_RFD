#!/bin/bash
# ---------------------------------------------------------------------------
# Partial diffusion round: re-diffuse one surviving binder, then redesign its
# sequence with ProteinMPNN and re-score with AF2.
#
# Usage: partial_diff_2.sh <pdb_file> <basename> <scaffolds> <seqs>
#
# All tool locations come from config.sh in the repository root.
# ---------------------------------------------------------------------------
set -eo pipefail

SERRANS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$SERRANS_ROOT/config.sh"

PDB_FILE=$1
BASENAME=$2
SCAFFOLDS=$3
SEQUENCES=$4

if [ -z "$SEQUENCES" ]; then
    echo "Usage: $0 <pdb_file> <basename> <scaffolds> <seqs>" >&2
    exit 1
fi

echo "PDB_FILE:  $PDB_FILE"
echo "BASENAME:  $BASENAME"
echo "SCAFFOLDS: $SCAFFOLDS"
echo "SEQUENCES: $SEQUENCES"

serrans_init_modules

# --- 1. Work out the contig string from the input complex --------------------
# Chain A is the binder, chain B is the target. The binder is fully re-diffused
# (its own length), the target is held fixed.
pdb_basename=$(basename "$PDB_FILE" .pdb)
target_end=$(awk '$1 == "ATOM" && $5 == "B" {value=$6} END{print value}' "$PDB_FILE")
binder_end=$(awk '$1 == "ATOM" && $5 == "A" {value=$6} END{print value}' "$PDB_FILE")

if [ -z "$binder_end" ] || [ -z "$target_end" ]; then
    echo "ERROR: could not read chain A/B residue numbers from $PDB_FILE" >&2
    exit 1
fi

target_start=$((1 + binder_end))
echo "Binder (chain A) last residue: $binder_end"
echo "Target (chain B) last residue: $target_end"

contigs="${binder_end}-${binder_end}/0 B${target_start}-${target_end}"

# --- 2. RFdiffusion in partial diffusion mode --------------------------------
serrans_load rfdiffusion
mkdir -p partial_outputs

run_inference.py \
    inference.output_prefix="partial_outputs/$pdb_basename" \
    inference.input_pdb="$PDB_FILE" \
    "contigmap.contigs=[$contigs]" \
    inference.num_designs="$SCAFFOLDS" \
    diffuser.partial_T="$SERRANS_PARTIAL_T"

rm -rf partial_outputs/traj

# Give the new backbones predictable names: <parent>_0.pdb, <parent>_1.pdb, ...
counter=0
cd partial_outputs
for file in *.pdb; do
    [ -e "$file" ] || continue
    mv "$file" "${BASENAME}_${counter}.pdb"
    counter=$((counter + 1))
done
cd ..
serrans_unload

# --- 3. ProteinMPNN: redesign the sequences ----------------------------------
serrans_load proteinmpnn
mkdir -p Binder_design_outputs

if ! compgen -G "partial_outputs/${BASENAME}*.pdb" >/dev/null; then
    echo "ERROR: partial diffusion produced no backbones for $BASENAME." >&2
    exit 1
fi

silentfrompdbs partial_outputs/"${BASENAME}"*.pdb > "Binder_design_outputs/$BASENAME.silent"
cd Binder_design_outputs
dl_interface_design.py -silent "$BASENAME.silent" \
                       -seqs_per_struct "$SEQUENCES" \
                       -relax_cycles 0 \
                       -outsilent "${BASENAME}_mpnn.silent"
rm -f "$BASENAME.silent"
cd ..
rm -rf partial_outputs
serrans_unload

# --- 4. AF2 initial guess: predict and score ---------------------------------
serrans_load af2
cd Binder_design_outputs
predict.py -silent "${BASENAME}_mpnn.silent" \
           -scorefilename "${BASENAME}_out.sc" \
           -outsilent "${BASENAME}_af2.silent"
rm -f "${BASENAME}_mpnn.silent"

echo "Finished partial diffusion for $BASENAME."
