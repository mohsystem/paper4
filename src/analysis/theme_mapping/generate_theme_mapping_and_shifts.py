#!/usr/bin/env python3
"""
Generate `theme_mapping.csv` and `theme_shifts.csv` from the validated Excel report.

This script uses a researcher-defined, single-assignment CWE-to-family mapping intended
for descriptive domain-level summarization in an identity-centric Java Spring Boot
backend study. It does NOT perform inferential analysis.

Outputs:
  - theme_mapping.csv  : one row per CWE with assigned weakness family
  - theme_shifts.csv   : pre/post counts and percentage change by weakness family
  - theme_repo_counts.csv (optional convenience output): per-repository family counts

Usage:
  python generate_theme_mapping_and_shifts.py \
      --vuln security_review_report_Reviewers_consolidated_validated_v8_Bataim_Ready_for_analysis.xlsx \
      --outdir theme_outputs
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Dict, List

import pandas as pd


# Single-assignment, researcher-defined descriptive mapping.
# This version addresses the main taxonomy issues noted in review:
# - CWE-1021 moved out of authentication/session/recovery into a broader browser/request-boundary family.
# - CWE-521 moved out of availability into credential policy.
# - CWE-259 and CWE-798 moved into credential policy/authentication.
# - CWE-258 and CWE-523 also grouped with credential policy/authentication.
# - Sensitive-data/crypto family tightened to actual data, key, transport, and randomness problems.
CWE_FAMILY_MAP: Dict[str, str] = {
    # Authorization / access-control
    "CWE-269": "Authorization & object access",
    "CWE-639": "Authorization & object access",
    "CWE-732": "Authorization & object access",
    "CWE-807": "Authorization & object access",
    "CWE-862": "Authorization & object access",

    # Authentication / credential policy / recovery
    "CWE-258": "Authentication, credential policy & recovery",
    "CWE-259": "Authentication, credential policy & recovery",
    "CWE-287": "Authentication, credential policy & recovery",
    "CWE-306": "Authentication, credential policy & recovery",
    "CWE-521": "Authentication, credential policy & recovery",
    "CWE-522": "Authentication, credential policy & recovery",
    "CWE-523": "Authentication, credential policy & recovery",
    "CWE-640": "Authentication, credential policy & recovery",
    "CWE-798": "Authentication, credential policy & recovery",
    "CWE-916": "Authentication, credential policy & recovery",

    # Session / request / browser trust boundary
    "CWE-1021": "Session, request & browser trust boundary",
    "CWE-352": "Session, request & browser trust boundary",
    "CWE-384": "Session, request & browser trust boundary",
    "CWE-613": "Session, request & browser trust boundary",

    # Sensitive data / secrets / cryptography
    "CWE-201": "Sensitive data, secrets & cryptography",
    "CWE-312": "Sensitive data, secrets & cryptography",
    "CWE-319": "Sensitive data, secrets & cryptography",
    "CWE-321": "Sensitive data, secrets & cryptography",
    "CWE-330": "Sensitive data, secrets & cryptography",
    "CWE-338": "Sensitive data, secrets & cryptography",

    # Logging / errors / exposure
    "CWE-117": "Logging, errors & information exposure",
    "CWE-203": "Logging, errors & information exposure",
    "CWE-204": "Logging, errors & information exposure",
    "CWE-209": "Logging, errors & information exposure",
    "CWE-532": "Logging, errors & information exposure",
    "CWE-778": "Logging, errors & information exposure",

    # Configuration / debug surface
    "CWE-489": "Configuration & debug surface",

    # Input validation / unsafe integration
    "CWE-20": "Input validation & unsafe integration",
    "CWE-611": "Input validation & unsafe integration",
    "CWE-90": "Input validation & unsafe integration",
    "CWE-918": "Input validation & unsafe integration",

    # Availability / abuse resistance
    "CWE-307": "Availability & abuse resistance",
    "CWE-400": "Availability & abuse resistance",

    # File handling
    "CWE-434": "File handling",
}

FAMILY_ORDER: List[str] = [
    "Authorization & object access",
    "Authentication, credential policy & recovery",
    "Session, request & browser trust boundary",
    "Sensitive data, secrets & cryptography",
    "Logging, errors & information exposure",
    "Configuration & debug surface",
    "Input validation & unsafe integration",
    "Availability & abuse resistance",
    "File handling",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate theme mapping and pre/post theme shifts from validated Excel report.")
    parser.add_argument("--vuln", required=True, help="Path to validated Excel report.")
    parser.add_argument("--sheet", default=None, help="Optional sheet name. Defaults to the first sheet.")
    parser.add_argument("--outdir", required=True, help="Output directory.")
    return parser.parse_args()


def normalize_condition(repo_name: str) -> str:
    m = re.search(r"(pre|post)$", str(repo_name).strip(), flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"Could not infer condition from repo name: {repo_name!r}")
    return m.group(1).lower()


def load_validated_report(path: Path, sheet: str | None) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet_name = sheet or xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet_name)

    required = {
        "Repo Name",
        "Updated CWE ID",
        "Updated CWE Name",
        "Updated Severity",
        "Updated Validation Status",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()
    df["Updated Validation Status"] = df["Updated Validation Status"].astype(str).str.strip().str.upper()
    df = df[df["Updated Validation Status"] == "CONFIRMED"].copy()
    df["condition"] = df["Repo Name"].astype(str).map(normalize_condition)
    df["cwe_id"] = df["Updated CWE ID"].astype(str).str.strip()
    df["cwe_name"] = df["Updated CWE Name"].astype(str).str.strip()
    df["severity"] = df["Updated Severity"].astype(str).str.strip()
    return df


def build_mapping_table(df: pd.DataFrame) -> pd.DataFrame:
    cwes = (
        df[["cwe_id", "cwe_name"]]
        .drop_duplicates()
        .sort_values(["cwe_id", "cwe_name"])
        .reset_index(drop=True)
    )
    cwes["weakness_family"] = cwes["cwe_id"].map(CWE_FAMILY_MAP)

    missing = cwes[cwes["weakness_family"].isna()]
    if not missing.empty:
        raise ValueError(
            "Unmapped CWE IDs found: " + ", ".join(sorted(missing["cwe_id"].unique()))
        )

    cwes = cwes[["weakness_family", "cwe_id", "cwe_name"]]
    cwes["family_order"] = cwes["weakness_family"].map({f: i for i, f in enumerate(FAMILY_ORDER)})
    cwes = cwes.sort_values(["family_order", "cwe_id"]).drop(columns="family_order")
    return cwes


def build_theme_shifts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["weakness_family"] = df["cwe_id"].map(CWE_FAMILY_MAP)
    missing = df[df["weakness_family"].isna()]
    if not missing.empty:
        raise ValueError(
            "Unmapped CWE IDs found in validated findings: " + ", ".join(sorted(missing["cwe_id"].unique()))
        )

    counts = (
        df.groupby(["weakness_family", "condition"])
          .size()
          .unstack(fill_value=0)
          .reindex(FAMILY_ORDER, fill_value=0)
          .reset_index()
          .rename(columns={"pre": "pre", "post": "post"})
    )
    if "pre" not in counts.columns:
        counts["pre"] = 0
    if "post" not in counts.columns:
        counts["post"] = 0

    counts["change_pct"] = counts.apply(
        lambda r: 0.0 if r["pre"] == 0 else round(((r["pre"] - r["post"]) / r["pre"]) * 100.0, 1),
        axis=1,
    )
    counts = counts[["weakness_family", "pre", "post", "change_pct"]]
    return counts


def build_repo_family_counts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["weakness_family"] = df["cwe_id"].map(CWE_FAMILY_MAP)
    repo_counts = (
        df.groupby(["Repo Name", "condition", "weakness_family"])  # noqa: N806
          .size()
          .reset_index(name="count")
          .sort_values(["Repo Name", "weakness_family"])
    )
    return repo_counts


def main() -> int:

    vuln_path = Path("C:/data/PhD/developer_study/security_review_report_Reviewers_consolidated_validated_v8_Bataim_Ready_for_analysis.xlsx")
    outdir = Path("./")
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_validated_report(vuln_path, "Both")
    mapping_df = build_mapping_table(df)
    shifts_df = build_theme_shifts(df)
    repo_counts_df = build_repo_family_counts(df)

    mapping_path = outdir / "theme_mapping.csv"
    shifts_path = outdir / "theme_shifts.csv"
    repo_counts_path = outdir / "theme_repo_counts.csv"

    mapping_df.to_csv(mapping_path, index=False)
    shifts_df.to_csv(shifts_path, index=False)
    repo_counts_df.to_csv(repo_counts_path, index=False)

    summary_lines = [
        f"Validated findings processed: {len(df)}",
        f"Unique mapped CWEs: {mapping_df['cwe_id'].nunique()}",
        f"theme_mapping.csv: {mapping_path}",
        f"theme_shifts.csv: {shifts_path}",
        f"theme_repo_counts.csv: {repo_counts_path}",
        "\nTheme shifts:",
        shifts_df.to_string(index=False),
    ]
    summary_path = outdir / "theme_summary.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
