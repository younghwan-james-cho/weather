# %% [markdown]
# # Chen et al. (2025) Replication — Korean Market
# **"Maxing out short-term reversals in weekly stock returns"**
# Journal of Empirical Finance 82, 101608
#
# Modifications:
# - Korean market (KRX) instead of U.S. (CRSP), 2005–2024
# - Table 1: 5 quintiles, no H−L, Excess returns only (EW/VW)
# - Table 13: 1 column (weekly MAX), excludes REV & MAX×REV
# - Controls: MAX, ILLIQ, IVOL, TVOL

# %% [markdown]
# ## 1. Setup & Configuration

# %%
import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = Path('/Users/younghwancho/dev/weather/data/processed/firm_char_weekly_clean.parquet')
OUTPUT_DIR = Path('/Users/younghwancho/dev/weather/analysis')
YEAR_START = 2005
YEAR_END = 2024
N_QUINTILES = 5

# %% [markdown]
# ## 2. Utility Functions

# %%
def nw_auto_lag(T):
    """Newey-West automatic lag selection: floor(4 * (T/100)^(2/9))"""
    return min(int(np.floor(4 * (T / 100) ** (2/9))), T - 1)


def nw_mean_tstat(series):
    """
    Compute time-series mean and Newey-West t-statistic.
    Equivalent to SAS: proc model fit / gmm kernel=(bart, lag)
    """
    arr = np.array(series, dtype=float)
    arr = arr[~np.isnan(arr)]
    T = len(arr)
    if T <= 1:
        return np.nan, np.nan
    maxlag = nw_auto_lag(T)
    try:
        model = sm.OLS(arr, np.ones(T)).fit(cov_type='HAC', cov_kwds={'maxlags': maxlag})
        return model.params[0], model.tvalues[0]
    except Exception:
        return np.nanmean(arr), np.nan


def significance_stars(t):
    """Return significance stars based on t-statistic."""
    if np.isnan(t):
        return ''
    at = abs(t)
    if at >= 2.576: return '***'
    if at >= 1.960: return '**'
    if at >= 1.645: return '*'
    return ''

print("Utility functions loaded ✓")

# %% [markdown]
# ## 3. Load Data
# The parquet file contains weekly stock data preprocessed from daily Korean stock data.
# - `RET` = **excess return** (raw return − CD91 risk-free rate), in percentage terms
# - `RET_raw` = raw return (recovered by adding CD91 back)

# %%
print("Loading data...")
df = pd.read_parquet(DATA_PATH)
df = df[(df['year'] >= YEAR_START) & (df['year'] <= YEAR_END)].copy()

# Recover raw return for Table 13
df['RET_raw'] = df['RET'] + df['CD91'].fillna(0)

print(f"Rows: {len(df):,}")
print(f"Weeks: {df['week_id'].nunique()}")
print(f"Unique stocks: {df['permno'].nunique()}")
print(f"Period: {df['year'].min()}–{df['year'].max()}")

# %% [markdown]
# ### 3.1 Variable Verification
# Check that all required variables are present and have sufficient coverage.

# %%
verify_cols = {
    'RET': 'Weekly excess return (%)',
    'RET_raw': 'Weekly raw return (%)',
    'CD91': 'Risk-free rate (%)',
    'MAX_t_minus_1': 'MAX at t−1 (Table 1 Panel A)',
    'MAX_t_minus_2': 'MAX at t−2 (Table 1 Panel B, Table 13)',
    'ME_mean_t_minus_1': 'Market cap at t−1 (VW weights)',
    'ILLIQ_t_minus_1': 'Amihud illiquidity at t−1',
    'IVOL_t_minus_1': 'FF4 residual vol at t−1',
    'TVOL_t_minus_1': 'Total vol (daily std) at t−1',
    'MKT_rf': 'Market excess return (FF4)',
    'SMB': 'Size factor (FF4)',
    'HML': 'Value factor (FF4)',
    'UMD': 'Momentum factor (FF4)',
}

print(f"{'Column':<25} {'Non-null':>10} {'Coverage':>10}  Description")
print("─" * 80)
for col, desc in verify_cols.items():
    n = df[col].notna().sum()
    print(f"{col:<25} {n:>10,} {n/len(df)*100:>9.1f}%  {desc}")

# %% [markdown]
# ### 3.2 Data Scaling Check
# The paper reports returns in percentage terms. Verify our data is scaled correctly.

