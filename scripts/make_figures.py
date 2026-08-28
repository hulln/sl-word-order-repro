#!/usr/bin/env python3
"""Generate the approved thesis figures from canonical public numerical files."""

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sl-word-order-repro-mplconfig")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize, PowerNorm
from matplotlib.patches import Circle, FancyArrowPatch, Patch, Rectangle
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.transforms import Bbox, blended_transform_factory


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "data"
FINAL_OUT = ROOT / "outputs" / "figures"

WORD_INPUT = DATA / "word_order_summary.tsv"
NER_INPUT = DATA / "ner_word_order.tsv"
TEST_INPUT = DATA / "statistical_tests.tsv"

# Preserve the exact PDF page dimensions of the committed thesis figures.
TARGET_PAGE_POINTS = {
    "fig_human_gpt5_stacked": (492.314, 173.982),
    "fig_h1_h2_stacked": (484.986, 256.191),
    "fig_jsd_matrix": (399.429, 344.934),
    "fig_ner_object_dumbbell": (461.378, 360.0),
    "fig_research_workflow": (514.177, 244.224),
    "fig_register_patterns_heatmap": (506.525, 293.918),
    "fig_svo_entropy": (486.735, 285.958),
}

FINAL_STEMS = {
    "fig_research_workflow": "fig_research_workflow",
    "fig_h1_h2_stacked": "fig_h1_h2_patterns",
    "fig_register_patterns_heatmap": "fig_register_patterns",
    "fig_human_gpt5_stacked": "fig_human_gpt5_patterns",
    "fig_jsd_matrix": "fig_jsd_matrix",
    "fig_svo_entropy": "fig_svo_entropy",
    "fig_ner_object_dumbbell": "fig_ner_objects",
}

PATTERNS = ["SVO", "SOV", "VSO", "VOS", "OSV", "OVS"]
REGISTER_IDS = [
    "SSJ",
    "SST",
    "JANES-Tweet",
    "JANES-Blog",
    "JANES-News",
    "JANES-Forum",
    "JANES-Wiki",
    "CLASSLA-Wikipedia",
    "ParlaMint",
]
JSD_ORDER = [
    "SSJ",
    "SST",
    "JANES-Tweet",
    "JANES-Blog",
    "JANES-News",
    "JANES-Forum",
    "JANES-Wiki",
    "CLASSLA-Wikipedia",
    "ParlaMint",
    "KDSP",
    "Human-essays",
    "GPT-5-essays",
]

# Shared visual language, anchored in the existing NER dumbbell candidate.
INK = "#28343A"
MID = "#617179"
LIGHT_TEXT = "#7D898F"
GRID = "#DCE3E6"
ACCENT = "#3F6E7D"
ACCENT_DARK = "#315661"
NEUTRAL_POINT = "#A6B2B7"
PATTERN_COLORS = {
    "SVO": "#3F6E7D",
    "SOV": "#64757D",
    "VSO": "#87979E",
    "VOS": "#A9B5BA",
    "OSV": "#CCD3D6",
    "OVS": "#E7EAEB",
}
HEAT_CMAP = LinearSegmentedColormap.from_list(
    "thesis_muted_blue",
    ["#F7F9FA", "#DDE7EA", "#AFC3CA", "#7898A4", "#3F6E7D"],
)

REGISTER_LABELS = {
    # These exact display forms are frozen to the committed thesis figures.
    # In particular, keep "Janes" title case and the established qualifiers.
    "SSJ": "SSJ",
    "SST": "SST",
    "JANES-Tweet": "Janes-Tweet",
    "JANES-Blog": "Janes-Blog",
    "JANES-News": "Janes-News",
    "JANES-Forum": "Janes-Forum",
    "JANES-Wiki": "Janes-Wiki\n(pogovorne strani)",
    "CLASSLA-Wikipedia": "CLASSLA-Wikipedia\n(članki)",
    "ParlaMint": "ParlaMint-SI",
    "KDSP": "KDSP (1836–1918)",
    "Human-essays": "človeški eseji",
    "GPT-5-essays": "eseji GPT-5",
}


