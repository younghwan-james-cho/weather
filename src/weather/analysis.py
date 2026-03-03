"""Extended Robustness Analysis - ALL Specifications
Tests all possible combinations:
- Weather: d_cloud, d_sun
- Threshold: median, mean, 10_90, 20_80, 30_40_30
- Weighting: vw, ew
- Sort: max1, ivol
- Groups: 5, 10
- Lags: 6, 12
"""

import warnings
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from tqdm import tqdm

warnings.filterwarnings("ignore")

PROJECT_DIR = Path(__file__).parent.parent.parent  # weather/
DATA_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"


def nw_t(series, lag=12):
    n = len(series)
    if n < 2:
        return np.nan
    mean = np.nanmean(series)
    demeaned = series - mean
    gamma_0 = np.nanmean(demeaned**2)
    wac = 0.0
    for j in range(1, lag + 1):
        if j >= n:
            break
        weight = 1 - j / (lag + 1)
        wac += 2 * weight * np.nanmean(demeaned[j:] * demeaned[:-j])
    hac_var = gamma_0 + wac
    se = np.sqrt(hac_var / n) if hac_var > 0 else np.nan
    return mean / se if se and se > 0 else np.nan


def gmm_alpha(y, X, lag=12):
    try:
        model = sm.OLS(y, sm.add_constant(X))
        results = model.fit(cov_type="HAC", cov_kwds={"maxlags": lag})
        return results.tvalues[0]
    except:
        return np.nan


def run_single_spec(firm, weather, factors, wv, threshold, wgt, sv, ng, lag):
    weather = weather.copy()

    # Classify weather
    if threshold == "median":
        th = weather[wv].median()
        weather["state"] = np.where(weather[wv] > th, "High", "Low")
        states = ["High", "Low"]
    elif threshold == "mean":
        th = weather[wv].mean()
        weather["state"] = np.where(weather[wv] > th, "High", "Low")
        states = ["High", "Low"]
    else:
        if threshold == "10_90":
            p_low, p_high = weather[wv].quantile(0.1), weather[wv].quantile(0.9)
        elif threshold == "20_80":
            p_low, p_high = weather[wv].quantile(0.2), weather[wv].quantile(0.8)
        elif threshold == "30_40_30":
            p_low, p_high = weather[wv].quantile(0.3), weather[wv].quantile(0.7)
        else:
            return None, None

        weather["state"] = np.where(
            weather[wv] <= p_low,
            "Low",
            np.where(weather[wv] >= p_high, "High", "Normal"),
        )
        states = ["High", "Normal", "Low"]

    df = firm.merge(weather[["year_month", "state"]], on="year_month")
    df = df.dropna(subset=[sv, "retex_next", "ME"])
    df["port"] = df.groupby("year_month")[sv].transform(
        lambda x: np.floor(x.rank(method="average") * ng / (len(x) + 1))
        .clip(0, ng - 1)
        .astype(int)
        if len(x) >= ng
        else pd.Series([np.nan] * len(x), index=x.index)
    )
    df = df.dropna(subset=["port"])

    results = {}
    for state in states:
        subset = df[df["state"] == state].copy()
        if len(subset) < 50:
            results[state] = {
                "raw": np.nan,
                "capm": np.nan,
                "ff3": np.nan,
                "ff4": np.nan,
            }
            continue

        if wgt == "vw":
            subset["wret"] = subset["retex_next"] * subset["ME"]
            m = subset.groupby(["port", "year_month"]).agg({"wret": "sum", "ME": "sum"})
            m["port_ret"] = m["wret"] / m["ME"]
        else:
            m = (
                subset.groupby(["port", "year_month"])["retex_next"]
                .mean()
                .reset_index(name="port_ret")
            )
            m = m.set_index(["port", "year_month"])

        try:
            top = m.loc[ng - 1, "port_ret"].reset_index()
            top.columns = ["year_month", "top_ret"]
            bottom = m.loc[0, "port_ret"].reset_index()
            bottom.columns = ["year_month", "bottom_ret"]

            spread_df = top.merge(bottom, on="year_month")
            spread_df["spread"] = spread_df["top_ret"] - spread_df["bottom_ret"]
            spread_df = spread_df.merge(factors, on="year_month").dropna()

            if len(spread_df) < 12:
                results[state] = {
                    "raw": np.nan,
                    "capm": np.nan,
                    "ff3": np.nan,
                    "ff4": np.nan,
                }
                continue

            y = spread_df["spread"].values

            results[state] = {
                "raw": nw_t(y, lag),
                "capm": gmm_alpha(y, spread_df[["MKT"]].values, lag),
                "ff3": gmm_alpha(y, spread_df[["MKT", "SMB", "HML"]].values, lag),
                "ff4": gmm_alpha(
                    y, spread_df[["MKT", "SMB", "HML", "UMD"]].values, lag
                ),
            }
        except:
            results[state] = {
                "raw": np.nan,
                "capm": np.nan,
                "ff3": np.nan,
                "ff4": np.nan,
            }

    return results, states


