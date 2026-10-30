# Serrans_RFD

Versatile automated pipeline for de novo minibinder design.

Serrans_RFD chains **RFdiffusion**, **ProteinMPNN** and **AlphaFold2** into a
closed loop: it designs small protein binders against a target, scores them,
keeps the best ones, and feeds those back into RFdiffusion as partial
diffusion seeds. The loop repeats until it has collected enough minibinders
that pass your quality thresholds, or until it runs out of rounds.

The output is a table of designed binder sequences with their AF2 scores,
plus the structures.

---

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Setup](#setup)
- [Running the pipeline](#running-the-pipeline)
- [Arguments](#arguments)
- [Output](#output)
- [Optional: ColabFold actifpTM scoring](#optional-colabfold-actifptm-scoring)
- [Repository layout](#repository-layout)
- [Troubleshooting](#troubleshooting)
- [Citing the underlying tools](#citing-the-underlying-tools)

---

## How it works

```
targets/*.pdb
     |
     v
  ROUND 0  ................................ de novo design
     RFdiffusion     generate -sc binder backbones against the target
     ProteinMPNN     design -seq sequences per backbone
     AlphaFold2      predict each complex, score pae_interaction / pLDDT
     filter          keep designs under the prefilter ipAE cut
     select          best design per backbone -> top -d parents
     |
     v
  PARTIAL DIFFUSION ROUND (repeated up to -r times)
     RFdiffusion     re-diffuse each parent (-psc each, partial_T=25)
     ProteinMPNN     redesign sequences (-pseq each)
     AlphaFold2      predict and re-score
     filter + select new parents for the next round
     |
     +--> any design with ipAE < -ipae AND pLDDT > -plddt
          is banked in minibinders_to_validate/
     |
     v
  stop when >= -m minibinders are banked, or -r rounds are done
     |
     v
  extract binder sequences -> minibinders_to_validate_seqs.csv
```

Partial diffusion is the point of the loop: rather than sampling new binders
from scratch every time, each round perturbs designs that already scored well,
so the search concentrates around promising backbones.

---

## Requirements

- An HPC cluster with at least one **GPU** node (an A100/V100-class card is
  comfortable; the pipeline runs for many hours to days).
- **RFdiffusion** — provides `run_inference.py`
- **dl_binder_design** — provides `dl_interface_design.py` (the ProteinMPNN
  interface design wrapper), `predict.py` (AF2 initial guess), and the
  **silent tools** (`silentfrompdbs`, `silentextract`,
  `silentextractspecific`)
- **Python 3** with `pandas` for the orchestrator
- Optional: **ColabFold** with `--calc-extra-ptm` support, only for the extra
  scoring step
- Optional: **Biopython**, only for the extra scoring step

> The pipeline calls ProteinMPNN and AlphaFold2 through
> [dl_binder_design](https://github.com/nrbennet/dl_binder_design), not
> directly. If you do not have dl_binder_design installed, install it first —
> its `mpnn_fr/dl_interface_design.py` and `af2_initial_guess/predict.py`
> entry points are what Serrans_RFD expects.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/DrDREspi/Serrans_RFD.git
cd Serrans_RFD
```

### 2. Point `config.sh` at your installations

**`config.sh` is the only file you need to edit.** All site-specific paths
live there; nothing else in the repository hardcodes a location.

It supports two mechanisms, chosen with `SERRANS_MODE`:

#### Module mode (`SERRANS_MODE="module"`)

Use this if your cluster exposes the tools as environment modules. This is how
the pipeline was originally developed, at DTU:

```bash
SERRANS_MODE="module"
SERRANS_MODULE_INIT="/dtu/projects/RFdiffusion/setup.sh"   # or "" if `module` just works
SERRANS_MOD_RFDIFFUSION="RFdiffusion"
SERRANS_MOD_DL_BINDER_DESIGN="DL_binder_design"
SERRANS_MOD_PROTEINMPNN="proteinmpnn"
SERRANS_MOD_AF2="af2_binder_design"
SERRANS_MOD_COLABFOLD="colabfold/1.5.6"
```

Replace the module names with whatever your cluster calls them. Leave any
value empty to skip that `module load`.

#### Path mode (`SERRANS_MODE="path"`)

Use this if you installed the tools yourself. Give the directories holding the
executables, and the conda environments to activate:

```bash
SERRANS_MODE="path"

SERRANS_RFDIFFUSION_BIN="/home/me/software/RFdiffusion/scripts"
SERRANS_DL_BINDER_DESIGN_BIN="/home/me/software/dl_binder_design/mpnn_fr"
SERRANS_SILENT_TOOLS_BIN="/home/me/software/dl_binder_design/include/silent_tools"
SERRANS_AF2_BIN="/home/me/software/dl_binder_design/af2_initial_guess"
SERRANS_COLABFOLD_BIN=""                      # optional

SERRANS_CONDA_SH="/opt/miniconda3/etc/profile.d/conda.sh"
SERRANS_ENV_RFDIFFUSION="SE3nv"               # RFdiffusion's env
SERRANS_ENV_DL_BINDER_DESIGN="dlbinder"       # dl_binder_design's env
SERRANS_ENV_AF2="dlbinder"
```

RFdiffusion and dl_binder_design normally need **different** conda
environments; that is why they are configured separately. Each tool is
activated only for the step that needs it.

`SERRANS_ENV_*` accepts either a conda environment **name** (requires
`SERRANS_CONDA_SH`) or the full path to a venv `activate` script.

#### The orchestrator's own environment

`Serrans_RFD.py` itself needs `pandas`:

```bash
SERRANS_ENV_MAIN="/path/to/an/env/bin/activate"   # or a conda env name, or "" to use system python3
```

### 3. Verify the setup

```bash
./check_setup.sh
```

**Run this on a GPU node**, not the login node — on many clusters (DTU
included) the GPU modules refuse to load on a login node, so a login-node run
reports false failures.

The script loads each tool exactly the way the pipeline does and reports
whether the executables appear, whether `pandas` imports, whether `targets/`
has PDB files, and whether a GPU is visible. Fix anything it flags before
queueing a multi-day job.

### 4. Add your target

Put the target protein's PDB file in `targets/`. One run processes every
`.pdb` file in that folder.

```bash
cp /path/to/my_target.pdb targets/
```

The repository ships `targets/amylin_1.pdb` as an example — remove it if you
do not want it designed against.

**Target PDB expectations**

- Clean it first: a single biological unit, no waters, no ligands, no
  alternate locations.
- Residue numbering is read straight out of the file, so hotspot numbering
  must match the numbering in your PDB.
- In the designed complexes that come back, **chain A is the binder and
  chain B is the target**.

---

## Running the pipeline

### On LSF

Edit the `#BSUB` block in `call_Serrans_RFD_for_HPC.sh` — the queue name at
minimum — set `SCRIPT_ARGS`, then:

```bash
bsub < call_Serrans_RFD_for_HPC.sh
```

### On SLURM

Replace the `#BSUB` block with the equivalent `#SBATCH` directives. Nothing
below the "do not modify" line needs to change:

```bash
#!/bin/bash
#SBATCH --job-name=serrans_rfd
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=10G
#SBATCH --time=150:00:00
#SBATCH --output=std/gpu_%j.out
#SBATCH --error=std/gpu_%j.err
```

Then `sbatch call_Serrans_RFD_for_HPC.sh`.

### Directly

Always run from the repository root — every path in the pipeline is relative
to it:

```bash
python3 Serrans_RFD.py -r 5 -m 200 -d 10 -ipae 7 -plddt 90 -hs A27 -sc 150 -seq 5 -psc 10 -pseq 5
```

### A short test run first

Before committing to a long job, prove the plumbing works end to end with a
tiny run (minutes to a couple of hours rather than days):

```bash
python3 Serrans_RFD.py -r 1 -m 1 -d 2 -ipae 30 -plddt 50 -sc 4 -seq 2 -psc 2 -pseq 2
```

Loose thresholds and small counts mean designs will actually survive the
filters, so you exercise every step.

---

## Arguments

| Flag | Meaning | Default |
|---|---|---|
| `-r` | Maximum number of partial diffusion rounds | `3` |
| `-m` | Number of minibinders to collect before stopping | `100` |
| `-d` | Designs carried into the next partial diffusion round | `10` |
| `-ipae` | ipAE (`pae_interaction`) threshold a design must beat | `10` |
| `-plddt` | pLDDT threshold a design must beat | `90` |
| `-hs` | Hotspot residues, e.g. `A23,A45` (no spaces). `False` lets RFdiffusion pick the interface | `False` |
| `-sc` | Scaffolds from RFdiffusion in round 0 | `175` |
| `-seq` | Sequences per scaffold from ProteinMPNN in round 0 | `5` |
| `-psc` | Scaffolds per parent in the partial diffusion rounds | `5` |
| `-pseq` | Sequences per scaffold in the partial diffusion rounds | `10` |

A few notes on choosing these:

- **`-hs` is the highest-leverage argument.** Hotspots tell RFdiffusion which
  surface to bind. Without them it picks for itself, which is usually not the
  epitope you care about. Numbering must match your target PDB.
- **`-ipae` is the main quality gate.** `pae_interaction` below ~10 is the
  usual "worth testing" signal, and below ~7 is strong. Raise it to get more
  designs through, lower it to get fewer and better ones.
- **`-sc` x `-seq` sets the round 0 cost.** The default 175 x 5 is 875 AF2
  predictions for round 0 alone.
- **`-m` and `-r` are both stopping conditions** — whichever is reached first
  ends the run.

Behaviour settings that rarely need changing live at the bottom of
`config.sh`: the sampled binder length range (`SERRANS_BINDER_LENGTH`,
default `100-150`), the partial diffusion noise level
(`SERRANS_PARTIAL_T`, default `25`), and the loose prefilter cut used when
unpacking structures (`SERRANS_PREFILTER_PAE`, default `30`).

---

## Output

After a successful run the repository root contains:

```
minibinders_to_validate/
    minibinders_to_validate_seqs.csv   <-- THE RESULT: designs + scores + sequences
    pdbs/                              <-- their structures
TOP10_designs_per_round/
    top10binders/                      <-- round 0 parents
    top10binders_PD1/ ... PDn/         <-- parents selected in each round
Serrans_int_files/
    Serrans_RFD_outputs0/ ... n/       <-- per-round raw scores and filtered designs
std/                                   <-- scheduler logs
```

`minibinders_to_validate_seqs.csv` is the file you want. One row per design:

| Column | Meaning |
|---|---|
| `pae_interaction` | AF2 predicted aligned error across the interface — lower is better |
| `plddt_binder` | AF2 confidence in the binder's own fold — higher is better |
| `design_name` | Identifier, matching the PDB filename in `pdbs/` |
| `sequence` | The designed binder's amino acid sequence (chain A) |

Designs are banked cumulatively as rounds progress, so a single run's table
can contain designs from several rounds.

If the run finds nothing, this file will be missing or empty. That is a real
result, not a crash: it means no design passed both `-ipae` and `-plddt`.
Loosen the thresholds, pick better hotspots, or sample more.

---

## Optional: ColabFold actifpTM scoring

`src/extract_ptm_metrics.py` re-predicts the surviving minibinders with
ColabFold and adds `actifptm`, `ptm` and `iptm` columns. actifpTM is a more
discriminating interface score than ipAE alone.

It is **not** part of the automatic pipeline. Run it afterwards, from the same
directory:

```bash
python3 src/extract_ptm_metrics.py
```

It needs ColabFold configured in `config.sh`, `Biopython`, and a GPU. It
rewrites `minibinders_to_validate/minibinders_to_validate_seqs.csv` in place.

---

## Repository layout

```
config.sh                       all site-specific paths — the only file to edit
check_setup.sh                  verifies config.sh against your cluster
call_Serrans_RFD_for_HPC.sh     LSF submit script
Serrans_RFD.py                  orchestrator: runs the rounds and the loop
targets/                        your target PDB files
Serrans_RFD.pdf                 pipeline diagram
src/
    cli_args.py                 the shared command-line interface
    serrans_config.py           reads config.sh from Python
    pdb_utils.py                PDB parsing and contig string helpers
    run_rf_dif.py               round 0 driver
    RF_diff.sh                  round 0: RFdiffusion -> ProteinMPNN -> AF2
    run_partial_diff_2.py       partial diffusion driver
    partial_diff_2.sh           partial diffusion: RFdiffusion -> MPNN -> AF2
    call_filter_pdbs.py         round 0 filter driver
    filter_pdbs_modified.sh     round 0 filter
    call_filter_pdbs_for_partial_diff.py   partial diffusion filter driver
    filter_pdbs_modified_pd.sh  partial diffusion filter
    selection.py                design ranking and selection logic
    select_best_designs.py      round 0 selection entry point
    select_best_designs_pd.py   partial diffusion selection entry point
    extract_seq.py              final step: add binder sequences to the table
    extract_ptm_metrics.py      optional ColabFold actifpTM scoring
```

The two stages read AF2 score files with slightly different column layouts
(the partial diffusion files carry one extra leading column). That difference
is isolated in `selection.py` as `ROUND0` and `partial_diffusion()`; the rest
of the selection logic is shared.

---

## Troubleshooting

**`check_setup.sh` reports tools missing, but they are installed.**
Run it on a GPU node. Many clusters refuse to load GPU modules on login nodes.

**`run_inference.py: command not found` in the job log.**
`config.sh` is not finding RFdiffusion. In module mode, check the module name
and `SERRANS_MODULE_INIT`. In path mode, check `SERRANS_RFDIFFUSION_BIN` and
that `SERRANS_ENV_RFDIFFUSION` is the right conda environment.

**`silentfrompdbs: command not found`.**
The silent tools ship inside dl_binder_design at
`include/silent_tools`. Point `SERRANS_SILENT_TOOLS_BIN` there, or load the
module that provides them.

**`ModuleNotFoundError: No module named 'pandas'`.**
`SERRANS_ENV_MAIN` is not pointing at an environment with pandas.

**The run finishes but `minibinders_to_validate_seqs.csv` is missing.**
No design passed both thresholds. Check the per-round
`Serrans_int_files/Serrans_RFD_outputs*/best_designs/*/*_filtered_out.csv` to
see how close anything got, then loosen `-ipae` / `-plddt`.

**The job dies partway through.**
Each round's outputs are tidied as it completes, so
`Serrans_int_files/Serrans_RFD_outputs*` shows how far it got. Common causes
are the walltime limit (`#BSUB -W`) and GPU out-of-memory from too large a
target; both mean reducing `-sc` / `-seq` or raising the limits.

**It is far slower than expected.**
Round 0 costs `-sc` x `-seq` AF2 predictions, and each later round costs
`-d` x `-psc` x `-pseq`. The defaults are a multi-day job. Scale down to test.

---

## Citing the underlying tools

Serrans_RFD orchestrates other people's methods. If you publish results from
it, cite them:

- **RFdiffusion** — Watson et al., *De novo design of protein structure and
  function with RFdiffusion*, Nature (2023)
- **ProteinMPNN** — Dauparas et al., *Robust deep learning-based protein
  sequence design using ProteinMPNN*, Science (2022)
- **AlphaFold2** — Jumper et al., *Highly accurate protein structure
  prediction with AlphaFold*, Nature (2021)
- **dl_binder_design / AF2 initial guess** — Bennett et al., *Improving de
  novo protein binder design with deep learning*, Nature Communications (2023)
- **ColabFold** — Mirdita et al., *ColabFold: making protein folding
  accessible to all*, Nature Methods (2022)
- **actifpTM** — Varga & Tusnády, *actifpTM: a refined confidence metric for
  AlphaFold protein complex predictions*, Bioinformatics (2025)

## License

See [LICENSE](LICENSE).
