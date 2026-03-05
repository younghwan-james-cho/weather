"""
Replication of Chen, Cohen, Liang & Sun (2025)
"Maxing out short-term reversals in weekly stock returns"
Journal of Empirical Finance 82, 101608

Applied to Korean stock market data (2005-2024).

Tables produced:
  - Table 1: Returns and alphas of weekly portfolios sorted on MAX
  - Table 13: Fama-MacBeth cross-sectional regressions

Modifications from original paper:
  - Korean market (KRX) instead of U.S. (CRSP)
  - Table 1: 5 quintiles, no High-minus-Low, alpha: FF4 only
  - Table 13: 1 column (weekly MAX), excludes REV & MAX×REV
  - Controls: MAX, ILLIQ, IVOL, TVOL (BM captured by HML factor)
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
RAW_DAILY_PATH = Path('/Users/younghwancho/dev/weather/data/raw/daily_characteristics.sas7bdat')
FF4_PATH = Path('/Users/younghwancho/dev/weather/data/raw/ff4_weekly.sas7bdat')
FIRM_CHAR_PATH = Path('/Users/younghwancho/dev/weather/data/temp2/data/raw/firm_char.sas7bdat')
CACHE_PATH = Path('/Users/younghwancho/dev/weather/data/processed/replication_cache.parquet')
OUTPUT_DIR = Path('/Users/younghwancho/dev/weather/analysis')
YEAR_START = 2005
YEAR_END = 2024
N_QUINTILES = 5


# ──────────────────────────────────────────────
# Utility Functions
# ──────────────────────────────────────────────

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
    if at >= 2.576:
        return '***'
    if at >= 1.960:
        return '**'
    if at >= 1.645:
        return '*'
    return ''


# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────

def compute_all_variables():
    """
    Compute ALL variables from raw data for self-contained replication.

    Data sources:
      - daily_characteristics.sas7bdat: daily ret, vold, ME
      - ff4_weekly.sas7bdat: MKT_rf, SMB, HML, UMD, CD91
      - firm_char.sas7bdat: BM (monthly)

    Variables computed (all per Chen et al. 2025):
      ┌─────────┬──────────────────────────────────────────────────────────────┐
      │ MAX     │ max daily return in a week (§2: "largest daily return")     │
      │ RET     │ geometric compound of daily returns within week             │
      │ TVOL    │ std of daily returns within week (Table 13 fn: "total vol") │
      │ ILLIQ   │ Amihud(2002): mean(|ret|/vol), 4-week rolling (§3, L286-8) │
      │ IVOL    │ FF4 residual std, 26-week rolling (Table 13 fn)            │
      │ BETA    │ Dimson(1979): lag+current+lead MKT, 26-week (§6.5, L5200)  │
      │ MOM     │ cum return, month t-2 to t-12 ≈ skip8+roll44 (L5173)       │
      │ SIZE    │ log(market cap) (Table 13 fn: "natural logarithm")         │
      │ BM      │ book-to-market ratio (Table 13 fn, from firm_char monthly) │
      └─────────┴──────────────────────────────────────────────────────────────┘
    """
    if CACHE_PATH.exists():
        print("Loading cached replication data...")
        return pd.read_parquet(CACHE_PATH)

    import datetime

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1: Load raw daily data
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[1/9] Loading raw daily data...")
    df_daily = pd.read_sas(str(RAW_DAILY_PATH))
    df_daily['date'] = pd.to_datetime(df_daily['date'])
    df_daily = df_daily[(df_daily['date'] >= '2005-01-01') &
                        (df_daily['date'] <= '2024-12-31')].copy()

    # Filter: weekdays only, remove extreme outliers (>±100%)
    df_daily['year'] = df_daily['date'].dt.isocalendar().year
    df_daily['week'] = df_daily['date'].dt.isocalendar().week
    df_daily['dayofweek'] = df_daily['date'].dt.dayofweek
    df_daily = df_daily[(df_daily['dayofweek'] <= 4) &
                        (df_daily['ret'] > -100) & (df_daily['ret'] < 100)].copy()

    print(f"       Daily obs: {len(df_daily):,}")

    # Load FF4 weekly factors
    df_ff4 = pd.read_sas(str(FF4_PATH))
    df_ff4['Date'] = pd.to_datetime(df_ff4['Date'])
    df_ff4 = df_ff4[(df_ff4['Date'] >= '2005-01-01') &
                    (df_ff4['Date'] <= '2024-12-31')].copy()
    df_ff4['year'] = df_ff4['Date'].dt.isocalendar().year
    df_ff4['week'] = df_ff4['Date'].dt.isocalendar().week

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2: Aggregate to weekly — MAX, RET, TVOL, raw ILLIQ, ME
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[2/9] Aggregating daily → weekly (MAX, RET, TVOL, ILLIQ)...")

    # Paper §2: "MAX is defined as the largest daily return in a week"
    # TVOL: std of daily returns within week
    # ILLIQ_daily: |ret| / dollar volume (Amihud 2002)
    df_daily['il'] = df_daily['ret'].abs() / df_daily['vold']
    df_daily['il'] = df_daily['il'].replace([np.inf, -np.inf], np.nan)
    df_daily['ret_plus_1'] = (df_daily['ret'] / 100.0) + 1.0

    w = df_daily.groupby(['permno', 'year', 'week'], as_index=False).agg(
        ILLIQ_raw_weekly=('il', 'mean'),       # Mean daily ILLIQ within week
        MAX=('ret', 'max'),                     # Max daily return
        TVOL=('ret', 'std'),                    # Std of daily returns
        RET_prod=('ret_plus_1', 'prod'),        # Geometric product
        ME_mean=('ME', 'mean'),                 # Average market cap
    )
    w['RET_raw'] = (w['RET_prod'] - 1.0) * 100.0   # Geometric weekly return (%)
    w.drop(columns=['RET_prod'], inplace=True)
    w['week_id'] = w['year'] * 100 + w['week']
    w.sort_values(['permno', 'year', 'week'], inplace=True)
    print(f"       Weekly obs: {len(w):,}, firms: {w['permno'].nunique():,}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3: ILLIQ — 4-week rolling Amihud (§3, L286-288)
    # Paper: "We estimate Illiquidity using daily data from weeks t-1 to t-4"
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[3/9] Computing ILLIQ (4-week rolling Amihud × 10⁸)...")
    w['ILLIQ'] = w.groupby('permno')['ILLIQ_raw_weekly'].transform(
        lambda x: x.rolling(window=4, min_periods=1).mean()
    ) * (10**8)
    w.drop(columns=['ILLIQ_raw_weekly'], inplace=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4: Merge FF4 factors, compute firm excess return
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[4/9] Merging FF4 factors...")
    ff_cols = ['year', 'week', 'MKT_rf', 'SMB', 'HML', 'UMD', 'CD91']
    w = w.merge(df_ff4[ff_cols], on=['year', 'week'], how='left')
    w['RET'] = w['RET_raw'] - w['CD91'].fillna(0)    # Excess return
    w['RET_excess_firm'] = w['RET']                    # For rolling regressions

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5: IVOL — FF4 residual std, 26-week rolling
    # Paper Table 13 fn: "IVOL [is] idiosyncratic volatility"
    # Implementation: regress weekly excess return on [MKT, SMB, HML, UMD],
    #   take std(residuals, ddof=1) over 26-week rolling window.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[5/9] Computing IVOL (FF4 residual std, 26-week rolling)...")
    def rolling_ivol(sub):
        sub = sub.sort_values('week_id')
        ret_ex = sub['RET_excess_firm'].values
        factors = sub[['MKT_rf', 'SMB', 'HML', 'UMD']].values
        n = len(ret_ex)
        ivols = np.full(n, np.nan)
        for i in range(25, n):  # 26-week window (indices 0..25)
            y = ret_ex[i-25:i+1]
            X = factors[i-25:i+1]
            mask = ~(np.isnan(y) | np.any(np.isnan(X), axis=1))
            if mask.sum() >= 10:  # min 10 valid obs
                y_m, X_m = y[mask], X[mask]
                X_m = np.column_stack([np.ones(X_m.shape[0]), X_m])
                try:
                    beta_hat = np.linalg.lstsq(X_m, y_m, rcond=None)[0]
                    resid = y_m - X_m @ beta_hat
                    ivols[i] = resid.std(ddof=1)
                except Exception:
                    pass
        return pd.Series(ivols, index=sub.index)

    w['IVOL'] = w.groupby('permno', group_keys=False).apply(rolling_ivol)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6: BETA — Dimson (1979) approach, 26-week rolling
    # Paper §6.5: "We follow Scholes and Williams (1977) and Dimson (1979)
    #   and use the lag and lead of the market portfolio as well as the
    #   current market when estimating beta."
    # β_Dimson = β_{MKT(t-1)} + β_{MKT(t)} + β_{MKT(t+1)}
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[6/9] Computing BETA (Dimson 1979: lag+current+lead MKT)...")
    ff_weekly = w[['week_id', 'MKT_rf']].drop_duplicates('week_id').sort_values('week_id')
    ff_weekly['MKT_rf_lag1'] = ff_weekly['MKT_rf'].shift(1)
    ff_weekly['MKT_rf_lead1'] = ff_weekly['MKT_rf'].shift(-1)
    w = w.merge(ff_weekly[['week_id', 'MKT_rf_lag1', 'MKT_rf_lead1']],
                on='week_id', how='left')

    def dimson_beta_firm(sub):
        sub = sub.sort_values('week_id')
        ret_ex = sub['RET_excess_firm'].values
        mkt_lag = sub['MKT_rf_lag1'].values
        mkt_cur = sub['MKT_rf'].values
        mkt_lead = sub['MKT_rf_lead1'].values
        n = len(ret_ex)
        betas = np.full(n, np.nan)
        for i in range(25, n):
            y = ret_ex[i-25:i+1]
            x0 = mkt_lag[i-25:i+1]
            x1 = mkt_cur[i-25:i+1]
            x2 = mkt_lead[i-25:i+1]
            mask = ~(np.isnan(y) | np.isnan(x0) | np.isnan(x1) | np.isnan(x2))
            if mask.sum() >= 10:
                y_m = y[mask]
                X_m = np.column_stack([np.ones(mask.sum()),
                                       x0[mask], x1[mask], x2[mask]])
                try:
                    coefs = np.linalg.lstsq(X_m, y_m, rcond=None)[0]
                    betas[i] = coefs[1] + coefs[2] + coefs[3]
                except Exception:
                    pass
        return pd.Series(betas, index=sub.index)

    w['BETA'] = w.groupby('permno', group_keys=False).apply(dimson_beta_firm)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 7: MOM — cumulative return, months t-2 to t-12
    # Paper Table 13 fn: "MOM is the cumulative return from month t-2
    #   to month t-12"
    # Weekly approx: skip 8 weeks (≈2 months), roll 44 weeks (≈10 months)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[7/9] Computing MOM (cumulative return, ~months t-2 to t-12)...")
    w['ret_factor'] = 1 + w['RET_raw'] / 100.0
    w['MOM'] = w.groupby('permno')['ret_factor'].transform(
        lambda x: x.shift(8).rolling(window=44, min_periods=20).apply(
            np.prod, raw=True) - 1
    ) * 100.0
    w.drop(columns=['ret_factor'], inplace=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 8: SIZE — log(market cap)
    # Paper Table 13 fn: "SIZE is the natural logarithm of the market
    #   capitalization"
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[8/9] Computing SIZE (log market cap)...")
    w['log_ME'] = np.log(w['ME_mean'].clip(lower=1e-10))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 9: Create lags (t-1, t-2) + BM + winsorize
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("[9/9] Creating lags, adding BM, winsorizing...")
    # Lag by 1 week (no look-ahead: these variables use data up to week t)
    lag1_cols = ['MAX', 'ME_mean', 'ILLIQ', 'TVOL', 'MOM', 'log_ME']
    for col in lag1_cols:
        w[f'{col}_t_minus_1'] = w.groupby('permno')[col].shift(1)
    # BETA uses shift(2) because Dimson regression includes MKT_rf_lead1
    # (= MKT at week t+1). So BETA[t] peeks 1 week ahead.
    # shift(2) ensures BETA_t_minus_1 = BETA computed at t-2,
    # whose lead = MKT at t-1, which is fully known at week t.
    w['BETA_t_minus_1'] = w.groupby('permno')['BETA'].shift(2)
    # IVOL uses shift(2) per paper: "idiosyncratic volatility from week
    # t-2 to week t-27" (L1604). IVOL[t] uses data [t-25, t], so
    # shift(2) makes IVOL_t_minus_1 = IVOL computed at t-2 → window [t-27, t-2].
    w['IVOL_t_minus_1'] = w.groupby('permno')['IVOL'].shift(2)
    # Lag by 2 weeks
    for col in ['MAX', 'ME_mean']:
        w[f'{col}_t_minus_2'] = w.groupby('permno')[col].shift(2)

    # BM from firm_char.sas7bdat (monthly → weekly)
    # Apply 6-month reporting lag per Fama-French methodology:
    # Accounting data at month M is not available until month M+6.
    print("       Loading BM from firm_char (with 6-month reporting lag)...")
    df_fc = pd.read_sas(str(FIRM_CHAR_PATH), encoding='latin1')
    df_fc['date'] = pd.to_datetime(df_fc['date'])
    df_fc = df_fc[['permno', 'date', 'bm']].dropna(subset=['bm']).copy()
    df_fc['permno'] = df_fc['permno'].astype(str).str.strip().str.encode('utf-8')
    # Apply 6-month reporting lag: data from month M becomes available at M+6
    df_fc['avail_date'] = df_fc['date'] + pd.DateOffset(months=6)
    df_fc['fc_year'] = df_fc['avail_date'].dt.year
    df_fc['fc_month'] = df_fc['avail_date'].dt.month
    df_fc = df_fc.sort_values('date').groupby(
        ['permno', 'fc_year', 'fc_month'], as_index=False).last()
    df_fc = df_fc[['permno', 'fc_year', 'fc_month', 'bm']]

    def week_to_month(year, week):
        try:
            d = datetime.date.fromisocalendar(int(year), int(week), 1)
            return d.year, d.month
        except Exception:
            return int(year), 1

    wym = w[['year', 'week']].drop_duplicates()
    results_list = wym.apply(lambda r: week_to_month(r['year'], r['week']), axis=1)
    wym['cal_year'] = [r[0] for r in results_list]
    wym['cal_month'] = [r[1] for r in results_list]
    w = w.merge(wym, on=['year', 'week'], how='left')
    w = w.merge(df_fc, left_on=['permno', 'cal_year', 'cal_month'],
                right_on=['permno', 'fc_year', 'fc_month'], how='left')
    w.drop(columns=['fc_year', 'fc_month', 'cal_year', 'cal_month'],
           errors='ignore', inplace=True)
    w.sort_values(['permno', 'week_id'], inplace=True)
    w['bm'] = w.groupby('permno')['bm'].ffill(limit=26)  # max 26 weeks (~6 months)
    w['BM_t_minus_1'] = w.groupby('permno')['bm'].shift(1)

    # Cross-sectional winsorization at 1%/99% per week
    cols_to_win = [
        'MAX_t_minus_1', 'MAX_t_minus_2', 'RET', 'RET_raw',
        'ILLIQ_t_minus_1', 'log_ME_t_minus_1', 'TVOL_t_minus_1',
        'BETA_t_minus_1', 'IVOL_t_minus_1', 'MOM_t_minus_1', 'BM_t_minus_1',
    ]
    for col in cols_to_win:
        if col not in w.columns:
            continue
        lb = w.groupby('week_id')[col].transform(lambda x: x.quantile(0.01))
        ub = w.groupby('week_id')[col].transform(lambda x: x.quantile(0.99))
        w[col] = w[col].clip(lower=lb, upper=ub)

    # Filter to sample period
    w = w[(w['year'] >= YEAR_START) & (w['year'] <= YEAR_END)].copy()

    # Cache for future runs
    w.to_parquet(CACHE_PATH, index=False)
    print(f"       Cached to {CACHE_PATH}")
    return w


def load_data():
    """Load fully computed replication dataset."""
    print("Loading data...")
    df = compute_all_variables()

    print(f"  Rows: {len(df):,}")
    print(f"  Weeks: {df['week_id'].nunique()}")
    print(f"  Period: {df['year'].min()}-{df['year'].max()}")

    # Verification: count non-null for every Table 13 variable
    print("\n  Variable verification (Table 13 controls):")
    verify_cols = [
        ('RET', 'Weekly excess return'),
        ('RET_raw', 'Weekly raw return'),
        ('MAX_t_minus_1', 'MAX (Panel A sort)'),
        ('MAX_t_minus_2', 'MAX (Panel B sort / Table 13)'),
        ('ME_mean_t_minus_1', 'Market cap (VW weight)'),
        ('MOM_t_minus_1', 'MOM: cum ret months t-2 to t-12'),
        ('BETA_t_minus_1', 'BETA: Dimson (1979)'),
        ('log_ME_t_minus_1', 'SIZE: log(market cap)'),
        ('BM_t_minus_1', 'BM: book-to-market'),
        ('IVOL_t_minus_1', 'IVOL: FF4 residual std'),
        ('TVOL_t_minus_1', 'TVOL: within-week daily std'),
        ('ILLIQ_t_minus_1', 'ILLIQ: 4-week Amihud'),
        ('MKT_rf', 'MKT excess return (factor)'),
        ('SMB', 'SMB factor'),
        ('HML', 'HML factor'),
        ('UMD', 'UMD factor'),
    ]
    for col, desc in verify_cols:
        if col in df.columns:
            n = df[col].notna().sum()
            print(f"    {col:25s} {n:>10,} ({n/len(df)*100:5.1f}%)  {desc}")
        else:
            print(f"    {col:25s}    MISSING     {desc}")

    return df


# ──────────────────────────────────────────────
# Table 1: Portfolio Sorts on MAX
# ──────────────────────────────────────────────

def compute_table1(df, ret_col='RET', ret_label='Excess',
                    ff4_cols=['MKT_rf', 'SMB', 'HML', 'UMD'],
                    n_groups=5):
    """
    Compute Table 1: portfolio sorts on MAX.

    For each panel (A: MAX_t-1, B: MAX_t-2):
      - Sort stocks into n_groups each week
      - Compute EW and VW returns per group-week
      - Time-series average with NW t-stat
      - High-minus-Low spread: Excess + FF4 alpha

    Args:
        ret_col: Column to use as return ('RET' for excess, 'RET_raw' for raw)
        ret_label: Label for the return type
        n_groups: Number of portfolio groups (5=quintile, 10=decile)
    """
    group_name = 'quintile' if n_groups == 5 else 'decile'
    print(f"\n{'='*60}")
    print(f"TABLE 1 ({ret_label}, {group_name}): Weekly portfolios sorted on MAX")
    print(f"{'='*60}")

    panels = {
        'A': {'max_col': 'MAX_t_minus_1', 'label': 'MAX from week t-1'},
        'B': {'max_col': 'MAX_t_minus_2', 'label': 'MAX from week t-2 (skip 1 week)'},
    }
    results = {}

    for panel_key, panel_cfg in panels.items():
        max_col = panel_cfg['max_col']
        me_col = 'ME_mean_t_minus_1'

        print(f"\n  Panel {panel_key}: {panel_cfg['label']}")

        # Drop rows missing sort var, return, or market cap
        df_panel = df.dropna(subset=[max_col, ret_col, me_col]).copy()

        # Collect per-group time series of EW and VW returns
        ew_series = {q: [] for q in range(n_groups)}
        vw_series = {q: [] for q in range(n_groups)}
        week_ids_list = []

        for week_id, group in df_panel.groupby('week_id'):
            if len(group) < n_groups:
                continue

            ranks = group[max_col].rank(method='first')
            try:
                grp_assign = pd.qcut(ranks, n_groups, labels=False, duplicates='drop')
            except ValueError:
                continue

            if grp_assign.nunique() < n_groups:
                continue

            week_ids_list.append(week_id)

            for q in range(n_groups):
                mask = grp_assign == q
                q_data = group[mask]
                if len(q_data) == 0:
                    ew_series[q].append(np.nan)
                    vw_series[q].append(np.nan)
                    continue

                ew_series[q].append(q_data[ret_col].mean())

                me = q_data[me_col].values
                ret = q_data[ret_col].values
                total_me = me.sum()
                if total_me > 0:
                    vw_series[q].append(np.sum(ret * me) / total_me)
                else:
                    vw_series[q].append(np.nan)

        n_weeks = len(week_ids_list)
        print(f"    Valid weeks: {n_weeks}")

        # Get FF4 factor data aligned with weeks
        week_ids_arr = np.array(week_ids_list)
        ff4_data = df[['week_id'] + ff4_cols].drop_duplicates('week_id').set_index('week_id')

        panel_results = {}
        for weight_type, series_dict in [('EW', ew_series), ('VW', vw_series)]:
            panel_results[weight_type] = {}

            # Group results
            for q in range(n_groups):
                ret_arr = np.array(series_dict[q])
                mean_val, t_val = nw_mean_tstat(ret_arr)

                panel_results[weight_type][q] = {
                    'excess_mean': mean_val,
                    'excess_t': t_val,
                }

                if n_groups == 5:
                    q_label = ['Low', '2', '3', '4', 'High'][q]
                else:
                    q_label = 'Low' if q == 0 else ('High' if q == n_groups - 1 else str(q + 1))
                print(f"    {weight_type} Q{q}({q_label}): "
                      f"{ret_label}={mean_val:.3f} (t={t_val:.2f})")

            # High-minus-Low spread
            hl_arr = np.array(series_dict[n_groups - 1]) - np.array(series_dict[0])

            # H-L Excess return
            hl_mean, hl_t = nw_mean_tstat(hl_arr)

            # H-L FF4 alpha: regress H-L returns on FF4 factors
            hl_df = pd.DataFrame({
                'ret': hl_arr,
                'week_id': week_ids_arr
            }).set_index('week_id')
            merged = hl_df.join(ff4_data, how='inner').dropna()

            if len(merged) > 10:
                y = merged['ret'].values
                X = sm.add_constant(merged[ff4_cols].values)
                T = len(y)
                maxlag = nw_auto_lag(T)
                try:
                    model = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': maxlag})
                    alpha = model.params[0]
                    alpha_t = model.tvalues[0]
                except Exception:
                    alpha, alpha_t = np.nan, np.nan
            else:
                alpha, alpha_t = np.nan, np.nan

            panel_results[weight_type]['HL'] = {
                'excess_mean': hl_mean,
                'excess_t': hl_t,
                'alpha': alpha,
                'alpha_t': alpha_t,
            }

            print(f"    {weight_type} H-L:     "
                  f"{ret_label}={hl_mean:.3f} (t={hl_t:.2f}), "
                  f"α_FF4={alpha:.3f} (t={alpha_t:.2f})")

        results[panel_key] = panel_results

    return results


# ──────────────────────────────────────────────
# Table 13: Fama-MacBeth Regressions
# ──────────────────────────────────────────────

def compute_table13(df):
    """
    Compute Table 13: Fama-MacBeth cross-sectional regressions.

    Equation (from paper, Eq. 3, excluding REV/interaction):
      Ret_raw_{i,t} = β₀ + β₁·MAX_{i,t-2} + β₂·MOM + β₃·BETA + β₄·SIZE
                      + β₅·BM + β₆·IVOL + β₇·TVOL + β₈·ILLIQ + ε

    Independent variables are cross-sectionally standardized (mean=0, std=1).
    Dependent variable is raw stock return in percentage terms.
    """
    print("\n" + "=" * 60)
    print("TABLE 13: Fama-MacBeth cross-sectional regressions")
    print("=" * 60)

    # All paper controls (Table 13 footnote order: MOM, BETA, SIZE, BM, IVOL, TVOL, ILLIQ)
    features = [
        'MAX_t_minus_2',
        'MOM_t_minus_1',
        'BETA_t_minus_1',
        'log_ME_t_minus_1',
        'BM_t_minus_1',
        'IVOL_t_minus_1',
        'TVOL_t_minus_1',
        'ILLIQ_t_minus_1',
    ]
    dep_var = 'RET_raw'  # Raw return per paper: "stock return at month/week t"

    # Listwise deletion per cross-section (standard FM approach)
    df_fm = df.replace([np.inf, -np.inf], np.nan).copy()
    df_fm = df_fm.dropna(subset=[dep_var] + features)

    print(f"  Usable rows: {len(df_fm):,}")
    min_obs = len(features) + 2

    coef_records = []
    adjr2_list = []

    for week_id, group in df_fm.groupby('week_id'):
        if len(group) < min_obs:
            continue

        y = group[dep_var].values

        # Cross-sectional standardization: mean=0, std=1 within each week
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
    n_weeks = len(df_coefs)
    print(f"  Valid weekly regressions: {n_weeks}")

    if n_weeks == 0:
        print("  ERROR: No valid regressions!")
        return {}

    var_labels = {
        'Intercept': 'Intercept',
        'MAX_t_minus_2': 'MAX',
        'MOM_t_minus_1': 'MOM',
        'BETA_t_minus_1': 'BETA',
        'log_ME_t_minus_1': 'SIZE',
        'BM_t_minus_1': 'BM',
        'IVOL_t_minus_1': 'IVOL',
        'TVOL_t_minus_1': 'TVOL',
        'ILLIQ_t_minus_1': 'ILLIQ',
    }

    results = {}
    print(f"\n  {'Variable':<15} {'Coeff':>10} {'t-stat':>10} {'Sig':>5}")
    print(f"  {'-'*42}")

    for col_key in ['Intercept'] + features:
        mean_val, t_val = nw_mean_tstat(df_coefs[col_key].values)
        stars = significance_stars(t_val)
        label = var_labels[col_key]
        results[col_key] = {'mean': mean_val, 't': t_val, 'label': label}
        print(f"  {label:<15} {mean_val:>10.4f} {t_val:>10.2f} {stars:>5}")

    avg_adjr2 = np.nanmean(adjr2_list)
    results['adj_r2'] = avg_adjr2
    print(f"  {'Adj. R²':<15} {avg_adjr2:>10.4f}")
    results['features'] = features

    return results


# ──────────────────────────────────────────────
# HTML Output
# ──────────────────────────────────────────────

def render_html(table1_results, table1_raw_results, table13_results,
                table1_decile_results=None):
    """Generate academic-format HTML with all tables."""

    def fmt_cell(mean_val, t_val):
        """Format a single cell: value with stars + t-stat."""
        stars = significance_stars(t_val)
        return (f"{mean_val:.3f}{stars}<br>"
                f"<span class='t-stat'>({t_val:.2f})</span>")

    def fmt_cell_4dp(mean_val, t_val):
        """Format for Table 13 (4 decimal places)."""
        stars = significance_stars(t_val)
        return (f"{mean_val:.4f}{stars}<br>"
                f"<span class='t-stat'>({t_val:.2f})</span>")

    def panel_rows(panel_key, panel_label, results, n_groups=5):
        """Generate HTML rows for one panel (works for any n_groups)."""
        rows = []
        panel_data = results[panel_key]
        total_cols = n_groups + 3  # row-label + n_groups + Excess + αFF4

        rows.append(f'<tr><td colspan="{total_cols}" class="panel-title">'
                    f'Panel {panel_key}: {panel_label}</td></tr>')

        for wt, wt_label in [('EW', 'equal-weighted'), ('VW', 'value-weighted')]:
            rows.append(f'<tr><td colspan="{total_cols}" class="panel-title" '
                        f'style="font-weight: normal;">Panel {panel_key}.{"1" if wt=="EW" else "2"}: '
                        f'{wt_label}</td></tr>')

            hl = panel_data[wt]['HL']
            cells = ''.join(
                f'<td>{fmt_cell(panel_data[wt][q]["excess_mean"], panel_data[wt][q]["excess_t"])}</td>'
                for q in range(n_groups)
            )
            cells += f'<td>{fmt_cell(hl["excess_mean"], hl["excess_t"])}</td>'
            cells += f'<td>{fmt_cell(hl["alpha"], hl["alpha_t"])}</td>'

            border = ' class="bottom-border"' if wt == 'VW' else ''
            rows.append(f'<tr{border}><td class="row-label"></td>{cells}</tr>')

        return '\n'.join(rows)

    def make_header(n_groups):
        """Generate <thead> for Table 1 with n_groups columns."""
        if n_groups == 5:
            gh = '<th>Low</th><th>2</th><th>3</th><th>4</th><th>High</th>'
        else:
            inner = ''.join(f'<th>{i+1}</th>' for i in range(1, n_groups - 1))
            gh = f'<th>Low</th>{inner}<th>High</th>'
        return f"""    <thead>
        <tr>
            <th class="row-label"></th>
            <th colspan="{n_groups}">MAX</th>
            <th colspan="2">High minus Low</th>
        </tr>
        <tr>
            <th class="row-label"></th>
            {gh}
            <th>Excess</th><th>&alpha;<sub>FF4</sub></th>
        </tr>
    </thead>"""

    def make_table1(title, subtitle, results, note, n_groups=5):
        """Generate a complete Table 1 HTML block."""
        hdr = make_header(n_groups)
        pa = panel_rows('A', 'Weekly portfolios sorted on MAX', results, n_groups)
        pb = panel_rows('B', 'Weekly portfolios sorted on MAX (skip 1 week)', results, n_groups)
        return f"""
