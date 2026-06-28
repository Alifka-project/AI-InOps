"""PDF report generation (reportlab + optional matplotlib charts).

Pulls every analysis from the stateless service layer for a given dataset and
scenario and renders a multi-section PDF the user can download. Charts are
rendered with matplotlib when available and skipped gracefully otherwise.
"""

from __future__ import annotations

import io
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import service

NAVY = colors.HexColor("#041E42")
ACCENT = colors.HexColor("#0E8C82")
LIGHT = colors.HexColor("#EAF1F6")
GREY = colors.HexColor("#5B6B7B")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H1b", parent=ss["Heading1"], textColor=NAVY, spaceAfter=6))
    ss.add(ParagraphStyle("H2b", parent=ss["Heading2"], textColor=NAVY, spaceBefore=10))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8, textColor=GREY))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=9.5, leading=13))
    return ss


def _table(data: List[List[str]], col_widths=None, header=True) -> Table:
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D4DEE7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def _line_chart(months, series: dict, title: str) -> Optional[Image]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return None
    fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=150)
    x = range(len(months))
    for label, (values, color) in series.items():
        ax.plot(x, values, label=label, color=color, linewidth=1.6)
    ax.set_title(title, fontsize=10, color="#041E42")
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=7)
    step = max(1, len(months) // 8)
    ax.set_xticks(list(x)[::step])
    ax.set_xticklabels([months[i] for i in list(x)[::step]], rotation=0)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=17 * cm, height=6.6 * cm)


def _bar_chart(labels, values, title: str, color="#0E8C82") -> Optional[Image]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return None
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=150)
    ax.bar(range(len(labels)), values, color=color)
    ax.set_title(title, fontsize=10, color="#041E42")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7, rotation=20, ha="right")
    ax.tick_params(labelsize=7)
    ax.grid(True, axis="y", alpha=0.2)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=17 * cm, height=6.2 * cm)


def _money(n: float) -> str:
    return f"${n:,.0f}"


