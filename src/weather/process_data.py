import pandas as pd
import numpy as np
from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
TEMP2_RAW = PROJECT_DIR / "data" / "temp2" / "data" / "raw"

def winsorize_series(series, limits=(0.01, 0.01)):
    """Winsorize a pandas series at the given limits (lower, upper)."""
    return series.clip(lower=series.quantile(limits[0]), upper=series.quantile(1 - limits[1]))

def process_daily_to_weekly():
    print("Loading Daily Stock Characteristics (This may take a few minutes)...")
    # Load daily stock data
    df_daily = pd.read_sas(RAW_DIR / "korea_stock_chars_daily_2005_2024.sas7bdat")
    
    # Capitalize strictly for our columns if they are weirdly cased, SAS usually outputs standard
    # Let's just use the columns we need. We know they are:
    # 'date', 'permno', 'Foreign_dvol', 'Foreign_vol', 'Individual_dvol', 'Individual_vol', 
    # 'Institution_dvol', 'Institution_vol', 'ret', 'vold', 'ME'
    
    print("Formatting dates, enforcing decimal limits, and calculating Amihud + Log Returns...")
    # SAS dataset has 'ret' in percentage points (e.g., 5.0 for 5%). Convert to decimal.
    df_daily['ret'] = df_daily['ret'] / 100.0
    
    # Filter severe data errors (e.g. unadjusted price splits) bounds: [-99%, +200%]
    df_daily = df_daily[(df_daily['ret'] > -0.99) & (df_daily['ret'] < 2.0)]
    
    # Add Amihud daily before grouping
    df_daily['amihud_daily'] = df_daily['ret'].abs() / df_daily['vold']
    # Use log returns for blazing fast C-optimized compounding
    df_daily['log_ret'] = np.log1p(df_daily['ret'])
    
    # Sort and set index for grouping
    df_daily = df_daily.sort_values(['permno', 'date'])
    
    print("Grouping by Firm and W-TUE (Wednesday to Tuesday)...")
    # Group by permno and W-TUE
    # W-TUE implies the week ends on Tuesday.
    grouped = df_daily.groupby(['permno', pd.Grouper(key='date', freq='W-TUE')])
    
    print("Aggregating weekly variables (Vectorized)...")
    weekly_df = grouped.agg(
        log_ret_sum=('log_ret', 'sum'),
        MAX=('ret', 'max'),
        ME=('ME', 'last'), # End of week size
        vold_sum=('vold', 'sum'),
        Individual_dvol_sum=('Individual_dvol', 'sum'),
        ILLIQ=('amihud_daily', 'mean') # Weekly average of daily Amihud
    ).reset_index()
    
    # Recover compounded return from sum of log returns
    weekly_df['RET'] = np.expm1(weekly_df['log_ret_sum'])
    weekly_df.drop(columns=['log_ret_sum'], inplace=True)
    
    print("Calculating rolling retail imbalance and temporal shifts...")
    # Sort by permno and date to apply shifts securely
    weekly_df = weekly_df.sort_values(['permno', 'date'])
    
    # Calculate RETAIL_IMB (4-week rolling sum of net retail buy / 4-week rolling sum of total volume)
    # Using rolling on the dataframe grouped by permno
    rolling_4w = weekly_df.groupby('permno')[['Individual_dvol_sum', 'vold_sum']].rolling(window=4, min_periods=1).sum().reset_index(level=0, drop=True)
    weekly_df['RETAIL_IMB'] = rolling_4w['Individual_dvol_sum'] / rolling_4w['vold_sum']
    
    # Strict Temporal Separations
    # RET_t: Current week return (already in 'RET')
    weekly_df['MAX_t_minus_1'] = weekly_df.groupby('permno')['MAX'].shift(1) # Panel A No Skip
    weekly_df['MAX_t_minus_2'] = weekly_df.groupby('permno')['MAX'].shift(2) # Panel B Skip
    weekly_df['REV_t_minus_1'] = weekly_df.groupby('permno')['RET'].shift(1)
    weekly_df['SIZE_t_minus_1'] = weekly_df.groupby('permno')['ME'].shift(1)
    weekly_df['ILLIQ_t_minus_1'] = weekly_df.groupby('permno')['ILLIQ'].shift(1)
    weekly_df['RETAIL_IMB_t_minus_1'] = weekly_df.groupby('permno')['RETAIL_IMB'].shift(1)
    
    # Drop rows where we don't have the fundamental lagged variables to run the regression
    weekly_df = weekly_df.dropna(subset=['RET', 'REV_t_minus_1', 'MAX_t_minus_1', 'MAX_t_minus_2'])
    
    print("Winsorizing target variables...")
    winsor_vars = ['RET', 'REV_t_minus_1', 'MAX_t_minus_1', 'MAX_t_minus_2', 'SIZE_t_minus_1', 'ILLIQ_t_minus_1', 'RETAIL_IMB_t_minus_1']
    for v in winsor_vars:
        if v in weekly_df.columns:
            weekly_df[v] = winsorize_series(weekly_df[v])
            
    # Compute log size
    weekly_df['log_SIZE_t_minus_1'] = np.log(weekly_df['SIZE_t_minus_1'])
    
    return weekly_df

