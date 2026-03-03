"""
Illiquidity (Amihud 2002) Calculation - Saturday Week-Ending

This module calculates the Amihud (2002) illiquidity measure:
- Daily illiquidity: abs(ret) / vold
- Weekly aggregation: mean(illiquidity) * 10^8
- Week definition: Saturday week-ending
  - Matches SAS code: intnx('week', date, 0, 'E')

Reference:
    Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects.
    Journal of Financial Markets, 5(1), 31-56.
"""

import pandas as pd
import numpy as np
from pathlib import Path


# Week definition: Saturday week-ending
# Matches SAS: intnx('week', date, 0, 'E')
# Dayofweek: Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
WEEK_END_DAY = 5  # Saturday


def calculate_weekly_illiquidity(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate weekly illiquidity using Saturday week-ending.

    Formula (matches SAS code exactly):
        il = abs(ret) / vold
        illiq = mean(il) * 10^8

    Week definition: Saturday
        - Matches SAS: intnx('week', date, 0, 'E')
        - Dayofweek: Monday=0, ..., Saturday=5, Sunday=6

    Parameters
    ----------
    daily_df : pd.DataFrame
        Daily data with columns: date, permno, ret, vold

    Returns
    -------
    pd.DataFrame
        Weekly illiquidity with columns: permno, date (Saturday), illiq, cnt
    """
    df = daily_df.copy()

    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])

    # Step 1: Calculate daily illiquidity (il = abs(ret) / vold)
    # Handle division by zero
    df['il'] = np.where(
        df['vold'] > 0,
        df['ret'].abs() / df['vold'],
        np.nan
    )

    # Step 2: Count non-missing returns (cnt)
    df['cnt'] = df['ret'].notna().astype(int)

    # Step 3: Get Saturday week-end
    # Dayofweek: Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
    # For Saturday: days_to_end = (5 - dayofweek) % 7
    df['days_to_sat'] = (WEEK_END_DAY - df['date'].dt.dayofweek) % 7
    df['date'] = df['date'] + pd.to_timedelta(df['days_to_sat'], unit='D')

    # Step 4: Aggregate to weekly
    weekly_illiq = df.groupby(['permno', 'date'], as_index=False).agg(
        illiq=('il', 'mean'),
        cnt=('cnt', 'sum')
    )

    # Step 5: Multiply by 10^8 (standardization, matches SAS)
    weekly_illiq['illiq'] = weekly_illiq['illiq'] * 1e8

    return weekly_illiq[['permno', 'date', 'illiq', 'cnt']]


def calculate_weekly_illiquidity_pandas(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Alternative: Calculate weekly illiquidity using pandas W-SAT frequency.

    Parameters
    ----------
    daily_df : pd.DataFrame
        Daily data with columns: date, permno, ret, vold

    Returns
    -------
    pd.DataFrame
        Weekly illiquidity with columns: permno, date (Saturday), illiq, cnt
    """
    df = daily_df.copy()
    df['date'] = pd.to_datetime(df['date'])

    # Calculate daily illiquidity
    df['il'] = np.where(
        df['vold'] > 0,
        df['ret'].abs() / df['vold'],
        np.nan
    )

    # Count non-missing returns
    df['cnt'] = df['ret'].notna().astype(int)

    # Use W-SAT frequency (week ending Saturday)
    weekly = df.groupby(['permno', pd.Grouper(key='date', freq='W-SAT')]).agg(
        illiq=('il', 'mean'),
        cnt=('cnt', 'sum')
    ).reset_index()

    # Multiply by 10^8
    weekly['illiq'] = weekly['illiq'] * 1e8

    return weekly.rename(columns={'date': 'week_end'})


if __name__ == "__main__":
    print("Weekly Illiquidity Calculation Module")
    print("=" * 50)
    print()
    print("Formula:")
    print("  il = abs(ret) / vold")
    print("  illiq = mean(il) * 10^8")
    print()
    print("Week definition: Saturday (W-SAT)")
    print("  - Matches SAS: intnx('week', date, 0, 'E')")
    print()
    print("Functions:")
    print("  - calculate_weekly_illiquidity(): Main function")
    print("  - calculate_weekly_illiquidity_pandas(): Using pd.Grouper")
