"""Design selection, shared by the round 0 and partial diffusion steps.

Two things happen here:

1. process_protein_designs - for each run, rank the filtered designs by
   pae_interaction, keep the best design per backbone up to -d of them (these
   become the parents of the next partial diffusion round), and separately
   collect every design that passes both the -ipae and -plddt cuts into
   minibinders_to_validate.

2. select_top_minibinders - pool the per-run winners and write the global best
   -d of them into <output_folder>/TOP10, which is what the next partial
   diffusion round reads.

The round 0 and partial diffusion stages differ only in where the relevant
columns sit in the AF2 score files and in how design names are parsed, so both
stages call in here with a StageConfig.
"""

import os
import shutil
from dataclasses import dataclass

import pandas as pd


@dataclass
class StageConfig:
    """What differs between the round 0 and the partial diffusion stages."""

    # Column positions of pae_interaction, plddt_binder and description in the
    # filtered CSV. The partial diffusion score files carry one extra leading
    # column, so everything shifts right.
    pae_col: int
    plddt_col: int
    name_col: int
    # Only look at run folders whose name contains this string ("" = all).
    folder_filter: str
    # Index used when splitting a design name on "dldesign" to recover its
    # backbone. Each partial diffusion round appends another "dldesign" tag to
    # the name, so the round number is the right index to group siblings.
    backbone_split_index: int


ROUND0 = StageConfig(
    pae_col=2, plddt_col=4, name_col=8,
    folder_filter="", backbone_split_index=0,
)


def partial_diffusion(round_num):
    return StageConfig(
        pae_col=3, plddt_col=5, name_col=10,
        folder_filter="af2pred", backbone_split_index=round_num,
    )


def _read_filtered_csv(csv_file, stage):
    """Load a filtered score CSV and normalise its three columns of interest."""
    df = pd.read_csv(csv_file)
    needed = max(stage.pae_col, stage.plddt_col, stage.name_col)
    if len(df.columns) <= needed:
        print(
            f"Skipping {csv_file}: expected at least {needed + 1} columns, "
            f"found {len(df.columns)}."
        )
        return None

    df_filtered = df.iloc[:, [stage.pae_col, stage.plddt_col, stage.name_col]].copy()
    df_filtered.columns = ["pae_interaction", "plddt_binder", "design_name"]
    return df_filtered.sort_values(by="pae_interaction")


def _pick_best_per_backbone(df_filtered, stage, limit):
    """Keep the single best design per backbone, up to `limit` designs."""
    selected = []

    for _, row in df_filtered.iterrows():
        design_name = row["design_name"]
        pae_interaction = row["pae_interaction"]

        parts = str(design_name).split("dldesign")
        index = min(stage.backbone_split_index, len(parts) - 1)
        backbone = parts[index]

        existing = next(
            (d for d in selected if backbone in str(d["design_name"])), None
        )
        if existing is not None:
            if pae_interaction < existing["pae_interaction"]:
                selected.remove(existing)
                selected.append(row)
        else:
            selected.append(row)

        if len(selected) >= limit:
            break

    return pd.DataFrame(selected)


