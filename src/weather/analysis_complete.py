"""
Complete Weather Analysis: Portfolio Sorting + Fama-MacBeth
- Tests multiple weather variables
- Fixed 30/40/30 threshold
- Newey-West Lag 4
- Output format matching output_format.xlsx
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path
from itertools import product

PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

# Config
WEATHER_VARS = ['d_cloud', 'd_sun', 'd_tempr', 'd_humd', 'd_wind', 'd_precip']
THRESHOLD = (0.3, 0.7)  # 30/40/30
LAG = 4
N_GROUPS = 10  # For MAX1 portfolio sorting


def nw_t_stat(series, lag=LAG):
    """Newey-West t-stat via statsmodels OLS on constant."""
    series = np.array(series)
    series = series[~np.isnan(series)]
    if len(series) < lag + 1:
        return np.nan
    try:
        res = sm.OLS(series, np.ones(len(series))).fit(
            cov_type='HAC', cov_kwds={'maxlags': lag}
        )
        return res.tvalues[0]
    except:
        return np.nan


def gmm_alpha(y, X, lag=LAG):
    """Calculate alpha t-stat from regression."""
    try:
        model = sm.OLS(y, sm.add_constant(X))
        results = model.fit(cov_type='HAC', cov_kwds={'maxlags': lag})
        return results.params[0], results.tvalues[0]  # alpha, t-stat
    except:
        return np.nan, np.nan


def load_data():
    """Load and merge all data."""
    print("Loading data...")
    firm = pd.read_parquet(DATA_DIR / "firm_char_clean.parquet")
    weather = pd.read_parquet(DATA_DIR / "weather_clean.parquet")
    factors = pd.read_parquet(DATA_DIR / "ff4_clean.parquet")
    
    # Create year_month keys
    if 'year_month' not in firm.columns and 'date' in firm.columns:
        firm['year_month'] = firm['date'].dt.to_period('M').astype(str)
    if 'year_month' not in weather.columns and 'date' in weather.columns:
        weather['year_month'] = weather['date'].dt.to_period('M').astype(str)
    if 'year_month' not in factors.columns and 'date' in factors.columns:
        factors['year_month'] = factors['date'].dt.to_period('M').astype(str)
    
    # Standardize factor column names to uppercase
    factors = factors.rename(columns={
        'mkt': 'MKT', 'smb': 'SMB', 'hml': 'HML', 'umd': 'UMD', 'mkt_rf': 'MKT_RF'
    })
    
    # Merge
    df = firm.merge(weather, on='year_month', how='inner')
    
    # Create next month return
    df = df.sort_values(['permno', 'year_month'])
    df['retex_next'] = df.groupby('permno')['retex'].shift(-1)
    
    # Map variables
    if 'mom' not in df.columns and 'mom12' in df.columns:
        df['mom'] = df['mom12']
    if 'ME' not in df.columns and 'size' in df.columns:
        df['ME'] = df['size']
        
    return df, factors


def classify_weather(weather_series, threshold=THRESHOLD):
    """Classify weather into High/Normal/Low based on quantiles."""
    low_th = weather_series.quantile(threshold[0])
    high_th = weather_series.quantile(threshold[1])
    
    conditions = [
        weather_series <= low_th,
        weather_series >= high_th
    ]
    choices = ['Low', 'High']
    return np.select(conditions, choices, default='Normal')


def run_portfolio_sort(df, factors, weather_var, weighting='ew'):
    """
    Portfolio Sorting Analysis for a given weather variable.
    Returns MAX1 Long-Short spread alpha for each weather state.
    """
    df = df.copy()
    
    # Weather state classification (using full sample quantiles)
    df['state'] = classify_weather(df[weather_var])
    
    # Filter valid data
    df = df.dropna(subset=['max1', 'retex_next', 'ME', 'state'])
    
    results = {}
    states = ['High', 'Normal', 'Low']
    
    for state in states:
        subset = df[df['state'] == state].copy()
        
        if len(subset) < 100:
            results[state] = {'raw': (np.nan, np.nan), 'capm': (np.nan, np.nan), 
                            'ff3': (np.nan, np.nan), 'ff4': (np.nan, np.nan)}
            continue
        
        # Create MAX1 decile portfolios per month
        subset['port'] = subset.groupby('year_month')['max1'].transform(
            lambda x: pd.qcut(x.rank(method='first'), N_GROUPS, labels=False, duplicates='drop')
            if len(x) >= N_GROUPS else pd.Series([np.nan]*len(x), index=x.index)
        )
        subset = subset.dropna(subset=['port'])
        
        # Calculate portfolio returns
        if weighting == 'vw':
            subset['wret'] = subset['retex_next'] * subset['ME']
            port_ret = subset.groupby(['port', 'year_month']).agg({'wret': 'sum', 'ME': 'sum'})
            port_ret['ret'] = port_ret['wret'] / port_ret['ME']
        else:
            port_ret = subset.groupby(['port', 'year_month'])['retex_next'].mean().to_frame('ret')
        
        port_ret = port_ret.reset_index()
        
        # Long-Short spread (Top - Bottom)
        try:
            top = port_ret[port_ret['port'] == N_GROUPS - 1].set_index('year_month')['ret']
            bottom = port_ret[port_ret['port'] == 0].set_index('year_month')['ret']
            spread = (top - bottom).dropna()
            
            spread_df = spread.reset_index()
            spread_df.columns = ['year_month', 'spread']
            spread_df = spread_df.merge(factors, on='year_month').dropna()
            
            if len(spread_df) < 12:
                results[state] = {'raw': (np.nan, np.nan), 'capm': (np.nan, np.nan), 
                                'ff3': (np.nan, np.nan), 'ff4': (np.nan, np.nan)}
                continue
            
            y = spread_df['spread'].values
            
            # Raw (mean return & t-stat)
            raw_mean = np.mean(y)
            raw_t = nw_t_stat(y)
            
            # CAPM Alpha
            capm_alpha, capm_t = gmm_alpha(y, spread_df[['MKT']].values)
            
            # FF3 Alpha
            ff3_alpha, ff3_t = gmm_alpha(y, spread_df[['MKT', 'SMB', 'HML']].values)
            
            # FF4 Alpha
            ff4_alpha, ff4_t = gmm_alpha(y, spread_df[['MKT', 'SMB', 'HML', 'UMD']].values)
            
            results[state] = {
                'raw': (raw_mean, raw_t),
                'capm': (capm_alpha, capm_t),
                'ff3': (ff3_alpha, ff3_t),
                'ff4': (ff4_alpha, ff4_t)
            }
        except Exception as e:
            results[state] = {'raw': (np.nan, np.nan), 'capm': (np.nan, np.nan), 
                            'ff3': (np.nan, np.nan), 'ff4': (np.nan, np.nan)}
    
    return results


def run_fama_macbeth(df, weather_var):
    """
    Fama-MacBeth regression per weather state.
    Returns coefficient estimates and t-stats for each factor by weather state.
    """
    df = df.copy()
    
    # Weather state classification
    df['state'] = classify_weather(df[weather_var])
    
    # Control variables (matching output_format.xlsx)
    controls = ['max1', 'beta', 'log_size', 'bm', 'roe', 'retex', 'mom', 'illiq', 'ivol']
    
    # Filter available controls
    available_controls = [c for c in controls if c in df.columns]
    
    df = df.dropna(subset=['retex_next', 'state'] + available_controls)
    
    results = {}
    states = ['High', 'Normal', 'Low']
    
    for state in states:
        subset = df[df['state'] == state].copy()
        
        if len(subset) < 500:
            results[state] = {c: (np.nan, np.nan) for c in available_controls}
            continue
        
        # Step 1: Monthly cross-sectional regressions
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
        
        lambdas = subset.groupby('year_month').apply(cross_section)
        
        # Step 2: Time-series average with Newey-West
        state_results = {}
        for col in lambdas.columns:
            if col == 'const':
                continue
            series = lambdas[col].dropna()
            if len(series) < LAG + 1:
                state_results[col] = (np.nan, np.nan)
            else:
                mean = series.mean()
                t = nw_t_stat(series)
                state_results[col] = (mean, t)
        
        results[state] = state_results
    
    return results


def format_portfolio_results(all_results):
    """Format portfolio sorting results into DataFrame matching output_format."""
    rows = []
    
    for weather_var in WEATHER_VARS:
        for weight in ['ew', 'vw']:
            key = f"{weather_var}_{weight}"
            if key not in all_results:
                continue
            
            res = all_results[key]
            
            for alpha_type in ['raw', 'capm', 'ff3', 'ff4']:
                row = {
                    'Weather': weather_var,
                    'Weight': weight.upper(),
                    'Alpha': alpha_type.upper(),
                }
                
                for state in ['High', 'Normal', 'Low']:
                    val, t = res.get(state, {}).get(alpha_type, (np.nan, np.nan))
                    row[f'{state}_Est'] = val
                    row[f'{state}_T'] = t
                
                # Calculate differences
                normal_val = res.get('Normal', {}).get(alpha_type, (np.nan, np.nan))[0]
                high_val = res.get('High', {}).get(alpha_type, (np.nan, np.nan))[0]
                low_val = res.get('Low', {}).get(alpha_type, (np.nan, np.nan))[0]
                
                row['Normal-High_Est'] = normal_val - high_val if not (np.isnan(normal_val) or np.isnan(high_val)) else np.nan
                row['Normal-Low_Est'] = normal_val - low_val if not (np.isnan(normal_val) or np.isnan(low_val)) else np.nan
                
                rows.append(row)
    
    return pd.DataFrame(rows)


def format_fm_results(all_fm_results):
    """Format FM results into DataFrame matching output_format."""
    rows = []
    
    for weather_var in WEATHER_VARS:
        if weather_var not in all_fm_results:
            continue
        
        res = all_fm_results[weather_var]
        
        # Get all factors
        factors = list(res.get('High', {}).keys())
        
        for factor in factors:
            row = {
                'Weather': weather_var,
                'Factor': factor.upper(),
            }
            
            for state in ['High', 'Normal', 'Low']:
                val, t = res.get(state, {}).get(factor, (np.nan, np.nan))
                row[f'{state}_Est'] = val
                row[f'{state}_T'] = t
            
            # Calculate differences
            normal_val = res.get('Normal', {}).get(factor, (np.nan, np.nan))[0]
            high_val = res.get('High', {}).get(factor, (np.nan, np.nan))[0]
            low_val = res.get('Low', {}).get(factor, (np.nan, np.nan))[0]
            
            row['Normal-High_Est'] = normal_val - high_val if not (np.isnan(normal_val) or np.isnan(high_val)) else np.nan
            row['Normal-Low_Est'] = normal_val - low_val if not (np.isnan(normal_val) or np.isnan(low_val)) else np.nan
            
            rows.append(row)
    
    return pd.DataFrame(rows)


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    df, factors = load_data()
    
    print(f"Data loaded: {len(df)} observations")
    print(f"Date range: {df['year_month'].min()} to {df['year_month'].max()}")
    
    # Run Portfolio Sorts for all weather variables
    print("\n=== Portfolio Sorting Analysis ===")
    all_port_results = {}
    
    for weather_var in WEATHER_VARS:
        for weight in ['ew', 'vw']:
            print(f"  Processing {weather_var} ({weight.upper()})...")
            key = f"{weather_var}_{weight}"
            all_port_results[key] = run_portfolio_sort(df, factors, weather_var, weight)
    
    port_df = format_portfolio_results(all_port_results)
    
    # Run Fama-MacBeth for all weather variables
    print("\n=== Fama-MacBeth Analysis ===")
    all_fm_results = {}
    
    for weather_var in WEATHER_VARS:
        print(f"  Processing {weather_var}...")
        all_fm_results[weather_var] = run_fama_macbeth(df, weather_var)
    
    fm_df = format_fm_results(all_fm_results)
    
    # Save results
    print("\n=== Saving Results ===")
    
    with pd.ExcelWriter(REPORT_DIR / "weather_analysis_results.xlsx") as writer:
        port_df.to_excel(writer, sheet_name='Panel_A_Portfolio', index=False)
        fm_df.to_excel(writer, sheet_name='Panel_B_FM', index=False)
    
    port_df.to_csv(REPORT_DIR / "portfolio_results.csv", index=False)
    fm_df.to_csv(REPORT_DIR / "fm_results.csv", index=False)
    
    print(f"Saved to {REPORT_DIR / 'weather_analysis_results.xlsx'}")
    
    # Print summary
    print("\n=== Summary (Cloud Cover, EW, FF4 Alpha) ===")
    cloud_ew = port_df[(port_df['Weather'] == 'd_cloud') & 
                       (port_df['Weight'] == 'EW') & 
                       (port_df['Alpha'] == 'FF4')]
    if not cloud_ew.empty:
        print(cloud_ew[['High_Est', 'High_T', 'Normal_Est', 'Normal_T', 'Low_Est', 'Low_T']].to_string())


if __name__ == "__main__":
    main()
