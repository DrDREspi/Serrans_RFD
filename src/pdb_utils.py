"""Small PDB helpers shared by the pipeline steps."""

import os

import serrans_config

# Three-letter to one-letter amino acid codes.
AMINO_ACID_CODES = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
    "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
    "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
    "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
}


def get_residue_info(pdb_file):
    """Return {chain: [first_resnum, last_resnum]} for a PDB file, or None."""
    residues = {}
    try:
        with open(pdb_file, "r") as pdb:
            for line in pdb:
                if line.startswith("ATOM"):
                    chain_id = line[21]
                    res_num = int(line[22:26].strip())
                    if chain_id not in residues:
                        residues[chain_id] = [res_num, res_num]
                    else:
                        residues[chain_id][1] = res_num
    except (OSError, ValueError) as e:
        print(f"Error processing file {pdb_file}: {e}")
        return None

    return residues or None


def format_residue_ranges(residues, binder_length=None):
    """Build an RFdiffusion contig string: 'A1-9/0 B1-206/0 100-150'.

    Every chain of the target is held fixed, then a binder of the configured
    length range is diffused de novo.
    """
    if binder_length is None:
        binder_length = serrans_config.get("SERRANS_BINDER_LENGTH", "100-150")
    residue_str = " ".join(
        f"{chain}{first}-{last}/0" for chain, (first, last) in residues.items()
    )
    return f"{residue_str} {binder_length}"


def extract_sequence_from_pdb(pdb_file, chain="A"):
    """Return the one-letter sequence of one chain, read from its CA atoms."""
    sequence = ""
    previous_residue_number = None

    with open(pdb_file, "r") as handle:
        for line in handle:
            if (
                line.startswith("ATOM")
                and line[13:15].strip() == "CA"
                and line[21].strip() == chain
            ):
                residue_name = line[17:20].strip()
                residue_number = line[22:26].strip()
                if residue_number != previous_residue_number:
                    sequence += AMINO_ACID_CODES.get(residue_name, "X")
                    previous_residue_number = residue_number

    return sequence