<div class="table-title">{title}</div>
<div class="table-subtitle">{subtitle}</div>
<table>
{hdr}
    <tbody>
{pa}
{pb}
    </tbody>
</table>
<div class="note">
{note}
</div>"""

    # ── Table 13 rows ──
    var_order = ['Intercept'] + table13_results.get('features', [])
    t13_rows = []
    for key in var_order:
        r = table13_results[key]
        t13_rows.append(f'''<tr>
            <td class="row-label">{r['label']}</td>
            <td>{fmt_cell_4dp(r['mean'], r['t'])}</td>
        </tr>''')
    t13_rows.append(f'''<tr class="bottom-border">
        <td class="row-label">Adj. R²</td>
        <td>{table13_results['adj_r2']:.4f}</td>
    </tr>''')
    t13_html = '\n'.join(t13_rows)

    # ── Table 1 blocks ──
    t1_note = f"""Note: Quintile portfolios are formed each week by sorting stocks on MAX (maximum daily return).
Panel A sorts on MAX from week <i>t</i>&minus;1; Panel B sorts on MAX from week <i>t</i>&minus;2
(skipping week <i>t</i>&minus;1). High minus Low is the return spread between the highest and lowest
MAX quintiles. &alpha;<sub>FF4</sub> is from a time-series regression of the H&minus;L spread on the
Fama&ndash;French&ndash;Carhart four-factor model. Newey&ndash;West adjusted <i>t</i>-statistics
with automatic lag selection are in parentheses.
***, **, * denote significance at the 1%, 5%, 10% levels.
Sample: Korean stocks, {YEAR_START}&ndash;{YEAR_END}."""

    t1_excess = make_table1('Table 1', 'Returns and alphas of weekly portfolios sorted on MAX.',
                            table1_results, t1_note, 5)
    t1_raw = make_table1('Table 1 (Raw Return)',
                         'Raw returns and alphas of weekly portfolios sorted on MAX.',
                         table1_raw_results,
                         f"""Note: Same as Table 1 but reporting raw returns (not adjusted for the risk-free rate).
