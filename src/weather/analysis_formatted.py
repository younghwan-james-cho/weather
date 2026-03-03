"""
Weather Analysis with Correct Output Format
- Separate tables per Weather Variable x Sort Variable (MAX, IVOL)
- FIXED: Difference t-stats calculated via pooled regression
         (because each month has only ONE weather state)
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

# Config
WEATHER_VARS = ['d_cloud', 'd_sun', 'd_tempr', 'd_humd', 'd_wind', 'd_precip']
WEATHER_LABELS = {
    'd_cloud': 'Cloudy',
    'd_sun': 'Sunshine', 
    'd_tempr': 'Temperature',
    'd_humd': 'Humidity',
    'd_wind': 'Wind',
    'd_precip': 'Precipitation'
}
SORT_VARS = ['max1', 'ivol']
THRESHOLD = (0.3, 0.7)
LAG = 4
N_GROUPS = 10


def nw_mean_t(series, lag=LAG):
    """Return (mean, t-stat) for a series using Newey-West."""
    series = np.array(series)
    series = series[~np.isnan(series)]
    if len(series) < lag + 1:
        return np.nan, np.nan
    try:
        res = sm.OLS(series, np.ones(len(series))).fit(
            cov_type='HAC', cov_kwds={'maxlags': lag}
        )
        return res.params[0], res.tvalues[0]
    except:
        return np.nan, np.nan


def diff_t_stat_pooled(series1, series2, lag=LAG):
    """
    Calculate t-stat for mean(series1) - mean(series2) using pooled regression.
    Model: Y = alpha + beta * D + epsilon, where D=1 for series1, D=0 for series2
    beta = mean(series1) - mean(series2), and we use HAC standard errors.
    """
    s1 = np.array(series1)
    s2 = np.array(series2)
    s1 = s1[~np.isnan(s1)]
    s2 = s2[~np.isnan(s2)]
    
    if len(s1) < 5 or len(s2) < 5:
        return np.nan, np.nan
    
    # Create pooled data
    Y = np.concatenate([s1, s2])
    D = np.concatenate([np.ones(len(s1)), np.zeros(len(s2))])
    X = sm.add_constant(D)
    
    try:
        res = sm.OLS(Y, X).fit(cov_type='HAC', cov_kwds={'maxlags': lag})
        # Coefficient on D is mean(s1) - mean(s2)
        return res.params[1], res.tvalues[1]
    except:
        return np.nan, np.nan


def load_data():
    """Load and merge all data."""
    print("Loading data...")
    firm = pd.read_parquet(DATA_DIR / "firm_char_clean.parquet")
    weather = pd.read_parquet(DATA_DIR / "weather_clean.parquet")
    factors = pd.read_parquet(DATA_DIR / "ff4_clean.parquet")
    
    if 'year_month' not in firm.columns:
        firm['year_month'] = firm['date'].dt.to_period('M').astype(str)
    if 'year_month' not in weather.columns:
        weather['year_month'] = weather['date'].dt.to_period('M').astype(str)
    if 'year_month' not in factors.columns:
        factors['year_month'] = factors['date'].dt.to_period('M').astype(str)
    
    factors = factors.rename(columns={
        'mkt': 'MKT', 'smb': 'SMB', 'hml': 'HML', 'umd': 'UMD', 'mkt_rf': 'MKT_RF'
    })
    
    df = firm.merge(weather, on='year_month', how='inner')
    df = df.sort_values(['permno', 'year_month'])
    df['retex_next'] = df.groupby('permno')['retex'].shift(-1)
    
    if 'mom' not in df.columns and 'mom12' in df.columns:
        df['mom'] = df['mom12']
    if 'ME' not in df.columns and 'size' in df.columns:
        df['ME'] = df['size']
    if 'ivol' not in df.columns and 'ivol_12m' in df.columns:
        df['ivol'] = df['ivol_12m']
        
    return df, factors


def classify_weather(weather_series, threshold=THRESHOLD):
    """Classify weather into High/Normal/Low."""
    low_th = weather_series.quantile(threshold[0])
    high_th = weather_series.quantile(threshold[1])
    
    conditions = [
        weather_series <= low_th,
        weather_series >= high_th
    ]
    choices = ['Low', 'High']
    return np.select(conditions, choices, default='Normal')


def run_portfolio_sort(df, factors, weather_var, sort_var, weighting='ew'):
    """
    Portfolio Sorting for ONE weather variable and ONE sort variable.
    Returns dict with monthly spread series for calculating difference t-stats.
    weighting: 'ew' (Equal-Weighted) or 'vw' (Value-Weighted)
    """
    df = df.copy()
    df['state'] = classify_weather(df[weather_var])
    df = df.dropna(subset=[sort_var, 'retex_next', 'ME', 'state'])
    
    # Store monthly spread series per state (for pooled comparison)
    spread_dict = {'High': {}, 'Normal': {}, 'Low': {}}
    results = {'High': {}, 'Normal': {}, 'Low': {}}
    
    for state in ['High', 'Normal', 'Low']:
        subset = df[df['state'] == state].copy()
        
        if len(subset) < 100:
            for a in ['Raw', 'CAPM', 'FF3', 'FF4']:
                results[state][a] = (np.nan, np.nan)
                spread_dict[state][a] = np.array([])
            continue
        
        subset['port'] = subset.groupby('year_month')[sort_var].transform(
            lambda x: pd.qcut(x.rank(method='first'), N_GROUPS, labels=False, duplicates='drop')
            if len(x) >= N_GROUPS else pd.Series([np.nan]*len(x), index=x.index)
        )
        subset = subset.dropna(subset=['port'])
        
        if weighting == 'vw':
            # Value-Weighted: Weighted average using Market Equity (ME)
            # Ensure ME is aligned (using previous month ME for weights is standard, assumed 'ME' is valid)
            port_ret = subset.groupby(['port', 'year_month']).apply(
                lambda x: np.average(x['retex_next'], weights=x['ME'])
            ).to_frame('ret').reset_index()
        else:
            # Equal-Weighted (default)
            port_ret = subset.groupby(['port', 'year_month'])['retex_next'].mean().to_frame('ret').reset_index()
        
        try:
            top = port_ret[port_ret['port'] == N_GROUPS - 1].set_index('year_month')['ret']
            bottom = port_ret[port_ret['port'] == 0].set_index('year_month')['ret']
            spread = (top - bottom).dropna()
            
            spread_df = spread.reset_index()
            spread_df.columns = ['year_month', 'spread']
            spread_df = spread_df.merge(factors, on='year_month').dropna()
            
            if len(spread_df) < 12:
                for a in ['Raw', 'CAPM', 'FF3', 'FF4']:
                    results[state][a] = (np.nan, np.nan)
                    spread_dict[state][a] = np.array([])
                continue
            
            y = spread_df['spread'].values
            
            # Raw
            results[state]['Raw'] = nw_mean_t(y)
            spread_dict[state]['Raw'] = y
            
            # CAPM
            try:
                model = sm.OLS(y, sm.add_constant(spread_df[['MKT']].values))
                res = model.fit(cov_type='HAC', cov_kwds={'maxlags': LAG})
                results[state]['CAPM'] = (res.params[0], res.tvalues[0])
                # Alpha series
                alpha_series = y - res.params[1:] @ spread_df[['MKT']].values.T
                spread_dict[state]['CAPM'] = alpha_series
            except:
                results[state]['CAPM'] = (np.nan, np.nan)
                spread_dict[state]['CAPM'] = np.array([])
            
            # FF3
            try:
                model = sm.OLS(y, sm.add_constant(spread_df[['MKT', 'SMB', 'HML']].values))
                res = model.fit(cov_type='HAC', cov_kwds={'maxlags': LAG})
                results[state]['FF3'] = (res.params[0], res.tvalues[0])
                alpha_series = y - res.params[1:] @ spread_df[['MKT', 'SMB', 'HML']].values.T
                spread_dict[state]['FF3'] = alpha_series
            except:
                results[state]['FF3'] = (np.nan, np.nan)
                spread_dict[state]['FF3'] = np.array([])
            
            # FF4
            try:
                model = sm.OLS(y, sm.add_constant(spread_df[['MKT', 'SMB', 'HML', 'UMD']].values))
                res = model.fit(cov_type='HAC', cov_kwds={'maxlags': LAG})
                results[state]['FF4'] = (res.params[0], res.tvalues[0])
                alpha_series = y - res.params[1:] @ spread_df[['MKT', 'SMB', 'HML', 'UMD']].values.T
                spread_dict[state]['FF4'] = alpha_series
            except:
                results[state]['FF4'] = (np.nan, np.nan)
                spread_dict[state]['FF4'] = np.array([])
                
        except:
            for a in ['Raw', 'CAPM', 'FF3', 'FF4']:
                results[state][a] = (np.nan, np.nan)
                spread_dict[state][a] = np.array([])
    
    # Calculate difference t-stats using pooled regression
    diff_results = {'Normal-High': {}, 'Normal-Low': {}}
    
    for alpha in ['Raw', 'CAPM', 'FF3', 'FF4']:
        normal_s = spread_dict.get('Normal', {}).get(alpha, np.array([]))
        high_s = spread_dict.get('High', {}).get(alpha, np.array([]))
        low_s = spread_dict.get('Low', {}).get(alpha, np.array([]))
        
        diff_results['Normal-High'][alpha] = diff_t_stat_pooled(normal_s, high_s)
        diff_results['Normal-Low'][alpha] = diff_t_stat_pooled(normal_s, low_s)
    
    return results, diff_results


def run_fama_macbeth(df, weather_var, interest_var):
    """Fama-MacBeth with difference t-stats via pooled regression."""
    df = df.copy()
    df['state'] = classify_weather(df[weather_var])
    
    # Base controls excluding interest variables (max1, ivol)
    base_controls = ['beta', 'log_size', 'bm', 'roe', 'retex', 'mom', 'illiq']
    
    # Define regression variables based on interest_var
    if interest_var == 'max1':
        regression_vars = ['max1'] + base_controls
    elif interest_var == 'ivol':
        regression_vars = ['ivol'] + base_controls
    else:
        # Fallback (should not happen with correct usage)
        regression_vars = [interest_var] + base_controls
        
    available_controls = [c for c in regression_vars if c in df.columns]
    
    df = df.dropna(subset=['retex_next', 'state'] + available_controls)
    
    results = {'High': {}, 'Normal': {}, 'Low': {}}
    lambda_dict = {'High': {}, 'Normal': {}, 'Low': {}}
    
    for state in ['High', 'Normal', 'Low']:
        subset = df[df['state'] == state].copy()
        
        if len(subset) < 500:
            for c in available_controls:
                results[state][c] = (np.nan, np.nan)
                lambda_dict[state][c] = np.array([])
            continue
        
        def cross_section(g):
            if len(g) < len(available_controls) + 2:
                return pd.Series([np.nan] * (len(available_controls) + 1), 
                               index=['const'] + available_controls)
            Y = g['retex_next']
            X = sm.add_constant(g[available_controls])
            try:
                return sm.OLS(Y, X).fit().params
            except:
                return pd.Series([np.nan] * (len(available_controls) + 1), 
                               index=['const'] + available_controls)
        
        lambdas = subset.groupby('year_month').apply(cross_section, include_groups=False)
        
        for col in available_controls:
            series = lambdas[col].dropna().values
            lambda_dict[state][col] = series
            results[state][col] = nw_mean_t(series)
    
    # Difference t-stats
    diff_results = {'Normal-High': {}, 'Normal-Low': {}}
    
    for col in available_controls:
        normal_s = lambda_dict.get('Normal', {}).get(col, np.array([]))
        high_s = lambda_dict.get('High', {}).get(col, np.array([]))
        low_s = lambda_dict.get('Low', {}).get(col, np.array([]))
        
        diff_results['Normal-High'][col] = diff_t_stat_pooled(normal_s, high_s)
        diff_results['Normal-Low'][col] = diff_t_stat_pooled(normal_s, low_s)
    
    return results, diff_results


def format_portfolio_table(results, diff_results, weather_label, sort_var):
    """Format portfolio results."""
    rows = []
    
    for alpha in ['Raw', 'CAPM', 'FF3', 'FF4']:
        row_est = {'': alpha, 'Type': 'Estimate'}
        for state in ['High', 'Normal', 'Low']:
            val, _ = results.get(state, {}).get(alpha, (np.nan, np.nan))
            row_est[state] = round(val, 2) if not np.isnan(val) else ''
        
        nh_val, _ = diff_results.get('Normal-High', {}).get(alpha, (np.nan, np.nan))
        nl_val, _ = diff_results.get('Normal-Low', {}).get(alpha, (np.nan, np.nan))
        row_est['Normal-High'] = round(nh_val, 2) if not np.isnan(nh_val) else ''
        row_est['Normal-Low'] = round(nl_val, 2) if not np.isnan(nl_val) else ''
        rows.append(row_est)
        
        row_t = {'': '', 'Type': 'T-value'}
        for state in ['High', 'Normal', 'Low']:
            _, t = results.get(state, {}).get(alpha, (np.nan, np.nan))
            row_t[state] = round(t, 2) if not np.isnan(t) else ''
        
        _, nh_t = diff_results.get('Normal-High', {}).get(alpha, (np.nan, np.nan))
        _, nl_t = diff_results.get('Normal-Low', {}).get(alpha, (np.nan, np.nan))
        row_t['Normal-High'] = round(nh_t, 2) if not np.isnan(nh_t) else ''
        row_t['Normal-Low'] = round(nl_t, 2) if not np.isnan(nl_t) else ''
        rows.append(row_t)
    
    return pd.DataFrame(rows)[['', 'Type', 'High', 'Normal', 'Low', 'Normal-High', 'Normal-Low']]


def format_fm_table(results, diff_results, weather_label, interest_var=None):
    """Format FM results."""
    rows = []
    
    factor_order = ['max1', 'beta', 'log_size', 'bm', 'roe', 'retex', 'mom', 'illiq', 'ivol']
    
    # Filter factors based on interest_var
    if interest_var == 'max1':
        factor_order = [f for f in factor_order if f != 'ivol']
    elif interest_var == 'ivol':
        factor_order = [f for f in factor_order if f != 'max1']
        # Move ivol to front
        if 'ivol' in factor_order:
            factor_order.remove('ivol')
            factor_order.insert(0, 'ivol')
    factor_labels = {
        'max1': 'MAX', 'beta': 'Beta', 'log_size': 'Log(ME)', 'bm': 'BM',
        'roe': 'OP', 'retex': 'Rev', 'mom': 'MOM', 'illiq': 'Illiq', 'ivol': 'IVOL'
    }
    
    for factor in factor_order:
        label = factor_labels.get(factor, factor.upper())
        
        row_est = {'': label, 'Type': 'Estimate'}
        for state in ['High', 'Normal', 'Low']:
            val, _ = results.get(state, {}).get(factor, (np.nan, np.nan))
            row_est[state] = round(val, 2) if not np.isnan(val) else ''
        
        nh_val, _ = diff_results.get('Normal-High', {}).get(factor, (np.nan, np.nan))
        nl_val, _ = diff_results.get('Normal-Low', {}).get(factor, (np.nan, np.nan))
        row_est['Normal-High'] = round(nh_val, 2) if not np.isnan(nh_val) else ''
        row_est['Normal-Low'] = round(nl_val, 2) if not np.isnan(nl_val) else ''
        rows.append(row_est)
        
        row_t = {'': '', 'Type': 'T-value'}
        for state in ['High', 'Normal', 'Low']:
            _, t = results.get(state, {}).get(factor, (np.nan, np.nan))
            row_t[state] = round(t, 2) if not np.isnan(t) else ''
        
        _, nh_t = diff_results.get('Normal-High', {}).get(factor, (np.nan, np.nan))
        _, nl_t = diff_results.get('Normal-Low', {}).get(factor, (np.nan, np.nan))
        row_t['Normal-High'] = round(nh_t, 2) if not np.isnan(nh_t) else ''
        row_t['Normal-Low'] = round(nl_t, 2) if not np.isnan(nl_t) else ''
        rows.append(row_t)
    
    return pd.DataFrame(rows)[['', 'Type', 'High', 'Normal', 'Low', 'Normal-High', 'Normal-Low']]


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    df, factors = load_data()
    
    print(f"Data loaded: {len(df)} observations")
    print(f"Date range: {df['year_month'].min()} to {df['year_month'].max()}")
    
    portfolio_tables = {}
    fm_tables = {}
    
    print("\n=== Portfolio Sorting Analysis ===")
    weighting_schemes = ['ew', 'vw']
    
    for weighting in weighting_schemes:
        print(f"  --- Weighting: {weighting.upper()} ---")
        for weather_var in WEATHER_VARS:
            for sort_var in SORT_VARS:
                print(f"  Processing {weather_var} + {sort_var.upper()}...")
                results, diff_results = run_portfolio_sort(df, factors, weather_var, sort_var, weighting=weighting)
                table = format_portfolio_table(results, diff_results, WEATHER_LABELS[weather_var], sort_var)
                portfolio_tables[(weather_var, sort_var, weighting)] = table
    
    print("\n=== Fama-MacBeth Analysis ===")
    print("\n=== Fama-MacBeth Analysis ===")
    for weather_var in WEATHER_VARS:
        print(f"  Processing {weather_var}...")
        for sort_var in SORT_VARS:
             print(f"    Sub-processing {sort_var} (separate regression)...")
             results, diff_results = run_fama_macbeth(df, weather_var, interest_var=sort_var)
             table = format_fm_table(results, diff_results, WEATHER_LABELS[weather_var], interest_var=sort_var)
             fm_tables[(weather_var, sort_var)] = table
    
    print("\n=== Saving Results ===")
    
    with pd.ExcelWriter(REPORT_DIR / "weather_analysis_formatted.xlsx") as writer:
        # Portfolio Sheets (EW and VW)
        for weighting in weighting_schemes:
            for sort_var in SORT_VARS:
                sheet_name = f"Portfolio_{sort_var.upper()}_{weighting.upper()}"
                start_row = 0
                
                for weather_var in WEATHER_VARS:
                    table = portfolio_tables[(weather_var, sort_var, weighting)]
                    header_df = pd.DataFrame([[f"Portfolio based on {sort_var.upper()} ({weighting.upper()}) - {WEATHER_LABELS[weather_var]}"]])
                    header_df.to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False, header=False)
                    table.to_excel(writer, sheet_name=sheet_name, startrow=start_row + 1, index=False)
                    start_row += len(table) + 4
        
        # Fama-MacBeth Sheets (Split by Sort Var i.e., Interest Var)
        for sort_var in SORT_VARS:
            sheet_name = f"FM_{sort_var.upper()}"
            start_row = 0
            
            for weather_var in WEATHER_VARS:
                table = fm_tables[(weather_var, sort_var)]
                header_df = pd.DataFrame([[f"Fama-MacBeth ({sort_var.upper()} model) - {WEATHER_LABELS[weather_var]}"]])
                header_df.to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False, header=False)
                table.to_excel(writer, sheet_name=sheet_name, startrow=start_row + 1, index=False)
                start_row += len(table) + 4
    
    print(f"Saved to {REPORT_DIR / 'weather_analysis_formatted.xlsx'}")
    
    print("\n=== Sample: Cloud Cover + MAX (Portfolio EW) ===")
    print(portfolio_tables[('d_cloud', 'max1', 'ew')])


if __name__ == "__main__":
    main()