# %%
print("=== Scaling Check ===")
print(f"RET (excess) — mean: {df['RET'].mean():.4f}, std: {df['RET'].std():.4f}")
print(f"CD91 (rf)    — mean: {df['CD91'].mean():.4f}")
print(f"MAX          — mean: {df['MAX'].mean():.4f}")
print()
if 0.01 < abs(df['RET'].mean()) < 10:
    print("✓ RET is in PERCENTAGE terms (e.g., 0.15 = 0.15%)")
    print("  No scaling adjustment needed.")
else:
    print("⚠ RET may be in DECIMAL terms — verify and multiply by 100 if needed.")

# %% [markdown]
# ### 3.3 Sample Statistics
# Quick look at the distribution of key variables.

# %%
stats_cols = ['RET', 'MAX', 'TVOL', 'ILLIQ', 'IVOL']
available = [c for c in stats_cols if c in df.columns]
print(df[available].describe().round(4).to_string())

# %% [markdown]
# ---
# ## 4. Table 1: Portfolio Sorts on MAX
#
# For each week:
# 1. Sort stocks into 5 quintiles based on MAX (max daily return)
# 2. Compute EW (equal-weighted) and VW (value-weighted) excess returns per quintile
# 3. After collecting all weeks, compute time-series average + Newey-West t-stat

# %% [markdown]
# ### 4.1 Panel A: Sort on MAX from week t−1

# %%
max_col = 'MAX_t_minus_1'
me_col = 'ME_mean_t_minus_1'

# Drop rows missing sort variable, return, or market cap
df_a = df.dropna(subset=[max_col, 'RET', me_col]).copy()
print(f"Panel A sample: {len(df_a):,} rows after dropping NaN in [{max_col}, RET, {me_col}]")

# Collect per-quintile EW and VW return time series
ew_a = {q: [] for q in range(N_QUINTILES)}
vw_a = {q: [] for q in range(N_QUINTILES)}

for week_id, group in df_a.groupby('week_id'):
    if len(group) < N_QUINTILES:
        continue

    ranks = group[max_col].rank(method='first')
    try:
        quintile = pd.qcut(ranks, N_QUINTILES, labels=False, duplicates='drop')
    except ValueError:
        continue
    if quintile.nunique() < N_QUINTILES:
        continue

    for q in range(N_QUINTILES):
        q_data = group[quintile == q]
        if len(q_data) == 0:
            ew_a[q].append(np.nan)
            vw_a[q].append(np.nan)
            continue
        ew_a[q].append(q_data['RET'].mean())
        me = q_data[me_col].values
        ret = q_data['RET'].values
        total_me = me.sum()
        vw_a[q].append(np.sum(ret * me) / total_me if total_me > 0 else np.nan)

print(f"Valid weeks: {len(ew_a[0])}")

# %% [markdown]
# #### Panel A Results

# %%
q_labels = ['Low', '2', '3', '4', 'High']
print(f"{'':8} {'Low':>10} {'2':>10} {'3':>10} {'4':>10} {'High':>10}")
print("─" * 60)

for wt_name, series in [('EW', ew_a), ('VW', vw_a)]:
    means, tstats = [], []
    for q in range(N_QUINTILES):
        m, t = nw_mean_tstat(np.array(series[q]))
        means.append(m)
        tstats.append(t)
    row1 = ''.join(f'{m:>10.3f}' for m in means)
    row2 = ''.join(f'{"("+f"{t:.2f}"+")":>10}' for t in tstats)
    print(f"{wt_name + ' Ret':8}{row1}")
    print(f"{'':8}{row2}")
    print()

# Store Panel A results
panel_a_results = {}
for wt_name, series in [('EW', ew_a), ('VW', vw_a)]:
    panel_a_results[wt_name] = {}
    for q in range(N_QUINTILES):
        m, t = nw_mean_tstat(np.array(series[q]))
        panel_a_results[wt_name][q] = {'excess_mean': m, 'excess_t': t}

# %% [markdown]
# ### 4.2 Panel B: Sort on MAX from week t−2 (skip 1 week)

# %%
max_col_b = 'MAX_t_minus_2'
df_b = df.dropna(subset=[max_col_b, 'RET', me_col]).copy()
print(f"Panel B sample: {len(df_b):,} rows")

ew_b = {q: [] for q in range(N_QUINTILES)}
vw_b = {q: [] for q in range(N_QUINTILES)}