&alpha;<sub>FF4</sub> is from a time-series regression of the H&minus;L spread on the FF4 model.""", 5)

    t1_decile = ''
    if table1_decile_results is not None:
        t1_decile = make_table1('Table 1 (Decile)',
                                'Returns and alphas of weekly decile portfolios sorted on MAX.',
                                table1_decile_results,
                                f"""Note: Same methodology as Table 1 but using <b>decile</b> (10-group) sorts.
High minus Low is the spread between the highest and lowest MAX deciles.
Newey&ndash;West adjusted <i>t</i>-statistics with automatic lag selection are in parentheses.
Sample: Korean stocks, {YEAR_START}&ndash;{YEAR_END}.""", 10)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: 'Times New Roman', Times, serif; font-size: 14px; margin: 40px; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1100px; margin-bottom: 30px; }}
    th, td {{ padding: 8px 10px; text-align: center; }}
    th {{ border-top: 2px solid black; border-bottom: 1px solid black; font-weight: normal; }}
    td {{ border-bottom: none; }}
    .table-title {{ font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
    .table-subtitle {{ font-style: italic; font-size: 13px; margin-bottom: 15px; }}
    .panel-title {{ font-style: italic; text-align: left; padding-top: 15px;
                    font-weight: bold; border-bottom: none; }}
    .bottom-border td {{ border-bottom: 2px solid black; }}
    .t-stat {{ font-style: italic; font-size: 13px; }}
    .note {{ font-size: 12px; margin-top: -15px; text-align: justify; max-width: 1100px; }}
    .row-label {{ text-align: left; width: 5%; }}
</style>
</head>
<body>

{t1_excess}
<br>
{t1_raw}
<br>
{t1_decile}
<br>

<div class="table-title">Table 13</div>
<div class="table-subtitle">Fama&ndash;MacBeth cross-sectional regressions.</div>
<table>
    <thead>
        <tr>
            <th class="row-label" style="width: 40%;">Variables</th>
            <th style="width: 60%;">Weekly MAX</th>
        </tr>
    </thead>
    <tbody>
{t13_html}
    </tbody>
</table>
<div class="note">
Note: This table reports time-series averages of slopes from week-by-week
Fama&ndash;MacBeth (1973) cross-sectional regressions. The dependent variable is the
weekly stock return from week <i>t</i> (in percentage terms). MAX is the maximum daily
return within a week, measured at week <i>t</i>&minus;2. MOM is the cumulative return from
approximately month <i>t</i>&minus;2 to month <i>t</i>&minus;12 (44-week rolling window, skipping 8 weeks).
BETA is the CAPM beta estimated following Dimson (1979), using the lag, current, and lead
market returns over a 26-week rolling window. SIZE is the natural logarithm of market
capitalization. BM is the book-to-market ratio (monthly, forward-filled to weekly frequency).
IVOL is idiosyncratic volatility (FF4 residual std, 26-week rolling).
TVOL is total volatility (std of daily returns within a week). ILLIQ is Amihud (2002)&rsquo;s
illiquidity measure (4-week rolling).
Independent variables are standardized to a mean of 0 and a standard deviation of 1 within each week.
Newey&ndash;West (1987, 1994) adjusted <i>t</i>-statistics with automatic lag selection are in
parentheses. ***, **, * denote significance at the 1%, 5%, 10% levels.
Sample: Korean stocks, {YEAR_START}&ndash;{YEAR_END}.
</div>

</body>
</html>"""

    output_path = OUTPUT_DIR / 'table_replication.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nHTML saved to: {output_path}")
    return output_path


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Chen et al. (2025) Replication — Korean Market")
    print("=" * 60)

    df = load_data()
    table1_results = compute_table1(df, ret_col='RET', ret_label='Excess', n_groups=5)
    table1_raw_results = compute_table1(df, ret_col='RET_raw', ret_label='Raw', n_groups=5)
    table1_decile_results = compute_table1(df, ret_col='RET', ret_label='Excess', n_groups=10)
    table13_results = compute_table13(df)
    render_html(table1_results, table1_raw_results, table13_results,
                table1_decile_results=table1_decile_results)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)



if __name__ == "__main__":
    main()