def configure_style() -> None:
    for font in glob.glob("/usr/share/fonts/truetype/liberation/LiberationSans-*.ttf"):
        font_manager.fontManager.addfont(font)
    plt.rcParams.update(
        {
            "font.family": "Liberation Sans",
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 8,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "axes.edgecolor": INK,
            "axes.linewidth": 0.75,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def sl_decimal(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def sl_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def sl_percent_tick(value: float, _position: int | None = None) -> str:
    """Numeric percentage tick with Slovene spacing before the percent sign."""
    if np.isclose(value, round(value)):
        number = str(int(round(value)))
    else:
        number = sl_decimal(value)
    return f"{number} %"


def save_pdf(fig: plt.Figure, stem: str) -> Path:
    output_dir = FINAL_OUT
    output_stem = FINAL_STEMS[stem]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{output_stem}.pdf"
    fig.canvas.draw()
    tight = fig.get_tightbbox(fig.canvas.get_renderer())
    target_width_pt, target_height_pt = TARGET_PAGE_POINTS[stem]
    target_width = target_width_pt / 72
    target_height = target_height_pt / 72
    center_x = (tight.x0 + tight.x1) / 2
    center_y = (tight.y0 + tight.y1) / 2
    fixed_bbox = Bbox.from_bounds(
        center_x - target_width / 2,
        center_y - target_height / 2,
        target_width,
        target_height,
    )
    fig.savefig(
        path,
        format="pdf",
        bbox_inches=fixed_bbox,
        pad_inches=0,
        metadata={
            "Title": output_stem,
            "Creator": "scripts/make_figures.py",
        },
    )
    plt.close(fig)
    print(f"written: {path.relative_to(ROOT)}")
    return path


def finish_axes(ax: plt.Axes, grid_axis: str = "x") -> None:
    ax.set_axisbelow(True)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=3, width=0.65)


PUBLIC_TO_THESIS = {
    "ssj": "SSJ",
    "sst": "SST",
    "suk-literary": "SUK-leposlovno",
    "suk-publicistic": "SUK-publicisticno",
    "suk-professional": "SUK-strokovno",
    "janes-tweet": "JANES-Tweet",
    "janes-blog": "JANES-Blog",
    "janes-news": "JANES-News",
    "janes-forum": "JANES-Forum",
    "janes-wiki": "JANES-Wiki",
    "classla-wikipedia": "CLASSLA-Wikipedia",
    "parlamint": "ParlaMint",
    "kdsp": "KDSP",
    "human-essays": "Human-essays",
    "gpt5-essays": "GPT-5-essays",
}


def load_word_summary() -> pd.DataFrame:
    df = pd.read_csv(WORD_INPUT, sep="\t")
    count_cols = [f"{pattern}_n" for pattern in PATTERNS]
    prop_cols = [f"{pattern}_proportion" for pattern in PATTERNS]
    if not np.array_equal(df[count_cols].sum(axis=1).to_numpy(), df["total"].to_numpy()):
        raise ValueError("Canonical summary: pattern counts do not sum to total")
    calculated = df[count_cols].to_numpy() / df["total"].to_numpy()[:, None]
    if not np.allclose(calculated, df[prop_cols].to_numpy(), atol=5e-7):
        raise ValueError("Canonical summary: proportions disagree with count/total")
    df.loc[:, prop_cols] = calculated
    return df


def select_pattern_table(ids: list[str], labels: list[str]) -> pd.DataFrame:
    source = load_word_summary().set_index("corpus_id")
    if not set(ids).issubset(source.index):
        raise ValueError("Canonical summary: requested corpus is missing")
    selected = source.loc[ids].reset_index()
    output = pd.DataFrame({"register": labels, "total": selected["total"]})
    for pattern in PATTERNS:
        output[f"{pattern}_n"] = selected[f"{pattern}_n"]
        output[f"{pattern}_prop"] = selected[f"{pattern}_proportion"]
    output["entropy_nat"] = selected["entropy_nat"]
    return output


def load_h2() -> pd.DataFrame:
    order = ["SUK-strokovno", "SUK-publicisticno", "SUK-leposlovno", "SST"]
    return select_pattern_table(
        ["suk-professional", "suk-publicistic", "suk-literary", "sst"], order
    )


def load_manual_ner() -> dict[str, pd.DataFrame]:
    df = pd.read_csv(NER_INPUT, sep="\t")
    ids = ["ssj", "suk-literary", "suk-publicistic", "suk-professional"]
    labels = ["SSJ", "SUK-leposlovno", "SUK-publicisticno_splosno", "SUK-strokovno"]
    rows = []
    for role in ["object", "subject"]:
        for corpus_id, source in zip(ids, labels):
            groups = {}
            for status in ["entity", "common"]:
                part = df[
                    (df["corpus_id"] == corpus_id)
                    & (df["role"] == role)
                    & (df["entity_status"] == status)
                ]
                if len(part) != 6 or set(part["pattern"]) != set(PATTERNS):
                    raise ValueError(f"NER: incomplete canonical rows for {corpus_id}/{role}/{status}")
                counts = dict(zip(part["pattern"], part["count"]))
                total = int(part["total"].iloc[0])
                outcome = counts["OVS"] + counts["OSV"] if role == "object" else counts["SVO"]
                groups[status] = (int(outcome), total)
            ne_outcome, ne_n = groups["entity"]
            non_ne_outcome, non_ne_n = groups["common"]
            rows.append(
                {
                    "source": source,
                    "role": role,
                    "ne_outcome_count": ne_outcome,
                    "ne_other_count": ne_n - ne_outcome,
                    "non_ne_outcome_count": non_ne_outcome,
                    "non_ne_other_count": non_ne_n - non_ne_outcome,
                    "ne_n": ne_n,
                    "non_ne_n": non_ne_n,
                    "ne_pct": 100 * ne_outcome / ne_n,
                    "non_ne_pct": 100 * non_ne_outcome / non_ne_n,
                }
            )
    selected = pd.DataFrame(rows)
    return {role: selected[selected["role"] == role].reset_index(drop=True) for role in ["object", "subject"]}


def load_essays() -> tuple[pd.DataFrame, pd.DataFrame]:
    source = load_word_summary().set_index("corpus_id").loc[["human-essays", "gpt5-essays"]]
    calculated = source[[f"{pattern}_proportion" for pattern in PATTERNS]].to_numpy()
    summary = pd.DataFrame(
        {
            "genre": ["Human", "AI"],
            "total": source["total"].to_numpy(),
            "svo_proportion": source["SVO_proportion"].to_numpy(),
            "entropy": source["entropy_nat"].to_numpy(),
        }
    )
    entropy = -(calculated * np.log(calculated, where=calculated > 0)).sum(axis=1)
    if not np.allclose(entropy, summary["entropy"].to_numpy(), atol=5e-7):
        raise ValueError("Essays: entropy disagrees with six-pattern distribution")
    tidy = []
    for i, genre in enumerate(["Human", "AI"]):
        row = {"genre": genre, "total": int(source.iloc[i]["total"])}
        for pattern in PATTERNS:
            row[f"{pattern}_n"] = int(source.iloc[i][f"{pattern}_n"])
            row[f"{pattern}_prop"] = float(source.iloc[i][f"{pattern}_proportion"])
        tidy.append(row)
    return summary, pd.DataFrame(tidy)


def load_registers() -> pd.DataFrame:
    ids = [
        "ssj", "sst", "janes-tweet", "janes-blog", "janes-news",
        "janes-forum", "janes-wiki", "classla-wikipedia", "parlamint",
    ]
    return select_pattern_table(ids, REGISTER_IDS)


def load_jsd() -> dict[tuple[str, str], float]:
    df = pd.read_csv(TEST_INPUT, sep="\t")
    df = df[df["effect_name"] == "jensen_shannon_distance_base2"]
    pairs: dict[tuple[str, str], float] = {}
    for row in df.itertuples():
        register_a = PUBLIC_TO_THESIS.get(row.corpus_a)
        register_b = PUBLIC_TO_THESIS.get(row.corpus_b)
        if register_a not in JSD_ORDER or register_b not in JSD_ORDER:
            continue
        key = tuple(sorted((register_a, register_b)))
        if key in pairs:
            raise ValueError(f"JSD: duplicate pair {key}")
        pairs[key] = float(row.effect_value)
    expected = len(JSD_ORDER) * (len(JSD_ORDER) - 1) // 2
    if len(pairs) != expected:
        raise ValueError(f"JSD: expected {expected} pairs, found {len(pairs)}")
    return pairs


def pattern_legend(ax: plt.Axes, y_anchor: float) -> None:
    handles = [
        Patch(
            facecolor=PATTERN_COLORS[pattern],
            edgecolor="none" if pattern == "OVS" else "white",
            linewidth=0.6,
            label=pattern,
        )
        for pattern in PATTERNS
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, y_anchor),
        ncol=6,
        frameon=False,
        handlelength=1.8,
        columnspacing=1.15,
    )


def draw_row_labels(
    ax: plt.Axes,
    positions: np.ndarray,
    labels: list[str],
    totals: np.ndarray,
) -> None:
    ax.set_yticks([])
    transform = blended_transform_factory(ax.transAxes, ax.transData)
    for y, label, total in zip(positions, labels, totals):
        ax.text(
            -0.012,
            y + 0.10,
            label,
            transform=transform,
            ha="right",
            va="center",
            fontsize=8.5,
            color=INK,
            clip_on=False,
        )
        ax.text(
            -0.012,
            y - 0.17,
            f"n = {sl_int(total)}",
            transform=transform,
            ha="right",
            va="center",
            fontsize=7.1,
            color=LIGHT_TEXT,
            clip_on=False,
        )


def draw_stacked_bars(
    ax: plt.Axes,
    df: pd.DataFrame,
    positions: np.ndarray,
    labels: list[str],
    height: float = 0.58,
) -> None:
    left = np.zeros(len(df))
    for pattern in PATTERNS:
        values = 100 * df[f"{pattern}_prop"].to_numpy()
        ax.barh(
            positions,
            values,
            left=left,
            height=height,
            color=PATTERN_COLORS[pattern],
            edgecolor="white",
            linewidth=0.75,
            zorder=3,
        )
        if pattern == "SVO":
            for y, value in zip(positions, values):
                ax.text(
                    value / 2,
                    y,
                    f"SVO {sl_decimal(value)} %",
                    ha="center",
                    va="center",
                    fontsize=8.1,
                    fontweight="bold",
                    color="white",
                    zorder=5,
                )
        left += values
    if not np.allclose(left, 100.0, atol=1e-10):
        raise ValueError("Stacked bars do not sum to exactly 100%")
    draw_row_labels(ax, positions, labels, df["total"].to_numpy())
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_locator(MultipleLocator(20))
    ax.xaxis.set_major_formatter(FuncFormatter(sl_percent_tick))
    ax.set_xlabel("Delež vzorca znotraj skupine")
    finish_axes(ax, "x")


def figure_workflow() -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 3.45))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    centers = [0.095, 0.35, 0.61, 0.87]
    section_y_offset = -0.012
    number_y_offset = -0.004
    headings = [
        "GRADIVO",
        "IZLUŠČENJE IN OPREDELITEV\nVZORCEV",
        "GLAVNE IN ŠIRŠE\nPRIMERJAVE",
        "DOPOLNILNE ANALIZE IN\nPREVERJANJA",
    ]
    bodies = [
        "Korpusi in drevesnice\n"
        "za slovenščino\n"
        "Človeški eseji in\n"
        "eseji modela GPT-5\n\n"
        "Skladenjske oznake:\n"
        "ročno pregledane,\n"
        "kjer so na voljo;\n"
        "sicer samodejne",
        "glagol z oznako VERB\n"
        "osebek (nsubj) in predmet (obj)\n"
        "z jedrom NOUN\n"
        "analitična enota: par osebka\n"
        "in predmeta ob glagolu\n\n"
        "SVO · SOV · VSO\n"
        "VOS · OSV · OVS",
        "H1: tri žanrske skupine SUK\n"
        "H2: izbrane skupine SUK ↔\n"
        "pogovorno gradivo SST\n"
        "širša opisna primerjava glede na\n"
        "register in prenosnik\n\n"
        "frekvence in deleži\n"
        "delež SVO · entropija\n"
        "Jensen–Shannonova razdalja\n"
        "χ² in permutacijski preizkus\n"
        "pri izbranih primerjavah",
        "človeški eseji ↔\n"
        "eseji modela GPT-5\n"
        "imenske entitete\n"
        "udeleženske vloge ACT/PAT\n"
        "preverjanje samodejne\n"
        "skladenjske razčlembe\n"
        "AI-GenT",
    ]

    for i, center in enumerate(centers):
        circle = Circle(
            (center, 0.86),
            0.029,
            transform=ax.transAxes,
            facecolor=ACCENT if i < 3 else "white",
            edgecolor=ACCENT,
            linewidth=1.0,
        )
        ax.add_patch(circle)
        ax.text(
            center,
            0.86 + number_y_offset,
            str(i + 1),
            ha="center",
            va="center",
            fontsize=8.2,
            fontweight="bold",
            color="white" if i < 3 else ACCENT_DARK,
        )
        if i < len(centers) - 1:
            arrow = FancyArrowPatch(
                (center + 0.038, 0.86),
                (centers[i + 1] - 0.038, 0.86),
                transform=ax.transAxes,
                arrowstyle="-|>",
                mutation_scale=8,
                linewidth=0.8,
                color="#9DAAAF",
            )
            ax.add_patch(arrow)
        ax.text(
            center,
            0.73 + section_y_offset,
            headings[i],
            ha="center",
            va="top",
            fontsize=9.2,
            fontweight="bold",
            color=INK,
            linespacing=0.92,
        )
        ax.plot(
            [center - 0.065, center + 0.065],
            [0.625 + section_y_offset, 0.625 + section_y_offset],
            transform=ax.transAxes,
            color=ACCENT,
            linewidth=1.4,
            solid_capstyle="round",
        )
        ax.text(
            center,
            0.585 + section_y_offset,
            bodies[i],
            ha="center",
            va="top",
            fontsize=7.65,
            color=INK,
            linespacing=1.25,
        )

    ax.text(
        centers[2],
        0.18 + section_y_offset,
        "pogovorno gradivo SST je ločen vir,\nne četrta žanrska skupina SUK",
        ha="center",
        va="top",
        fontsize=7.15,
        fontstyle="italic",
        color=MID,
    )
    ax.text(
        centers[3],
        0.28 + section_y_offset,
        "samodejno pripisane oznake imenskih\n"
        "entitet: eksplorativno\n"
        "ACT/PAT: analiza omejena na eno podmnožico\n"
        "preverjanje razčlembe: iste povedi SSJ\n"
        "AI-GenT: brez primerljivega\n"
        "človeškega gradiva\n"
        "NER: Fisherjev eksaktni preizkus in\n"
        "Holmova prilagoditev",
        ha="center",
        va="top",
        fontsize=6.25,
        color=MID,
        linespacing=1.15,
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    return save_pdf(fig, "fig_research_workflow")


def figure_h1_h2() -> Path:
    df = load_h2()
    positions = np.array([3.35, 2.35, 1.35, -0.15])
    labels = ["strokovno", "publicistično", "leposlovno", "pogovorno"]
    fig, ax = plt.subplots(figsize=(7.2, 3.75))
    draw_stacked_bars(ax, df, positions, labels)
    ax.set_ylim(-0.70, 4.05)
    ax.text(
        0,
        3.90,
        "Žanrske skupine korpusa SUK",
        ha="left",
        va="center",
        fontsize=8.6,
        fontweight="bold",
        color=MID,
    )
    ax.hlines(
        0.63,
        35,
        100,
        color="#96A4AA",
        linewidth=0.7,
        linestyle=(0, (3, 3)),
        zorder=1,
    )
    ax.text(
        0,
        0.58,
        "Pogovorni korpus SST – ločen vir",
        ha="left",
        va="bottom",
        fontsize=8.6,
        fontweight="bold",
        color=MID,
    )
    pattern_legend(ax, -0.18)
    fig.subplots_adjust(left=0.18, right=0.985, top=0.98, bottom=0.25)
    return save_pdf(fig, "fig_h1_h2_stacked")


def figure_human_gpt() -> Path:
    _, df = load_essays()
    positions = np.array([0.95, 0.0])
    labels = ["človeški eseji", "eseji modela GPT-5"]
    fig, ax = plt.subplots(figsize=(7.2, 2.55))
    draw_stacked_bars(ax, df, positions, labels, height=0.56)
    ax.set_ylim(-0.48, 1.58)
    pattern_legend(ax, -0.30)
    fig.subplots_adjust(left=0.22, right=0.985, top=0.97, bottom=0.34)
    return save_pdf(fig, "fig_human_gpt5_stacked")


def combined_svo_entropy(registers: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    reg = registers[["register", "total", "SVO_prop", "entropy_nat"]].rename(
        columns={"register": "source", "SVO_prop": "svo_share", "entropy_nat": "entropy"}
    )
    reg["kind"] = "register"
    essays = summary[["genre", "total", "svo_proportion", "entropy"]].rename(
        columns={"genre": "source", "svo_proportion": "svo_share"}
    )
    essays["source"] = essays["source"].map({"Human": "Human essays", "AI": "GPT-5 essays"})
    essays["kind"] = essays["source"].map(
        {"Human essays": "human", "GPT-5 essays": "gpt"}
    )
    return pd.concat([reg, essays], ignore_index=True)


def figure_svo_entropy() -> Path:
    registers = load_registers()
    summary, _ = load_essays()
    df = combined_svo_entropy(registers, summary)
    labels = {
        "SSJ": "SSJ",
        "SST": "SST",
        "JANES-Tweet": "Tweet",
        "JANES-Blog": "Blog",
        "JANES-News": "News",
        "JANES-Forum": "Forum",
        "JANES-Wiki": "Wiki pog.",
        "CLASSLA-Wikipedia": "Wiki čl.",
        "ParlaMint": "ParlaMint",
        "Human essays": "člov. eseji",
        "GPT-5 essays": "GPT-5",
    }
    offsets = {
        "SST": (0, 9, "center", "bottom"),
        "ParlaMint": (-7, -7, "right", "top"),
        "SSJ": (-9, -8, "right", "top"),
        "JANES-Forum": (7, 8, "left", "bottom"),
        "JANES-News": (-3, -13, "right", "top"),
        "JANES-Wiki": (11, 11, "left", "bottom"),
        "JANES-Blog": (10, -2, "left", "top"),
        "CLASSLA-Wikipedia": (-7, -8, "right", "top"),
        "JANES-Tweet": (7, 5, "left", "bottom"),
        "Human essays": (8, -11, "left", "top"),
        "GPT-5 essays": (-8, 6, "right", "bottom"),
    }

    fig, ax = plt.subplots(figsize=(7.2, 4.15))
    neutral = df[(df["kind"] == "register") & (df["source"] != "SST")]
    ax.scatter(
        100 * neutral["svo_share"],
        neutral["entropy"],
        s=30,
        marker="o",
        facecolor=NEUTRAL_POINT,
        edgecolor=MID,
        linewidth=0.55,
        zorder=3,
    )
    sst = df[df["source"] == "SST"]
    ax.scatter(
        100 * sst["svo_share"],
        sst["entropy"],
        s=48,
        marker="o",
        facecolor=ACCENT,
        edgecolor=ACCENT_DARK,
        linewidth=0.7,
        zorder=4,
    )
    human = df[df["kind"] == "human"]
    ax.scatter(
        100 * human["svo_share"],
        human["entropy"],
        s=48,
        marker="s",
        facecolor="white",
        edgecolor=ACCENT_DARK,
        linewidth=1.0,
        zorder=4,
    )
    gpt = df[df["kind"] == "gpt"]
    ax.scatter(
        100 * gpt["svo_share"],
        gpt["entropy"],
        s=52,
        marker="^",
        facecolor=ACCENT,
        edgecolor=ACCENT_DARK,
        linewidth=0.7,
        zorder=4,
    )

    emphasized = {"SST", "Human essays", "GPT-5 essays"}
    for row in df.itertuples():
        dx, dy, ha, va = offsets[row.source]
        ax.annotate(
            labels[row.source],
            (100 * row.svo_share, row.entropy),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=7.5,
            fontweight="bold" if row.source in emphasized else "normal",
            color=INK if row.source in emphasized else MID,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.90, "pad": 0.25},
            arrowprops={
                "arrowstyle": "-",
                "color": "#A5B0B5",
                "linewidth": 0.4,
                "shrinkA": 1.5,
                "shrinkB": 4,
            },
        )
    ax.set_xlabel("Delež SVO (%)")
    ax.set_ylabel("Shannonova entropija")
    ax.set_xlim(61, 91)
    ax.set_ylim(0.43, 1.21)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _position: sl_decimal(value)))
    finish_axes(ax, "both")
    fig.subplots_adjust(left=0.11, right=0.985, top=0.97, bottom=0.14)
    return save_pdf(fig, "fig_svo_entropy")