for week_id, group in df_b.groupby('week_id'):
    if len(group) < N_QUINTILES:
        continue
    ranks = group[max_col_b].rank(method='first')
    try:
        quintile = pd.qcut(ranks, N_QUINTILES, labels=False, duplicates='drop')
    except ValueError:
        continue
    if quintile.nunique() < N_QUINTILES:
        continue
    for q in range(N_QUINTILES):
        q_data = group[quintile == q]
        if len(q_data) == 0:
            ew_b[q].append(np.nan)
            vw_b[q].append(np.nan)
            continue
        ew_b[q].append(q_data['RET'].mean())
        me = q_data[me_col].values
        ret = q_data['RET'].values
        total_me = me.sum()
        vw_b[q].append(np.sum(ret * me) / total_me if total_me > 0 else np.nan)

print(f"Valid weeks: {len(ew_b[0])}")

# %%
print(f"{'':8} {'Low':>10} {'2':>10} {'3':>10} {'4':>10} {'High':>10}")
print("─" * 60)

for wt_name, series in [('EW', ew_b), ('VW', vw_b)]:
    means, tstats = [], []
    for q in range(N_QUINTILES):
        m, t = nw_mean_tstat(np.array(series[q]))
        means.append(m)
        tstats.append(t)
    row1 = ''.join(f'{m:>10.3f}' for m in means)
    row2 = ''.join(f'{"("+f"{t:.2f}"+")":>10}' for t in tstats)
    print(f"{wt_name + ' Ret':8}{row1}")
    print(f"{'':8}{row2}")
    print()

panel_b_results = {}
for wt_name, series in [('EW', ew_b), ('VW', vw_b)]:
    panel_b_results[wt_name] = {}
    for q in range(N_QUINTILES):
        m, t = nw_mean_tstat(np.array(series[q]))
        panel_b_results[wt_name][q] = {'excess_mean': m, 'excess_t': t}

table1_results = {'A': panel_a_results, 'B': panel_b_results}
print("Table 1 results stored ✓")

# %% [markdown]
# ---
# ## 5. Table 13: Fama-MacBeth Cross-Sectional Regressions
#
# **Equation** (modified, no REV/interaction):
# $$Ret^{raw}_{i,t} = \beta_0 + \beta_1 \cdot MAX_{i,t-2} + \beta_2 \cdot ILLIQ + \beta_3 \cdot IVOL + \beta_4 \cdot TVOL + \varepsilon_{i,t}$$
#
# **Procedure:**
# 1. Each week: standardize independent variables cross-sectionally (mean=0, std=1)
# 2. Run OLS: raw return on standardized controls
# 3. Collect coefficients + adj R² across all weeks
# 4. Time-series average with Newey-West t-statistics

# %% [markdown]
# ### 5.1 Prepare Fama-MacBeth Sample

# %%
features = ['MAX_t_minus_2', 'ILLIQ_t_minus_1', 'IVOL_t_minus_1', 'TVOL_t_minus_1']
dep_var = 'RET_raw'

# NOTE: FF4 factors (MKT_rf, SMB, HML, UMD) are market-wide — identical for all
# stocks in a given week. They cannot enter a cross-sectional regression because
# they are perfectly collinear with the constant (no within-week variation).

df_fm = df.replace([np.inf, -np.inf], np.nan).copy()
df_fm = df_fm.dropna(subset=[dep_var] + features)

print(f"FM sample: {len(df_fm):,} rows")
print(f"FM sample weeks: {df_fm['week_id'].nunique()}")
print(f"\nDependent variable ({dep_var}) stats:")
print(df_fm[dep_var].describe().round(4))
print(f"\nIndependent variables stats (before standardization):")
print(df_fm[features].describe().round(4).to_string())

# %% [markdown]
# ### 5.2 Example: Single-Week Cross-Sectional Regression
# Let's look at one week to see the procedure step by step.

# %%
# Pick one week as an example
example_week = df_fm['week_id'].value_counts().idxmax()  # most populated week
example_group = df_fm[df_fm['week_id'] == example_week]
print(f"Example week: {example_week} ({len(example_group)} stocks)")
print()

# Step 1: Raw features
print("Step 1: Raw features (first 5 stocks):")
print(example_group[features].head().to_string())
print()

# Step 2: Cross-sectional standardization
X_raw = example_group[features].copy()
X_std = (X_raw - X_raw.mean()) / X_raw.std()
print("Step 2: Standardized features (first 5 stocks):")
print(X_std.head().round(4).to_string())
print(f"\nMean after standardization: {X_std.mean().round(6).to_dict()}")
print(f"Std after standardization:  {X_std.std().round(6).to_dict()}")
print()

