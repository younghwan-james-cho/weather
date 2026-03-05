# Chen et al. (2025) JEF - Variable Definitions & Data Availability Analysis

## Paper: "Maxing out short-term reversals in weekly stock returns"

**Goal:** Check if Korean stock data can replicate Table 1 and Table 13

---

## Part 1: Exact Variable Definitions (from Paper)

### 1.1 MAX (Maximum Daily Return)

**Paper Definition (Section 3):**
> "MAX is defined as the largest daily return in a week"

**Calculation:**
```
MAX_t = max(R_{day1}, R_{day2}, R_{day3}, R_{day4}, R_{day5})
```
Where R_{day} = (P_{day} - P_{day-1}) / P_{day-1}

**Paper uses:**
- Weekly MAX from week t-1 (Panel A)
- Weekly MAX from week t-2 (Panel B, skip one week)
- Alternative: MAX_4w, MAX_13w, MAX_26w (robustness)

**In our data:** ✓ Available as `MAX`, `MAX_t_minus_1`, `MAX_t_minus_2`

---

### 1.2 REV / PRET (Past 1-Week Return)

**Paper Definition (Section 4.2):**
> "PRET = past 1-week returns from week t-1"
> "REV = lagged return from t-1"

**Calculation:**
```
REV_t-1 = (P_{t-1} - P_{t-2}) / P_{t-2}
```

**In our data:** ✓ Available as `REV_t_minus_1`

---

### 1.3 Weekly Return (RET)

**Paper Definition:**
> Weekly returns constructed from CRSP daily data

**In our data:** ✓ Available as `RET`

---

### 1.4 Risk-Free Rate (CD91)

**Paper Definition:**
> "Excess Return = Stock Return - Risk-free rate"
> Uses 3-month T-bill rate (CD91 from Ken French)

**In our data:** ✓ Available as `CD91` (but only monthly, not weekly)

---

### 1.5 Excess Return

**Calculation:**
```
EXCESS_RET = RET - RF
```

**In our data:** Can compute from RET - CD91

---

### 1.6 Factor Alphas (FF4, FF6, Q)

**Paper Definition:**
- **FF4:** Fama-French 3-factor + Carhart momentum
- **FF6:** Fama-French 5-factor + momentum
- **Q-factor:** Hou, Xue, Zhang model

**Alpha calculation:**
```
R_i,t - RF_t = α + β1*Factor1 + β2*Factor2 + ... + ε_t
```

**In our data:** ⚠️ PROBLEM
- FF4 factors are MONTHLY (337 months from 1998-2026)
- Need WEEKLY factors to compute alphas
- Current factors cannot be used directly

---

## Part 2: Table 13 Control Variables

| Variable | Paper Definition | In Our Data |
|----------|------------------|-------------|
| MOM | Cumulative return month t-2 to t-12 | `MOM_t_minus_1` (88.8% available) |
| BETA | CAPM beta (Scholes-Williams) | `BETA_t_minus_1` (98.4% available) |
| SIZE | log(market cap) | `log_SIZE_t_minus_1` (100%) |
| BM | Book-to-market | `BM_t_minus_1` (90.6% available) |
| IVOL | Idiosyncratic volatility | `IVOL_t_minus_1` (99.6% available) |
| ILLIQ | Amihud illiquidity | `ILLIQ_t_minus_1` (97.7% available) |

---

## Part 3: Replication Feasibility Summary

### Table 1: Portfolio Sorts on MAX

| Component | Paper | Our Data | Status |
|-----------|-------|----------|--------|
| MAX (t-1) | Week t-1 MAX | `MAX_t_minus_1` | ✓ Can replicate |
| MAX (t-2) | Week t-2 MAX | `MAX_t_minus_2` | ✓ Can replicate |
| Weekly RET | Week t return | `RET` | ✓ Can replicate |
| Risk-free | 3-month T-bill | `CD91` | ✓ Can compute |
| Quintile sorts | 5 groups | 5 groups | ✓ Can replicate |
| Equal-weighted | Simple average | Simple average | ✓ Can replicate |
| Value-weighted | By market cap | By `ME` | ✓ Can replicate |
| FF4/FF6/Q Alpha | Factors needed | ⚠️ Need weekly factors | ❌ CANNOT |