def finish_vector_matrix(ax: plt.Axes, n_rows: int, n_cols: int, equal: bool) -> None:
    ax.set_xlim(-0.5, n_cols - 0.5)
    ax.set_ylim(n_rows - 0.5, -0.5)
    if equal:
        ax.set_aspect("equal")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def figure_jsd() -> Path:
    pairs = load_jsd()
    n = len(JSD_ORDER)
    grid = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(i):
            grid[i, j] = pairs[tuple(sorted((JSD_ORDER[i], JSD_ORDER[j])))]
    vmax = float(np.nanmax(grid))
    norm = Normalize(vmin=0, vmax=vmax)
    short = [
        "SSJ",
        "SST",
        "Tweet",
        "Blog",
        "News",
        "Forum",
        "Wiki pog.",
        "Wiki čl.",
        "ParlaMint",
        "KDSP",
        "člov. eseji",
        "GPT-5",
    ]

    fig, ax = plt.subplots(figsize=(7.2, 5.75))
    for i in range(n):
        for j in range(i):
            value = grid[i, j]
            ax.add_patch(
                Rectangle(
                    (j - 0.5, i - 0.5),
                    1,
                    1,
                    facecolor=HEAT_CMAP(norm(value)),
                    edgecolor="white",
                    linewidth=0.85,
                )
            )
    ax.set_xticks(range(n), short, rotation=45, ha="left", fontsize=8)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(n), [REGISTER_LABELS[key] for key in JSD_ORDER], fontsize=8)
    for i in range(n):
        for j in range(i):
            value = grid[i, j]
            ax.text(
                j,
                i,
                sl_decimal(value, 3),
                ha="center",
                va="center",
                fontsize=6.7,
                color="white" if norm(value) > 0.63 else INK,
            )
    finish_vector_matrix(ax, n, n, equal=True)
    mapper = ScalarMappable(norm=norm, cmap=HEAT_CMAP)
    mapper.set_array([])
    colorbar = fig.colorbar(mapper, ax=ax, orientation="horizontal", fraction=0.045, pad=0.085, aspect=38)
    if colorbar.solids is not None:
        colorbar.solids.set_rasterized(False)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=7.3, length=2, width=0.5, colors=MID)
    colorbar.ax.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _position: sl_decimal(value, 2))
    )
    colorbar.set_label("Jensen–Shannonova razdalja", fontsize=7.8, color=MID)
    fig.subplots_adjust(left=0.25, right=0.96, top=0.79, bottom=0.10)
    return save_pdf(fig, "fig_jsd_matrix")