# Step 3: Run OLS
y = example_group[dep_var].values
X = sm.add_constant(X_std.values)
model = sm.OLS(y, X).fit()
print("Step 3: OLS results for this week:")
print(f"  Intercept: {model.params[0]:.4f}")
for i, feat in enumerate(features):
    print(f"  {feat}: {model.params[i+1]:.4f}")
print(f"  Adj. R²: {model.rsquared_adj:.4f}")
print(f"  N stocks: {model.nobs:.0f}")

# %% [markdown]
# ### 5.3 Run Full Fama-MacBeth (All Weeks)

# %%
min_obs = len(features) + 2
coef_records = []
adjr2_list = []

for week_id, group in df_fm.groupby('week_id'):
    if len(group) < min_obs:
        continue

    y = group[dep_var].values
    X_raw = group[features].copy()
    X_std = (X_raw - X_raw.mean()) / X_raw.std()
    if X_std.isna().any().any():
        continue
    X = sm.add_constant(X_std.values)

    if np.linalg.matrix_rank(X) < X.shape[1]:
        continue

    try:
        model = sm.OLS(y, X).fit()
        coefs = {'Intercept': model.params[0]}
        for i, feat in enumerate(features):
            coefs[feat] = model.params[i + 1]
        coef_records.append(coefs)
        adjr2_list.append(model.rsquared_adj)
    except Exception:
        continue

df_coefs = pd.DataFrame(coef_records)
print(f"Valid weekly regressions: {len(df_coefs)}")
print(f"\nCoefficient time series (first 5 weeks):")
print(df_coefs.head().round(4).to_string())
print(f"\nCoefficient time series stats:")
print(df_coefs.describe().round(4).to_string())

# %% [markdown]
# ### 5.4 FM Results: Time-Series Averages with Newey-West t-stats

# %%
var_labels = {
    'Intercept': 'Intercept',
    'MAX_t_minus_2': 'MAX',
    'ILLIQ_t_minus_1': 'ILLIQ',
    'IVOL_t_minus_1': 'IVOL',
    'TVOL_t_minus_1': 'TVOL',
}

table13_results = {}
print(f"{'Variable':<15} {'Coeff':>10} {'t-stat':>10} {'Sig':>5}")
print("─" * 42)

for col_key in ['Intercept'] + features:
    mean_val, t_val = nw_mean_tstat(df_coefs[col_key].values)
    stars = significance_stars(t_val)
    label = var_labels[col_key]
    table13_results[col_key] = {'mean': mean_val, 't': t_val, 'label': label}
    print(f"{label:<15} {mean_val:>10.4f} {t_val:>10.2f} {stars:>5}")

avg_adjr2 = np.nanmean(adjr2_list)
table13_results['adj_r2'] = avg_adjr2
print(f"{'Adj. R²':<15} {avg_adjr2:>10.4f}")

# %% [markdown]
# ---
# ## 6. Generate HTML Output

# %%
def fmt_cell(mean_val, t_val):
    stars = significance_stars(t_val)
    return f"{mean_val:.3f}{stars}<br><span class='t-stat'>({t_val:.2f})</span>"

def fmt_cell_4dp(mean_val, t_val):
    stars = significance_stars(t_val)
    return f"{mean_val:.4f}{stars}<br><span class='t-stat'>({t_val:.2f})</span>"

def panel_rows(panel_key, panel_label, results):
    rows = []
    rows.append(f'<tr><td colspan="6" class="panel-title">'
                f'Panel {panel_key}: {panel_label}</td></tr>')
    for wt, wt_label in [('EW', 'equal-weighted'), ('VW', 'value-weighted')]:
        rows.append(f'<tr><td colspan="6" class="panel-title" '
                    f'style="font-weight: normal;">Panel {panel_key}.{"1" if wt=="EW" else "2"}: '
                    f'{wt_label}</td></tr>')
        cells = ''.join(f'<td>{fmt_cell(results[wt][q]["excess_mean"], results[wt][q]["excess_t"])}</td>'
                        for q in range(N_QUINTILES))
        border = ' class="bottom-border"' if wt == 'VW' else ''
        rows.append(f'<tr{border}><td class="row-label">Excess</td>{cells}</tr>')
    return '\n'.join(rows)

