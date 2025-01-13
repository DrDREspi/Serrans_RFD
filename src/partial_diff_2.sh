

# Input arguments
PDB_FILE=$1
BASENAME=$2
SCAFFOLDS=$3
SEQUENCES=$4

# Log the inputs
echo "PDB_FILE: $PDB_FILE"
echo "BASENAME: $BASENAME"
echo "SCAFFOLDS: $SCAFFOLDS"
echo "SEQUENCES: $SEQUENCES"

# Set-up paths for modules
source /dtu/projects/RFdiffusion/setup.sh

# RFdiffusion
module load RFdiffusion
mkdir partial_outputs

# Extracting the base name of the file for use in output prefix
pdb_basename=$(basename $PDB_FILE .pdb)
target_atom_value=$(awk '$1 == "ATOM" && $5 == "B" {value=$6} END{print value}' "$PDB_FILE")
echo "Last ATOM value in chain B of $pdb_basename: $target_atom_value"
binder_atom_value=$(awk '$1 == "ATOM" && $5 == "A" {value=$6} END{print value}' "$PDB_FILE")
echo "Last ATOM value in chain A of $pdb_basename: $binder_atom_value"
target_start=$((1 + binder_atom_value))
echo "Target length in $pdb_basename: $target_length"
# Run the inference command with the current PDB file
# Dynamically construct the command with variable substitution
cmd="run_inference.py inference.output_prefix=partial_outputs/$pdb_basename inference.input_pdb=$PDB_FILE 'contigmap.contigs=[$binder_atom_value-$binder_atom_value/0 B$target_start-$target_atom_value]' inference.num_designs="$SCAFFOLDS" diffuser.partial_T=25"
# 'contigmap.provide_seq=[$binder_atom_value-$target_atom_value]'"

echo "Executing command: $cmd"

# Execute the command
eval $cmd


rm -rf partial_outputs/traj

# Initialize a counter
counter=0
cd partial_outputs
# Loop through all .pdb files in the current directory
for file in *.pdb; do
    # Construct the new file name
    newFileName="${BASENAME}_${counter}.pdb"
    
    # Rename the file
    mv "$file" "$newFileName"
    
    # Increment the counter
    ((counter++))
done
cd ..

module purge

# ProteinMPNN 
module load proteinmpnn 
mkdir -p Binder_design_outputs
# compress pdb files from RFdiffusion into a silent file
silentfrompdbs partial_outputs/${BASENAME}*.pdb > Binder_design_outputs/$BASENAME.silent
cd Binder_design_outputs
dl_interface_design.py -silent $BASENAME.silent -seqs_per_struct "$SEQUENCES" -relax_cycles 0 -outsilent ${BASENAME}_mpnn.silent
module purge
rm -rf partial_outputs


# AF2
module load af2_binder_design
predict.py -silent ${BASENAME}_mpnn.silent -scorefilename ${BASENAME}_out.sc -outsilent ${BASENAME}_af2.silent