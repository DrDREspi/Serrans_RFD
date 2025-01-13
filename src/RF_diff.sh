

#!/bin/sh

# Input arguments
PDB_FILE=$1
BASENAME=$2
CHAIN_RESIDUES=$3
HOTSPOTS=$4
SCAFFOLDS=$5
SEQUENCES=$6


# Log the inputs
echo "PDB_FILE: $PDB_FILE"
echo "BASENAME: $BASENAME"
echo "CHAIN_RESIDUES: $CHAIN_RESIDUES"
echo "HOTSPOTS: '$HOTSPOTS'"


# Set-up paths for modules
source /dtu/projects/RFdiffusion/setup.sh

# RFdiffusion
module load RFdiffusion

if [ "$HOTSPOTS" == "False" ]; then
    # If HOTSPOTS is "False", run the command without the hotspot_res argument
    run_inference.py inference.input_pdb="$PDB_FILE" \
                      inference.output_prefix="RFdiffusion_outputs/$BASENAME" \
                      inference.num_designs="$SCAFFOLDS" \
                      "contigmap.contigs=[$CHAIN_RESIDUES]" \
                      denoiser.noise_scale_ca=0 \
                      denoiser.noise_scale_frame=0
else
    # If HOTSPOTS is not "False", append the hotspot_res argument
    run_inference.py inference.input_pdb="$PDB_FILE" \
                      inference.output_prefix="RFdiffusion_outputs/$BASENAME" \
                      inference.num_designs="$SCAFFOLDS" \
                      "contigmap.contigs=[$CHAIN_RESIDUES]" \
                      "ppi.hotspot_res=[$HOTSPOTS]" \
                      denoiser.noise_scale_ca=0 \
                      denoiser.noise_scale_frame=0
fi


# Remove intermediate RFdiffusion trajectory files
rm -rf RFdiffusion_outputs/traj
module purge

module load DL_binder_design
mkdir Binder_design_outputs
silentfrompdbs RFdiffusion_outputs/${BASENAME}*.pdb > Binder_design_outputs/$BASENAME.silent

# Remove intermediate RFdiffusion PDB files
rm -rf RFdiffusion_outputs/${BASENAME}*.pdb

cd Binder_design_outputs
dl_interface_design.py -silent $BASENAME.silent -seqs_per_struct "$SEQUENCES" -relax_cycles 0 -outsilent ${BASENAME}_mpnn.silent

# Remove intermediate silent file
rm -f $BASENAME.silent

predict.py -silent ${BASENAME}_mpnn.silent -scorefilename ${BASENAME}_out.sc -outsilent ${BASENAME}_af2.silent

# Remove intermediate MPNN silent file
rm -f ${BASENAME}_mpnn.silent
rm -rf RFdiffusion_outputs
mkdir pdbs && cd pdbs
silentextract ${BASENAME}_af2.silent