def build_report(
    ds: dict,
    scenario_name: str,
    alpha: float,
    beta: float,
    horizon: int,
    service_level,
    auto_tune: bool = True,
) -> bytes:
    ss = _styles()
    story: list = []
    meta = ds["meta"]

    # Run the full analysis through the same engine the UI uses.
    fcast = service.forecast_demand(ds, scenario_name, alpha, beta, horizon, auto_tune)
    suppliers = service.forecast_suppliers(ds, scenario_name, alpha, beta, horizon)
    transport = service.optimize_transport(ds, scenario_name, "vogel", "modi")
    warehouse = service.warehouse_policy(ds, scenario_name, alpha, beta, service_level)
    materials = service.materials_recovery(ds, scenario_name)
    comparison = service.compare_scenarios(ds, alpha, beta, horizon, service_level)
    scen = fcast["scenario"]

    # ---- Title -----------------------------------------------------------
    story.append(Paragraph("Digital Twin — Operations Report", ss["H1b"]))
    story.append(
        Paragraph(
            "Electrolux UAE supply-chain &amp; warehouse resilience · "
            "sensitive-material recovery network",
            ss["Small"],
        )
    )
    story.append(Spacer(1, 6))
    badge = (
        "SAMPLE (synthetic) dataset" if meta["is_sample"] else "User-uploaded dataset"
    )
    story.append(
        Paragraph(
            f"<b>Dataset:</b> {meta['name']} &nbsp;|&nbsp; <b>{badge}</b> "
            f"&nbsp;|&nbsp; <b>Scenario:</b> {scen['label']}",
            ss["Body"],
        )
    )
    if meta["is_sample"]:
        story.append(
            Paragraph(
                "<i>Note: this report was generated from the synthetic sample "
                "dataset for demonstration. Upload real data for production use.</i>",
                ss["Small"],
            )
        )
    story.append(Spacer(1, 8))

    # ---- Executive summary (KPIs) ---------------------------------------
    k = (
        comparison["normal"]
        if scenario_name == "normal"
        else comparison["hormuz_disruption"]
    )
    story.append(Paragraph("1. Executive Summary", ss["H2b"]))
    kpi_rows = [
        ["KPI", "Value"],
        ["Next-period planning demand", f"{k['next_month_demand']:,.0f} units"],
        ["Optimal transport cost", _money(k["optimal_transport_cost"])],
        ["Avg supplier utilization", f"{k['avg_supplier_utilization'] * 100:.1f}%"],
        ["Recovered-material value", _money(k["recovered_material_value"])],
        [
            "Hubs needing reorder",
            f"{k['hubs_needing_reorder']} of {meta['n_warehouses']}",
        ],
        [
            "Network balance",
            "Balanced" if k["balanced"] else "Unbalanced (dummy added)",
        ],
    ]
    story.append(_table(kpi_rows, col_widths=[9 * cm, 6 * cm]))
    story.append(Spacer(1, 8))

    # ---- Dataset overview ------------------------------------------------
    story.append(Paragraph("2. Dataset Overview", ss["H2b"]))
    story.append(
        Paragraph(
            f"{meta['n_periods']} sales periods · {meta['n_suppliers']} suppliers · "
            f"{meta['n_warehouses']} warehouses · {meta['n_orders']} customer orders. "
            "All eight data-augmentation categories were provided.",
            ss["Body"],
        )
    )
    for w in meta.get("warnings", []):
        story.append(Paragraph(f"• {w}", ss["Small"]))
    story.append(Spacer(1, 6))

    # ---- Demand forecasting ---------------------------------------------
    story.append(Paragraph("3. Demand Forecasting", ss["H2b"]))
    tune_txt = ""
    if fcast.get("tuning"):
        tn = fcast["tuning"]
        tune_txt = (
            f" Auto-tuned over {tn['grid_size']} (α,β) combinations; "
            f"validation MAD {tn['validation_mad']}."
        )
    story.append(
        Paragraph(
            f"Adjusted Exponential Smoothing with α={fcast['alpha']}, "
            f"β={fcast['beta']}.{tune_txt} Out-of-sample back-test on "
            f"{fcast['validation']['holdout']} "
            f"held-out periods: MAD {fcast['validation']['mad']}, "
            f"MAPE {fcast['validation']['mape']}%.",
            ss["Body"],
        )
    )
    metrics_rows = [["Method", "MAD", "MSE", "MAPE %", "Bias"]]
    for key in ("adjusted_es", "linear_trend", "seasonal"):
        m = fcast[key]["metrics"]
        metrics_rows.append(
            [
                fcast[key]["name"],
                f"{m['MAD']}",
                f"{m['MSE']}",
                f"{m['MAPE']}",
                f"{m['Bias']}",
            ]
        )
    story.append(
        _table(metrics_rows, col_widths=[6 * cm, 2.4 * cm, 3 * cm, 2.4 * cm, 2.4 * cm])
    )
    story.append(Spacer(1, 6))
    chart = _line_chart(
        fcast["months"],
        {
            "Actual": (fcast["actual"], "#1f2937"),
            "Adjusted ES": (fcast["adjusted_es"]["fitted"], "#0E8C82"),
            "Linear Trend": (fcast["linear_trend"]["fitted"], "#2E9BFF"),
        },
        "Actual vs forecast methods",
    )
    if chart:
        story.append(chart)
    story.append(PageBreak())

    # ---- Supplier availability ------------------------------------------
    story.append(Paragraph("4. Supplier Integration &amp; Forecasting", ss["H2b"]))
    sup_rows = [["Supplier", "Lead (d)", "Capacity", "Forecast", "Available", "Util %"]]
    for s in suppliers["suppliers"]:
        sup_rows.append(
            [
                s["center"],
                str(s["lead_time_days"]),
                f"{s['monthly_capacity_t']}",
                f"{s['forecast_next_t']:.0f}",
                f"{s['available_t']:.0f}",
                f"{s['capacity_utilization'] * 100:.0f}",
            ]
        )
    story.append(_table(sup_rows))
    story.append(Spacer(1, 6))
    bar = _bar_chart(
        [s["center"] for s in suppliers["suppliers"]],
        [s["available_t"] for s in suppliers["suppliers"]],
        "Forecast available tonnage by supplier",
    )
    if bar:
        story.append(bar)
    story.append(Spacer(1, 8))

    # ---- Transportation --------------------------------------------------
    story.append(Paragraph("5. Transportation Optimization", ss["H2b"]))
    story.append(
        Paragraph(
            f"Method {transport['method']}. Optimal total cost "
            f"<b>{_money(transport['total_cost'])}</b>. Network is "
            f"{'balanced' if transport['balanced'] else 'unbalanced'}"
            + (
                f" — a dummy {transport['dummy_added']} was added."
                if transport["dummy_added"]
                else "."
            ),
            ss["Body"],
        )
    )
    alloc_header = ["From \\ To"] + transport["col_labels"]
    alloc_rows = [alloc_header]
    for i, row in enumerate(transport["allocation"]):
        alloc_rows.append(
            [transport["row_labels"][i]] + [f"{v:.0f}" if v else "·" for v in row]
        )
    story.append(_table(alloc_rows))
    story.append(Spacer(1, 4))
    agree = (
        "All six initial×optimality combinations agree on the optimum."
        if transport["all_methods_agree"]
        else "Methods did not all agree — review inputs."
    )
    story.append(Paragraph(agree, ss["Small"]))
    story.append(Spacer(1, 8))

    # ---- Warehouse -------------------------------------------------------
    story.append(Paragraph("6. Warehouse Management", ss["H2b"]))
    story.append(
        Paragraph(
            f"Service level {warehouse['service_level'] * 100:.1f}%, ordering cost "
            f"{_money(warehouse['ordering_cost'])}, holding cost "
            f"{_money(warehouse['holding_cost_per_unit'])}/unit, avg lead time "
            f"{warehouse['avg_lead_time_days']} days.",
            ss["Body"],
        )
    )
    wh_rows = [["Hub", "Stock", "Safety", "ROP", "EOQ", "Order", "Status"]]
    for p in warehouse["policies"]:
        wh_rows.append(
            [
                p["hub"],
                f"{p['current_stock']:.0f}",
                f"{p['safety_stock']:.0f}",
                f"{p['reorder_point']:.0f}",
                f"{p['eoq']:.0f}",
                f"{p['suggested_order']:.0f}" if p["suggested_order"] else "—",
                p["status"],
            ]
        )
    story.append(_table(wh_rows))
    story.append(Spacer(1, 8))

    # ---- Materials -------------------------------------------------------
    if materials["enabled"]:
        story.append(Paragraph("7. Recovered-Material Value", ss["H2b"]))
        story.append(
            Paragraph(
                f"Processed {materials['processed_t']:.0f} t this cycle; total "
                f"recovered value <b>{_money(materials['total_value_usd'])}</b> "
                "(reference market prices).",
                ss["Body"],
            )
        )
        mat_rows = [["Material", "Share", "Recovered t", "$/t", "Value"]]
        for m in materials["materials"]:
            mat_rows.append(
                [
                    m["material"],
                    f"{m['mass_share'] * 100:.0f}%",
                    f"{m['recovered_t']:.0f}",
                    _money(m["value_per_t_usd"]),
                    _money(m["value_usd"]),
                ]
            )
        story.append(_table(mat_rows))
        story.append(Spacer(1, 8))

    # ---- Scenario comparison --------------------------------------------
    story.append(
        Paragraph("8. Scenario Comparison (Normal vs Hormuz Disruption)", ss["H2b"])
    )
    n, d = comparison["normal"], comparison["hormuz_disruption"]

    def _delta(a, b):
        if not a:
            return "—"
        return f"{(b - a) / a * 100:+.1f}%"

    cmp_rows = [
        ["Metric", "Normal", "Disruption", "Δ"],
        [
            "Transport cost",
            _money(n["optimal_transport_cost"]),
            _money(d["optimal_transport_cost"]),
            _delta(n["optimal_transport_cost"], d["optimal_transport_cost"]),
        ],
        [
            "Planning demand",
            f"{n['next_month_demand']:,.0f}",
            f"{d['next_month_demand']:,.0f}",
            _delta(n["next_month_demand"], d["next_month_demand"]),
        ],
        [
            "Recovered value",
            _money(n["recovered_material_value"]),
            _money(d["recovered_material_value"]),
            _delta(n["recovered_material_value"], d["recovered_material_value"]),
        ],
        [
            "Hubs to reorder",
            str(n["hubs_needing_reorder"]),
            str(d["hubs_needing_reorder"]),
            "—",
        ],
    ]
    story.append(_table(cmp_rows, col_widths=[5 * cm, 4 * cm, 4 * cm, 2.5 * cm]))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Methodology: time-series demand forecasting (Adjusted Exponential "
            "Smoothing, Linear Trend, Seasonal Adjustment) validated by out-of-sample "
            "back-testing; supplier availability forecast from historical shipment "
            "volumes capped by contractual capacity; transportation optimised with "
            "NWC / Least-Cost / Vogel initial solutions improved by Stepping-Stone and "
            "MODI, handling balanced and unbalanced cases via a dummy row/column; "
            "inventory policy (safety stock, ROP, EOQ) from demand, lead time, and the "
            "warehouse operational parameters.",
            ss["Small"],
        )
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Digital Twin Operations Report",
    )
    doc.build(story)
    buf.seek(0)
    return buf.read()
