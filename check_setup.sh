#!/bin/bash
# ---------------------------------------------------------------------------
# Check that config.sh points at a working installation before you queue a
# multi-day job. Run this on a compute node (or an interactive GPU session):
#
#     ./check_setup.sh
#
# It loads each tool the way the pipeline does and reports what it finds.
# ---------------------------------------------------------------------------

SERRANS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SERRANS_ROOT/config.sh"

problems=0

ok()   { echo "  [ ok ] $1"; }
bad()  { echo "  [FAIL] $1"; problems=$((problems + 1)); }
warn() { echo "  [warn] $1"; }

echo "Serrans_RFD setup check"
echo "======================="
echo "Repository: $SERRANS_ROOT"
echo "Mode:       $SERRANS_MODE"
echo

# --- config.sh sanity --------------------------------------------------------
echo "1. Configuration"
if [ "$SERRANS_MODE" = "module" ]; then
    if [ -z "$SERRANS_MODULE_INIT" ]; then
        warn "SERRANS_MODULE_INIT is empty; relying on 'module' already working."
    elif [ -f "$SERRANS_MODULE_INIT" ]; then
        ok "module init script found: $SERRANS_MODULE_INIT"
    else
        bad "module init script missing: $SERRANS_MODULE_INIT"
    fi
elif [ "$SERRANS_MODE" = "path" ]; then
    for var in SERRANS_RFDIFFUSION_BIN SERRANS_DL_BINDER_DESIGN_BIN \
               SERRANS_SILENT_TOOLS_BIN SERRANS_AF2_BIN; do
        dir="${!var}"
        if [ -z "$dir" ]; then
            bad "$var is not set (required in path mode)."
        elif [ -d "$dir" ]; then
            ok "$var -> $dir"
        else
            bad "$var points at a missing directory: $dir"
        fi
    done
else
    bad "SERRANS_MODE must be 'module' or 'path', got '$SERRANS_MODE'."
fi
echo

# --- tools -------------------------------------------------------------------
# Each tool is loaded in a subshell so the loads do not interfere, and the
# result is written to a temp file (a pipe would lose the problem counter).
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

check_tool() {
    local tool="$1"; shift
    local optional=0
    if [ "$1" = "--optional" ]; then optional=1; shift; fi

    (
        serrans_init_modules
        serrans_load "$tool"
        for exe in "$@"; do
            if command -v "$exe" >/dev/null 2>&1; then
                echo "OK|$exe|$(command -v "$exe")"
            else
                echo "MISSING|$exe|"
            fi
        done
    ) >"$tmp" 2>/dev/null

    if [ ! -s "$tmp" ]; then
        if [ "$optional" -eq 1 ]; then
            warn "could not load '$tool' (optional)."
        else
            bad "could not load '$tool'. Check config.sh."
        fi
        return
    fi

    while IFS='|' read -r status exe path; do
        [ -z "$exe" ] && continue
        if [ "$status" = "OK" ]; then
            ok "$exe -> $path"
        elif [ "$optional" -eq 1 ]; then
            warn "$exe not found after loading '$tool' (optional)."
        else
            bad "$exe not found after loading '$tool'."
        fi
    done <"$tmp"
}

echo "2. Tools"
echo "   RFdiffusion:"
check_tool rfdiffusion run_inference.py
echo "   ProteinMPNN / dl_binder_design (also provides the silent tools):"
check_tool dl_binder_design dl_interface_design.py silentfrompdbs silentextractspecific
echo "   AlphaFold2 initial guess:"
check_tool af2 predict.py
echo "   ColabFold (only for the optional extract_ptm_metrics.py step):"
check_tool colabfold --optional colabfold_batch
echo

# --- python ------------------------------------------------------------------
echo "3. Python environment for Serrans_RFD.py"
if [ -n "$SERRANS_ENV_MAIN" ]; then
    echo "   SERRANS_ENV_MAIN = $SERRANS_ENV_MAIN"
fi
if ( serrans_activate "$SERRANS_ENV_MAIN" >/dev/null 2>&1
     python3 -c "import pandas" >/dev/null 2>&1 ); then
    ok "python3 with pandas available"
else
    bad "python3 cannot import pandas in SERRANS_ENV_MAIN."
fi
echo

# --- inputs ------------------------------------------------------------------
echo "4. Inputs"
if [ -d "$SERRANS_ROOT/targets" ]; then
    count=$(find "$SERRANS_ROOT/targets" -maxdepth 1 -name '*.pdb' | wc -l)
    if [ "$count" -gt 0 ]; then
        ok "$count target PDB file(s) in targets/"
    else
        bad "targets/ contains no .pdb files."
    fi
else
    bad "targets/ folder not found."
fi
echo

# --- GPU ---------------------------------------------------------------------
echo "5. GPU"
if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 | grep -q .; then
        ok "GPU visible: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
    else
        warn "nvidia-smi found but no GPU reported. Run this on a GPU node."
    fi
else
    warn "nvidia-smi not found. Run this on a GPU node."
fi
echo

echo "======================="
if [ "$problems" -eq 0 ]; then
    echo "No blocking problems found. You can submit the job."
else
    echo "$problems problem(s) found. Fix config.sh before submitting."
    exit 1
fi
