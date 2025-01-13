import subprocess
import os
import csv
import shutil
import argparse
import stat



def delete_folder(folder_path):
    """Delete a folder and its contents."""
    if os.path.exists(folder_path):
        try:
            # Force delete read-only files
            def remove_readonly(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                func(path)

            print(f"Attempting to delete folder: {folder_path}")
            shutil.rmtree(folder_path, onerror=remove_readonly)
            print(f"Folder '{folder_path}' has been deleted successfully.")
        except Exception as e:
            print(f"Error deleting folder '{folder_path}': {e}")
    else:
        print(f"Folder '{folder_path}' does not exist.")

def move_top10_folders(target_location):
    """
    Moves all folders in the current directory whose names start with 'TOP10' to the specified target location.
    
    Parameters:
        target_location (str): The path to the directory where the folders will be moved.
    """
    # Ensure the target location exists
    os.makedirs(target_location, exist_ok=True)

    # Get the current working directory
    current_dir = os.getcwd()

    # Iterate through items in the current directory
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)

        # Check if the item is a directory and starts with 'TOP10'
        if os.path.isdir(item_path) and item.startswith("top10"):
            target_path = os.path.join(target_location, item)
            shutil.move(item_path, target_path)
            print(f"Moved {item} to {target_location}")
        else:
            print(f"Skipped {item} (not a 'top10' folder)")

def move_serrans_folders(target_location):
    """
    Moves all folders in the current directory whose names start with 'Serrans' to the specified target location.
    
    Parameters:
        target_location (str): The path to the directory where the folders will be moved.
    """
    # Ensure the target location exists
    os.makedirs(target_location, exist_ok=True)

    # Get the current working directory
    current_dir = os.getcwd()

    # Iterate through items in the current directory
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)

        # Check if the item is a directory and starts with 'Serrans'
        if os.path.isdir(item_path) and item.startswith("Serrans") and "int" not in item_path:
            target_path = os.path.join(target_location, item)
            shutil.move(item_path, target_path)
            print(f"Moved {item} to {target_location}")
        else:
            print(f"Skipped {item} (not a 'Serrans' folder)")


def move_folders_to_new_folder(folder_names, new_folder_name):
    """
    Moves specified folders in the current directory to a new folder in the same directory.
    
    Parameters:
        folder_names (list of str): Names of the folders to move.
        new_folder_name (str): Name of the new folder to create and move folders into.
    """
    # Define paths
    current_dir = os.getcwd()
    new_folder_path = os.path.join(current_dir, new_folder_name)
    
    # Ensure the new folder exists
    os.makedirs(new_folder_path, exist_ok=True)
    
    for folder_name in folder_names:
        source_folder_path = os.path.join(current_dir, folder_name)
        target_folder_path = os.path.join(new_folder_path, folder_name)
        
        if os.path.exists(source_folder_path):
            # Move the folder
            shutil.move(source_folder_path, target_folder_path)
            print(f"Moved {folder_name} to {new_folder_name}")
        else:
            print(f"Folder {folder_name} not found in the current directory.")


def validate_hotspots(hotspot_str):
    """
    Validates and processes the hotspots string.
    Ensures that the hotspots are in the correct format: "A23", "B254", etc.
    """
    if hotspot_str:
        # Split by commas and strip extra spaces
        hotspots = [x.strip() for x in hotspot_str.split(",")]
        # Check format for each hotspot (e.g., "A23", "B254")
        for h in hotspots:
            if not h or len(h) < 2 or not h[0].isalpha() or not h[1:].isdigit():
                raise ValueError(f"Invalid hotspot format: {h}. Expected format: Chain + Residue number (e.g., 'A23').")
        return hotspots
    return []

def submit_python_script(script_path, round_num, rounds, minibinders, designs, ipae, plddt, hotspots, scaffolds, sequences, partial_sc, partial_seq):
    try:
        # Convert all arguments to strings
        str_round_num = str(round_num)
        str_rounds = str(rounds)
        str_minibinders = str(minibinders)
        str_designs = str(designs)
        str_ipae = str(ipae)
        str_plddt = str(plddt)
        str_scaffolds = str(scaffolds)
        str_sequences = str(sequences)
        str_partial_sc = str(partial_sc)
        str_partial_seq = str(partial_seq)

        command = [
        "python3", script_path,
        "-rn", str_round_num,
        "-r", str_rounds,
        "-m", str_minibinders,
        "-d", str_designs,  # Designs (flag: -d)
        "-ipae", str_ipae,  # Ipae (flag: -ipae)
        "-plddt", str_plddt,  # Plddt (flag: -plddt)
        "-hs", hotspots,  # Hotspots (flag: -hs)
        "-sc", str_scaffolds,
        "-seq", str_sequences,
        "-psc", str_partial_sc,
        "-pseq", str_partial_seq
        ]

        # Pass the round number as an argument to the script
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        error = result.stderr.decode('utf-8')
        
        if result.returncode != 0:
            raise RuntimeError(f"Error executing {script_path}: {error}")

        print(f"Executed {script_path} successfully (Round {round_num}).")
        print(f"Output: {output}")
        print(f"Error: {error}")
        return output
    except Exception as e:
        print(f"Error executing {script_path}: {e}")
        raise

def run_pipeline_step(script_path, round_num):
    output = submit_python_script(script_path, round_num)
    print(f"Pipeline step for {script_path} (Round {round_num}) completed.")

