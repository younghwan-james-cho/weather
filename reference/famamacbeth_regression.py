# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 14:05:56 2026

@author: ys1ha
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
import pandas as pd

# .dta 파일 읽기
df = pd.read_stata('C:/Users/ys1ha/Dropbox/Donghoon/4. Weather/data share/FM_sample.dta')

#%%
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date')

#%%
# ---------------------------------------------------------
# 방법 A: 각 그룹별 개별 평균 및 t-값 (NW 4)
# ---------------------------------------------------------
groups = ['Low', 'Mid', 'High']
A_results = []

for g in groups:
    sub_data = df[df['cld'] == g]['max1']
    res = sm.OLS(sub_data, np.ones(len(sub_data))).fit(
        cov_type='HAC', cov_kwds={'maxlags': 4}
    )
    A_results.append({
        'Group': g,
        'Mean': res.params[0],
        't-stat': res.tvalues[0]
    })

Group_mean=pd.DataFrame(A_results)

#%%
# ---------------------------------------------------------
# 방법 B: 그룹 간 차이 검정 (Low-Mid, High-Mid)
# ---------------------------------------------------------
# Mid를 기준 그룹(Reference)으로 설정하여 더미 회귀분석 수행
# Max1 = intercept(Mid) + b1*Low_dummy + b2*High_dummy
model = smf.ols('max1 ~ C(cld, Treatment(reference="Mid"))', data=df)

# Newey-West (HAC) 4 lag 적용
res_diff = model.fit(cov_type='HAC', cov_kwds={'maxlags': 4})



Group_diff = pd.DataFrame({
    'Metric': ['Mid Mean (Intercept)', 'Low - Mid (Diff)', 'High - Mid (Diff)'],
    'Value': res_diff.params.values,
    't-stat (NW 4)': res_diff.tvalues.values
})




#%%
# ---------------------------------------------------------
# Fama-Macbeth 하는 법
# ---------------------------------------------------------
# ---------------------------------------------------------
# Fama-Macbeth 하는 법
# ---------------------------------------------------------
# ---------------------------------------------------------
# Fama-Macbeth 하는 법
# ---------------------------------------------------------
df = pd.read_stata('C:/Users/ys1ha/Dropbox/Donghoon/4. Weather/data share/FM_sample2.dta')
df2 = pd.read_stata('C:/Users/ys1ha/Dropbox/Donghoon/4. Weather/data share/FM_sample.dta')
dep_var = 'retex_a1'
indep_vars = ['max1', 'beta', 'log_size', 'bm', 'roe', 'retex', 'mom', 'illiq', 'ivol_12m']

# 2. Step 1: 매월(Monthly) 회귀를 돌려 계수(Beta)만 추출
def get_monthly_coeffs(group):
    group = group.dropna(subset=[dep_var] + indep_vars)
    if len(group) < len(indep_vars) + 1: return None
    
    Y = group[dep_var]
    X = sm.add_constant(group[indep_vars])
    return sm.OLS(Y, X).fit().params

monthly_betas = df.groupby('date').apply(get_monthly_coeffs).dropna()
#%%
# 3. Step 2: 계수 시계열을 Newey-West(4 lag)로 평균 및 t-값 계산
fm_final = []

for col in monthly_betas.columns:
    ts_coef = monthly_betas[col]
    
    # 시계열 평균값 구하기
    # Newey-West 4 lag 적용
    res = sm.OLS(ts_coef, np.ones(len(ts_coef))).fit(
        cov_type='HAC', cov_kwds={'maxlags': 4}
    )
    
    fm_final.append({
        'Variable': col,
        'Coeff_Mean': res.params[0],
        't-stat (NW4)': res.tvalues[0],
        'p-value': res.pvalues[0]
    })

# 4. 최종 결과 DataFrame화
fm_results = pd.DataFrame(fm_final).set_index('Variable')