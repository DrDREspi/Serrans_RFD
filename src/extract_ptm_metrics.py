import os
import csv
import json
import shutil
import re
from Bio import SeqIO
from Bio.PDB import PDBParser
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from subprocess import run

# Step 1: Extract sequences from PDB and create FASTA files
def extract_sequences_and_create_fasta(pdb_folder, csv_file, fasta_folder):
    os.makedirs(fasta_folder, exist_ok=True)
    parser = PDBParser(QUIET=True)

    # Mapping three-letter codes to one-letter codes
    aa_map = {
        'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F',
        'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L',
        'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R',
        'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y'
    }

    with open(csv_file, 'r') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            pdb_file = os.path.join(pdb_folder, row['design_name'] + '.pdb')
            if not os.path.exists(pdb_file):
                print(f"PDB file {pdb_file} not found! Skipping...")
                continue

            structure = parser.get_structure(row['design_name'], pdb_file)
            chains = {}
            for chain in structure.get_chains():
                sequence = ''
                for residue in chain:
                    if residue.id[0] == ' ' and residue.resname in aa_map:
                        sequence += aa_map[residue.resname]
                chains[chain.id] = sequence

            fasta_seq = f">{row['design_name']}\n{chains.get('A', '')}:{chains.get('B', '')}"

            fasta_path = os.path.join(fasta_folder, row['design_name'] + '.fasta')
            with open(fasta_path, 'w') as fasta_file:
                fasta_file.write(fasta_seq)

# Step 2: Run ColabFold

def run_colabfold(fasta_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    command = (
        "source /dtu/projects/RFdiffusion/setup.sh && "
        "module load colabfold/1.5.6 && "
        f"colabfold_batch {fasta_folder} {output_folder} --calc-extra-ptm"
    )
    print(f"Running command: {command}")
    result = run(command, shell=True, executable="/bin/bash", capture_output=True, text=True)
    print(f"Standard Output:\n{result.stdout}")
    print(f"Standard Error:\n{result.stderr}")
    result.check_returncode()

    
# Step 3: Process ColabFold outputs and select the best PDBs

def process_colabfold_outputs(output_folder, mid_files_folder, csv_file):
    os.makedirs(mid_files_folder, exist_ok=True)

    updated_rows = []

    with open(csv_file, 'r') as infile:
        reader = csv.DictReader(infile)
        fieldnames = ['actifptm', 'ptm', 'iptm'] + [fn for fn in reader.fieldnames if fn != 'actifptm' and fn != 'ptm' and fn != 'iptm']
        for row in reader:
            design_name = row['design_name']

            # Find JSON and extract scores
            best_pdb, best_scores = None, None

            for file in os.listdir(output_folder):
                if file.endswith('.json') and design_name in file:
                    with open(os.path.join(output_folder, file), 'r') as json_file:
                        data = json_file.read()

                        # Use regex to extract scores
                        ptm_match = re.search(r'"ptm"\s*:\s*([0-9\.]+)', data)
                        iptm_match = re.search(r'"iptm"\s*:\s*([0-9\.]+)', data)
                        actifptm_match = re.search(r'"actifptm"\s*:\s*([0-9\.]+)', data)

                        ptm = float(ptm_match.group(1)) if ptm_match else 0
                        iptm = float(iptm_match.group(1)) if iptm_match else 0
                        actifptm = float(actifptm_match.group(1)) if actifptm_match else 0

                        scores = {'actifptm': actifptm, 'ptm': ptm, 'iptm': iptm}

                        if best_scores is None or scores['actifptm'] > best_scores['actifptm']:
                            best_scores = scores
                            best_pdb = file.replace('.json', '.pdb').replace('scores', 'unrelaxed')

            if best_pdb:
                shutil.copy(os.path.join(output_folder, best_pdb), mid_files_folder)
                row.update(best_scores)
            else:
                print(f"No valid PDB/JSON found for {design_name}! Adding empty scores.")
                row.update({'actifptm': '', 'ptm': '', 'iptm': ''})

            updated_rows.append(row)


    # Write updated CSV
    with open(csv_file, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    

# Main Workflow
def main():
    pdb_folder = "minibinders_to_validate/pdbs"
    input_csv = "minibinders_to_validate/minibinders_to_validate_seqs.csv"
    fasta_folder = "Serrans_RFD_ptm_outputs/fastas"
    output_folder = "Serrans_RFD_ptm_outputs"
    mid_files_folder = "ptm_mid_files"


    extract_sequences_and_create_fasta(pdb_folder, input_csv, fasta_folder)
    run_colabfold(fasta_folder, output_folder)
    process_colabfold_outputs(output_folder, mid_files_folder, input_csv)

if __name__ == "__main__":
    main()
