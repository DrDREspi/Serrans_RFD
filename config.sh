#!/bin/bash
# ============================================================================
# Serrans_RFD site configuration
# ============================================================================
# This is the ONLY file you need to edit to run the pipeline on your own HPC.
# Point the variables below at your installations of RFdiffusion, ProteinMPNN
# (via dl_binder_design) and AlphaFold2, then run ./check_setup.sh to verify.
#
# Two ways to make the tools available are supported:
#
#   MODULE mode  - your cluster provides environment modules (module load ...).
#                  This is how the pipeline was originally developed (DTU).
#   PATH mode    - you installed the tools yourself and want to activate a
#                  conda env and add the install directories to PATH.
#
# Set SERRANS_MODE below to pick one. You can also mix them: any module name
# left empty is skipped, and any *_BIN directory you set is added to PATH.
# ============================================================================

# ---------------------------------------------------------------------------
# 1. Which mechanism to use: "module" or "path"
# ---------------------------------------------------------------------------
SERRANS_MODE="${SERRANS_MODE:-module}"

# ---------------------------------------------------------------------------
# 2. MODULE mode settings
# ---------------------------------------------------------------------------
# Script that initialises the module system / shared paths on your cluster.
# Leave empty if `module` already works in a non-interactive shell.
SERRANS_MODULE_INIT="${SERRANS_MODULE_INIT:-/dtu/projects/RFdiffusion/setup.sh}"

# Module names for each tool. Leave a value empty to skip loading it.
SERRANS_MOD_RFDIFFUSION="${SERRANS_MOD_RFDIFFUSION:-RFdiffusion}"
SERRANS_MOD_DL_BINDER_DESIGN="${SERRANS_MOD_DL_BINDER_DESIGN:-DL_binder_design}"
SERRANS_MOD_PROTEINMPNN="${SERRANS_MOD_PROTEINMPNN:-proteinmpnn}"
SERRANS_MOD_AF2="${SERRANS_MOD_AF2:-af2_binder_design}"
SERRANS_MOD_COLABFOLD="${SERRANS_MOD_COLABFOLD:-colabfold/1.5.6}"

# ---------------------------------------------------------------------------
# 3. PATH mode settings
# ---------------------------------------------------------------------------
# Directories holding the executables the pipeline calls. For example:
#   SERRANS_RFDIFFUSION_BIN=/home/me/software/RFdiffusion/scripts
#     -> must contain run_inference.py
#   SERRANS_DL_BINDER_DESIGN_BIN=/home/me/software/dl_binder_design/mpnn_fr
#     -> must contain dl_interface_design.py
#   SERRANS_SILENT_TOOLS_BIN=/home/me/software/dl_binder_design/include/silent_tools
#     -> must contain silentfrompdbs, silentextract, silentextractspecific
#   SERRANS_AF2_BIN=/home/me/software/dl_binder_design/af2_initial_guess
#     -> must contain predict.py
SERRANS_RFDIFFUSION_BIN="${SERRANS_RFDIFFUSION_BIN:-}"
SERRANS_DL_BINDER_DESIGN_BIN="${SERRANS_DL_BINDER_DESIGN_BIN:-}"
SERRANS_SILENT_TOOLS_BIN="${SERRANS_SILENT_TOOLS_BIN:-}"
SERRANS_AF2_BIN="${SERRANS_AF2_BIN:-}"
SERRANS_COLABFOLD_BIN="${SERRANS_COLABFOLD_BIN:-}"

# Conda / venv environments to activate per tool. Give either a conda env name
# (needs SERRANS_CONDA_SH set) or the full path to a venv activate script.
# RFdiffusion and dl_binder_design usually need different environments.
SERRANS_CONDA_SH="${SERRANS_CONDA_SH:-}"            # e.g. /opt/miniconda3/etc/profile.d/conda.sh
SERRANS_ENV_RFDIFFUSION="${SERRANS_ENV_RFDIFFUSION:-}"   # e.g. SE3nv
SERRANS_ENV_DL_BINDER_DESIGN="${SERRANS_ENV_DL_BINDER_DESIGN:-}"  # e.g. dlbinder
SERRANS_ENV_AF2="${SERRANS_ENV_AF2:-}"
SERRANS_ENV_COLABFOLD="${SERRANS_ENV_COLABFOLD:-}"

# ---------------------------------------------------------------------------
# 4. Environment for the top-level orchestrator (Serrans_RFD.py)
# ---------------------------------------------------------------------------
# A Python environment with pandas available. Full path to an activate script,
# or a conda env name if SERRANS_CONDA_SH is set. Leave empty to use whatever
# python3 is already on PATH.
SERRANS_ENV_MAIN="${SERRANS_ENV_MAIN:-/dtu/projects/RFdiffusion/netMHCpan/envs/VALENTIA/bin/activate}"

