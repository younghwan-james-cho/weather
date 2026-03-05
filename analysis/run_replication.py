import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

NOTEBOOK_DIR = Path('/Users/younghwancho/dev/weather/analysis')
PROCESSED_DATA_DIR = Path('/Users/younghwancho/dev/weather/data/processed')
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_PATH = '/Users/younghwancho/dev/weather/data/raw/daily_characteristics.sas7bdat'
FF4_DATA_PATH = '/Users/younghwancho/dev/weather/data/raw/ff4_weekly.sas7bdat'
PROCESSED_PARQUET = PROCESSED_DATA_DIR / 'firm_char_weekly_clean.parquet'

def preprocess_and_save():
    print("=" * 60)
    print("1. Loading and Preprocessing Raw Data (Vectorized)")
    print("=" * 60)
    if PROCESSED_PARQUET.exists():
        print(f"Loading already processed data from {PROCESSED_PARQUET}")
        return pd.read_parquet(PROCESSED_PARQUET)

    print("Reading SAS files... this takes a moment.")
    df_daily = pd.read_sas(RAW_DATA_PATH)
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    df_daily = df_daily[(df_daily['date'] >= '2005-01-01') & (df_daily['date'] <= '2024-12-31')].copy()

    df_ff4 = pd.read_sas(FF4_DATA_PATH)
    df_ff4['Date'] = pd.to_datetime(df_ff4['Date'])
    df_ff4 = df_ff4[(df_ff4['Date'] >= '2005-01-01') & (df_ff4['Date'] <= '2024-12-31')].copy()

    print("Calculating Weekly RET, MAX, and ILLIQ...")
    # ret is in % format (e.g., 5.0 means 5%). Remove only clearly erroneous obs.
    # Korean daily limit is ±30%, so anything beyond ±100% is a data error.
    df_daily = df_daily[(df_daily['ret'] > -100) & (df_daily['ret'] < 100)].copy()
    
    # Fast date parts
    df_daily['year'] = df_daily['date'].dt.isocalendar().year
    df_daily['week'] = df_daily['date'].dt.isocalendar().week
    df_daily['dayofweek'] = df_daily['date'].dt.dayofweek
    df_daily = df_daily[df_daily['dayofweek'] <= 4].copy()

    # Vectorized ILLIQ prep (daily value)
    df_daily['il'] = df_daily['ret'].abs() / df_daily['vold']
    df_daily['il'] = df_daily['il'].replace([np.inf, -np.inf], np.nan)
    
    # Pre-calculate (1 + r) for geometric compounding
    df_daily['ret_plus_1'] = (df_daily['ret'] / 100.0) + 1.0
    
    # Vectorized Groupby logic using NamedAgg for speed and clarity
    print("Aggregating to weekly level and adding TVOL...")
    weekly_base = df_daily.groupby(['permno', 'year', 'week'], as_index=False).agg(
        ILLIQ_raw_weekly=('il', 'mean'), # Will be rolled 4 weeks later
        MAX=('ret', 'max'),
        TVOL=('ret', 'std'),
        RET_prod=('ret_plus_1', 'prod'), # Geometric product
        ME_mean=('ME', 'mean')
    )
    
    # Convert product back to percentage return
    weekly_base['RET'] = (weekly_base['RET_prod'] - 1.0) * 100.0
    weekly_base.drop(columns=['RET_prod'], inplace=True)

    weekly_base['week_id'] = weekly_base['year'] * 100 + weekly_base['week']
    weekly_base.sort_values(['permno', 'year', 'week'], inplace=True)

    print("Calculating 4-week rolling ILLIQ...")
    weekly_base['ILLIQ_roll_4w'] = weekly_base.groupby('permno')['ILLIQ_raw_weekly'].transform(
        lambda x: x.rolling(window=4, min_periods=1).mean()
    )
    weekly_base['ILLIQ'] = weekly_base['ILLIQ_roll_4w'] * (10**8)
    weekly_base.drop(columns=['ILLIQ_raw_weekly', 'ILLIQ_roll_4w'], inplace=True)

    # --- Merge FF4 factors into weekly base BEFORE computing rolling firm-level stats ---
    print("Merging FF4 factors for BETA/IVOL computation...")
    df_ff4['year'] = df_ff4['Date'].dt.isocalendar().year
    df_ff4['week'] = df_ff4['Date'].dt.isocalendar().week
    ff4_cols = ['year', 'week', 'MKT_rf', 'SMB', 'HML', 'UMD', 'CD91']
    weekly_base = pd.merge(weekly_base, df_ff4[ff4_cols], on=['year', 'week'], how='left')

    # Firm excess return for rolling regressions (RET is raw at this point)
    weekly_base['RET_excess_firm'] = weekly_base['RET'] - weekly_base['CD91'].fillna(0)

    # --- Compute BETA (simplified Dimson: CAPM beta, 26-week rolling) ---
    print("Computing rolling BETA (26-week CAPM)...")
    def rolling_beta(sub):
        """Compute rolling CAPM beta for a single firm."""
        ret_ex = sub['RET_excess_firm'].values
        mkt = sub['MKT_rf'].values
        n = len(ret_ex)
        betas = np.full(n, np.nan)
        for i in range(25, n):  # 26-week window: index 0..25 = first window
            y = ret_ex[i-25:i+1]
            x = mkt[i-25:i+1]
            mask = ~(np.isnan(y) | np.isnan(x))
            if mask.sum() >= 10:  # Need at least 10 valid obs
                x_m, y_m = x[mask], y[mask]
                x_dm = x_m - x_m.mean()
                denom = (x_dm ** 2).sum()
                if denom > 0:
                    betas[i] = (x_dm * (y_m - y_m.mean())).sum() / denom
        return pd.Series(betas, index=sub.index)

    weekly_base['BETA'] = weekly_base.groupby('permno', group_keys=False).apply(rolling_beta)

    # --- Compute IVOL (std of FF4 regression residuals, 26-week rolling) ---
    print("Computing rolling IVOL (FF4 residual std, 26-week)...")
    def rolling_ivol(sub):
        """Compute rolling idiosyncratic volatility from FF4 residuals."""
        ret_ex = sub['RET_excess_firm'].values
        factors = sub[['MKT_rf', 'SMB', 'HML', 'UMD']].values
        n = len(ret_ex)
        ivols = np.full(n, np.nan)
        for i in range(25, n):
            y = ret_ex[i-25:i+1]
            X = factors[i-25:i+1]
            mask = ~(np.isnan(y) | np.any(np.isnan(X), axis=1))
            if mask.sum() >= 10:
                y_m, X_m = y[mask], X[mask]
                X_m = np.column_stack([np.ones(X_m.shape[0]), X_m])
                try:
                    beta_hat = np.linalg.lstsq(X_m, y_m, rcond=None)[0]
                    resid = y_m - X_m @ beta_hat
                    ivols[i] = resid.std(ddof=1)
                except:
                    pass
        return pd.Series(ivols, index=sub.index)

    weekly_base['IVOL'] = weekly_base.groupby('permno', group_keys=False).apply(rolling_ivol)

    # --- Compute TVOL_26w (26-week rolling std of weekly returns) ---
    print("Computing rolling TVOL (26-week std of weekly returns)...")
    weekly_base['TVOL_26w'] = weekly_base.groupby('permno')['RET'].transform(
        lambda x: x.rolling(window=26, min_periods=10).std()
    )

    # --- Compute MOM (cumulative return from week t-13 to t-2, ~months t-2 to t-12) ---
    print("Computing MOM (cumulative return, weeks t-13 to t-2)...")
    # First compute (1 + r/100) for geometric compounding, then rolling product
    weekly_base['ret_factor'] = 1 + weekly_base['RET'] / 100.0
    # Rolling product over 12 weeks (t-13 to t-2 means 12 weeks, lagged by 2)
    weekly_base['MOM_raw'] = weekly_base.groupby('permno')['ret_factor'].transform(
        lambda x: x.shift(2).rolling(window=12, min_periods=6).apply(np.prod, raw=True) - 1
    ) * 100.0  # Convert back to percentage
    weekly_base.drop(columns=['ret_factor'], inplace=True)

    # Convert raw RET to excess return
    weekly_base['RET'] = weekly_base['RET'] - weekly_base['CD91'].fillna(0)

    # --- Lagging ---
    print("Calculating Strict Lags (t-1, t-2)...")
    def create_lag(df, lag_weeks, cols_to_lag):
        lag_df = df[['permno', 'year', 'week'] + cols_to_lag].copy()
        lag_df['pseudo_date'] = pd.to_datetime(lag_df['year'].astype(str) + '-' + lag_df['week'].astype(str) + '-1', format='%G-%V-%u')
        lag_df['pseudo_date_future'] = lag_df['pseudo_date'] + pd.Timedelta(weeks=lag_weeks)
        lag_df['target_year'] = lag_df['pseudo_date_future'].dt.isocalendar().year
        lag_df['target_week'] = lag_df['pseudo_date_future'].dt.isocalendar().week
        rename_dict = {c: f'{c}_t_minus_{lag_weeks}' for c in cols_to_lag}
        lag_df.rename(columns=rename_dict, inplace=True)
        return lag_df[['permno', 'target_year', 'target_week'] + list(rename_dict.values())]

    lag1 = create_lag(weekly_base, 1, ['MAX', 'ME_mean', 'ILLIQ', 'TVOL', 'BETA', 'IVOL', 'TVOL_26w', 'MOM_raw'])
    lag2 = create_lag(weekly_base, 2, ['MAX', 'ME_mean'])

    df_weekly = pd.merge(weekly_base, lag1, left_on=['permno', 'year', 'week'], right_on=['permno', 'target_year', 'target_week'], how='left')
    df_weekly = pd.merge(df_weekly, lag2, left_on=['permno', 'year', 'week'], right_on=['permno', 'target_year', 'target_week'], how='left')
    df_weekly.drop(columns=['target_year_x', 'target_week_x', 'target_year_y', 'target_week_y'], errors='ignore', inplace=True)

    df_weekly['log_ME_t_minus_1'] = np.log(df_weekly['ME_mean_t_minus_1'].clip(lower=1e-10))

    # Cross-sectional winsorization
    print("Applying Cross-Sectional Winsorization (Vectorized)...")
    cols_to_winsorize = [
        'MAX_t_minus_1', 'MAX_t_minus_2', 'RET',
        'ILLIQ_t_minus_1', 'log_ME_t_minus_1', 'TVOL_t_minus_1',
        'BETA_t_minus_1', 'IVOL_t_minus_1', 'TVOL_26w_t_minus_1', 'MOM_raw_t_minus_1'
    ]
    for col in cols_to_winsorize:
        if col not in df_weekly.columns:
            continue
        lower_bounds = df_weekly.groupby('week_id')[col].transform(lambda x: x.quantile(0.01))
        upper_bounds = df_weekly.groupby('week_id')[col].transform(lambda x: x.quantile(0.99))
        df_weekly[col] = df_weekly[col].clip(lower=lower_bounds, upper=upper_bounds)

    print(f"Saving fully processed data to {PROCESSED_PARQUET}...")
    df_weekly.to_parquet(PROCESSED_PARQUET, index=False)
    return df_weekly