panel_a_html = panel_rows('A', 'Weekly portfolios sorted on MAX', table1_results['A'])
panel_b_html = panel_rows('B', 'Weekly portfolios sorted on MAX (skip 1 week)', table1_results['B'])

var_order = ['Intercept', 'MAX_t_minus_2', 'ILLIQ_t_minus_1', 'IVOL_t_minus_1', 'TVOL_t_minus_1']
t13_rows = []
for key in var_order:
    r = table13_results[key]
    t13_rows.append(f'<tr><td class="row-label">{r["label"]}</td>'
                    f'<td>{fmt_cell_4dp(r["mean"], r["t"])}</td></tr>')
t13_rows.append(f'<tr class="bottom-border"><td class="row-label">Adj. R²</td>'
                f'<td>{table13_results["adj_r2"]:.4f}</td></tr>')
t13_html = '\n'.join(t13_rows)

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: 'Times New Roman', Times, serif; font-size: 14px; margin: 40px; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 900px; margin-bottom: 30px; }}
    th, td {{ padding: 10px; text-align: center; }}
    th {{ border-top: 2px solid black; border-bottom: 1px solid black; font-weight: normal; }}
    td {{ border-bottom: none; }}
    .table-title {{ font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
    .table-subtitle {{ font-style: italic; font-size: 13px; margin-bottom: 15px; }}
    .panel-title {{ font-style: italic; text-align: left; padding-top: 15px;
                    font-weight: bold; border-bottom: none; }}
    .bottom-border {{ border-bottom: 2px solid black; }}
    .t-stat {{ font-style: italic; font-size: 13px; }}
    .note {{ font-size: 12px; margin-top: -15px; text-align: justify; max-width: 900px; }}
    .row-label {{ text-align: left; }}
</style>
</head>
<body>

<div class="table-title">Table 1</div>
<div class="table-subtitle">Returns of weekly portfolios sorted on MAX.</div>
<table>
    <thead>
        <tr><th class="row-label"></th><th colspan="5">MAX</th></tr>
        <tr><th class="row-label"></th><th>Low</th><th>2</th><th>3</th><th>4</th><th>High</th></tr>
    </thead>
    <tbody>
{panel_a_html}
{panel_b_html}
    </tbody>
</table>
<div class="note">
Note: Quintile portfolios are formed each week by sorting stocks on MAX (maximum daily return).
Panel A sorts on MAX from week <i>t</i>&minus;1; Panel B sorts on MAX from week <i>t</i>&minus;2
(skipping week <i>t</i>&minus;1). Equal-weighted (EW) and value-weighted (VW) average weekly
excess returns are reported in percentage terms. Newey&ndash;West (1987, 1994) adjusted
<i>t</i>-statistics with automatic lag selection are in parentheses.
***, **, * denote significance at the 1%, 5%, 10% levels.
Sample: Korean stocks, {YEAR_START}&ndash;{YEAR_END}.
</div>

<br><br>

<div class="table-title">Table 13</div>
<div class="table-subtitle">Fama&ndash;MacBeth cross-sectional regressions.</div>
<table>
    <thead>
        <tr><th class="row-label" style="width: 40%;">Variables</th>
            <th style="width: 60%;">Weekly MAX</th></tr>
    </thead>
    <tbody>
{t13_html}
    </tbody>
</table>
<div class="note">
Note: This table reports time-series averages of slopes from week-by-week
Fama&ndash;MacBeth (1973) cross-sectional regressions. The dependent variable is the
weekly stock return from week <i>t</i> (in percentage terms). MAX is the maximum daily
return within a week, measured at week <i>t</i>&minus;2. ILLIQ is Amihud (2002)&rsquo;s
illiquidity measure (4-week rolling). IVOL is idiosyncratic volatility (FF4 residual
std, 26-week rolling). TVOL is total volatility (std of daily returns within a week).
Independent variables are standardized to a mean of 0 and a standard deviation of 1
within each week. Newey&ndash;West (1987, 1994) adjusted <i>t</i>-statistics with
automatic lag selection are in parentheses.
***, **, * denote significance at the 1%, 5%, 10% levels.
Sample: Korean stocks, {YEAR_START}&ndash;{YEAR_END}.
</div>

</body>
</html>"""

output_path = OUTPUT_DIR / 'table_replication.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"HTML saved to: {output_path}")

# %% [markdown]
# ---
# ## Done ✓
# Open `analysis/table_replication.html` in a browser to see the formatted tables.
