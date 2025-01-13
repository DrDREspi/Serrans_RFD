import os
import pandas as pd
import shutil
import argparse


def process_protein_designs(input_folder, output_folder, minibinders_folder):
    # Create the output folder for top 10 designs if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Create the folder for minibinders to validate outside the top 10 folder
    if not os.path.exists(minibinders_folder):
        os.makedirs(minibinders_folder)

    minibinders_pdbs_folder = os.path.join(minibinders_folder, "pdbs")
    if not os.path.exists(minibinders_pdbs_folder):
        os.makedirs(minibinders_pdbs_folder)

    # List to hold minibinders data
    minibinders_list = []

    # Loop through each protein design folder in the input folder
    for protein_folder in os.listdir(input_folder):
        protein_path = os.path.join(input_folder, protein_folder)

        if os.path.isdir(protein_path):
            # Identify the CSV file and the "pdbs" folder
            csv_file = None
            pdbs_folder = None
            for file in os.listdir(protein_path):
                if file.endswith(".csv"):
                    csv_file = os.path.join(protein_path, file)
                elif file == "pdbs":
                    pdbs_folder = os.path.join(protein_path, "pdbs")

            if csv_file and pdbs_folder:
                # Read the CSV file
                df = pd.read_csv(csv_file)

                # Extract the necessary columns: pae_interaction (3rd), plddt_binder (5th), name (9th)
                df_filtered = df[[df.columns[2], df.columns[4], df.columns[8]]]
                df_filtered.columns = ['pae_interaction', 'plddt_binder', 'design_name']

                # Filter designs with plddt_binder > 80
                #df_filtered = df_filtered[df_filtered['plddt_binder'] > args.plddt]

                # Sort by pae_interaction (ascending)
                df_filtered = df_filtered.sort_values(by='pae_interaction')

                # Select the top 10 designs, considering different backbones
                selected_designs = []
                seen_backbones = set()

                for _, row in df_filtered.iterrows():
                    design_name = row['design_name']
                    pae_interaction = row['pae_interaction']
                    
                    # Extract the backbone from the design_name (split by "dldesign" and take the first part)
                    backbone = design_name.split("dldesign")[0]

                    # Check if a design with the same backbone already exists in selected_designs
                    existing_design = next((design for design in selected_designs if backbone in design['design_name']), None)

                    if existing_design is not None:
                        # Compare pae_interaction values and keep the one with the lowest value
                        if pae_interaction < existing_design['pae_interaction']:
                            selected_designs.remove(existing_design)
                            selected_designs.append(row)
                    else:
                        # If no design with the same backbone exists, add this design
                        selected_designs.append(row)                        

                    # Stop when 10 designs are selected
                    if len(selected_designs) >= args.d:
                        break

                # Convert the selected designs to a DataFrame
                top_designs = pd.DataFrame(selected_designs)
                
                # Create a separate folder for each protein design inside the output folder
                protein_output_folder = os.path.join(output_folder, protein_folder)
                if not os.path.exists(protein_output_folder):
                    os.makedirs(protein_output_folder)

                # Prepare the output CSV file path
                output_csv_file = os.path.join(protein_output_folder, f"top_10_designs.csv")

                # Save the top 10 designs to the output CSV file
                top_designs.to_csv(output_csv_file, index=False)

                # Create a folder to store the PDB files for the top designs inside the protein folder
                top_pdbs_folder = os.path.join(protein_output_folder, "pdbs")
                if not os.path.exists(top_pdbs_folder):
                    os.makedirs(top_pdbs_folder)
                
                # Copy the corresponding PDB files to the output folder
                for design_name in top_designs['design_name']:
                    pdb_file = os.path.join(pdbs_folder, f"{design_name}.pdb")
                    if os.path.exists(pdb_file):
                        shutil.copy(pdb_file, top_pdbs_folder)
                    else:
                        print(f"PDB file {pdb_file} not found.")

                # Additional processing for minibinders with pae_interaction < 7
                minibinders = df_filtered[(df_filtered['pae_interaction'] < args.ipae) & (df_filtered['plddt_binder'] > args.plddt)]
                print(args.ipae)
                print(args.plddt)
                # Append minibinders to the list
                minibinders_list.append(minibinders)
                
                # Copy corresponding PDB files for minibinders
                for design_name in minibinders['design_name']:
                    pdb_file = os.path.join(pdbs_folder, f"{design_name}.pdb")
                    if os.path.exists(pdb_file):
                        shutil.copy(pdb_file, minibinders_pdbs_folder)
                    else:
                        print(f"Minibinder PDB file {pdb_file} not found.")
                


    # Concatenate all minibinders and prepare for saving to CSV
    if minibinders_list:
        minibinders_combined = pd.concat(minibinders_list)
        minibinders_csv_file = os.path.join(minibinders_folder, "minibinders_to_validate.csv")

        # Check if the CSV file exists, append if it does, otherwise create a new file
        if os.path.exists(minibinders_csv_file):
            minibinders_combined.to_csv(minibinders_csv_file, mode='a', header=False, index=False)
        else:
            minibinders_combined.to_csv(minibinders_csv_file, index=False)

