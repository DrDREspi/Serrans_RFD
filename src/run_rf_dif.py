import os
import subprocess
import tempfile
import argparse


def get_residue_info(pdb_file):
    # This function extracts the first and last residue number for each chain in a PDB file.
    residues = {}
    try:
        with open(pdb_file, 'r') as pdb:
            for line in pdb:
                if line.startswith("ATOM"):
                    chain_id = line[21]  # Chain identifier at position 22
                    res_num = int(line[22:26].strip())  # Residue number
                    if chain_id not in residues:
                        residues[chain_id] = [res_num, res_num]
                    else:
                        residues[chain_id][1] = res_num
    except Exception as e:
        print(f"Error processing file {pdb_file}: {e}")
        return None  # Or return an empty dictionary, depending on how you want to handle errors
    
    return residues if residues else None  # Return None if no valid residues were found

def format_residue_ranges(residues):
    # Format the residues into a string with the required format (e.g., A1-9/0 B1-206/0 100-150)
    residue_str = ' '.join([f"{chain}{first}-{last}/0" for chain, (first, last) in residues.items()])
    
    # Append '100-150' after all chain ranges
    return f"{residue_str} 100-150"

def main(pdb_folder, bash_script):

    # Argument parsing for the round number
    parser = argparse.ArgumentParser(description='Process protein designs and output top designs and minibinders.')
    parser.add_argument('-rn', type=int, help='The round number for this execution')
    parser.add_argument('-r', type=int, help='The round number for this execution', default=5)
    parser.add_argument("-m", type=int, help="Number of minibinders required.", default=10)
    parser.add_argument("-d", type=int, help="Number of desings going to the next partial diffusion round.", default=10)
    parser.add_argument("-ipae", type=float, help="ipAE threshold.", default=10)
    parser.add_argument("-plddt", type=float, help="pLDDT threshold.", default=90)
    parser.add_argument("-hs", type=str, help="Hotspots. e.g., A23, A45", default="False")
    parser.add_argument("-sc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=175)
    parser.add_argument("-seq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 5)
    parser.add_argument("-psc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=5)
    parser.add_argument("-pseq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 10)

    args = parser.parse_args()


    for pdb_file in os.listdir(pdb_folder):
        if pdb_file.endswith(".pdb"):
            pdb_path = os.path.join(pdb_folder, pdb_file)
            basename = os.path.splitext(pdb_file)[0]
            
            residues = get_residue_info(pdb_path)
            
            if residues is None:
                print(f"Skipping {pdb_file} due to missing residue information.")
                continue

            formatted_residues = format_residue_ranges(residues)

            # Run the bash script directly with os.system
            os.system(f'bash {bash_script} {pdb_path} {basename} "{formatted_residues}" {args.hs} {args.sc} {args.seq}')

if __name__ == "__main__":
    # Define the folder containing the PDB files and the bash script to run
    pdb_folder = "targets"
    bash_script = "src/RF_diff.sh"
    
    main(pdb_folder, bash_script)
