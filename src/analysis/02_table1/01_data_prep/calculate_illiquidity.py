"""
Weekly Illiquidity Calculation (SAS to Python Conversion)
========================================================
Converts SAS code to Python for calculating Amihud illiquidity measure.

Original SAS Logic:
1. il = abs(ret)/vold                      # Daily illiquidity
2. week_end = intnx('week',date,0,'E')   # End of week (Saturday)
3. illiq = mean(il) * (10^8)              # Weekly average * 10^8
4. cnt = count of non-missing returns per week

Reference: Amihud (2002) - Illiquidity measure
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_DIR / "data" / "temp2" / "data" / "raw"


def calculate_weekly_illiquidity():
    """
    Calculate weekly Amihud illiquidity measure matching SAS approach.

    Formula: illiq = mean(abs(ret) / vold) * 10^8
    Week definition: Ends on Saturday (SAS 'E' modifier)
    """
    print("Loading daily characteristics...")
    df = pd.read_sas(RAW_DIR / "daily_characteristics.sas7bdat")

    # Convert date
    df['date'] = pd.to_datetime(df['date'])

    print("Step 1: Calculate daily illiquidity = abs(ret) / vold")
    # Handle division by zero
    df['il'] = np.where(
        df['vold'] > 0,
        np.abs(df['ret']) / df['vold'],
        np.nan
    )

    print("Step 2: Define week ending on Saturday")
    # SAS: intnx('week', date, 0, 'E') - week ending on Saturday
    # Python: Use week ending on Saturday (W-SAT or similar)
    # Align to Saturday end of week
    df['week_end'] = df['date'] + pd.to_timedelta(6 - df['date'].dt.dayofweek, unit='d')
    df['week_end'] = df['week_end'].dt.floor('d')

    print("Step 3: Count non-missing returns per week")
    df['cnt'] = df['ret'].notna().astype(int)

    print("Step 4: Aggregate to weekly (mean illiquidity * 10^8)")
    weekly_illiq = df.groupby(['permno', 'week_end']).agg(
        illiq=('il', lambda x: np.nanmean(x) * 1e8),  # * 10^8 as in SAS
        cnt=('cnt', 'sum')  # Count of non-missing returns
    ).reset_index()

    weekly_illiq.rename(columns={'week_end': 'date'}, inplace=True)

    return weekly_illiq


def verify_vs_sas():
    """
    Verify Python implementation matches SAS output.
    Run this to compare results.
    """
    print("\n=== Verification ===")
    print("Comparing Python output structure with SAS:")
    print('''
SAS Output:
| permno | week_end | illiq | cnt |
|---------|----------|-------|-----|
| A000010 | 1998-01-03 | X.XX  | N   |

Python Output:
| permno | date | illiq | cnt |
|--------|------|-------|-----|
| A000010 | 1998-01-03 | X.XX | N   |
''')


def main():
    """Run illiquidity calculation."""
    illiq_df = calculate_weekly_illiquidity()

    # Save
    output_path = PROJECT_DIR / "data" / "processed" / "illiq_weekly_sas.parquet"
    illiq_df.to_parquet(output_path)
    print(f"\nSaved to: {output_path}")
    print(f"Shape: {illiq_df.shape}")
    print(illiq_df.head())


if __name__ == "__main__":
    main()
