"""The shared command-line interface for every pipeline step.

Each step used to carry its own near-identical copy of this argument parser,
with defaults that quietly disagreed with each other. The orchestrator always
passes every argument explicitly, so the defaults below are documentation of
the recommended values rather than something the pipeline relies on.
"""

import argparse

# Recommended defaults, also quoted in the README and the submit script.
DEFAULTS = {
    "rn": 0,
    "r": 3,
    "m": 100,
    "d": 10,
    "ipae": 10.0,
    "plddt": 90.0,
    "hs": "False",
    "sc": 175,
    "seq": 5,
    "psc": 5,
    "pseq": 10,
}

HELP = {
    "rn": "Current round number (set by the orchestrator).",
    "r": "Maximum number of partial diffusion rounds.",
    "m": "Number of minibinders required before the pipeline stops.",
    "d": "Number of designs carried into the next partial diffusion round.",
    "ipae": "ipAE (pae_interaction) threshold a design must beat.",
    "plddt": "pLDDT threshold a design must beat.",
    "hs": "Hotspots, e.g. A23,A45 (no spaces). 'False' to let RFdiffusion choose.",
    "sc": "Number of scaffolds produced by RFdiffusion in round 0.",
    "seq": "Sequences per scaffold from ProteinMPNN in round 0.",
    "psc": "Scaffolds per parent in the partial diffusion rounds.",
    "pseq": "Sequences per scaffold from ProteinMPNN in the partial diffusion rounds.",
}

_TYPES = {
    "rn": int, "r": int, "m": int, "d": int,
    "ipae": float, "plddt": float,
    "hs": str,
    "sc": int, "seq": int, "psc": int, "pseq": int,
}


def build_parser(description="A Serrans_RFD pipeline step.", **overrides):
    """Build the standard parser. Pass e.g. ipae=40 to override one default."""
    parser = argparse.ArgumentParser(description=description)
    for name, default in DEFAULTS.items():
        parser.add_argument(
            f"-{name}",
            type=_TYPES[name],
            default=overrides.get(name, default),
            help=HELP[name],
        )
    return parser


def parse(description="A Serrans_RFD pipeline step.", **overrides):
    return build_parser(description, **overrides).parse_args()


def as_cli_args(args, exclude=()):
    """Turn a parsed namespace back into a flag list for a child process."""
    out = []
    for name in DEFAULTS:
        if name in exclude:
            continue
        out += [f"-{name}", str(getattr(args, name))]
    return out
