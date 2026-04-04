#!/usr/bin/env python3
"""Generate Figure 3 (participant-level pre/post weighted scores) directly from the
validated security review spreadsheet.

Inputs
------
- Vulnerability report Excel file with a sheet containing at least:
    * Repo Name
    * Updated Severity
  The latest validated report uses a single sheet named 'Both'.

Outputs
-------
- figure3_paired_bars.png
- figure3_paired_bars.pdf
- figure3_participant_profiles.csv
- figure3_summary.txt

The script reproduces the weighted participant-level scores used in the paper:
    S = 4*Critical + 3*High + 2*Medium + 1*Low
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Embedded participant metadata from the latest study allocation record provided by the user.
PARTICIPANT_MAPPING = [
    {"participant_id": 1, "seniority": "Senior Developer", "schedule": "Schedule 1"},
    {"participant_id": 2, "seniority": "Senior Developer", "schedule": "Schedule 1"},
    {"participant_id": 3, "seniority": "Senior Developer", "schedule": "Schedule 1"},
    {"participant_id": 4, "seniority": "Junior Developers", "schedule": "Schedule 1"},
    {"participant_id": 5, "seniority": "Junior Developers", "schedule": "Schedule 1"},
    {"participant_id": 6, "seniority": "Junior Developers", "schedule": "Schedule 1"},
    {"participant_id": 7, "seniority": "Junior Developers", "schedule": "Schedule 2"},
    {"participant_id": 8, "seniority": "Senior Developer", "schedule": "Schedule 2"},
    {"participant_id": 9, "seniority": "Senior Developer", "schedule": "Schedule 2"},
    {"participant_id": 10, "seniority": "Senior Developer", "schedule": "Schedule 2"},
    {"participant_id": 11, "seniority": "Junior Developers", "schedule": "Schedule 2"},
    {"participant_id": 12, "seniority": "Junior Developers", "schedule": "Schedule 2"},
]

SEVERITY_WEIGHTS: Dict[str, int] = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Figure 3 from the validated Excel report.")
    parser.add_argument(
        "--vuln",
        required=True,
        help="Path to the validated vulnerability Excel report.",
    )
    parser.add_argument(
        "--sheet",
        default="Both",
        help="Sheet name to read from the Excel report (default: Both).",
    )
    parser.add_argument(
        "--outdir",
        default="figure3_outputs",
        help="Directory where outputs will be written.",
    )
    return parser.parse_args()


def read_vulnerability_report(path: Path, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name)

    required_cols = {"Repo Name", "Updated Severity"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path.name}: {sorted(missing)}")

    out = df[["Repo Name", "Updated Severity"]].copy()
    out["Repo Name"] = out["Repo Name"].astype(str).str.strip()
    out["Updated Severity"] = out["Updated Severity"].astype(str).str.strip()

    repo_parts = out["Repo Name"].str.extract(r"llm-study26-(\d+)-(pre|post)", expand=True)
    if repo_parts.isna().any().any():
        bad = out.loc[repo_parts.isna().any(axis=1), "Repo Name"].unique().tolist()
        raise ValueError(
            "Some repo names do not match the expected pattern 'llm-study26-XX-pre/post': "
            f"{bad}"
        )

    out["participant_id"] = repo_parts[0].astype(int)
    out["condition"] = repo_parts[1]

    invalid_sev = sorted(set(out["Updated Severity"]) - set(SEVERITY_WEIGHTS))
    if invalid_sev:
        raise ValueError(
            "Unexpected severity values found in the report: "
            f"{invalid_sev}. Expected only {sorted(SEVERITY_WEIGHTS)}."
        )

    return out


def compute_profiles(vuln_df: pd.DataFrame) -> pd.DataFrame:
    sev_cols = ["Critical", "High", "Medium", "Low"]
    counts = (
        vuln_df.groupby(["participant_id", "condition", "Updated Severity"]).size()
        .unstack(fill_value=0)
        .reindex(columns=sev_cols, fill_value=0)
        .reset_index()
    )

    # Ensure both conditions exist for every participant, even if one condition had zero findings.
    idx = pd.MultiIndex.from_product(
        [sorted(set(vuln_df["participant_id"])), ["pre", "post"]],
        names=["participant_id", "condition"],
    )
    counts = (
        counts.set_index(["participant_id", "condition"])
        .reindex(idx, fill_value=0)
        .reset_index()
    )

    counts["total_findings"] = counts[sev_cols].sum(axis=1)
    counts["weighted_score"] = sum(counts[col] * wt for col, wt in SEVERITY_WEIGHTS.items())

    mapping_df = pd.DataFrame(PARTICIPANT_MAPPING)
    counts = counts.merge(mapping_df, on="participant_id", how="left")

    if counts[["seniority", "schedule"]].isna().any().any():
        missing = counts.loc[counts["seniority"].isna() | counts["schedule"].isna(), "participant_id"].tolist()
        raise ValueError(f"Missing participant metadata for participant IDs: {missing}")

    wide = counts.pivot(index="participant_id", columns="condition", values="weighted_score")
    counts_by_id = wide.rename(columns={"pre": "weighted_pre", "post": "weighted_post"}).reset_index()
    counts_by_id["weighted_improvement"] = counts_by_id["weighted_pre"] - counts_by_id["weighted_post"]

    profiles = pd.DataFrame(PARTICIPANT_MAPPING).merge(counts_by_id, on="participant_id", how="left")
    profiles["participant_label"] = profiles["participant_id"].map(lambda x: f"P{x:02d}")

    # Add severity counts in wide form for transparency.
    severity_wide = counts.pivot(index="participant_id", columns="condition", values=sev_cols)
    severity_wide.columns = [f"{sev.lower()}_{cond}" for sev, cond in severity_wide.columns]
    profiles = profiles.merge(severity_wide.reset_index(), on="participant_id", how="left")

    profiles = profiles.sort_values("participant_id").reset_index(drop=True)
    return profiles


def make_figure(profiles: pd.DataFrame, outdir: Path) -> None:
    participants = profiles["participant_label"].tolist()
    pre_scores = profiles["weighted_pre"].to_numpy(dtype=float)
    post_scores = profiles["weighted_post"].to_numpy(dtype=float)

    x = np.arange(len(participants))
    width = 0.38

    fig, ax = plt.subplots(figsize=(14, 5.5))

    ax.bar(x - width/2, pre_scores, width, label="Pre-training")
    ax.bar(x + width/2, post_scores, width, label="Post-training")

    ax.set_ylabel("Severity-weighted score", fontsize=16)
    ax.set_xlabel("Participant", fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(participants, rotation=45, ha="right", fontsize=16)
    ax.tick_params(axis="y", labelsize=16)
    ax.legend(fontsize=16)
    ax.set_ylim(0, 80)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    # ax.set_title("Participant-level severity-weighted scores", fontsize=16)

    plt.tight_layout()
    # fig.savefig(outdir / "Participant-level_severity-weighted_scores.png", dpi=400, bbox_inches="tight")
    fig.savefig(outdir / "Participant-level_severity-weighted_scores.pdf", bbox_inches="tight")
    plt.close(fig)


def write_summary(profiles: pd.DataFrame, outdir: Path) -> None:
    improved = int((profiles["weighted_improvement"] > 0).sum())
    worsened = int((profiles["weighted_improvement"] < 0).sum())
    unchanged = int((profiles["weighted_improvement"] == 0).sum())

    lines = [
        "Figure 3 validation summary",
        "===========================",
        f"Participants: {len(profiles)}",
        f"Improved: {improved}",
        f"Worsened: {worsened}",
        f"Unchanged: {unchanged}",
        "",
        "Weighted score formula:",
        "  weighted_score = 4*Critical + 3*High + 2*Medium + 1*Low",
        "",
        "Participant-level weighted scores:",
    ]

    for _, row in profiles.iterrows():
        lines.append(
            f"  {row['participant_label']}: pre={int(row['weighted_pre'])}, "
            f"post={int(row['weighted_post'])}, improvement={int(row['weighted_improvement'])}"
        )

    (outdir / "figure3_summary.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    # args = parse_args()
    vuln_path = Path("C:/data/PhD/developer_study/security_review_report_Reviewers_consolidated_validated_v8_Bataim_Ready_for_analysis.xlsx")
    outdir = Path("./")
    outdir.mkdir(parents=True, exist_ok=True)

    vuln_df = read_vulnerability_report(vuln_path, sheet_name="Both")
    profiles = compute_profiles(vuln_df)

    profiles.to_csv(outdir / "figure3_participant_profiles.csv", index=False)
    make_figure(profiles, outdir)
    write_summary(profiles, outdir)

    # print(f"Wrote: {outdir / 'Participant-level_severity-weighted_scores.png'}")
    print(f"Wrote: {outdir / 'Participant-level_severity-weighted_scores.pdf'}")
    print(f"Wrote: {outdir / 'figure3_participant_profiles.csv'}")
    print(f"Wrote: {outdir / 'figure3_summary.txt'}")


if __name__ == "__main__":
    main()