def figure_register_heatmap() -> Path:
    df = load_registers().sort_values("SVO_prop", ascending=False).reset_index(drop=True)
    pct = 100 * df[[f"{p}_prop" for p in PATTERNS]].to_numpy()
    labels = [
        f"{REGISTER_LABELS[row.register]}   n = {sl_int(row.total)}"
        for row in df.itertuples()
    ]
    norm = PowerNorm(gamma=0.55, vmin=0, vmax=80)

    fig, ax = plt.subplots(figsize=(7.2, 4.65))
    for i in range(pct.shape[0]):
        for j in range(pct.shape[1]):
            ax.add_patch(
                Rectangle(
                    (j - 0.5, i - 0.5),
                    1,
                    1,
                    facecolor=HEAT_CMAP(norm(pct[i, j])),
                    edgecolor="white",
                    linewidth=1.15,
                )
            )
    ax.set_xticks(range(len(PATTERNS)), PATTERNS, fontsize=8.6)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(len(labels)), labels, fontsize=7.8)
    for i in range(pct.shape[0]):
        for j in range(pct.shape[1]):
            value = pct[i, j]
            ax.text(
                j,
                i,
                f"{sl_decimal(value)} %",
                ha="center",
                va="center",
                fontsize=7.7,
                color="white" if norm(value) > 0.64 else INK,
            )
    finish_vector_matrix(ax, len(labels), len(PATTERNS), equal=False)
    mapper = ScalarMappable(norm=norm, cmap=HEAT_CMAP)
    mapper.set_array([])
    colorbar = fig.colorbar(mapper, ax=ax, orientation="horizontal", fraction=0.045, pad=0.10, aspect=38)
    if colorbar.solids is not None:
        colorbar.solids.set_rasterized(False)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=7.3, length=2, width=0.5, colors=MID)
    colorbar.set_label("Delež vzorca znotraj vira (%)", fontsize=7.8, color=MID)
    fig.subplots_adjust(left=0.27, right=0.985, top=0.88, bottom=0.12)
    return save_pdf(fig, "fig_register_patterns_heatmap")


