import pandas as pd
import numpy as np
import statsmodels.api as sm
from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

def nw_t_stat(series, lag=4):
    """Calculate Newey-West adjusted t-stat for the mean of a time series."""
    series = np.array(series, dtype=float)
    series = series[~np.isnan(series)]
    if len(series) < lag + 1:
        return np.nan
    try:
        res = sm.OLS(series, np.ones(len(series))).fit(cov_type='HAC', cov_kwds={'maxlags': lag})
        return res.tvalues[0]
    except:
        return np.nan

def load_and_prep_data():
    print("Loading pre-processed weekly dataset with legacy firm controls...")
    df = pd.read_parquet(DATA_DIR / "firm_char_weekly.parquet")
    
    # We need both MAX(t-1) for Panel A and MAX(t-2) for Panel B
    # We also need the new legacy controls for Regression
    df = df.dropna(subset=['date', 'RET', 'REV_t_minus_1', 'MAX_t_minus_1', 'MAX_t_minus_2', 'SIZE_t_minus_1'])
    return df

def generate_table_1_panel(df, max_col, header_prefix):
    """Generates the EW and VW portfolio spreads and alphas for a specific MAX timing."""
    df_cur = df.copy()
    
    def assign_quintiles(s):
        pct = s.rank(pct=True, method='first')
        return pd.cut(pct, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0], labels=['Low', '2', '3', '4', 'High'])
        
    df_cur['MAX_Quintile'] = df_cur.groupby('date')[max_col].transform(assign_quintiles)
    df_sorted = df_cur.dropna(subset=['MAX_Quintile'])
    
    # EW Return
    ew_ret = df_sorted.groupby(['date', 'MAX_Quintile'])['RET'].mean().unstack()
    
    # VW Return
    def vw_mean(g):
        weights = g['SIZE_t_minus_1']
        rets = g['RET']
        if weights.sum() == 0: return np.nan
        return np.average(rets, weights=weights)
        
    vw_ret = df_sorted.groupby(['date', 'MAX_Quintile']).apply(vw_mean, include_groups=False).unstack()
    
    ew_ret['High minus Low'] = ew_ret['High'] - ew_ret['Low']
    vw_ret['High minus Low'] = vw_ret['High'] - vw_ret['Low']
    
    ew_ret = ew_ret * 100
    vw_ret = vw_ret * 100
    
    # Factor merges
    factors = df_cur[['date', 'MKT_rf', 'SMB', 'HML', 'UMD', 'CD91']].drop_duplicates().set_index('date')
    ew_excess = ew_ret.subtract(factors['CD91'], axis=0).dropna()
    vw_excess = vw_ret.subtract(factors['CD91'], axis=0).dropna()
    aligned_factors = factors.loc[ew_excess.index, ['MKT_rf', 'SMB', 'HML', 'UMD']]
    
    def calc_alpha_and_t(port_excess_ret):
        X = sm.add_constant(aligned_factors)
        valid_idx = port_excess_ret.notna() & aligned_factors.notna().all(axis=1)
        if valid_idx.sum() < 10: return np.nan, np.nan
        y = port_excess_ret[valid_idx]
        X_val = X[valid_idx]
        res = sm.OLS(y, X_val).fit(cov_type='HAC', cov_kwds={'maxlags': 4})
        return res.params['const'], res.tvalues['const']
        
    cols = ['Low', '2', '3', '4', 'High', 'High minus Low']
    ret_ew = [ew_ret[c].mean() for c in cols]
    tst_ew = [nw_t_stat(ew_ret[c]) for c in cols]
    ret_vw = [vw_ret[c].mean() for c in cols]
    tst_vw = [nw_t_stat(vw_ret[c]) for c in cols]
    
    ew_alpha, ew_alpha_t = calc_alpha_and_t(ew_excess['High minus Low'])
    vw_alpha, vw_alpha_t = calc_alpha_and_t(vw_excess['High minus Low'])
    
    ret_ew.append(ew_alpha)
    tst_ew.append(ew_alpha_t)
    ret_vw.append(vw_alpha)
    tst_vw.append(vw_alpha_t)
    
    rows = []
    rows.append([f"Panel {header_prefix}: Weekly Portfolios sorted on MAX {'(skip 1 week)' if max_col=='MAX_t_minus_2' else ''}"] + [''] * 7)
    rows.append([f"Panel {header_prefix}.1: equal-weighted"] + [''] * 7)
    rows.append([f"{v:.2f}" for v in ret_ew])
    rows.append([f"({v:.2f})" for v in tst_ew])
    rows.append([f"Panel {header_prefix}.2: value-weighted"] + [''] * 7)
    rows.append([f"{v:.2f}" for v in ret_vw])
    rows.append([f"({v:.2f})" for v in tst_vw])
    
    # Prepend dummy index column names for structure
    for i in range(2, 7):
        if len(rows[i]) == 7:
            rows[i].insert(0, "") # Placeholder for the metric column so everything aligns correctly.
            
    # We must construct it nicely
    formatted = []
    formatted.append([rows[0][0], '', '', '', '', '', '', ''])
    formatted.append(['MAX', 'Low', '2', '3', '4', 'High', 'High minus Low\nExcess', r'α_FF4'])
    formatted.append(rows[1])
    formatted.append(rows[2])
    formatted.append(rows[3])
    formatted.append(rows[4])
    formatted.append(rows[5])
    formatted.append(rows[6])
    
    return pd.DataFrame(formatted, columns=['Metric', 'Col1', 'Col2', 'Col3', 'Col4', 'Col5', 'Col6', 'Col7'])