def select_top_minibinders(input_folder):
    # List to store top minibinders from all subfolders
    all_minibinders = []

    # Recursively walk through the input folder
    for root, dirs, files in os.walk(input_folder):
        # Check if the current directory contains a csv file and a 'pdbs' folder
        csv_files = [f for f in files if f.endswith('.csv')]
        if 'pdbs' in dirs and csv_files:
            csv_file_path = os.path.join(root, csv_files[0])
            pdbs_folder_path = os.path.join(root, 'pdbs')
            
            # Read the CSV file
            try:
                df = pd.read_csv(csv_file_path)
                
                # Check if required columns exist
                if {'pae_interaction', 'plddt_binder', 'design_name'}.issubset(df.columns):
                    # Sort by 'pae_interaction' and select the top 10 rows
                    top_minibinders = df.nsmallest(args.d, 'pae_interaction')
                    
                    # Add folder path to design_name for PDB lookup
                    top_minibinders['folder_path'] = pdbs_folder_path
                    all_minibinders.append(top_minibinders)
                else:
                    print(f"Required columns missing in {csv_file_path}. Skipping.")
            except Exception as e:
                print(f"Error reading {csv_file_path}: {e}")

    # Combine top minibinders from all subfolders
    if all_minibinders:
        combined_top_minibinders = pd.concat(all_minibinders, ignore_index=True)
        final_top_minibinders = combined_top_minibinders.nsmallest(args.d, 'pae_interaction')
        
        # Create the TOP10 directory
        top10_dir = os.path.join(input_folder, 'TOP10')
        os.makedirs(top10_dir, exist_ok=True)
        
        # Save the CSV file
        output_csv_path = os.path.join(top10_dir, 'top10_minibinders.csv')
        final_top_minibinders[['pae_interaction', 'plddt_binder', 'design_name']].to_csv(output_csv_path, index=False)
        
        # Copy the corresponding PDB files
        top_pdbs_dir = os.path.join(top10_dir, 'pdbs')
        os.makedirs(top_pdbs_dir, exist_ok=True)
        
        for _, row in final_top_minibinders.iterrows():
            pdb_file_name = f"{row['design_name']}.pdb"
            pdb_file_path = os.path.join(row['folder_path'], pdb_file_name)
            if os.path.exists(pdb_file_path):
                shutil.copy(pdb_file_path, top_pdbs_dir)
            else:
                print(f"PDB file not found: {pdb_file_path}")
        
        print(f"TOP10 minibinders and corresponding PDB files saved in {top10_dir}.")
    else:
        print("No minibinders found in the input folder.")


if __name__ == "__main__":
    # Argument parsing for the round number
    parser = argparse.ArgumentParser(description='Process protein designs and output top designs and minibinders.')
    parser.add_argument('-rn', type=int, help='The round number for this execution')
    parser.add_argument('-r', type=int, help='The round number for this execution', default=5)
    parser.add_argument("-m", type=int, help="Number of minibinders required.", default=10)
    parser.add_argument("-d", type=int, help="Number of desings going to the next partial diffusion round.", default=10)
    parser.add_argument("-ipae", type=float, help="ipAE threshold.", default=10)
    parser.add_argument("-plddt", type=float, help="pLDDT threshold.", default=30)
    parser.add_argument("-hs", type=str, help="Hotspots. e.g., A23, A45", default= False)
    parser.add_argument("-sc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=175)
    parser.add_argument("-seq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 5)
    parser.add_argument("-psc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=5)
    parser.add_argument("-pseq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 10)

    args = parser.parse_args()

    
    # Input folder containing the protein designs
    print(os.getcwd())
    input_folder = "best_designs"  # Replace with your folder path

    # Output folder for top 10 designs
    output_folder = "top10binders"

    # Minibinders folder outside the top 10 folder
    minibinders_folder = "minibinders_to_validate"

    # Process the protein designs
    process_protein_designs(input_folder, output_folder, minibinders_folder)
    select_top_minibinders(output_folder)
