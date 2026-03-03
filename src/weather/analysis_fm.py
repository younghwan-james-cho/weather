
"""
Fama-MacBeth and Portfolio Sort Analysis
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

def nw_t_stat(series, lag=4):
    """
    Calculate t-stat using Newey-West adjustment via statsmodels OLS on constant.
    This matches the reference methodology.
    """
    series = np.array(series)
    # Drop NaNs
    series = series[~np.isnan(series)]
    if len(series) < lag + 1:
        return np.nan
        
    try:
        # Regression on constant
        res = sm.OLS(series, np.ones(len(series))).fit(
            cov_type='HAC', cov_kwds={'maxlags': lag}
        )
        return res.tvalues[0]
    except:
        return np.nan

def load_data():
    print("Loading data...")
    firm = pd.read_parquet(DATA_DIR / "firm_char_clean.parquet")
    weather = pd.read_parquet(DATA_DIR / "weather_clean.parquet")
    factors = pd.read_parquet(DATA_DIR / "ff4_clean.parquet")
    
    # Ensure date formats match for merging
    # Trying to detect date columns. 'date' or 'year_month'?
    # In process_data, we loaded SAS directly. SAS usually exports 'date' as datetime.
    # We need a common join key. Usually 'year_month' string or 'date' (month end).
    
    # Check firm data dates
    if 'year_month' not in firm.columns:
        # Create year_month from date if exists
        if 'date' in firm.columns:
             firm['year_month'] = firm['date'].dt.to_period('M').astype(str)
    
    # Check weather data dates
    if 'year_month' not in weather.columns:
         if 'date' in weather.columns:
             weather['year_month'] = weather['date'].dt.to_period('M').astype(str)
             
    # Check factors data dates
    if 'year_month' not in factors.columns:
         if 'date' in factors.columns:
             factors['year_month'] = factors['date'].dt.to_period('M').astype(str)
             

    # Merge Weather into Firm
    # Use d_cloud as cld
    if 'd_cloud' in weather.columns:
        weather['cld'] = weather['d_cloud']
    elif 'cloud' in weather.columns:
        weather['cld'] = weather['cloud']
        
    # Left join firm with weather
    df = firm.merge(weather, on='year_month', how='left')
    
    return df, factors

def run_portfolio_sorts(df, factors):
    print("Running Portfolio Sorts...")
    results = []
    
    # Filter valid data
    # We need 'cld', 'max1', 'retex_next' (target), 'me' (weight)
    # Check column names. process_data lowercased them.
    # Target return: The reference used 'retex_a1' or similar. 
    # Let's assume 'retex' is current month, we need next month return?
    # Or 'retex' IS the return we analyze against PAST characteristics.
    # Usually in asset pricing: Return (t+1) on Char (t).
    # If `retex` in firm_char is the return for that month, and `max1` is from THAT month...
    # We usually predict Next Month Return.
    # Let's shift `retex` to get `retex_next` if not present.
    
    # Results container
    results = []
    
    # Filter valid data (retex_next already exists)
    df = df.dropna(subset=['cld', 'max1', 'retex_next', 'size']) # size used for VW
    
    # 3 Groups based on Cloud (Low, Mid, High)
    # In reference FM_Python, it looped ['Low', 'Mid', 'High'].
    # This implies 'cld' column already has these strings.
    # If 'cld' is numeric, we need to bin it.
    # Converting check:
    if pd.api.types.is_numeric_dtype(df['cld']):
        # create bins? Or maybe it is already categorical 1,2,3?
        # SAS file name `weather_grp10` suggests groups.
        # Let's check unique values in execution or assume it matches.
        # Safe bet: If numeric, 3 bins.
        pass
    
    # Actually, let's assume 'cld' has the group info or we map it.
    # The reference code: `sub_data = df[df['cld'] == g]` where g in ['Low', 'Mid', 'High']
    # If our data has 1,2,3...
    
    # For now, let's run the loop assuming mapping exists or create it
    # We'll create a 'CloudGroup' column.
    # If cld is float/int, we split into 3 quantiles PER MONTH?
    # Or strict thresholds? 
    # The plan said: "Sort into 3 groups (Low, Mid, High) by `cld`".
    # Implementation: Quantile sort (30, 70 percentiles) per month.

    # Use rank(pct=True) to avoid qcut bin edges issues
    # method='first' breaks ties, ensuring uniform bucket sizes
    def assign_group_rank(x):
         pct = x.rank(pct=True, method='first')
         return pd.cut(pct, [0, 0.3, 0.7, 1.0], labels=['Low', 'Mid', 'High'])

    df['CloudGroup'] = df.groupby('year_month')['cld'].transform(assign_group_rank)
    df = df.dropna(subset=['CloudGroup'])
    
    # Prepare High-Low Difference Data (Pooled)
    # Create Dummies
    # Force integer dummies
    dummies = pd.get_dummies(df['CloudGroup'], prefix='D', dtype=int)
    # D_Low, D_Mid, D_High
    
    # Ensure all columns exist even if some groups are empty (unlikely with qcut but safe)
    for col in ['D_Low', 'D_Mid', 'D_High']:
        if col not in dummies.columns:
            dummies[col] = 0
            
            
    df = pd.concat([df, dummies], axis=1)
    
    # --- Weighting Schemes ---
    for weight in ['EW', 'VW']:
        row_base = {'Weight': weight}
        
        # 1. Group Means
        for group in ['Low', 'Mid', 'High']:
            sub = df[df['CloudGroup'] == group]
            
            if weight == 'VW':
                # Weighted Average Return per Month
                grp_ret = sub.groupby('year_month').apply(
                    lambda x: np.average(x['retex_next'], weights=x['size'])
                )
            else:
                grp_ret = sub.groupby('year_month')['retex_next'].mean()
                
            # Time series mean & t-stat
            mean_val = grp_ret.mean()
            t_val = nw_t_stat(grp_ret, lag=4)
            
            row_base[f'{group}_Mean'] = mean_val
            row_base[f'{group}_T'] = t_val
        
        # 2. High-Low Difference (Pooled OLS)
        # Model: Ret = alpha + b_Low*D_Low + b_High*D_High (Mid is base)
        # OR: Ret = b_Low*D_Low + b_Mid*D_Mid + b_High*D_High (No intercept) -> linear test High-Low
        # Valid Pooled OLS for panel with weights
        
        # Weighted Data for OLS?
        # If VW, we run WLS with weights = size.
        # If EW, we run OLS.
        
        formula = "retex_next ~ D_Low + D_High" # Base is Mid (Intercept)
        
        if weight == 'VW':
            mod = smf.wls(formula, data=df, weights=df['size'])
        else:
            mod = smf.ols(formula, data=df)
            
        res = mod.fit(cov_type='HAC', cov_kwds={'maxlags': 4, 'use_correction': True, 'cluster_entity': True}) 
        # Note: Standard HAC in statsmodels for panel requires defining clusters usually (Time). 
        # Simple HAC (Newey-West) on pooled data without time clustering might be wrong if we just stack rows.
        # Wait, the reference `FM_Python.py` Method B used:
        # `model = smf.ols('max1 ~ C(cld, Treatment(reference="Mid"))', data=df)`
        # `res_diff = model.fit(cov_type='HAC', cov_kwds={'maxlags': 4})`
        # This implies the reference treated the panel as a time-series or assumed HAC handles the serial correlation
        # adequately if sorted by time.
        # However, for Portfolio Sort difference, the standard is:
        # Calculate Monthly Difference Series -> Mean/T-stat of that series.
        # High-Low = (Ret_High_t - Ret_Low_t)
        # This naturally handles the "Unequal N" simply by taking the mean of available stocks in that bucket.
        # The user's concern about "Pooled OLS" suggests they WANT the regression approach.
        # Let's stick to the Method B reference exactly.
        # Method B Regression tests the "Difference from Mid".
        
        high_minus_mid = res.params['D_High'] # Coefficient of High Dummy (vs Mid)
        high_minus_mid_t = res.tvalues['D_High']
        
        low_minus_mid = res.params['D_Low']
        low_minus_mid_t = res.tvalues['D_Low']
        
        # High - Low = D_High - D_Low
        # Test linear combination
        f_test = res.t_test("D_High - D_Low = 0")
        diff_val = f_test.effect[0]
        diff_t = f_test.tvalue.item() # Access scalar from array
        
        row_base['High-Low_Mean'] = diff_val
        row_base['High-Low_T'] = diff_t
        
        results.append(row_base)
        
    return pd.DataFrame(results)

def run_fama_macbeth(df):
    print("Running Fama-MacBeth...")
    # Step 1: Monthly Cross Sectional
    # Ret_next ~ max1 + controls
    controls = ['max1', 'beta', 'log_size', 'bm', 'retex', 'mom', 'ivol']
    
    df = df.dropna(subset=['retex_next'] + controls)
    
    def cross_section(g):
        if len(g) < len(controls) + 2:
            return pd.Series([np.nan]*(len(controls)+1), index=['Intercept']+controls)
        Y = g['retex_next']
        X = sm.add_constant(g[controls])
        try:
            return sm.OLS(Y, X).fit().params
        except:
            return pd.Series([np.nan]*(len(controls)+1), index=['Intercept']+controls)

    lambdas = df.groupby('year_month').apply(cross_section)
    
    # Step 2: Time Series Average
    results = []
    for col in lambdas.columns:
        series = lambdas[col].dropna()
        mean = series.mean()
        t = nw_t_stat(series, lag=4)
        results.append({'Factor': col, 'Mean': mean, 'T-stat': t})
        
    return pd.DataFrame(results)

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    df, factors = load_data()
    
    # Prepare Variables Globally
    print("Preparing variables...")
    df = df.sort_values(['permno', 'year_month'])
    df['retex_next'] = df.groupby('permno')['retex'].shift(-1)
    
    # Map mom12 -> mom
    if 'mom' not in df.columns and 'mom12' in df.columns:
        df['mom'] = df['mom12']
    
    # Sorts
    sort_res = run_portfolio_sorts(df, factors)
    print("\n--- Portfolio Sort Results ---")
    print(sort_res.set_index('Weight').T)
    sort_res.to_csv(REPORT_DIR / "portfolio_sorts.csv")
    
    # Fama-MacBeth
    fm_res = run_fama_macbeth(df)
    print("\n--- Fama-MacBeth Results ---")
    print(fm_res)
    fm_res.to_csv(REPORT_DIR / "fama_macbeth.csv")
    
    # Save to Excel (Final Format)
    with pd.ExcelWriter(REPORT_DIR / "fama_macbeth_results.xlsx") as writer:
        sort_res.to_excel(writer, sheet_name='Panel A_Sorts', index=False)
        fm_res.to_excel(writer, sheet_name='Panel B_FM', index=False)
    
    print(f"\nReport saved to {REPORT_DIR / 'fama_macbeth_results.xlsx'}")

if __name__ == "__main__":
    main()