def get_stars(t):
    abs_t = abs(t)
    if abs_t >= 2.576: return '***'
    if abs_t >= 1.96: return '**'
    if abs_t >= 1.645: return '*'
    return ''

def compute_nw_stats(returns):
    T = len(returns)
    if T <= 1: return {'mean': np.nan, 't': np.nan}
    maxlag = int(np.floor(4 * (T / 100) ** (2/9)))
    maxlag = min(maxlag, T - 1)
    try:
        model = sm.OLS(returns, np.ones(T)).fit(cov_type='HAC', cov_kwds={'maxlags': maxlag})
        return {'mean': model.params[0], 't': model.params[0] / model.bse[0]}
    except:
        return {'mean': np.nan, 't': np.nan}


def calculate_table1_panel(df, max_col, me_col):
    df_clean = df.dropna(subset=[max_col, me_col, 'RET'])
    
    ew_rets = {q: [] for q in range(5)}
    vw_rets = {q: [] for q in range(5)}
    
    def assign_quintiles(group):
        try:
            # Rank values to handle ties, then qcut the ranks
            ranks = group[max_col].rank(method='first')
            return pd.qcut(ranks, 5, labels=False, duplicates='drop')
        except ValueError: # Handle cases where qcut might fail (e.g., not enough unique values)
            return pd.Series(np.nan, index=group.index)

    for week, group in df_clean.groupby('week_id'):
        if len(group) < 5: continue  # Need at least 5 stocks for quintile assignment
        try:
            group['q'] = assign_quintiles(group)
            group = group.dropna(subset=['q']) # Drop rows where quintile assignment failed
            
            for q in range(5): # Iterate from 0 to 4 for 5 quintiles
                q_data = group[group['q'] == q]
                if len(q_data) > 0:
                    ew_rets[q].append(q_data['RET'].mean())
                    w = q_data[me_col].values
                    r = q_data['RET'].values
                    if w.sum() > 0:
                        vw_rets[q].append(np.sum(r * w) / np.sum(w))
        except Exception: # Catch any other unexpected errors in the loop
            continue
            
    stats_ew = {q: compute_nw_stats(ew_rets[q]) for q in range(5)}
    stats_vw = {q: compute_nw_stats(vw_rets[q]) for q in range(5)}
    return stats_ew, stats_vw


