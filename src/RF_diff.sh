#!/bin/bash
# ---------------------------------------------------------------------------
# Round 0: RFdiffusion -> ProteinMPNN -> AF2 for one target PDB.
#
# Usage: RF_diff.sh <pdb_file> <basename> <contigs> <hotspots> <scaffolds> <seqs>
#
# All tool locations come from config.sh in the repository root.
# ---------------------------------------------------------------------------
set -eo pipefail

SERRANS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$SERRANS_ROOT/config.sh"

PDB_FILE=$1
BASENAME=$2
CHAIN_RESIDUES=$3
HOTSPOTS=$4
SCAFFOLDS=$5
SEQUENCES=$6

if [ -z "$SEQUENCES" ]; then
    echo "Usage: $0 <pdb_file> <basename> <contigs> <hotspots> <scaffolds> <seqs>" >&2
    exit 1
fi

echo "PDB_FILE:       $PDB_FILE"
echo "BASENAME:       $BASENAME"
echo "CHAIN_RESIDUES: $CHAIN_RESIDUES"
echo "HOTSPOTS:       '$HOTSPOTS'"
echo "SCAFFOLDS:      $SCAFFOLDS"
echo "SEQUENCES:      $SEQUENCES"

serrans_init_modules

# --- 1. RFdiffusion: generate binder backbones --------------------------------
serrans_load rfdiffusion

rfd_args=(
    inference.input_pdb="$PDB_FILE"
    inference.output_prefix="RFdiffusion_outputs/$BASENAME"
    inference.num_designs="$SCAFFOLDS"
    "contigmap.contigs=[$CHAIN_RESIDUES]"
    denoiser.noise_scale_ca=0
    denoiser.noise_scale_frame=0
)
if [ "$HOTSPOTS" != "False" ]; then
    rfd_args+=("ppi.hotspot_res=[$HOTSPOTS]")
fi

run_inference.py "${rfd_args[@]}"

rm -rf RFdiffusion_outputs/traj
serrans_unload

# --- 2. ProteinMPNN: design sequences for those backbones ---------------------
serrans_load dl_binder_design

mkdir -p Binder_design_outputs

# Fail clearly here rather than letting an empty silent file confuse AF2.
if ! compgen -G "RFdiffusion_outputs/${BASENAME}*.pdb" >/dev/null; then
    echo "ERROR: RFdiffusion produced no backbones for $BASENAME." >&2
    exit 1
fi

silentfrompdbs RFdiffusion_outputs/"${BASENAME}"*.pdb > "Binder_design_outputs/$BASENAME.silent"
rm -f RFdiffusion_outputs/"${BASENAME}"*.pdb

cd Binder_design_outputs
dl_interface_design.py -silent "$BASENAME.silent" \
                       -seqs_per_struct "$SEQUENCES" \
                       -relax_cycles 0 \
                       -outsilent "${BASENAME}_mpnn.silent"
rm -f "$BASENAME.silent"

# --- 3. AF2 initial guess: predict and score the complexes -------------------
predict.py -silent "${BASENAME}_mpnn.silent" \
           -scorefilename "${BASENAME}_out.sc" \
           -outsilent "${BASENAME}_af2.silent"
rm -f "${BASENAME}_mpnn.silent"

# The predicted structures stay packed in ${BASENAME}_af2.silent. Only the
# designs that pass the filter are unpacked, by filter_pdbs_modified.sh.
echo "Finished round 0 for $BASENAME."
