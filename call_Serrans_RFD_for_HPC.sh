#!/bin/bash
# ============================================================================
# LSF submit script for Serrans_RFD.
#
#   1. Edit config.sh so it points at your RFdiffusion / ProteinMPNN / AF2.
#   2. Edit the #BSUB lines below for your cluster (queue name especially).
#   3. Put your target PDB file(s) in targets/.
#   4. Set SCRIPT_ARGS below, then:  bsub < call_Serrans_RFD_for_HPC.sh
#
# On a SLURM cluster, replace the #BSUB block with the equivalent #SBATCH
# directives; nothing below the "do not modify" line needs to change.
# ============================================================================

### -- queue (CHANGE THIS to a GPU queue on your cluster) --
#BSUB -q cabgpu
### -- job name --
#BSUB -J serrans_rfd
### -- number of cores --
#BSUB -n 8
### -- one GPU in exclusive process mode --
#BSUB -gpu "num=1:mode=exclusive_process"
### -- walltime limit, hh:mm --
#BSUB -W 150:00
### -- system memory --
#BSUB -R "rusage[mem=10GB]"
### -- email address for notifications (uncomment and fill in to use) --
##BSUB -u your.email@example.com
### -- notify at start and at completion --
#BSUB -B
#BSUB -N
### -- output and error files; %J is the job id --
#BSUB -o std/gpu_%J.out
#BSUB -e std/gpu_%J.err
# -- end of LSF options --


####################################################################
# Pipeline arguments
####################################################################
# -r     Maximum number of partial diffusion rounds.              (default 3)
# -m     Number of minibinders required before stopping.           (default 100)
# -d     Designs carried into the next partial diffusion round.    (default 10)
# -ipae  ipAE (pae_interaction) threshold a design must beat.      (default 10)
# -plddt pLDDT threshold a design must beat.                       (default 90)
# -hs    Hotspots, e.g. A23,A45 (no spaces). "False" to let
#        RFdiffusion choose the interface.                         (default False)
# -sc    Scaffolds from RFdiffusion in round 0.                    (default 175)
# -seq   Sequences per scaffold from ProteinMPNN in round 0.       (default 5)
# -psc   Scaffolds per parent in the partial diffusion rounds.     (default 5)
# -pseq  Sequences per scaffold in the partial diffusion rounds.   (default 10)
#
# For example:
# SCRIPT_ARGS="-r 5 -m 10 -d 7 -ipae 6 -plddt 95 -hs A27 -sc 200 -seq 10 -psc 10 -pseq 15"

SCRIPT_ARGS="-r 5 -m 200 -d 10 -ipae 7 -plddt 90 -sc 150 -seq 5 -psc 10 -pseq 5"


####################################################################
# Do not modify anything after this line
####################################################################
set -eo pipefail

SERRANS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SERRANS_ROOT"

# shellcheck disable=SC1091
source "$SERRANS_ROOT/config.sh"

mkdir -p std

# Activate the Python environment the orchestrator runs in (needs pandas).
if [ -n "$SERRANS_ENV_MAIN" ]; then
    serrans_activate "$SERRANS_ENV_MAIN"
fi

PYTHON_FILE="Serrans_RFD.py"

echo "Running: python3 $PYTHON_FILE $SCRIPT_ARGS"
# SCRIPT_ARGS is intentionally unquoted so it splits into separate arguments.
# shellcheck disable=SC2086
status=0
python3 "$PYTHON_FILE" $SCRIPT_ARGS || status=$?

if [ $status -eq 0 ]; then
    echo "Script executed successfully."
else
    echo "Script execution failed with exit code $status."
fi
exit $status