def count_csv_rows(csv_file_path):
    """
    Counts the number of rows in the given CSV file.
    """
    try:
        with open(csv_file_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            row_count = sum(1 for row in reader) - 1  # Subtract 1 for the header row
        return row_count
    except FileNotFoundError:
        print(f"CSV file {csv_file_path} not found.")
        return 0

def main():
    # Create ArgumentParser object
    parser = argparse.ArgumentParser(description="A script with customizable command-line arguments.")

    # Add arguments
    parser.add_argument("-r", type=int, help="Number of partial diffusion rounds.", default=3)   
    parser.add_argument("-m", type=int, help="Number of minibinders required.", default=100)
    #parser.add_argument("-IN_c", type=float, help="InstaNovo confidence threshold.", default=0.98)
    parser.add_argument("-d", type=int, help="Number of desings going to the next partial diffusion round.", default=7)
    parser.add_argument("-ipae", type=float, help="ipAE threshold.", default=30)
    parser.add_argument("-plddt", type=float, help="pLDDT threshold.", default=40)
    parser.add_argument("-hs", type=str, help="Hotspots. e.g., A23,A45 (no spaces in between).", default="False")
    parser.add_argument("-sc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=2)
    parser.add_argument("-seq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 2)
    parser.add_argument("-psc", type=int, help="Number of scaffolds produced by RFDiffusion in partial diffusion steps.", default=2)
    parser.add_argument("-pseq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN in partial diffusion steps", default= 2)


    #parser.add_argument("-hla", type=str, help="Txt file with patient HLAs.", default= '/zhome/8a/d/184033/DBL001_CD/test_data/patient_HLAs.txt')
    #parser.add_argument("-cancer", type=str, help="Csv file with cancer immunopeptidomics data.", default= '/zhome/8a/d/184033/DBL001_CD/test_data/neodisc.csv')
    #parser.add_argument("-healthy", type=str, help="Csv file with healthy immunopeptidomics data.", default= None)
    #parser.add_argument("-RF", type=str, help="RFDiff-only mode - Folder with targets.", default= False)

    # Parse the arguments
    args = parser.parse_args()

    # Process the hotspots argument
    if args.hs != "False":
        try:
            hotspots = validate_hotspots(args.hs)
            if hotspots:
                print(f"Processing hotspots: {', '.join(hotspots)}")
            else:
                print("No hotspots provided.")
        except ValueError as e:
            print(f"Error: {e}")
            return


    print("Starting the pipeline...")
    
    # Step 1: Run the first step of RFDiffusion
    print("Executing first RFdiffusion step.")
    submit_python_script('src/run_rf_dif.py', 0, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)
    print("Finished first RFdiffusion step.")

    # Step 2: Filter pdbs
    print("Filtering designs from the first RFdiffusion step.")
    submit_python_script('src/call_filter_pdbs.py', 0, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)
    print("Finished filtering designs from the first RFdiffusion step.")


    # Step 3: Select best pdbs
    print("Selecting best designs from the first RFdiffusion step.")
    submit_python_script('src/select_best_designs.py', 0, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)
    print("Finished selecting best designs from the first RFdiffusion step.")
    
    # Output_file: minibinders to validate
    csv_file_path = 'minibinders_to_validate/minibinders_to_validate.csv'
    
    round_num = 0  # Initialize the round number
    print("Round number: ", round_num)
    

    folders_to_move = ["best_designs", "Binder_design_outputs"]
    new_folder_name = f"Serrans_RFD_outputs{round_num}"
    move_folders_to_new_folder(folders_to_move, new_folder_name)
    

    #Loop 
    while True and round_num < args.r:
        print(f"Starting loop for round {round_num}...")
        
        # Step 4: Run partial diffusion
        p_diff_round = round_num+1
        print(f"Executing {p_diff_round} partial diffusion round.")
        submit_python_script('src/run_partial_diff_2.py', round_num, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)
        print(f"Finished {p_diff_round} partial diffusion round.")

        # Step 5: Filter pdbs
        print(f"Filtering designs from the {p_diff_round} partial diffusion round.")
        submit_python_script('src/call_filter_pdbs_for_partial_diff.py', round_num, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)            
        print(f"Finished filtering designs from the {p_diff_round} partial diffusion round.")

        # Increment the round number for the next iteration
        round_num += 1
        print("Round number: ", round_num)


        # Step 6: Select best binders from partial diffusion
        print(f"Selecting best designs from the {p_diff_round} partial diffusion round.")
        submit_python_script('src/select_best_designs_pd.py', round_num, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)
        print(f"Finished selecting best designs from the {p_diff_round} partial diffusion round.")
        
        # Check how many rows are in the CSV file
        row_count = count_csv_rows(csv_file_path)
        print(f"CSV file contains {row_count} rows after round {round_num}.")
        
        #Make output beautiful: move folders around
        folders_to_move = ["best_designs", "Binder_design_outputs"]
        new_folder_name = f"Serrans_RFD_outputs{round_num}"
        move_folders_to_new_folder(folders_to_move, new_folder_name)
        

        # Break the loop if we have 100 or more rows
        if row_count >= args.m:
            print(f"Reached =>{args.m} minibinders to validate. Ending the pipeline loop.")
            break
    
    # Extract aminoacid sequences from minibinders
    submit_python_script('src/extract_seq.py', round_num, args.r, args.m, args.d, args.ipae, args.plddt, args.hs, args.sc, args.seq, args.psc, args.pseq)


    print("Minibinder design pipeline completed.")


if __name__ == "__main__":
    main()
    folder_to_delete = "partial_outputs"
    delete_folder(folder_to_delete)
    folder_to_delete = "RFdiffusion_outputs"
    delete_folder(folder_to_delete)
    folder_to_delete = "outputs"
    delete_folder(folder_to_delete)
    target_directory = "TOP10_designs_per_round"
    move_top10_folders(target_directory)
    target_directory = "Serrans_int_files"
    move_serrans_folders(target_directory) 
