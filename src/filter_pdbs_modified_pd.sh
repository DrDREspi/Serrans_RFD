#!/bin/bash

# Function to show usage
usage() {
    echo "Usage: $0 -r RUN_ID -t threshold"
    exit 1
}

# Parse command line options
while getopts ":r:t:" opt; do
  case $opt in
    r) RUN_ID="$OPTARG"
    ;;
    t) threshold="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
       usage
    ;;
  esac
done

# Check if both RUN_ID and threshold are provided
if [ -z "$RUN_ID" ] || [ -z "$threshold" ]; then
    usage
fi

# Load required modules and setup
source /dtu/projects/RFdiffusion/setup.sh
module load DL_binder_design

# Create a directory for best designs
mkdir -p "../best_designs/${RUN_ID}"
mkdir -p "../best_designs/${RUN_ID}/pdbs"

# Setting input and output file names based on RUN_ID
input_file="${RUN_ID}_out.sc"
output_file="../best_designs/${RUN_ID}/${RUN_ID}_filtered_out.csv"

# Process the input file and create a CSV output
{
    # Read the header, convert to CSV format and write to the output file
    IFS= read -r first_line
    echo "$first_line" | sed 's/ \+/,/g' > "$output_file"

    # Read each line and process
    while IFS= read -r line; do
        pae_interaction=$(echo "$line" | awk '{print $4}')
        if (( $(echo "$pae_interaction < $threshold" | bc -l) )); then
            # Convert line to CSV format and write to the output file
            echo "$line" | sed 's/ \+/,/g' >> "$output_file"
            # Extract the description and process the PDB file
            description_line=$(echo "$line" | awk '{print $NF}')
            silentextractspecific "../Binder_design_outputs/${RUN_ID}_af2.silent" "$description_line"
            mv *.pdb "../best_designs/${RUN_ID}/pdbs"
        fi
    done
} < "$input_file"


