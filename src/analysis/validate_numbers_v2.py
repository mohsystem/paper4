
#!/usr/bin/env python3
"""
Validate the main quantitative results for Paper 4 from the consolidated
validated security review report.

This script computes only the calculations that are typically required for
a reviewer-facing quasi-experimental paper of this type:

1) Overall pre/post descriptive totals
2) Participant-level paired outcomes
3) Holm adjustment for the confirmatory within-subject outcomes
   (principal weighted endpoint and corroborative total-count endpoint)
4) Exploratory expertise-stratified descriptive summaries and exact
   Mann-Whitney tests on change scores
5) Counterbalancing schedule validation
6) Sensitivity analysis for alternative severity-weighting schemes
7) Participant-level severity profiles for appendix/auditability

Usage
-----
python validate_paper4_numbers_v2.py \
  --vuln security_review_report_Reviewers_consolidated_validated_v8_Bataim_Ready_for_analysis.xlsx \
  --outdir paper4_validation_outputs
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------
# Fixed participant mapping supplied by the study record
# ---------------------------------------------------------------------
MAPPING_ROWS = [
    ("llm-study26-01-pre", "llm-study26-01-post", 1, "Senior Developer", "Schedule 1"),
    ("llm-study26-02-pre", "llm-study26-02-post", 2, "Senior Developer", "Schedule 1"),
    ("llm-study26-03-pre", "llm-study26-03-post", 3, "Senior Developer", "Schedule 1"),
    ("llm-study26-04-pre", "llm-study26-04-post", 4, "Junior Developers", "Schedule 1"),
    ("llm-study26-05-pre", "llm-study26-05-post", 5, "Junior Developers", "Schedule 1"),
    ("llm-study26-06-pre", "llm-study26-06-post", 6, "Junior Developers", "Schedule 1"),
    ("llm-study26-07-pre", "llm-study26-07-post", 7, "Junior Developers", "Schedule 2"),
    ("llm-study26-08-pre", "llm-study26-08-post", 8, "Senior Developer", "Schedule 2"),
    ("llm-study26-09-pre", "llm-study26-09-post", 9, "Senior Developer", "Schedule 2"),
    ("llm-study26-10-pre", "llm-study26-10-post", 10, "Senior Developer", "Schedule 2"),
    ("llm-study26-11-pre", "llm-study26-11-post", 11, "Junior Developers", "Schedule 2"),
    ("llm-study26-12-pre", "llm-study26-12-post", 12, "Junior Developers", "Schedule 2"),
]

SEVERITIES = ["Critical", "High", "Medium", "Low"]
PRINCIPAL_WEIGHTS = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
EXPONENTIAL_WEIGHTS = {"Critical": 10, "High": 5, "Medium": 2, "Low": 1}
UNWEIGHTED_WEIGHTS = {"Critical": 1, "High": 1, "Medium": 1, "Low": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vuln", required=True, help="Path to the validated review report (.xlsx)")
    parser.add_argument("--outdir", required=True, help="Output directory")
    return parser.parse_args()


def holm_adjust(pvals: Iterable[float]) -> List[float]:
    """Holm step-down adjustment."""
    pvals = np.asarray(list(pvals), dtype=float)
    m = len(pvals)
    order = np.argsort(pvals)
    adjusted = np.empty(m, dtype=float)
    running_max = 0.0
    for rank, idx in enumerate(order):
        candidate = (m - rank) * pvals[idx]
        running_max = max(running_max, candidate)
        adjusted[idx] = min(running_max, 1.0)
    return adjusted.tolist()


def load_counts(vuln_path: str) -> pd.DataFrame:
    df = pd.read_excel(vuln_path, sheet_name=0)
    required = {"Repo Name", "Updated Severity", "Updated Validation Status"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df[df["Updated Validation Status"].astype(str).str.upper().eq("CONFIRMED")].copy()

    counts = (
        df.groupby(["Repo Name", "Updated Severity"])
        .size()
        .unstack(fill_value=0)
    )

    for sev in SEVERITIES:
        if sev not in counts.columns:
            counts[sev] = 0

    counts = counts[SEVERITIES].astype(int)
    counts["Total"] = counts[SEVERITIES].sum(axis=1)
    counts["Weighted_4_3_2_1"] = sum(counts[s] * w for s, w in PRINCIPAL_WEIGHTS.items())
    counts["Weighted_10_5_2_1"] = sum(counts[s] * w for s, w in EXPONENTIAL_WEIGHTS.items())
    return counts.sort_index()


def build_participant_frame(counts: pd.DataFrame) -> pd.DataFrame:
    mapping = pd.DataFrame(
        MAPPING_ROWS,
        columns=["Pre", "Post", "participant_id", "participant_seniority", "Schedule"],
    )

    missing_pre = sorted(set(mapping["Pre"]) - set(counts.index))
    missing_post = sorted(set(mapping["Post"]) - set(counts.index))
    if missing_pre or missing_post:
        raise ValueError(
            f"Missing repos in review report. Missing pre={missing_pre}, missing post={missing_post}"
        )

    rows = []
    for _, r in mapping.iterrows():
        pre = counts.loc[r["Pre"]]
        post = counts.loc[r["Post"]]
        row = {
            "participant_id": int(r["participant_id"]),
            "participant_seniority": r["participant_seniority"],
            "Schedule": r["Schedule"],
            "Pre_repo": r["Pre"],
            "Post_repo": r["Post"],
        }
        for sev in SEVERITIES + ["Total"]:
            row[f"pre_{sev}"] = int(pre[sev])
            row[f"post_{sev}"] = int(post[sev])
            row[f"delta_{sev}"] = int(pre[sev] - post[sev])

        row["pre_Weighted_4_3_2_1"] = int(pre["Weighted_4_3_2_1"])
        row["post_Weighted_4_3_2_1"] = int(post["Weighted_4_3_2_1"])
        row["delta_Weighted_4_3_2_1"] = int(pre["Weighted_4_3_2_1"] - post["Weighted_4_3_2_1"])

        row["pre_Weighted_10_5_2_1"] = int(pre["Weighted_10_5_2_1"])
        row["post_Weighted_10_5_2_1"] = int(post["Weighted_10_5_2_1"])
        row["delta_Weighted_10_5_2_1"] = int(pre["Weighted_10_5_2_1"] - post["Weighted_10_5_2_1"])

        rows.append(row)

    return pd.DataFrame(rows).sort_values("participant_id").reset_index(drop=True)


def matched_pairs_rank_biserial(deltas: np.ndarray) -> float:
    deltas = np.asarray(deltas, dtype=float)
    nz = deltas[deltas != 0]
    if nz.size == 0:
        return math.nan
    ranks = stats.rankdata(np.abs(nz), method="average")
    w_pos = float(ranks[nz > 0].sum())
    w_neg = float(ranks[nz < 0].sum())
    return (w_pos - w_neg) / (w_pos + w_neg)


def wilcoxon_result(pre: np.ndarray, post: np.ndarray) -> Dict[str, float]:
    delta = np.asarray(pre, dtype=float) - np.asarray(post, dtype=float)
    test = stats.wilcoxon(delta, zero_method="wilcox", alternative="two-sided", method="exact")
    return {
        "pre_mean": float(np.mean(pre)),
        "post_mean": float(np.mean(post)),
        "median_delta": float(np.median(delta)),
        "wilcoxon_statistic": float(test.statistic),
        "p_value": float(test.pvalue),
        "rank_biserial": float(matched_pairs_rank_biserial(delta)),
        "mean_delta": float(np.mean(delta)),
    }


def bootstrap_mean_ci(deltas: np.ndarray, seed: int = 2026, reps: int = 10000) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    deltas = np.asarray(deltas, dtype=float)
    samples = rng.choice(deltas, size=(reps, len(deltas)), replace=True)
    means = samples.mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def overall_results_table(paired: pd.DataFrame) -> pd.DataFrame:
    pre = {sev: int(paired[f"pre_{sev}"].sum()) for sev in SEVERITIES}
    post = {sev: int(paired[f"post_{sev}"].sum()) for sev in SEVERITIES}
    pre["Total"] = int(paired["pre_Total"].sum())
    post["Total"] = int(paired["post_Total"].sum())
    pre["Weighted"] = int(paired["pre_Weighted_4_3_2_1"].sum())
    post["Weighted"] = int(paired["post_Weighted_4_3_2_1"].sum())

    cols = ["Total", "Weighted"] + SEVERITIES
    table = pd.DataFrame(index=["Pre-training", "Post-training", "Change"], columns=cols)
    for c in cols:
        table.loc["Pre-training", c] = pre[c]
        table.loc["Post-training", c] = post[c]
        if pre[c] == 0:
            table.loc["Change", c] = np.nan
        else:
            table.loc["Change", c] = (post[c] - pre[c]) / pre[c] * 100.0
    return table


def paired_outcomes_table(paired: pd.DataFrame) -> pd.DataFrame:
    outcome_map = [
        ("Weighted score", "Weighted_4_3_2_1"),
        ("Total findings", "Total"),
        ("Critical", "Critical"),
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]
    rows = []
    for label, suffix in outcome_map:
        pre = paired[f"pre_{suffix}"].to_numpy()
        post = paired[f"post_{suffix}"].to_numpy()
        res = wilcoxon_result(pre, post)
        ci_low, ci_high = bootstrap_mean_ci(pre - post)
        rows.append({
            "Outcome": label,
            "Pre mean": res["pre_mean"],
            "Post mean": res["post_mean"],
            "Median Delta": res["median_delta"],
            "p_value": res["p_value"],
            "rank_biserial": res["rank_biserial"],
            "Mean Delta": res["mean_delta"],
            "Bootstrap mean CI low": ci_low,
            "Bootstrap mean CI high": ci_high,
        })

    out = pd.DataFrame(rows)
    # Holm only for confirmatory within-subject outcomes:
    # weighted principal endpoint + corroborative total-count endpoint.
    holm = holm_adjust(out.loc[:1, "p_value"].tolist())
    out["Holm p (confirmatory only)"] = np.nan
    out.loc[0, "Holm p (confirmatory only)"] = holm[0]
    out.loc[1, "Holm p (confirmatory only)"] = holm[1]
    return out


def expertise_tables(paired: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    desc = (
        paired.groupby("participant_seniority")
        .agg(
            pre_findings_mean=("pre_Total", "mean"),
            post_findings_mean=("post_Total", "mean"),
            median_delta_weighted=("delta_Weighted_4_3_2_1", "median"),
            critical_total_pre=("pre_Critical", "sum"),
            critical_total_post=("post_Critical", "sum"),
            n=("participant_id", "count"),
        )
        .reset_index()
    )

    junior = paired[paired["participant_seniority"] == "Junior Developers"]
    senior = paired[paired["participant_seniority"] == "Senior Developer"]

    rows = []
    comparisons = [
        ("Weighted delta", "delta_Weighted_4_3_2_1"),
        ("Total delta", "delta_Total"),
        ("Critical delta", "delta_Critical"),
        ("High delta", "delta_High"),
        ("Medium delta", "delta_Medium"),
        ("Low delta", "delta_Low"),
    ]
    for label, col in comparisons:
        exact_p = stats.mannwhitneyu(
            junior[col].to_numpy(),
            senior[col].to_numpy(),
            alternative="two-sided",
            method="exact",
        ).pvalue
        rows.append({
            "Outcome": label,
            "Junior median": float(junior[col].median()),
            "Senior median": float(senior[col].median()),
            "Junior mean": float(junior[col].mean()),
            "Senior mean": float(senior[col].mean()),
            "Mann-Whitney exact p": float(exact_p),
        })
    tests = pd.DataFrame(rows)
    return desc, tests


def schedule_validation_table(paired: pd.DataFrame) -> pd.DataFrame:
    s1 = paired[paired["Schedule"] == "Schedule 1"]
    s2 = paired[paired["Schedule"] == "Schedule 2"]

    rows = []
    comparisons = [
        ("Pre total findings", "pre_Total"),
        ("Pre weighted score", "pre_Weighted_4_3_2_1"),
        ("Weighted improvement", "delta_Weighted_4_3_2_1"),
    ]
    for label, col in comparisons:
        exact_p = stats.mannwhitneyu(
            s1[col].to_numpy(), s2[col].to_numpy(),
            alternative="two-sided", method="exact"
        ).pvalue
        rows.append({
            "Comparison": label,
            "Schedule 1 mean": float(s1[col].mean()),
            "Schedule 2 mean": float(s2[col].mean()),
            "Mann-Whitney exact p": float(exact_p),
        })
    return pd.DataFrame(rows)


def sensitivity_table(paired: pd.DataFrame) -> pd.DataFrame:
    schemes = [
        ("4/3/2/1", "delta_Weighted_4_3_2_1"),
        ("10/5/2/1", "delta_Weighted_10_5_2_1"),
        ("1/1/1/1 (unweighted total)", "delta_Total"),
    ]
    rows = []
    for label, col in schemes:
        delta = paired[col].to_numpy()
        test = stats.wilcoxon(delta, zero_method="wilcox", alternative="two-sided", method="exact")
        rows.append({
            "Scheme": label,
            "Median delta": float(np.median(delta)),
            "Wilcoxon exact p": float(test.pvalue),
            "Rank-biserial": float(matched_pairs_rank_biserial(delta)),
        })
    return pd.DataFrame(rows)


def write_summary(
    overall: pd.DataFrame,
    paired_tbl: pd.DataFrame,
    expertise_desc: pd.DataFrame,
    schedule_tbl: pd.DataFrame,
    sensitivity_tbl: pd.DataFrame,
    out_path: Path,
) -> None:
    overall_pre = overall.loc["Pre-training"]
    overall_post = overall.loc["Post-training"]

    lines = []
    lines.append("Validated Paper 4 Quantitative Summary")
    lines.append("=" * 50)
    lines.append("")
    lines.append("Overall descriptive totals")
    lines.append(f"- Total findings: {int(overall_pre['Total'])} -> {int(overall_post['Total'])}")
    lines.append(f"- Weighted score (4/3/2/1): {int(overall_pre['Weighted'])} -> {int(overall_post['Weighted'])}")
    lines.append(f"- Critical: {int(overall_pre['Critical'])} -> {int(overall_post['Critical'])}")
    lines.append(f"- High: {int(overall_pre['High'])} -> {int(overall_post['High'])}")
    lines.append(f"- Medium: {int(overall_pre['Medium'])} -> {int(overall_post['Medium'])}")
    lines.append(f"- Low: {int(overall_pre['Low'])} -> {int(overall_post['Low'])}")
    lines.append("")
    lines.append("Paired outcomes")
    for _, r in paired_tbl.iterrows():
        holm = r["Holm p (confirmatory only)"]
        holm_str = f", Holm={holm:.4f}" if pd.notna(holm) else ""
        lines.append(
            f"- {r['Outcome']}: pre_mean={r['Pre mean']:.2f}, post_mean={r['Post mean']:.2f}, "
            f"median_delta={r['Median Delta']:.1f}, p={r['p_value']:.4f}{holm_str}, "
            f"r_rb={r['rank_biserial']:.2f}"
        )
    lines.append("")
    lines.append("Schedule validation")
    for _, r in schedule_tbl.iterrows():
        lines.append(
            f"- {r['Comparison']}: Schedule 1 mean={r['Schedule 1 mean']:.2f}, "
            f"Schedule 2 mean={r['Schedule 2 mean']:.2f}, exact p={r['Mann-Whitney exact p']:.4f}"
        )
    lines.append("")
    lines.append("Sensitivity analysis")
    for _, r in sensitivity_tbl.iterrows():
        lines.append(
            f"- {r['Scheme']}: median_delta={r['Median delta']:.1f}, "
            f"exact p={r['Wilcoxon exact p']:.4f}, r_rb={r['Rank-biserial']:.2f}"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    # args = parse_args()
    outdir = Path("./")
    outdir.mkdir(parents=True, exist_ok=True)

    counts = load_counts("C:/data/PhD/developer_study/security_review_report_Reviewers_consolidated_validated_v8_Bataim_Ready_for_analysis.xlsx")
    paired = build_participant_frame(counts)

    overall = overall_results_table(paired)
    paired_tbl = paired_outcomes_table(paired)
    expertise_desc, expertise_tests = expertise_tables(paired)
    schedule_tbl = schedule_validation_table(paired)
    sensitivity_tbl = sensitivity_table(paired)

    counts.to_csv(outdir / "repo_level_counts.csv", index=True)
    paired.to_csv(outdir / "participant_level_profiles.csv", index=False)
    overall.to_csv(outdir / "overall_results.csv")
    paired_tbl.to_csv(outdir / "paired_outcomes.csv", index=False)
    expertise_desc.to_csv(outdir / "expertise_descriptives.csv", index=False)
    expertise_tests.to_csv(outdir / "expertise_mannwhitney.csv", index=False)
    schedule_tbl.to_csv(outdir / "schedule_validation.csv", index=False)
    sensitivity_tbl.to_csv(outdir / "sensitivity_analysis.csv", index=False)
    write_summary(overall, paired_tbl, expertise_desc, schedule_tbl, sensitivity_tbl, outdir / "validation_summary.txt")

    print(f"Wrote validation outputs to: {outdir}")


if __name__ == "__main__":
    main()