def main():
    df_weekly = preprocess_and_save()

    print("\n" + "=" * 60)
    print("2. TABLE 1: Quintile Sorts")
    print("=" * 60)
    stats_pa_ew, stats_pa_vw = calculate_table1_panel(df_weekly, 'MAX_t_minus_1', 'ME_mean_t_minus_1')
    stats_pb_ew, stats_pb_vw = calculate_table1_panel(df_weekly, 'MAX_t_minus_2', 'ME_mean_t_minus_1')

    print("\n" + "=" * 60)
    print("3. TABLE 13: Fama-MacBeth (Weekly)")
    print("=" * 60)
    
    # Full set of controls matching paper (except BM which is unavailable)
    controls = [
        'log_ME_t_minus_1',    # SIZE
        'ILLIQ_t_minus_1',     # Amihud illiquidity
        'BETA_t_minus_1',      # CAPM beta from FF4
        'IVOL_t_minus_1',      # Idiosyncratic vol from FF4 residuals
        'TVOL_26w_t_minus_1',  # Total vol (26-week rolling)
        'MOM_raw_t_minus_1',   # Momentum (weeks t-13 to t-2)
    ]
    features = ['MAX_t_minus_2'] + controls

    df_fm = df_weekly.copy()
    df_fm = df_fm.replace([np.inf, -np.inf], np.nan)
    df_fm = df_fm.dropna(subset=['RET'] + features)

    print(f"FM Regressions usable rows: {len(df_fm)}")
    min_obs = len(features) + 2
    fmb_coefs = []
    
    for week, group in df_fm.groupby('week_id'):
        if len(group) < min_obs: continue
        y = group['RET']
        # Cross-sectional standardization: mean=0, std=1 within each week
        # Per paper: "Independent variables are standardized to a mean of 0
        # and a standard deviation of 1."
        X_raw = group[features].copy()
        X_std = (X_raw - X_raw.mean()) / X_raw.std()
        X_std = X_std.fillna(0)
        X = sm.add_constant(X_std)
        try:
            if np.linalg.matrix_rank(X.values) < X.shape[1]:
                continue
            model = sm.OLS(y, X).fit()
            res_dict = {'alpha': model.params.iloc[0]}
            for feat in features:
                res_dict[feat] = model.params.get(feat, 0)
            fmb_coefs.append(res_dict)
        except Exception as e:
            continue

    df_coefs = pd.DataFrame(fmb_coefs)
    if len(df_coefs) == 0:
        print("NO REGRESSIONS PASSED")
        exit(1)

    fmb_stats = {'alpha': compute_nw_stats(df_coefs['alpha'].values)}
    for feat in features:
        fmb_stats[feat] = compute_nw_stats(df_coefs[feat].values)

    print(f"FMB Beta MAX_t-2: {fmb_stats['MAX_t_minus_2']['mean']:.4f} (t={fmb_stats['MAX_t_minus_2']['t']:.2f})")
    for feat in features:
        print(f"  {feat}: {fmb_stats[feat]['mean']:.4f} (t={fmb_stats[feat]['t']:.2f})")

    print("\n" + "=" * 60)
    print("4. Generating Final HTML Output")
    print("=" * 60)

    # Helper for Table 13 rows
    def fmb_row(label, key):
        m = fmb_stats[key]['mean']
        t = fmb_stats[key]['t']
        return f"""        <tr>
            <td class="row-label">{label}</td>
            <td>{m:.4f}{get_stars(t)}<br><span class='t-stat'>({t:.2f})</span></td>
        </tr>"""

    html_template = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: 'Times New Roman', Times, serif; font-size: 14px; margin: 40px; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 900px; margin-bottom: 30px; }}
    th, td {{ padding: 10px; text-align: center; }}
    th {{ border-top: 2px solid black; border-bottom: 1px solid black; font-weight: normal; }}
    td {{ border-bottom: none; }}
    .table-title {{ font-weight: bold; font-size: 16px; margin-bottom: 10px; }}
    .panel-title {{ font-style: italic; text-align: left; padding-top: 15px; font-weight: bold; border-bottom: none; }}
    .bottom-border {{ border-bottom: 2px solid black; }}
    .t-stat {{ font-style: italic; font-size: 13px; }}
    .note {{ font-size: 12px; margin-top: -20px; text-align: justify; max-width: 900px; }}
    .row-label {{ text-align: left; }}