def process_protein_designs(
    input_folder, output_folder, minibinders_folder, stage, args
):
    os.makedirs(output_folder, exist_ok=True)
    minibinders_pdbs_folder = os.path.join(minibinders_folder, "pdbs")
    os.makedirs(minibinders_pdbs_folder, exist_ok=True)

    if not os.path.isdir(input_folder):
        print(f"No '{input_folder}' folder; nothing to select from.")
        return

    minibinders_list = []

    for protein_folder in sorted(os.listdir(input_folder)):
        protein_path = os.path.join(input_folder, protein_folder)

        if not os.path.isdir(protein_path):
            continue
        if stage.folder_filter and stage.folder_filter not in protein_folder:
            continue

        csv_file = None
        pdbs_folder = None
        for file in os.listdir(protein_path):
            if file.endswith(".csv"):
                csv_file = os.path.join(protein_path, file)
            elif file == "pdbs":
                pdbs_folder = os.path.join(protein_path, "pdbs")

        if not (csv_file and pdbs_folder):
            print(f"Skipping {protein_folder}: no CSV and pdbs/ pair found.")
            continue

        df_filtered = _read_filtered_csv(csv_file, stage)
        if df_filtered is None or df_filtered.empty:
            print(f"Skipping {protein_folder}: no designs survived the prefilter.")
            continue

        top_designs = _pick_best_per_backbone(df_filtered, stage, args.d)

        protein_output_folder = os.path.join(output_folder, protein_folder)
        top_pdbs_folder = os.path.join(protein_output_folder, "pdbs")
        os.makedirs(top_pdbs_folder, exist_ok=True)

        top_designs.to_csv(
            os.path.join(protein_output_folder, "top_10_designs.csv"), index=False
        )
        _copy_designs(top_designs["design_name"], pdbs_folder, top_pdbs_folder)

        # Designs good enough to hand to the wet lab.
        minibinders = df_filtered[
            (df_filtered["pae_interaction"] < args.ipae)
            & (df_filtered["plddt_binder"] > args.plddt)
        ]
        print(
            f"{protein_folder}: {len(top_designs)} parent(s) for the next round, "
            f"{len(minibinders)} minibinder(s) passing "
            f"ipae < {args.ipae} and pLDDT > {args.plddt}."
        )

        minibinders_list.append(minibinders)
        _copy_designs(
            minibinders["design_name"], pdbs_folder, minibinders_pdbs_folder
        )

    if minibinders_list:
        minibinders_combined = pd.concat(minibinders_list)
        minibinders_csv = os.path.join(
            minibinders_folder, "minibinders_to_validate.csv"
        )
        header = not os.path.exists(minibinders_csv)
        minibinders_combined.to_csv(
            minibinders_csv, mode="a", header=header, index=False
        )


def _copy_designs(design_names, src_folder, dst_folder):
    for design_name in design_names:
        pdb_file = os.path.join(src_folder, f"{design_name}.pdb")
        if os.path.exists(pdb_file):
            shutil.copy(pdb_file, dst_folder)
        else:
            print(f"PDB file not found, not copied: {pdb_file}")


def select_top_minibinders(input_folder, args):
    """Pool the per-run winners and write the global best into TOP10."""
    all_minibinders = []

    for root, dirs, files in os.walk(input_folder):
        csv_files = [f for f in files if f.endswith(".csv")]
        if "pdbs" not in dirs or not csv_files:
            continue

        csv_file_path = os.path.join(root, csv_files[0])
        try:
            df = pd.read_csv(csv_file_path)
        except Exception as e:
            print(f"Error reading {csv_file_path}: {e}")
            continue

        if not {"pae_interaction", "plddt_binder", "design_name"}.issubset(df.columns):
            print(f"Required columns missing in {csv_file_path}. Skipping.")
            continue

        top = df.nsmallest(args.d, "pae_interaction").copy()
        top["folder_path"] = os.path.join(root, "pdbs")
        all_minibinders.append(top)

    if not all_minibinders:
        print(f"No designs found under '{input_folder}'.")
        return

    combined = pd.concat(all_minibinders, ignore_index=True)
    final = combined.nsmallest(args.d, "pae_interaction")

    top10_dir = os.path.join(input_folder, "TOP10")
    top_pdbs_dir = os.path.join(top10_dir, "pdbs")
    os.makedirs(top_pdbs_dir, exist_ok=True)

    final[["pae_interaction", "plddt_binder", "design_name"]].to_csv(
        os.path.join(top10_dir, "top10_minibinders.csv"), index=False
    )

    for _, row in final.iterrows():
        pdb_file_path = os.path.join(row["folder_path"], f"{row['design_name']}.pdb")
        if os.path.exists(pdb_file_path):
            shutil.copy(pdb_file_path, top_pdbs_dir)
        else:
            print(f"PDB file not found: {pdb_file_path}")

    print(f"Top {len(final)} designs and their PDB files saved in {top10_dir}.")


def run_stage(stage, output_folder, args, input_folder="best_designs",
              minibinders_folder="minibinders_to_validate"):
    process_protein_designs(
        input_folder, output_folder, minibinders_folder, stage, args
    )
    select_top_minibinders(output_folder, args)
