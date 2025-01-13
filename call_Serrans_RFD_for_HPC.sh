#!/bin/sh
### General options
### –- specify queue --
#BSUB -q cabgpu
### -- set the job Name --
#BSUB -J Serrans_RFD_Amylin-1
### -- ask for number of cores (default: 1) --
#BSUB -n 8
### -- Select the resources: 1 gpu in exclusive process mode --
#BSUB -gpu "num=1:mode=exclusive_process"
### -- set walltime limit: hh:mm --
#BSUB -W 150:00
# request 5GB of system-memory
#BSUB -R "rusage[mem=10GB]"
### -- set the email address --
# please uncomment the following line and put in your e-mail address,
# if you want to receive e-mail notifications on a non-default address
#BSUB -u diruespi@gmail.com
### -- send notification at start --
#BSUB -B
### -- send notification at completion--
#BSUB -N
### -- Specify the output and error file. %J is the job-id --
### -- -o and -e mean append, -oo and -eo mean overwrite --
#BSUB -o std/gpu_%J.out
#BSUB -e std/gpu_%J.err
# -- end of LSF options --

# Change RUN_ID to keep track of files/runs
#!/bin/bash

source /dtu/projects/RFdiffusion/netMHCpan/envs/VALENTIA/bin/activate



####################################################################
# Define the arguments here.
#ARGUMENTS:
# "-r", type=int, help="Number of partial diffusion rounds.", default=3
# "-m", type=int, help="Number of minibinders required.", default=100
# "-d", type=int, help="Number of desings going to the next partial diffusion round.", default=10
# "-ipae", type=float, help="ipAE threshold.", default=10
# "-plddt", type=float, help="pLDDT threshold.", default=90
# "-hs", type=str, help="Hotspots. e.g., A23,A45 (no spaces in between).", default="A4,A7"
# "-sc", type=int, help="Number of scaffolds produced by RFDiffusion.", default=175
# "-seq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN", default= 5
# "-psc", type=int, help="Number of scaffolds produced by RFDiffusion in partial diffusion steps.", default=5
# "-pseq", type=int, help="Number of sequences per scaffold produced by ProteinMPNN in partial diffusion steps", default= 10

#For example:
#SCRIPT_ARGS="Serrans_RFD.py -r 5 -m 10 -d 7 -ipae 6 -plddt 95 -hs A27 -sc 200 -seq 10 -psc 10 -pseq 15"

# Define the arguments to be passed to the script (leave empty if no arguments)
SCRIPT_ARGS="-r 5 -m 200 -d 10 -ipae 7 -plddt 90 -sc 150 -seq 5 -psc 10 -pseq 5"




####################################################################
#Do not modify anything after this line
####################################################################

PYTHON_FILE="Serrans_RFD.py"


# Debugging: Print the command being executed
if [[ -z "$SCRIPT_ARGS" ]]; then
    echo "Executing Python script without arguments: $PYTHON_FILE"
    python "$PYTHON_FILE"
else
    echo "Executing Python script with arguments: $PYTHON_FILE $SCRIPT_ARGS"
    python "$PYTHON_FILE" $SCRIPT_ARGS
fi

# Check the exit status of the python command
if [[ $? -eq 0 ]]; then
    echo "Script executed successfully."
else
    echo "Script execution failed with an error."
fi