def process_weather_data():
    print("Processing National Weather & AQI...")
    # Load weather
    TEMP_DIR = PROJECT_DIR / "data" / "temp" / "data" / "processed"
    w_df = pd.read_csv(TEMP_DIR / "korea_weather_daily_pw.csv", parse_dates=['date'])
    
    # Load AQI
    a_df = pd.read_csv(TEMP_DIR / "korea_air_quality_daily_pw.csv", parse_dates=['date'])
    
    # Merge them
    env_df = pd.merge(w_df, a_df, on=['date', 'year'], how='outer')
    
    # Group by W-TUE
    env_weekly = env_df.groupby(pd.Grouper(key='date', freq='W-TUE')).agg({
        'cloud_cover_d': 'mean',
        'sunshine_d': 'mean',
        'apparent_temp_d': 'mean',
        'aqi_d': 'mean',
        'precipitation': 'sum',
        'temperature': 'mean'
    }).reset_index()
    
    # We want weather at t-1 to predict return at t
    # So we shift the weather variables by 1 row (1 week)
    # Actually, if we just shift the `date` by 1 week FORWARD, then a join on `date` will map week t-1 weather to week t's row!
    shift_cols = ['cloud_cover_d', 'sunshine_d', 'apparent_temp_d', 'aqi_d', 'precipitation', 'temperature']
    
    env_weekly_shifted = env_weekly.copy()
    for col in shift_cols:
        env_weekly_shifted[f'{col}_t_minus_1'] = env_weekly_shifted[col].shift(1)
        
    env_weekly_shifted = env_weekly_shifted[['date'] + [f'{col}_t_minus_1' for col in shift_cols]]
    
    return env_weekly_shifted

def process_factors():
    print("Processing Fama-French Weekly Factors...")
    # Dates are Saturdays.
    # To join with our Tuesday dates, we can map each Tuesday to the closest previous Saturday factor, or just week/year.
    # W-TUE week typically covers Wednesday to Tuesday.
    # The FF4 weekly factor ending on Friday/Saturday perfectly represents that same week's market movement.
    ff_df = pd.read_sas(RAW_DIR / "ff4_weekly_2005_2024.sas7bdat")
    
    # We will adjust FF4 Date to the following Tuesday to ensure a clean join on 'date'
    # Saturday + 3 days = Tuesday.
    ff_df['Date'] = ff_df['Date'] + pd.Timedelta(days=3)
    ff_df.rename(columns={'Date': 'date'}, inplace=True)
    
    return ff_df

def process_monthly_controls():
    print("Processing Legacy Monthly Control Variables (BM, BETA, MOM, IVOL)...")
    df = pd.read_sas(TEMP2_RAW / "firm_char.sas7bdat")
    df.columns = df.columns.str.lower()
    
    # Rename mom12 to mom
    if 'mom12' in df.columns:
        df.rename(columns={'mom12': 'mom'}, inplace=True)
        
    req_cols = ['permno', 'date', 'beta', 'mom', 'bm', 'ivol']
    df = df[[c for c in req_cols if c in df.columns]].copy()
    
    # Create a YearMonth string to merge with the weekly data
    # To prevent look-ahead bias, we shift the date forward by 1 month.
    # So end-of-January data applies to all weeks ending in February.
    df['date'] = pd.to_datetime(df['date'])
    df['applied_year_month'] = (df['date'] + pd.DateOffset(months=1)).dt.to_period('M').astype(str)
    
    # Drop the original date to avoid collision
    df.drop(columns=['date'], inplace=True)
    
    # Rename variables to match the t_minus_1 convention for regressions
    df.rename(columns={
        'beta': 'BETA_t_minus_1',
        'mom': 'MOM_t_minus_1',
        'bm': 'BM_t_minus_1',
        'ivol': 'IVOL_t_minus_1'
    }, inplace=True)
    
    return df

def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    weekly_stocks = process_daily_to_weekly()
    weekly_env = process_weather_data()
    weekly_ff = process_factors()
    monthly_ctrls = process_monthly_controls()
    
    print("Merging Data Streams...")
    # Add YearMonth to weekly_stocks to merge with the monthly_ctrls
    weekly_stocks['applied_year_month'] = weekly_stocks['date'].dt.to_period('M').astype(str)
    
    # Join monthly controls on permno + applied_year_month
    master_df = pd.merge(weekly_stocks, monthly_ctrls, on=['permno', 'applied_year_month'], how='left')
    master_df.drop(columns=['applied_year_month'], inplace=True)
    
    # Merge env
    master_df = pd.merge(master_df, weekly_env, on='date', how='left')
    
    # Merge FF4
    # We join on date (Tuesday to Tuesday)
    master_df = pd.merge(master_df, weekly_ff, on='date', how='left')
    
    out_path = PROCESSED_DIR / "firm_char_weekly.parquet"
    master_df.to_parquet(out_path)
    print(f"Pipeline Complete! Saved master file to {out_path} ({len(master_df)} rows)")

if __name__ == "__main__":
    main()
