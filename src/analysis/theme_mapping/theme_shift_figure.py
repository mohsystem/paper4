import argparse
from pathlib import Path
import re
import textwrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to snake_case for robustness."""
    cols = {}
    for c in df.columns:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", c.strip().lower()).strip("_")
        cols[c] = normalized
    return df.rename(columns=cols)


def find_required_columns(df: pd.DataFrame) -> dict:
    """Map expected semantic names to actual columns."""
    candidates = {
        "family": ["weakness_family", "family", "theme", "theme_name"],
        "pre": ["pre", "pre_count", "before", "before_count"],
        "post": ["post", "post_count", "after", "after_count"],
        "change": ["change_pct", "change_percent", "change", "pct_change", "percent_change"],
    }

    found = {}
    for key, names in candidates.items():
        for name in names:
            if name in df.columns:
                found[key] = name
                break
        if key not in found:
            raise ValueError(
                f"Could not find a column for '{key}'. Available columns: {list(df.columns)}"
            )
    return found


def parse_change_value(value) -> float:
    """Parse percentage values whether stored as numbers or strings like '53.3%'."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, str):
        value = value.strip().replace("%", "")
        return float(value)
    return float(value)


def wrap_label(label: str, width: int) -> str:
    """Wrap long y-axis labels onto multiple lines."""
    return textwrap.fill(
        str(label),
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )


def compute_wrap_width(max_label_len: int, short_labels: bool) -> int:
    """Choose a reasonable wrap width based on label length."""
    if short_labels:
        return 20
    if max_label_len <= 20:
        return 20
    if max_label_len <= 40:
        return 32
    return 36


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a grouped horizontal bar chart for weakness-family shifts."
    )
    parser.add_argument("--csv",        default="./theme_shifts.csv",
                        help="Path to theme_shifts.csv")
    parser.add_argument(
        "--outdir",
        default="./",
        help="Output directory for figure files",
    )
    parser.add_argument(
        "--short-labels",
        action="store_true",
        default=True,
        help="Use shorter label aliases for the main figure",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Optional figure title",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    df = normalize_columns(df)
    colmap = find_required_columns(df)

    df = df[[colmap["family"], colmap["pre"], colmap["post"], colmap["change"]]].copy()
    df.columns = ["family", "pre", "post", "change_pct"]

    df["pre"] = pd.to_numeric(df["pre"])
    df["post"] = pd.to_numeric(df["post"])
    df["change_pct"] = df["change_pct"].apply(parse_change_value)

    short_label_map = {
        "Authorization & object access": "Authorization & object access",
        "Authentication, credential policy & recovery": "Auth., credential policy & recovery",
        "Session, request & browser trust boundary": "Session, request & browser trust",
        "Sensitive data, secrets & cryptography": "Sensitive data, secrets & crypto",
        "Logging, errors & information exposure": "Logging, errors & exposure",
        "Configuration & debug surface": "Configuration & debug surface",
        "Input validation & unsafe integration": "Input validation & unsafe integration",
        "Availability & abuse resistance": "Availability & abuse resistance",
        "File handling": "File handling",
    }

    label_series = (
        df["family"].map(short_label_map).fillna(df["family"])
        if args.short_labels
        else df["family"]
    )

    # Sort by pre-training count descending so the strongest signals appear first
    df = df.assign(label_source=label_series).sort_values("pre", ascending=False).reset_index(drop=True)

    max_label_len = max(len(str(x)) for x in df["label_source"])
    wrap_width = compute_wrap_width(max_label_len, args.short_labels)
    df["label"] = df["label_source"].apply(lambda x: wrap_label(x, wrap_width))

    # Dynamic sizing
    n = len(df)
    fig_width = 10.0 if max_label_len > 34 else 9.2
    fig_height = max(6.0, 0.65 * n + 1.6)

    plt.rcParams.update(
        {
            "font.size": 15,
            "axes.labelsize": 15,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "legend.fontsize": 15,
        }
    )

    y = np.arange(n)
    bar_h = 0.38

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Bars
    ax.barh(y - bar_h / 2, df["pre"], height=bar_h, label="Pre-training")
    ax.barh(y + bar_h / 2, df["post"], height=bar_h, label="Post-training")

    ax.set_yticks(y)
    ax.set_yticklabels(df["label"])
    ax.invert_yaxis()

    ax.set_xlabel("Number of weakness")
    if args.title:
        ax.set_title(args.title, fontsize=15)

    # Grid and legend
    ax.grid(True, axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    ax.legend(
        frameon=True,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        fontsize=15,
    )

    xmax = float(max(df["pre"].max(), df["post"].max()))

    # Small offset for numeric labels at the end of each bar
    value_pad = 0.35

    # Reserve a right-side annotation column INSIDE the frame
    right_margin = max(6.0, xmax * 0.22)
    x_limit = xmax + right_margin
    ax.set_xlim(0, x_limit)

    # Numeric labels at the end of each bar
    for i, row in df.iterrows():
        ax.text(
            row["pre"] + value_pad,
            i - bar_h / 2,
            f"{int(row['pre'])}",
            va="center",
            ha="left",
            fontsize=15,
            zorder=5,
            )
        ax.text(
            row["post"] + value_pad,
            i + bar_h / 2,
            f"{int(row['post'])}",
            va="center",
            ha="left",
            fontsize=15,
            zorder=5,
            )

    # Percentage labels in a fixed right-side column, still inside the frame
    percent_x = xmax + right_margin * 0.35
    for i, row in df.iterrows():
        ax.text(
            percent_x,
            i,
            f"{row['change_pct']:.1f}%",
            va="center",
            ha="left",
            fontsize=15,
        )

    # Header for the percentage column
    ax.text(
        percent_x,
        -0.85,
        "Change",
        ha="left",
        va="bottom",
        fontsize=15,
    )

    # Extra margins: left for wrapped family labels, top for legend
    plt.subplots_adjust(
        left=0.42 if max_label_len > 20 else 0.36,
        right=0.97,
        top=0.88,
        bottom=0.10,
    )

    pdf_path = outdir / "theme_shifts_grouped_bar_v3.pdf"
    png_path = outdir / "theme_shifts_grouped_bar_v3.png"

    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {pdf_path}")
    print(f"Saved: {png_path}")


if __name__ == "__main__":
    main()