**Verdict:** CAN replicate Table 1 (excess returns only), CANNOT compute alphas

---

### Table 13: Fama-MacBeth Regression

| Component | Paper | Our Data | Status |
|-----------|-------|----------|--------|
| Dependent: RET | Weekly return | `RET` | ✓ Available |
| MAX × REV | Interaction term | Can compute | ✓ Available |
| MAX | Week t-2 MAX | `MAX_t_minus_2` | ✓ Available |
| REV | Week t-1 return | `REV_t_minus_1` | ✓ Available |
| MOM | Month t-2 to t-12 | `MOM_t_minus_1` | ⚠️ 88.8% |
| BETA | CAPM beta | `BETA_t_minus_1` | ⚠️ 98.4% |
| SIZE | log(ME) | `log_SIZE_t_minus_1` | ✓ 100% |
| BM | Book-to-market | `BM_t_minus_1` | ⚠️ 90.6% |
| IVOL | Idiosyncratic vol | `IVOL_t_minus_1` | ✓ 99.6% |
| ILLIQ | Amihud illiq | `ILLIQ_t_minus_1` | ✓ 97.7% |

**Verdict:** CAN replicate Table 13 with available controls

---

## Part 4: Key Issues Identified

### Issue 1: Risk-Free Rate Frequency
- **Problem:** CD91 is monthly, not weekly
- **Solution:** Use monthly CD91 for each week, or interpolate

### Issue 2: Factor Alphas
- **Problem:** FF4 factors are monthly (337 observations = months, not weeks)
- **Solution:** Either:
  1. Create weekly factors by averaging monthly
  2. Skip alpha calculation
  3. Use only excess returns (not risk-adjusted)

**UPDATE:** We have weekly FF4 factors!
- File: `data/raw/ff4_weekly_2005_2024.sas7bdat`
- Shape: (1469, 7) - weekly observations
- Date range: 1998-01-03 to 2026-02-24
- Columns: Date, SMB, HML, UMD, MKT, CD91, MKT_rf

---

## Part 4: User-Specified Replication Scope

### Table 1 (User Request):
- Panel A: Sort on MAX from week t-1
- Panel B: Sort on MAX from week t-2 (skip one week)
- **Only quintiles Q1-Q5** (NO high-low spread)

### Table 13 (User Request):
- **Weekly MAX only** (not monthly, not 26-week)
- **EXCLUDE REV and MAX×REV interaction**
- **Only MAX + control variables**

Regression specification:
```
RET_t = α + β*MAX_{t-2} + γ'CONTROLS + ε
```

Controls: SIZE, BETA, MOM, BM, IVOL, ILLIQ

**UPDATE:** We have weekly FF4 factors!
- File: `data/raw/ff4_weekly_2005_2024.sas7bdat`
- Shape: (1469, 7) - weekly observations
- Date range: 1998-01-03 to 2026-02-24
- Columns: Date, SMB, HML, UMD, MKT, CD91, MKT_rf

### Issue 3: Missing Control Variables
- Some controls have ~10% missing data
- **Solution:** Use available controls only (SIZE, IVOL, ILLIQ always available)

---

## Part 5: Data Summary

### Stock Data
- **Source:** Korean stocks (KOSPI) - codes like A000010
- **Period:** 1998-01-20 to 2025-02-04
- **Stocks:** 3,713 unique
- **Observations:** 2,489,772 (weekly)

### Key Variables Available
```
✓ MAX (max daily return in week)
✓ MAX_t_minus_1 (MAX from week t-1)
✓ MAX_t_minus_2 (MAX from week t-2)
✓ RET (weekly return)
✓ REV_t_minus_1 (past week return)
✓ CD91 (risk-free rate, monthly)
✓ SIZE, log_SIZE (market cap)
✓ MKT, SMB, HML, UMD (factor returns, monthly only)
✓ ILLIQ, IVOL (liquidity/volatility)
✓ Weather variables (national level, 81% coverage)
```

---

## Conclusion

**Can replicate Table 1?** ✓ YES (excess returns, but not alphas)
**Can replicate Table 13?** ✓ YES (with available controls)
**Need for weather data?** ❌ NO - Table 1/13 don't use weather

The weather data in this folder is for a DIFFERENT research question - studying how weather affects stock returns, not for replicating the MAX-reversal paper.