def check_single_sig(results, states, return_type):
    sig_count = 0
    sig_state = None
    for state in states:
        t = results.get(state, {}).get(return_type, np.nan)
        if not np.isnan(t) and abs(t) > 2:
            sig_count += 1
            sig_state = state
    return sig_count == 1, sig_state


def main():
    print("Loading data...")
    firm = pd.read_parquet(DATA_DIR / "firm_char_grid_win_1.parquet")
    weather = pd.read_parquet(DATA_DIR / "weather.parquet")
    factors = pd.read_parquet(DATA_DIR / "ff4_factors.parquet")

    # Full grid
    weather_vars = ["d_cloud", "d_sun"]
    thresholds = ["median", "mean", "10_90", "20_80", "30_40_30"]
    weightings = ["vw", "ew"]
    sort_vars = ["max1", "ivol"]
    n_groups = [5, 10]
    lags = [6, 12]

    all_combos = list(
        product(weather_vars, thresholds, weightings, sort_vars, n_groups, lags)
    )
    print(f"Testing {len(all_combos)} specifications...")

    all_results = []

    for wv, th, wgt, sv, ng, lag in tqdm(all_combos, desc="Specs"):
        spec_name = f"{wv}_{th}_{wgt}_{sv}_g{ng}_lag{lag}"

        results, states = run_single_spec(
            firm, weather, factors, wv, th, wgt, sv, ng, lag
        )

        if results is None:
            continue

        row = {
            "spec": spec_name,
            "weather_var": wv,
            "threshold": th,
            "weighting": wgt,
            "sort_var": sv,
            "n_groups": ng,
            "lag": lag,
            "n_states": len(states),
        }

        for state in ["High", "Normal", "Low"]:
            for rt in ["raw", "capm", "ff3", "ff4"]:
                t_val = results.get(state, {}).get(rt, np.nan)
                row[f"{rt}_{state}_t"] = t_val

        for rt in ["raw", "capm", "ff3", "ff4"]:
            is_single, sig_state = check_single_sig(results, states, rt)
            row[f"{rt}_single_sig"] = is_single
            row[f"{rt}_sig_state"] = sig_state if is_single else None

        row["fully_robust"] = all(
            [row[f"{rt}_single_sig"] for rt in ["raw", "capm", "ff3", "ff4"]]
        )

        all_results.append(row)

    df = pd.DataFrame(all_results)

    # Summary
    print("\n" + "=" * 80)
    print(f"TOTAL: {len(df)} specs | FULLY ROBUST: {df['fully_robust'].sum()}")
    print("=" * 80)

    # Save
    df.to_parquet(OUTPUT_DIR / "all_specs_robustness.parquet")
    df.to_excel(OUTPUT_DIR / "all_specs_robustness.xlsx", index=False)
    print(f"\nSaved: {OUTPUT_DIR / 'all_specs_robustness.xlsx'}")


if __name__ == "__main__":
    main()