# ---------------------------------------------------------------------------
# 5. Pipeline behaviour (safe to leave alone)
# ---------------------------------------------------------------------------
# Binder length range sampled by RFdiffusion, appended to the contig string.
SERRANS_BINDER_LENGTH="${SERRANS_BINDER_LENGTH:-100-150}"
# partial_T for the partial diffusion rounds: lower = stay closer to the parent.
SERRANS_PARTIAL_T="${SERRANS_PARTIAL_T:-25}"
# Loose pae_interaction cut applied when pulling PDBs out of the silent files.
# The strict per-design cut is the -ipae argument of the pipeline.
SERRANS_PREFILTER_PAE="${SERRANS_PREFILTER_PAE:-30}"

# ============================================================================
# Loader functions - used by the pipeline, no need to edit below this line
# ============================================================================

serrans_init_modules() {
    if [ "$SERRANS_MODE" = "module" ] && [ -n "$SERRANS_MODULE_INIT" ]; then
        if [ -f "$SERRANS_MODULE_INIT" ]; then
            # shellcheck disable=SC1090
            source "$SERRANS_MODULE_INIT"
        else
            echo "ERROR: SERRANS_MODULE_INIT not found: $SERRANS_MODULE_INIT" >&2
            echo "       Edit config.sh (see section 2)." >&2
            return 1
        fi
    fi
}

# serrans_activate <env>  - activate a conda env name or a venv activate script
serrans_activate() {
    local env="$1"
    [ -z "$env" ] && return 0
    if [ -f "$env" ]; then
        # shellcheck disable=SC1090
        source "$env"
    elif [ -n "$SERRANS_CONDA_SH" ] && [ -f "$SERRANS_CONDA_SH" ]; then
        # shellcheck disable=SC1090
        source "$SERRANS_CONDA_SH"
        conda activate "$env" || return 1
    else
        echo "ERROR: cannot activate '$env'." >&2
        echo "       It is not a file, and SERRANS_CONDA_SH is unset or missing." >&2
        return 1
    fi
}

# serrans_add_path <dir> - prepend a directory to PATH if it exists
serrans_add_path() {
    local dir="$1"
    [ -z "$dir" ] && return 0
    if [ -d "$dir" ]; then
        export PATH="$dir:$PATH"
    else
        echo "WARNING: directory not found, not added to PATH: $dir" >&2
    fi
}

# serrans_load <tool> - make one tool available. tool is one of:
#   rfdiffusion | dl_binder_design | proteinmpnn | af2 | colabfold
serrans_load() {
    local tool="$1"
    local mod env bin

    case "$tool" in
        rfdiffusion)
            mod="$SERRANS_MOD_RFDIFFUSION"
            env="$SERRANS_ENV_RFDIFFUSION"
            bin="$SERRANS_RFDIFFUSION_BIN" ;;
        dl_binder_design|proteinmpnn)
            # Both the MPNN and the silent-tools steps live in dl_binder_design.
            # proteinmpnn is kept as a separate module name because some sites
            # (including DTU) expose it that way.
            if [ "$tool" = "proteinmpnn" ]; then
                mod="$SERRANS_MOD_PROTEINMPNN"
            else
                mod="$SERRANS_MOD_DL_BINDER_DESIGN"
            fi
            env="$SERRANS_ENV_DL_BINDER_DESIGN"
            bin="$SERRANS_DL_BINDER_DESIGN_BIN" ;;
        af2)
            mod="$SERRANS_MOD_AF2"
            env="$SERRANS_ENV_AF2"
            bin="$SERRANS_AF2_BIN" ;;
        colabfold)
            mod="$SERRANS_MOD_COLABFOLD"
            env="$SERRANS_ENV_COLABFOLD"
            bin="$SERRANS_COLABFOLD_BIN" ;;
        *)
            echo "ERROR: serrans_load: unknown tool '$tool'" >&2
            return 1 ;;
    esac

    if [ "$SERRANS_MODE" = "module" ]; then
        [ -n "$mod" ] && { module load "$mod" || return 1; }
    else
        serrans_activate "$env" || return 1
        serrans_add_path "$bin"
        # silent_tools is needed alongside every structure-handling step
        serrans_add_path "$SERRANS_SILENT_TOOLS_BIN"
    fi
}

# serrans_unload - drop the currently loaded tool so the next one is clean
serrans_unload() {
    if [ "$SERRANS_MODE" = "module" ]; then
        module purge
    elif [ -n "$SERRANS_CONDA_SH" ] && command -v conda >/dev/null 2>&1; then
        conda deactivate 2>/dev/null || true
    fi
}