def run_table_1_sorts(df):
    print("Replicating Table 1: Dual Panel MAX Sorts...")
    panel_a = generate_table_1_panel(df, 'MAX_t_minus_1', 'A')
    panel_b = generate_table_1_panel(df, 'MAX_t_minus_2', 'B')
    
    # Vertically stack the panels to perfectly mimic the target Chen Table 1 structure
    # panel_b[0:1] is the "Panel B" overarching title row
    # panel_b[2:] skips the duplicate "MAX, Low, 2..." header row
    return pd.concat([panel_a, panel_b[0:1], panel_b[2:]]).reset_index(drop=True)

def run_table_13_fm(df):
    print("Replicating Table 13: Fama-MacBeth Regressions with Full Controls...")
    
    df['RET_pct'] = df['RET'] * 100
    
    # Including new variables sourced from firm_char.sas7bdat
    controls = ['MOM_t_minus_1', 'BETA_t_minus_1', 'log_SIZE_t_minus_1', 'BM_t_minus_1', 'IVOL_t_minus_1', 'ILLIQ_t_minus_1']
    vars_to_std = ['MAX_t_minus_2', 'REV_t_minus_1'] + controls
    
    coef_list = []
    weeks = df['date'].unique()
    
    for w in weeks:
        week_data = df[df['date'] == w].copy()
        week_data = week_data.dropna(subset=['RET_pct', 'MAX_t_minus_2', 'REV_t_minus_1'] + controls)
        if len(week_data) < 30:
            continue
            
        for v in vars_to_std:
            std = week_data[v].std()
            if std > 0:
                week_data[v] = (week_data[v] - week_data[v].mean()) / std
                
        week_data['MAX_x_REV'] = week_data['MAX_t_minus_2'] * week_data['REV_t_minus_1']
        
        X_base = week_data[['MAX_x_REV', 'MAX_t_minus_2', 'REV_t_minus_1']]
        X_ctrl = week_data[['MAX_x_REV', 'MAX_t_minus_2', 'REV_t_minus_1'] + controls]
        Y = week_data['RET_pct']
        
        X_base = sm.add_constant(X_base)
        X_ctrl = sm.add_constant(X_ctrl)
        
        try:
            res_base = sm.OLS(Y, X_base).fit()
            res_ctrl = sm.OLS(Y, X_ctrl).fit()
            
            coefs = {
                'Intercept_Base': res_base.params.get('const', np.nan),
                'MAX_x_REV_Base': res_base.params.get('MAX_x_REV', np.nan),
                'MAX_Base': res_base.params.get('MAX_t_minus_2', np.nan),
                'REV_Base': res_base.params.get('REV_t_minus_1', np.nan),
                'R2_Base': res_base.rsquared_adj,
                
                'Intercept_Ctrl': res_ctrl.params.get('const', np.nan),
                'MAX_x_REV_Ctrl': res_ctrl.params.get('MAX_x_REV', np.nan),
                'MAX_Ctrl': res_ctrl.params.get('MAX_t_minus_2', np.nan),
                'REV_Ctrl': res_ctrl.params.get('REV_t_minus_1', np.nan),
                'MOM_Ctrl': res_ctrl.params.get('MOM_t_minus_1', np.nan),
                'BETA_Ctrl': res_ctrl.params.get('BETA_t_minus_1', np.nan),
                'SIZE_Ctrl': res_ctrl.params.get('log_SIZE_t_minus_1', np.nan),
                'BM_Ctrl': res_ctrl.params.get('BM_t_minus_1', np.nan),
                'IVOL_Ctrl': res_ctrl.params.get('IVOL_t_minus_1', np.nan),
                'ILLIQ_Ctrl': res_ctrl.params.get('ILLIQ_t_minus_1', np.nan),
                'R2_Ctrl': res_ctrl.rsquared_adj,
            }
            coef_list.append(coefs)
        except np.linalg.LinAlgError:
            pass
            
    df_coefs = pd.DataFrame(coef_list)
    
    def summarize(series_name):
        s = df_coefs[series_name].dropna()
        if len(s) == 0: return np.nan, np.nan
        return s.mean(), nw_t_stat(s)

    vars_order = [
        ('Intercept', 'Intercept_Base', 'Intercept_Ctrl'),
        ('MAX x REV', 'MAX_x_REV_Base', 'MAX_x_REV_Ctrl'),
        ('MAX', 'MAX_Base', 'MAX_Ctrl'),
        ('REV', 'REV_Base', 'REV_Ctrl'),
        ('MOM', None, 'MOM_Ctrl'),
        ('BETA', None, 'BETA_Ctrl'),
        ('SIZE', None, 'SIZE_Ctrl'),
        ('BM', None, 'BM_Ctrl'),
        ('IVOL', None, 'IVOL_Ctrl'),
        ('ILLIQ', None, 'ILLIQ_Ctrl')
    ]
    
    t13_rows = [['Variable', '(1) Base', '(2) +Controls']]
    
    for var_name, base_col, ctrl_col in vars_order:
        row_est = [f"**{var_name}**"]
        row_tstat = [""]
        
        if base_col:
            m, t = summarize(base_col)
            row_est.append(f"{m:.3f}" if not np.isnan(m) else "")
            row_tstat.append(f"({t:.2f})" if not np.isnan(t) else "")
        else:
            row_est.append("")
            row_tstat.append("")
            
        if ctrl_col:
            m, t = summarize(ctrl_col)
            row_est.append(f"{m:.3f}" if not np.isnan(m) else "")
            row_tstat.append(f"({t:.2f})" if not np.isnan(t) else "")
        else:
            row_est.append("")
            row_tstat.append("")
            
        t13_rows.append(row_est)
        t13_rows.append(row_tstat)
        
    # Append Adj R^2
    r2_base_mean = df_coefs['R2_Base'].mean()
    r2_ctrl_mean = df_coefs['R2_Ctrl'].mean()
    t13_rows.append(['**Adj. R^2**', f"{r2_base_mean:.2f}", f"{r2_ctrl_mean:.2f}"])
        
    return pd.DataFrame(t13_rows[1:], columns=t13_rows[0])

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_and_prep_data()
    
    table_1 = run_table_1_sorts(df)
    print("\n=== Table 1 Compiled ===")
    table_13 = run_table_13_fm(df)
    print("\n=== Table 13 Compiled ===")
    
    with pd.ExcelWriter(REPORT_DIR / "chen_2025_replication.xlsx") as writer:
        table_1.to_excel(writer, sheet_name='Table 1 (MAX Sort)', header=False, index=False)
        table_13.to_excel(writer, sheet_name='Table 13 (FM Reg)', header=True, index=False)
        
    print(f"\nSaved updated Table 1 & 13 replication formats to {REPORT_DIR / 'chen_2025_replication.xlsx'}!")

if __name__ == "__main__":
    main()