def figure_ner() -> Path:
    data = load_manual_ner()
    source_labels = {
        "SSJ": "SSJ",
        "SUK-leposlovno": "SUK – leposlovno",
        "SUK-publicisticno_splosno": "SUK – publicistično",
        "SUK-strokovno": "SUK – strokovno",
    }
    panels = [
        ("object", "A  PREDMETI", "Delež OVS + OSV med predmeti", (0, 44), 10),
        ("subject", "B  OSEBKI", "Delež SVO med osebki", (60, 100), 10),
    ]
    subject_ne_offsets = {
        "SSJ": (5, 7, "left", "bottom"),
        "SUK-publicisticno_splosno": (5, 6, "left", "bottom"),
    }
    subject_non_ne_offsets = {
        "SSJ": (-5, -7, "right", "top"),
        "SUK-leposlovno": (-5, -6, "right", "top"),
    }
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.0))
    legend_handles = None
    for ax, (role, title, xlabel, xlim, tick_step) in zip(axes, panels):
        df = data[role]
        y = np.arange(len(df))
        for i, row in enumerate(df.itertuples()):
            ax.plot(
                [row.non_ne_pct, row.ne_pct],
                [i, i],
                color="#B5C0C5",
                linewidth=0.9,
                zorder=2,
            )
        ne_marks = ax.scatter(
            df["ne_pct"],
            y,
            s=46,
            marker="o",
            facecolor=ACCENT,
            edgecolor=ACCENT_DARK,
            linewidth=0.65,
            label="jedro z oznako imenske entitete",
            zorder=4,
        )
        non_ne_marks = ax.scatter(
            df["non_ne_pct"],
            y,
            s=42,
            marker="s",
            facecolor="white",
            edgecolor=INK,
            linewidth=0.85,
            label="jedro brez oznake imenske entitete",
            zorder=4,
        )
        legend_handles = [ne_marks, non_ne_marks]
        for i, row in enumerate(df.itertuples()):
            ne_offset = subject_ne_offsets.get(
                row.source, (0, 9, "center", "bottom")
            ) if role == "subject" else (0, 9, "center", "bottom")
            non_ne_offset = subject_non_ne_offsets.get(
                row.source, (0, -10, "center", "top")
            ) if role == "subject" else (0, -10, "center", "top")
            ax.annotate(
                f"{sl_decimal(row.ne_pct)} %",
                (row.ne_pct, i),
                xytext=ne_offset[:2],
                textcoords="offset points",
                ha=ne_offset[2],
                va=ne_offset[3],
                fontsize=7.6,
                color=INK,
            )
            ax.annotate(
                f"{sl_decimal(row.non_ne_pct)} %",
                (row.non_ne_pct, i),
                xytext=non_ne_offset[:2],
                textcoords="offset points",
                ha=non_ne_offset[2],
                va=non_ne_offset[3],
                fontsize=7.6,
                color=INK,
            )

        ax.set_yticks(y, [source_labels[source] for source in df["source"]])
        ax.invert_yaxis()
        ax.set_ylim(len(df) - 0.2, -0.35)
        label_transform = blended_transform_factory(ax.transAxes, ax.transData)
        for i, row in enumerate(df.itertuples()):
            ax.text(
                -0.020,
                i + 0.22,
                f"n = {sl_int(row.ne_n)} / {sl_int(row.non_ne_n)}",
                transform=label_transform,
                ha="right",
                va="center",
                fontsize=6.8,
                color=LIGHT_TEXT,
                clip_on=False,
            )
        ax.set_xlim(*xlim)
        ax.xaxis.set_major_locator(MultipleLocator(tick_step))
        ax.xaxis.set_major_formatter(FuncFormatter(sl_percent_tick))
        ax.set_xlabel(xlabel)
        ax.set_title(title, loc="left", fontsize=8.4, fontweight="bold", color=MID, pad=5)
        finish_axes(ax, "x")

    fig.legend(
        legend_handles,
        ["jedro z oznako imenske entitete", "jedro brez oznake imenske entitete"],
        loc="upper center",
        bbox_to_anchor=(0.59, 0.99),
        ncol=2,
        frameon=False,
        handletextpad=0.5,
        columnspacing=1.4,
    )
    fig.subplots_adjust(left=0.25, right=0.985, top=0.88, bottom=0.12, hspace=0.42)
    return save_pdf(fig, "fig_ner_object_dumbbell")


def print_values() -> None:
    h2 = load_h2()
    print("H1/H2 exact percentages (SVO/SOV/VSO/VOS/OSV/OVS):")
    for row in h2.itertuples():
        values = [100 * getattr(row, f"{pattern}_prop") for pattern in PATTERNS]
        print(f"  {row.register}: " + ", ".join(f"{value:.6f}" for value in values))
    _, essays = load_essays()
    print("Slovenian essay exact percentages (SVO/SOV/VSO/VOS/OSV/OVS):")
    for row in essays.itertuples():
        values = [100 * getattr(row, f"{pattern}_prop") for pattern in PATTERNS]
        print(f"  {row.genre}: " + ", ".join(f"{value:.6f}" for value in values))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    configure_style()
    figure_workflow()
    figure_h1_h2()
    figure_human_gpt()
    figure_svo_entropy()
    figure_jsd()
    figure_register_heatmap()
    figure_ner()
    print_values()


if __name__ == "__main__":
    main()
