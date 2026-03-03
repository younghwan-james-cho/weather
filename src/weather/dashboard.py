"""Deep Nested Robustness Dashboard
Structure: Base Spec → Variation (g5_lag6, g5_lag12, g10_lag6, g10_lag12) → Model → H/N/L
Robust = lag-robust (both lags) OR group-robust (both g5/g10)
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).parent.parent.parent  # weather/
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORTS_DIR = PROJECT_DIR / "reports"


def main():
    df = pd.read_parquet(DATA_DIR / "all_specs_robustness.parquet")

    # Create base spec (without g and lag)
    df["base_spec"] = df.apply(
        lambda r: f"{r['weather_var']}_{r['threshold']}_{r['weighting']}_{r['sort_var']}",
        axis=1,
    )
    df["variation"] = df.apply(lambda r: f"g{r['n_groups']}_lag{r['lag']}", axis=1)

    # Sort
    threshold_order = {"10_90": 1, "20_80": 2, "30_40_30": 3, "median": 4, "mean": 5}
    df["th_order"] = df["threshold"].map(threshold_order)
    df = df.sort_values(["weather_var", "sort_var", "th_order", "weighting"])

    # Calculate robustness per base spec
    base_specs = df["base_spec"].unique()
    robustness_info = {}

    for base in base_specs:
        subset = df[df["base_spec"] == base]

        # Check each variation's full robustness (all 4 models single-sig)
        var_robust = {}
        for _, row in subset.iterrows():
            var = row["variation"]
            var_robust[var] = row["fully_robust"]

        # Lag robust: g5_lag6 + g5_lag12 both robust OR g10_lag6 + g10_lag12 both robust
        lag_robust_g5 = var_robust.get("g5_lag6", False) and var_robust.get(
            "g5_lag12", False
        )
        lag_robust_g10 = var_robust.get("g10_lag6", False) and var_robust.get(
            "g10_lag12", False
        )

        # Group robust: g5_lag6 + g10_lag6 both robust OR g5_lag12 + g10_lag12 both robust
        group_robust_lag6 = var_robust.get("g5_lag6", False) and var_robust.get(
            "g10_lag6", False
        )
        group_robust_lag12 = var_robust.get("g5_lag12", False) and var_robust.get(
            "g10_lag12", False
        )

        is_robust = (
            lag_robust_g5 or lag_robust_g10 or group_robust_lag6 or group_robust_lag12
        )

        robustness_info[base] = {
            "is_robust": is_robust,
            "lag_robust_g5": lag_robust_g5,
            "lag_robust_g10": lag_robust_g10,
            "group_robust_lag6": group_robust_lag6,
            "group_robust_lag12": group_robust_lag12,
            "var_robust": var_robust,
        }

    # Best specs (robust ones)
    best_specs = [b for b, info in robustness_info.items() if info["is_robust"]]

    total_base = len(base_specs)
    robust_count = len(best_specs)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Weather × Lottery: Complete Robustness Analysis</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: #0a0a0f;
            color: #e4e4e7;
            line-height: 1.4;
            font-size: 12px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        header {{
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #27272a;
        }}
        h1 {{ font-size: 1.3rem; font-weight: 600; color: #fff; }}
        .subtitle {{ color: #71717a; font-size: 0.8rem; margin-top: 4px; }}
        
        .legend {{
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .legend h3 {{ font-size: 0.85rem; margin-bottom: 10px; color: #fff; }}
        .legend-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            font-size: 0.72rem;
        }}
        .legend-item {{
            display: flex;
            gap: 8px;
        }}
        .legend-item code {{
            font-family: 'JetBrains Mono', monospace;
            background: #27272a;
            padding: 2px 6px;
            border-radius: 3px;
            color: #60a5fa;
        }}
        .legend-item span {{ color: #a1a1aa; }}
        
        .best-specs {{
            background: linear-gradient(135deg, #14532d 0%, #166534 100%);
            border: 1px solid #22c55e;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .best-specs h3 {{
            font-size: 0.9rem;
            color: #86efac;
            margin-bottom: 10px;
        }}
        .best-specs-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}
        .best-spec-item {{
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 6px;
        }}
        .best-spec-item .name {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #fff;
        }}
        .best-spec-item .desc {{
            font-size: 0.68rem;
            color: #86efac;
            margin-top: 4px;
        }}
        
        .summary {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 15px;
            padding: 12px;
            background: #18181b;
            border-radius: 8px;
        }}
        .summary-item {{ text-align: center; }}
        .summary-item .val {{ font-size: 1.2rem; font-weight: 600; color: #22c55e; }}
        .summary-item .lbl {{ font-size: 0.6rem; color: #71717a; text-transform: uppercase; }}
        
        .toc {{
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
        }}
        .toc h3 {{ font-size: 0.8rem; margin-bottom: 8px; color: #fff; }}
        .toc-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }}
        .toc-item {{ padding: 5px 8px; background: #0f0f1a; border-radius: 4px; font-size: 0.68rem; }}
        .toc-item a {{ color: #60a5fa; text-decoration: none; }}
        
        .section {{
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 8px;
            margin-bottom: 12px;
            overflow: hidden;
        }}
        .section-header {{
            background: #1f1f28;
            padding: 8px 12px;
            font-weight: 600;
            color: #fff;
            font-size: 0.85rem;
            border-bottom: 1px solid #27272a;
            display: flex;
            justify-content: space-between;
        }}
        
        .base-spec-block {{
            border-bottom: 2px solid #27272a;
            padding: 8px 0;
        }}
        .base-spec-block:last-child {{ border-bottom: none; }}
        .base-spec-header {{
            padding: 6px 12px;
            background: #1a1a24;
            font-weight: 500;
            font-size: 0.78rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .base-spec-name {{
            font-family: 'JetBrains Mono', monospace;
            color: #fff;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.68rem;
        }}
        th {{
            text-align: center;
            padding: 4px 3px;
            background: #0f0f1a;
            color: #71717a;
            font-weight: 500;
            font-size: 0.6rem;
        }}
        th.left {{ text-align: left; }}
        td {{
            padding: 3px;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            border-bottom: 1px solid #1f1f28;
        }}
        td.left {{ text-align: left; font-family: 'Inter', sans-serif; }}
        
        .sig {{ color: #22c55e; font-weight: 500; }}
        .not-sig {{ color: #3f3f46; }}
        
        .var-row {{ background: #1a1a24; }}
        .model-row {{ }}
        .model-row:hover {{ background: #1f1f28; }}
        
        .badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 6px;
            font-size: 0.55rem;
            font-weight: 500;
        }}
        .badge-robust {{ background: #22c55e; color: #052e16; }}
        .badge-var-ok {{ background: #27272a; color: #22c55e; font-size: 0.5rem; }}
        .badge-var-fail {{ background: #27272a; color: #52525b; font-size: 0.5rem; }}
        
        footer {{
            text-align: center;
            margin-top: 15px;
            color: #52525b;
            font-size: 0.65rem;
        }}
        
        /* Force dark mode for PDF print */
        @media print {{
            body {{
                background: #0a0a0f !important;
                color: #e4e4e7 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .container, .section, .legend, .toc, .summary, .best-specs {{
                background: #18181b !important;
                -webkit-print-color-adjust: exact !important;
            }}
            .section-header, .base-spec-header, header, .var-row {{
                background: #1f1f28 !important;
                -webkit-print-color-adjust: exact !important;
            }}
            th {{
                background: #0f0f1a !important;
                -webkit-print-color-adjust: exact !important;
            }}
            .sig {{ color: #22c55e !important; }}
            .not-sig {{ color: #3f3f46 !important; }}
            h1, .base-spec-name, .toc h3, .legend h3 {{ color: #fff !important; }}
            font-size: 0.65rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Weather × Lottery Effect: Complete Robustness Analysis</h1>
            <p class="subtitle">Deep Nested View | Lag & Group Robustness | {datetime.now().strftime("%Y-%m-%d")}</p>
        </header>
        
        <div class="legend">
            <h3>Variable Definitions</h3>
            <div class="legend-grid">
                <div class="legend-item"><code>d_cloud</code><span>Deseasonalized cloud cover (DSKC)</span></div>
                <div class="legend-item"><code>d_sun</code><span>Deseasonalized sunshine hours</span></div>
                <div class="legend-item"><code>max1</code><span>Maximum daily return (lottery preference)</span></div>
                <div class="legend-item"><code>ivol</code><span>Idiosyncratic volatility (FF3 residuals)</span></div>
                <div class="legend-item"><code>G5/G10</code><span>Portfolio groups (quintile/decile)</span></div>
                <div class="legend-item"><code>Lag 6/12</code><span>Newey-West HAC lag parameter</span></div>
                <div class="legend-item"><code>VW/EW</code><span>Value-weighted / Equal-weighted</span></div>
                <div class="legend-item"><code>Robust</code><span>Lag-robust OR Group-robust (both work)</span></div>
            </div>
        </div>
        
        <div class="best-specs">
            <h3>🏆 Best Robust Specifications ({robust_count} total)</h3>
            <div class="best-specs-grid">"""

    # Add best specs
    for base in best_specs:
        info = robustness_info[base]
        desc_parts = []
        if info["lag_robust_g5"]:
            desc_parts.append("g5 lag-robust")
        if info["lag_robust_g10"]:
            desc_parts.append("g10 lag-robust")
        if info["group_robust_lag6"]:
            desc_parts.append("lag6 group-robust")
        if info["group_robust_lag12"]:
            desc_parts.append("lag12 group-robust")
        desc = " | ".join(desc_parts)

        html += f"""
                <div class="best-spec-item">
                    <div class="name">{base}</div>
                    <div class="desc">{desc}</div>
                </div>"""

    if len(best_specs) == 0:
        html += """<div class="best-spec-item"><div class="name">No fully robust specs found</div></div>"""

    html += f"""
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-item">
                <div class="val">{total_base}</div>
                <div class="lbl">Base Specs</div>
            </div>
            <div class="summary-item">
                <div class="val">{robust_count}</div>
                <div class="lbl">Robust</div>
            </div>
            <div class="summary-item">
                <div class="val">{len(df)}</div>
                <div class="lbl">Total Variations</div>
            </div>
        </div>
        
        <div class="toc">
            <h3>Table of Contents</h3>
            <div class="toc-grid">
                <div class="toc-item"><a href="#d_cloud_max1">☁️ Cloud × MAX</a></div>
                <div class="toc-item"><a href="#d_cloud_ivol">☁️ Cloud × IVOL</a></div>
                <div class="toc-item"><a href="#d_sun_max1">☀️ Sun × MAX</a></div>
                <div class="toc-item"><a href="#d_sun_ivol">☀️ Sun × IVOL</a></div>
            </div>
        </div>"""

    groups = [
        ("d_cloud", "max1", "☁️ Cloud × MAX", "d_cloud_max1"),
        ("d_cloud", "ivol", "☁️ Cloud × IVOL", "d_cloud_ivol"),
        ("d_sun", "max1", "☀️ Sun × MAX", "d_sun_max1"),
        ("d_sun", "ivol", "☀️ Sun × IVOL", "d_sun_ivol"),
    ]

    for wv, sv, title, anchor in groups:
        subset = df[(df["weather_var"] == wv) & (df["sort_var"] == sv)].copy()
        group_bases = subset["base_spec"].unique()
        group_robust = sum(1 for b in group_bases if robustness_info[b]["is_robust"])

        html += f"""
        <div class="section" id="{anchor}">
            <div class="section-header">
                {title}
                <span style="color:#71717a;font-weight:400;">{len(group_bases)} base specs | {group_robust} robust</span>
            </div>"""

        for base in group_bases:
            base_data = subset[subset["base_spec"] == base]
            info = robustness_info[base]

            # Simplify base name
            base_short = base.replace(f"{wv}_", "").replace(f"_{sv}", "")

            robust_badge = (
                '<span class="badge badge-robust">✓ ROBUST</span>'
                if info["is_robust"]
                else ""
            )

            html += f"""
            <div class="base-spec-block">
                <div class="base-spec-header">
                    <span class="base-spec-name">{base_short}</span>
                    {robust_badge}
                </div>
                <table>
                    <tr>
                        <th class="left" style="width:70px;">Variation</th>
                        <th style="width:45px;">Model</th>
                        <th style="width:50px;">High</th>
                        <th style="width:50px;">Normal</th>
                        <th style="width:50px;">Low</th>
                        <th style="width:50px;">Single</th>
                    </tr>"""

            variations = ["g5_lag6", "g5_lag12", "g10_lag6", "g10_lag12"]
            models = ["raw", "capm", "ff3", "ff4"]
            model_names = ["Raw", "CAPM", "FF3", "FF4"]

            for var in variations:
                row_data = base_data[base_data["variation"] == var]
                if len(row_data) == 0:
                    continue
                row = row_data.iloc[0]
                n_states = row["n_states"]
                var_ok = info["var_robust"].get(var, False)
                var_badge = "✓" if var_ok else ""

                for i, (model, model_name) in enumerate(zip(models, model_names)):

                    def fmt_t(val):
                        if pd.isna(val):
                            return "-"
                        cls = "sig" if abs(val) > 2 else "not-sig"
                        return f'<span class="{cls}">{val:.2f}</span>'

                    high_t = row[f"{model}_High_t"]
                    normal_t = row[f"{model}_Normal_t"] if n_states == 3 else np.nan
                    low_t = row[f"{model}_Low_t"]
                    sig_state = row[f"{model}_sig_state"] or "-"

                    if i == 0:
                        html += f"""
                    <tr class="var-row">
                        <td class="left" rowspan="4">{var} {var_badge}</td>
                        <td>{model_name}</td>
                        <td>{fmt_t(high_t)}</td>
                        <td>{fmt_t(normal_t)}</td>
                        <td>{fmt_t(low_t)}</td>
                        <td>{sig_state}</td>
                    </tr>"""
                    else:
                        html += f"""
                    <tr class="model-row">
                        <td>{model_name}</td>
                        <td>{fmt_t(high_t)}</td>
                        <td>{fmt_t(normal_t)}</td>
                        <td>{fmt_t(low_t)}</td>
                        <td>{sig_state}</td>
                    </tr>"""

            html += """
                </table>
            </div>"""

        html += """
        </div>"""

    html += """
        <footer>
            <p>Robust = Lag-robust (g5 both lags OR g10 both lags) OR Group-robust (lag6 both groups OR lag12 both groups)</p>
        </footer>
    </div>
</body>
</html>"""

    with open(REPORTS_DIR / "robustness_complete.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard saved: {REPORTS_DIR / 'robustness_complete.html'}")
    print(f"Robust base specs: {robust_count}/{total_base}")
    for b in best_specs:
        print(f"  ✓ {b}")


if __name__ == "__main__":
    main()