</style>
</head>
<body>

<div class="table-title">Table 1. Returns of weekly portfolios sorted on MAX.</div>
<table>
    <thead>
        <tr>
            <th></th>
            <th colspan="5">MAX</th>
        </tr>
        <tr>
            <th class="row-label"></th>
            <th>Low</th>
            <th>2</th>
            <th>3</th>
            <th>4</th>
            <th>High</th>
        </tr>
    </thead>
    <tbody>
        <tr><td colspan="6" class="panel-title">Panel A: Weekly portfolios sorted on MAX</td></tr>
        <tr><td colspan="6" class="panel-title" style="font-weight: normal;">Panel A.1: equal-weighted</td></tr>
        <tr>
            <td class="row-label"></td>
            <td>{stats_pa_ew[0]['mean']:.3f}<br><span class='t-stat'>({stats_pa_ew[0]['t']:.2f})</span></td>
            <td>{stats_pa_ew[1]['mean']:.3f}<br><span class='t-stat'>({stats_pa_ew[1]['t']:.2f})</span></td>
            <td>{stats_pa_ew[2]['mean']:.3f}<br><span class='t-stat'>({stats_pa_ew[2]['t']:.2f})</span></td>
            <td>{stats_pa_ew[3]['mean']:.3f}<br><span class='t-stat'>({stats_pa_ew[3]['t']:.2f})</span></td>
            <td>{stats_pa_ew[4]['mean']:.3f}<br><span class='t-stat'>({stats_pa_ew[4]['t']:.2f})</span></td>
        </tr>
        <tr><td colspan="6" class="panel-title" style="font-weight: normal;">Panel A.2: value-weighted</td></tr>
        <tr class="bottom-border">
            <td class="row-label"></td>
            <td>{stats_pa_vw[0]['mean']:.3f}<br><span class='t-stat'>({stats_pa_vw[0]['t']:.2f})</span></td>
            <td>{stats_pa_vw[1]['mean']:.3f}<br><span class='t-stat'>({stats_pa_vw[1]['t']:.2f})</span></td>
            <td>{stats_pa_vw[2]['mean']:.3f}<br><span class='t-stat'>({stats_pa_vw[2]['t']:.2f})</span></td>
            <td>{stats_pa_vw[3]['mean']:.3f}<br><span class='t-stat'>({stats_pa_vw[3]['t']:.2f})</span></td>
            <td>{stats_pa_vw[4]['mean']:.3f}<br><span class='t-stat'>({stats_pa_vw[4]['t']:.2f})</span></td>
        </tr>
        <tr><td colspan="6" class="panel-title">Panel B: Weekly portfolios sorted on MAX (skip 1 week)</td></tr>
        <tr><td colspan="6" class="panel-title" style="font-weight: normal;">Panel B.1: equal-weighted</td></tr>
        <tr>
            <td class="row-label"></td>
            <td>{stats_pb_ew[0]['mean']:.3f}<br><span class='t-stat'>({stats_pb_ew[0]['t']:.2f})</span></td>
            <td>{stats_pb_ew[1]['mean']:.3f}<br><span class='t-stat'>({stats_pb_ew[1]['t']:.2f})</span></td>
            <td>{stats_pb_ew[2]['mean']:.3f}<br><span class='t-stat'>({stats_pb_ew[2]['t']:.2f})</span></td>
            <td>{stats_pb_ew[3]['mean']:.3f}<br><span class='t-stat'>({stats_pb_ew[3]['t']:.2f})</span></td>
            <td>{stats_pb_ew[4]['mean']:.3f}<br><span class='t-stat'>({stats_pb_ew[4]['t']:.2f})</span></td>
        </tr>
        <tr><td colspan="6" class="panel-title" style="font-weight: normal;">Panel B.2: value-weighted</td></tr>
        <tr class="bottom-border">
            <td class="row-label"></td>
            <td>{stats_pb_vw[0]['mean']:.3f}<br><span class='t-stat'>({stats_pb_vw[0]['t']:.2f})</span></td>
            <td>{stats_pb_vw[1]['mean']:.3f}<br><span class='t-stat'>({stats_pb_vw[1]['t']:.2f})</span></td>
            <td>{stats_pb_vw[2]['mean']:.3f}<br><span class='t-stat'>({stats_pb_vw[2]['t']:.2f})</span></td>
            <td>{stats_pb_vw[3]['mean']:.3f}<br><span class='t-stat'>({stats_pb_vw[3]['t']:.2f})</span></td>
            <td>{stats_pb_vw[4]['mean']:.3f}<br><span class='t-stat'>({stats_pb_vw[4]['t']:.2f})</span></td>
        </tr>
    </tbody>
