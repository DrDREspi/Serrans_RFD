"""Read config.sh from Python.

config.sh is the single source of truth for site-specific settings. Rather than
duplicating those values here, this module asks bash to source the file and
print the variables back, so the shell scripts and the Python steps can never
drift apart.
"""

import os
import subprocess

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_SH = os.path.join(_REPO_ROOT, "config.sh")

# Variables the Python steps need. Keep in sync with config.sh.
_WANTED = [
    "SERRANS_MODE",
    "SERRANS_MODULE_INIT",
    "SERRANS_MOD_COLABFOLD",
    "SERRANS_ENV_COLABFOLD",
    "SERRANS_COLABFOLD_BIN",
    "SERRANS_BINDER_LENGTH",
    "SERRANS_PARTIAL_T",
    "SERRANS_PREFILTER_PAE",
]

_cache = None


def load():
    """Return the config.sh settings as a dict of strings."""
    global _cache
    if _cache is not None:
        return _cache

    if not os.path.exists(CONFIG_SH):
        raise FileNotFoundError(
            f"config.sh not found at {CONFIG_SH}. Copy it from the repository "
            "and edit it for your cluster."
        )

    script = f'source "{CONFIG_SH}" >/dev/null 2>&1\n'
    for name in _WANTED:
        script += f'printf "%s=%s\\n" "{name}" "${name}"\n'

    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )

    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            values[key] = value
    _cache = values
    return values


def get(name, default=""):
    """Return one setting from config.sh, falling back to default."""
    return load().get(name, default) or default


def repo_root():
    return _REPO_ROOT


def colabfold_command(inner):
    """Wrap a shell command so ColabFold is on PATH when it runs."""
    cfg = load()
    parts = [f'source "{CONFIG_SH}"']
    parts.append("serrans_init_modules")
    parts.append("serrans_load colabfold")
    parts.append(inner)
    return " && ".join(parts)
