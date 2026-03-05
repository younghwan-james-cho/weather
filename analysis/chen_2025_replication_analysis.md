# Chen et al. (2025) JEF - Table 1 & 13 Replication Analysis
# Variable Definitions and Data Mapping for Korean Stock Market

---

## 1. Variable Definitions (from Paper)

### 1.1 MAX (Maximum Daily Return)
**Definition (from paper, Section 3):**
> "MAX is defined as the largest daily return in a week" (Bali, Cakici, Whitelaw 2011)

**Paper's calculation:**
- For week t: MAX_t = max(daily returns from day 1 to day 5 of week t)
- Alternative measures:
  - MAX_4w: max daily return over past 4 weeks
  - MAX_13w: max daily return over past 13 weeks
  - MAX_26w: max daily return over past 26 weeks

**Temporal structure in paper:**
- MAX at week t-2 (portfolio formation)
- PRET/REV at week t-1 (past 1-week return)
- Return at week t (holding period)

### 1.2 PRET/REV (Past Return / Reversal)
**Definition (from paper):**
> "PRET = past 1-week returns from week t-1"
> "REV = lagged return from t-1"

**Paper's calculation:**
- For stock i: REV_{i,t-1} = (P_{t-1} - P_{t-2}) / P_{t-2}
- Used as continuous variable for regression
- For portfolio sorts: Past winners (top 20%) vs Past losers (bottom 20%)

### 1.3 Portfolio Sorting Method

**Table 1 (Panel A):**
1. Sort stocks into quintiles (5 groups) based on MAX from week t-1
2. Calculate average excess return in week t
3. Report both equal-weighted and value-weighted

**Table 1 (Panel B):**
1. Sort stocks into quintiles based on MAX from week t-2 (skip week t-1)
2. Calculate average excess return in week t (1-week lag)

### 1.4 Excess Return Calculation
**Definition (from paper):**
- Excess Return = Stock Return - Risk-Free Rate
- Risk-free rate: CD91 (3-month T-bill rate) from Ken French database

### 1.5 Factor Alphas
**Factor models used:**
- FF4: Fama-French 3-factor + Carhart momentum
- FF6: Fama-French 5-factor + momentum
- Q-factor: Hou, Xue, Zhang model

**Alpha calculation:**
- Regress excess returns on factors
- Alpha = intercept from regression

---

## 2. Table 13 Regression Specification

### 2.1 Fama-MacBeth Cross-Sectional Regression

**Model (from paper, Equation 3):**
```
Ret_{i,t} = β0 + β1 * MAX_{i,t-2} * Ret_{i,t-1}
           + β2 * MAX_{i,t-2}
           + β3 * Ret_{i,t-1}
           + γ' CONTROLS
           + ε_{i,t}
```

**Control variables (from paper):**
| Variable | Definition |
|----------|------------|
| MOM | Momentum: cumulative return from month t-2 to t-12 |
| BETA | CAPM beta (Scholes-Williams, Dimson adjustment) |
| SIZE | log(market capitalization) |
| BM | Book-to-market ratio |
| IVOL | Idiosyncratic volatility |
| TVOL | Total volatility |
| ILLIQ | Amihud illiquidity measure |

---

## 3. Available Data Mapping

### 3.1 Data Files in weather folder

| File | Shape | Key Variables |
|------|-------|---------------|
| `firm_char_weekly.parquet` | 2,489,772 × 32 | MAX, RET, REV_t_minus_1, factors |
| `firm_char_clean.parquet` | 1,309,728 × 19 | Daily/monthly stock characteristics |
| `ff4_clean.parquet` | 337 × 7 | Fama-French factors |
| `weather_clean.parquet` | 240 × 29 | Korean weather variables |

### 3.2 Variable Mapping

| Paper Variable | Available in Data | Column Name | Notes |
|----------------|-------------------|-------------|-------|
| MAX (weekly) | ✓ | `MAX` | Max daily return in week |
| MAX_t_minus_1 | ✓ | `MAX_t_minus_1` | MAX from week t-1 |
| MAX_t_minus_2 | ✓ | `MAX_t_minus_2` | MAX from week t-2 |
| RET (weekly) | ✓ | `RET` | Weekly return |
| REV (past week) | ✓ | `REV_t_minus_1` | Return from week t-1 |
| MKT | ✓ | `MKT` | Market factor |
| SMB | ✓ | `SMB` | Size factor |
| HML | ✓ | `HML` | Value factor |
| UMD | ✓ | `UMD` | Momentum factor |
| CD91 (rf) | ✓ | `CD91` | Risk-free rate |
| MKT_rf | ✓ | `MKT_rf` | Market excess return |
| SIZE | ✓ | `ME`, `log_SIZE_t_minus_1` | Market equity |
| BETA | ⚠ | `BETA_t_minus_1` | Has NaN values |
| MOM | ⚠ | `MOM_t_minus_1` | Has NaN values |
| BM | ⚠ | `BM_t_minus_1` | Has NaN values |
| IVOL | ⚠ | `IVOL_t_minus_1` | Has NaN values |
| ILLIQ | ✓ | `ILLIQ_t_minus_1` | Amihud illiquidity |

### 3.3 Weather Variables Available

| Variable | Column Name | Definition |
|----------|-------------|------------|
| Cloud Cover | `cloud_cover_d_t_minus_1` | Calendar-week deasonalized |
| Sunshine | `sunshine_d_t_minus_1` | Calendar-week deasonalized |
| Apparent Temp | `apparent_temp_d_t_minus_1` | Calendar-week deasonalized |
| AQI | `aqi_d_t_minus_1` | Air quality index (deseasonalized) |
| Precipitation | `precipitation_t_minus_1` | Raw precipitation |
| Temperature | `temperature_t_minus_1` | Raw temperature |

---

## 4. Data Gaps Analysis

### 4.1 Critical Gaps for Table 1 Replication

| Required | Status | Issue |
|----------|--------|-------|
| Korean stock returns | ❓ | Need KRX data |
| Korean risk-free rate | ❓ | Need KOSPI treasury rates |
| Korean factor models | ❓ | Need K-factor models |

### 4.2 What We Have

- US stock data with MAX, REV variables (firm_char_weekly.parquet)
- Korean weather data (separation: national EW/PW)
- Fama-French factors (US only)

### 4.3 Recommendation

**Option 1:** Replicate with US data in firm_char_weekly.parquet
- Has all required variables: MAX, REV, RET, factors
- Period: 1998-01 to 2025-02

**Option 2:** Extend Korean weather data to stock level
- Currently: National-level daily aggregates only
- Need: Daily stock-weather merged dataset

---

## 5. Next Steps

To replicate Table 1 and Table 13:

1. **Use firm_char_weekly.parquet** (US data) - already has MAX, REV
2. **Construct portfolio sorts** as per paper methodology
3. **Run Fama-MacBeth regressions** with available controls

The Korean weather data is at national daily level only - not usable for stock-level replication without additional processing.