</table>
<div class="note">Note: This table reports the time-series average of weekly portfolio returns (in %). Portfolios are sorted cross-sectionally based on MAX. Newey-West adjusted t-statistics are in parentheses. The High-minus-Low spread is excluded per design choice.</div>

<br><br>

<div class="table-title">Table 13. Fama-MacBeth cross-sectional regressions.</div>
<table>
    <thead>
        <tr>
            <th class="row-label" style="width: 40%;">Variables</th>
            <th style="width: 60%;">(1)</th>
        </tr>
    </thead>
    <tbody class="bottom-border">
{fmb_row('Intercept', 'alpha')}
{fmb_row('MAX', 'MAX_t_minus_2')}
{fmb_row('BETA', 'BETA_t_minus_1')}
{fmb_row('SIZE', 'log_ME_t_minus_1')}
{fmb_row('MOM', 'MOM_raw_t_minus_1')}
{fmb_row('IVOL', 'IVOL_t_minus_1')}
{fmb_row('TVOL', 'TVOL_26w_t_minus_1')}
{fmb_row('ILLIQ', 'ILLIQ_t_minus_1')}
    </tbody>
</table>
<div class="note">Note: This table reports the time-series average of slopes from week-by-week Fama&ndash;MacBeth (1973) cross-sectional regressions. The dependent variable is the weekly stock return from week <i>t</i> (in %). Independent variables are standardized to a mean of 0 and a standard deviation of 1 within each week (Chen et al., 2025, Table 13). Newey&ndash;West (1987, 1994) adjusted <i>t</i>-statistics with automatic lag selection are reported in parentheses. ***, **, and * denote statistical significance at the 1%, 5%, and 10% levels, respectively.</div>

