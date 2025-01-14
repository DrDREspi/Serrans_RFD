import os
import argparse


def extract_sequence_from_pdb(pdb_file):
    # A dictionary to map three-letter amino acid codes to one-letter codes
    amino_acid_codes = {
        'ALA': 'A', 'CYS': 'C', 'ASP': 'D', 'GLU': 'E', 'PHE': 'F',
        'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LYS': 'K', 'LEU': 'L',
        'MET': 'M', 'ASN': 'N', 'PRO': 'P', 'GLN': 'Q', 'ARG': 'R',
        'SER': 'S', 'THR': 'T', 'VAL': 'V', 'TRP': 'W', 'TYR': 'Y'
    }

    sequence = ""
    previous_residue_number = None

    with open(pdb_file, 'r') as file:
        for line in file:
            # Check if the line is for an ATOM, chain A, and CA atom
            if (
                line.startswith("ATOM") and
                line[13:15].strip() == "CA" and  # Check for alpha carbon
                line[21].strip() == "A"         # Check for chain A
            ):
                residue_name = line[17:20].strip()
                residue_number = line[22:26].strip()

                # Avoid adding duplicate residues
                if residue_number != previous_residue_number:
                    sequence += amino_acid_codes.get(residue_name, 'X')
                    previous_residue_number = residue_number

    return sequence




def read_csv_file(csv_file, output_file):
    infile = open(csv_file, "r")
    for line in infile:
        if "pae_interaction" in line:
            output_file.write(line[:-1]+",sequence\n")
        else:
            splitted = line.strip().split(",")
            print(splitted)
            pdb_file_path = 'minibinders_to_validate/pdbs/' + splitted[2] + ".pdb"

            # Check if the PDB file exists
            if os.path.exists(pdb_file_path):
                # If it exists, extract the sequence
                sequence = extract_sequence_from_pdb(pdb_file_path)
                # Write the result to the output file
                output_file.write(line[:-1] + "," + sequence + "\n")
            else:
                # Optionally, handle the case where the file does not exist
                print(f"PDB file not found: {pdb_file_path}")

parser = argparse.ArgumentParser(description='Process protein designs and output top designs and minibinders.')
parser.add_argument('-rn', type=int, help='The round number for this execution')
parser.add_argument('-r', type=int, help='The round number for this execution', default=5)
parser.add_argument("-m", type=int, help="Number of minibinders required.", default=10)
parser.add_argument("-d", type=int, help="Number of desings going to the next partial diffusion round.", default=10)
parser.add_argument("-ipae", type=float, help="ipAE threshold.", default=10)
parser.add_argument("-plddt", type=float, help="pLDDT threshold.", default=90)
parser.add_argument("-hs", type=str, help="Hotspots. e.g., A23, A45", default= False)
parser.add_argument("-sc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=175)
parser.add_argument("-seq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 5)
parser.add_argument("-psc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=5)
parser.add_argument("-pseq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 10)

args = parser.parse_args()


output_file = open("minibinders_to_validate/minibinders_to_validate_seqs.csv", "w")

infile = "minibinders_to_validate/minibinders_to_validate.csv"


read_csv_file(infile, output_file)

os.remove(infile)
