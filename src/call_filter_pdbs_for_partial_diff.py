import os
import subprocess
import argparse

# Argument parsing for the round number
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



# Path to the folder containing the files
folder_path = 'Binder_design_outputs'
# Path to the shell script
shell_script = '../src/filter_pdbs_modified_pd.sh'

os.chdir(folder_path)
print("Round number: ", args.rn)

# Loop through every file in the folder
for filename in os.listdir('.'):
    # Check if the file ends with '_out.sc'
    if filename.endswith('af2pred_out.sc'):
        # Extract the RUN_ID (part of the filename before '_out.sc')
        run_id = filename.split('_out.sc')[0]
        print(run_id)
        
        # Prepare the command
        command = [shell_script, '-r', run_id, '-t', "30"]
        
        # Run the shell script with the appropriate arguments
        try:
            subprocess.run(command, check=True)
            print(f"Successfully ran script for {filename} with RUN_ID {run_id}")
        except subprocess.CalledProcessError as e:
            print(f"Error running script for {filename}: {e}")