<br><br>
<div style="page-break-before: always;"></div>

<div class="table-title">Appendix: Variable Definitions and Construction</div>
<table style="max-width: 900px;">
    <thead>
        <tr>
            <th class="row-label" style="width: 15%;">Variable</th>
            <th style="width: 45%; text-align: left;">Definition &amp; Construction</th>
            <th style="width: 40%; text-align: left;">Paper Source</th>
        </tr>
    </thead>
    <tbody class="bottom-border">
        <tr>
            <td class="row-label"><b>RET</b></td>
            <td style="text-align: left;">Weekly stock return, computed by geometrically compounding daily returns within each Monday&ndash;Friday week: RET = &Pi;(1 + r<sub>d</sub>) &minus; 1. Expressed in percentage terms. Excess return = RET &minus; CD91.</td>
            <td style="text-align: left;">&ldquo;The CRSP daily data files are used to help construct weekly stock returns.&rdquo; (Section 3)</td>
        </tr>
        <tr>
            <td class="row-label"><b>MAX</b></td>
            <td style="text-align: left;">Maximum daily return within a week. MAX = max(r<sub>Mon</sub>, r<sub>Tue</sub>, ..., r<sub>Fri</sub>). Table 1 sorts on MAX from week <i>t</i>&minus;1 (Panel A) or <i>t</i>&minus;2 (Panel B). Table 13 uses MAX at <i>t</i>&minus;2.</td>
            <td style="text-align: left;">&ldquo;MAX is defined as the largest daily return in a week.&rdquo; (Section 3) &ldquo;We measure the Max at month/week <i>t</i>&minus;2.&rdquo; (Table 13 footnote)</td>
        </tr>
        <tr>
            <td class="row-label"><b>BETA</b></td>
            <td style="text-align: left;">CAPM market beta, estimated via OLS regression of firm weekly excess return on MKT<sub>rf</sub> using a 26-week rolling window (weeks <i>t</i>&minus;26 to <i>t</i>&minus;1). Minimum 10 valid observations required. Lagged by 1 week.</td>
            <td style="text-align: left;">&ldquo;BETA is the market beta. We follow Scholes and Williams (1977) and Dimson (1979) and use the lag and lead of the market portfolio as well as the current market when estimating beta.&rdquo; (Table 13 footnote)</td>
        </tr>
        <tr>
            <td class="row-label"><b>SIZE</b></td>
            <td style="text-align: left;">Natural logarithm of market capitalization. SIZE = ln(ME), where ME is the average daily market equity within the week. Lagged by 1 week.</td>
            <td style="text-align: left;">&ldquo;SIZE is the natural logarithm of the market capitalization.&rdquo; (Table 13 footnote)</td>
        </tr>
        <tr>
            <td class="row-label"><b>MOM</b></td>
            <td style="text-align: left;">Momentum: cumulative geometric return from week <i>t</i>&minus;13 to <i>t</i>&minus;2 (approximately months <i>t</i>&minus;2 to <i>t</i>&minus;12 in weekly terms). MOM = &Pi;(1 + r<sub>w</sub>) &minus; 1 over 12 weeks, shifted by 2 weeks.</td>
            <td style="text-align: left;">&ldquo;MOM is the cumulative return from month <i>t</i>&minus;2 to month <i>t</i>&minus;12.&rdquo; (Table 13 footnote)</td>
        </tr>
        <tr>
            <td class="row-label"><b>IVOL</b></td>
            <td style="text-align: left;">Idiosyncratic volatility: standard deviation of residuals from a weekly FF4 factor regression (firm excess return ~ MKT<sub>rf</sub> + SMB + HML + UMD) using a 26-week rolling window. Minimum 10 valid observations. Lagged by 1 week.</td>
            <td style="text-align: left;">&ldquo;IVOL [is] idiosyncratic volatility.&rdquo; (Table 13 footnote). Estimation uses Fama&ndash;French&ndash;Carhart 4-factor model residuals.</td>
        </tr>
        <tr>
            <td class="row-label"><b>TVOL</b></td>
            <td style="text-align: left;">Total volatility: standard deviation of weekly returns over a 26-week rolling window (weeks <i>t</i>&minus;26 to <i>t</i>&minus;1). Minimum 10 valid observations. Lagged by 1 week.</td>
            <td style="text-align: left;">&ldquo;TVOL [is] total volatility.&rdquo; (Table 13 footnote)</td>
        </tr>
        <tr>
            <td class="row-label"><b>ILLIQ</b></td>
            <td style="text-align: left;">Amihud (2002) illiquidity measure: ILLIQ = mean(|r<sub>d</sub>| / Volume<sub>d</sub>) &times; 10<sup>8</sup>, averaged over daily observations from weeks <i>t</i>&minus;1 to <i>t</i>&minus;4 (4-week rolling mean). Lagged by 1 week.</td>
            <td style="text-align: left;">&ldquo;ILLIQ is Amihud (2002)&rsquo;s illiquidity measure.&rdquo; (Table 13 footnote) &ldquo;We estimate Illiquidity using daily data from weeks <i>t</i>&minus;1 to <i>t</i>&minus;4.&rdquo; (Section 3)</td>
        </tr>
        <tr>
            <td class="row-label"><b>CD91</b></td>
            <td style="text-align: left;">Weekly risk-free rate derived from the 91-day certificate of deposit rate. Used to compute excess returns: RET<sub>excess</sub> = RET &minus; CD91.</td>
            <td style="text-align: left;">Source: FF4 weekly factor data file (Korean market equivalent of U.S. Treasury bill rate).</td>
        </tr>
    </tbody>
</table>

<div class="table-title" style="margin-top: 20px;">Methodology Notes</div>
<table style="max-width: 900px;">
    <thead>
        <tr>
            <th class="row-label" style="width: 25%;">Method</th>
            <th style="width: 75%; text-align: left;">Description</th>
        </tr>
    </thead>
    <tbody class="bottom-border">
        <tr>
            <td class="row-label"><b>Winsorization</b></td>
            <td style="text-align: left;">All variables are cross-sectionally winsorized at the 1st and 99th percentiles within each week. This follows standard empirical finance practice to mitigate the influence of extreme outliers.</td>
        </tr>
        <tr>
            <td class="row-label"><b>Standardization</b></td>
            <td style="text-align: left;">&ldquo;Independent variables are standardized to a mean of 0 and a standard deviation of 1.&rdquo; (Table 13 footnote). Standardization is applied cross-sectionally within each week before running OLS.</td>
        </tr>
        <tr>
            <td class="row-label"><b>Newey&ndash;West</b></td>
            <td style="text-align: left;">&ldquo;Newey&ndash;West (1987, 1994) adjusted <i>t</i>-statistics with automatic lag selection.&rdquo; Maximum lag = &lfloor;4 &times; (T/100)<sup>2/9</sup>&rfloor;, where T is the number of weekly observations.</td>
        </tr>
        <tr>
            <td class="row-label"><b>Portfolio VW</b></td>
            <td style="text-align: left;">Value-weighted portfolio returns use lagged market equity (ME from week <i>t</i>&minus;1) as weights to avoid look-ahead bias.</td>
        </tr>
        <tr>
            <td class="row-label"><b>Rolling windows</b></td>
            <td style="text-align: left;">BETA, IVOL, and TVOL use 26-week (half-year) rolling windows of <i>weekly</i>-frequency data. ILLIQ uses a 4-week rolling window of <i>daily</i>-frequency data.</td>
        </tr>
        <tr>
            <td class="row-label"><b>Data</b></td>
            <td style="text-align: left;">Korean stock market daily data (2005&ndash;2024). Common stocks listed on KRX. Source: daily_characteristics.sas7bdat, ff4_weekly.sas7bdat.</td>
        </tr>
        <tr>
            <td class="row-label"><b>Unavailable</b></td>
            <td style="text-align: left;">BM (book-to-market ratio) is not computed because book equity data is not available in the raw daily data file. The paper includes BM as a control in its full specification.</td>
        </tr>
    </tbody>
</table>

<div class="note" style="margin-top: 10px;">Reference: Chen, C., Cohen, A., Liang, Q., Sun, L. (2025). &ldquo;Maxing out short-term reversals in weekly stock returns.&rdquo; <i>Journal of Empirical Finance</i>, 82, 101608.</div>
</body>
</html>
"""

    with open(NOTEBOOK_DIR / 'table_replication.html', 'w') as f:
        f.write(html_template)
        
    print(f"Check final rendered output at: {NOTEBOOK_DIR / 'table_replication.html'}")

if __name__ == "__main__":
    main()
