# Detailed Analysis Report: Chen, Cohen, Liang & Sun (2025)
## *"Maxing Out Short-Term Reversals in Weekly Stock Returns"*
**Journal of Empirical Finance 82, 101608**

---

## 1. Paper Overview

### 1.1 Core Thesis
The paper hypothesizes that **pent-up demand from lottery-seeking investors amplifies their overreactions to news**, leading to larger short-term return reversals. Grounded in Subrahmanyam (1991), the theory posits that increased variance in liquidity trades (driven by lottery demand) reduces price efficiency when market makers are risk-averse.

> *"Subrahmanyam (1991) presents a model in which increased variance in liquidity trades reduces price efficiency when market makers are risk-averse. Motivated by this theoretical insight, we hypothesize that pent-up demand from lottery-seeking investors amplifies their overreactions to news, leading to larger short-term return reversals."* — Abstract, p.1

### 1.2 Key Finding
High-MAX stocks that were past 1-week losers (winners) exhibit notably positive (negative) returns the following week. A short-term reversal strategy on high-MAX stocks yields **1.66% average weekly return**, vs. only 0.65% on low-MAX stocks.

> *"Specifically, high-MAX stocks that were past 1-week losers (or winners) exhibit notably positive (or negative) returns in the following week. Applying a short-term reversal strategy to high-MAX stocks generates an average weekly return of 1.66%, significantly outperforming the 0.65% return from the same strategy applied to low-MAX stocks."* — Abstract, p.1

### 1.3 Sample & Data Sources

| Aspect | Detail |
|--------|--------|
| **Universe** | Domestic common stocks (share code 10 or 11) on NYSE, AMEX, NASDAQ |
| **Period** | July 1963 – December 2022 |
| **Return data** | CRSP monthly + daily files |
| **Accounting data** | Compustat database |
| **Factor models** | Fama–French (Ken French's website), q-factor (Lu Zhang's website) |
| **Sentiment** | Jeffrey Wurgler's investor sentiment data |
| **Retail trading** | TAQ off-exchange data (exchange code "D"), Jan 2010–Dec 2019 |

> *"Our main sample consists of domestic common stocks (share code 10 or 11) listed on the New York Stock Exchange (NYSE), American Stock Exchange (AMEX), and National Association of Securities Dealers Automated Quotations (NASDAQ) from July 1963 to December 2022. We rely on both the monthly and daily data files from the Center for Research in Security Prices (CRSP) database to obtain stock price, trading volume, shares outstanding, exchange codes, and so on. The CRSP daily data files are used to help construct weekly stock returns. Financial statement data are collected from the Compustat database."* — Section 3, p.4

---

## 2. Master Variable Definitions

### 2.1 MAX — Maximum Daily Return (Lottery Proxy)

| Property | Detail |
|----------|--------|
| **Definition** | Largest daily return within a given week |
| **Measurement Window** | 1 week (baseline), also tested with 4-week, 13-week, 26-week, and 1-month windows |
| **Lag** | t−1 for Table 1 Panel A; t−2 for Table 1 Panel B and Table 13 |
| **Source** | CRSP daily file |

> *"Since our empirical work mainly focuses on weekly returns, we construct the (weekly) maximum daily return variable (MAX) following the ideas from Bali, Cakici, and Whitelaw (2011). Specifically, MAX is defined as the largest daily return in a week."* — Section 3, p.4

**Justification:** MAX is used as a proxy for investors' demand for lottery-like payoffs. Bali et al. (2011) originally defined MAX over a monthly window; this paper extends it to weekly frequency.

> *"As noted by Bali, Cakici, and Whitelaw (2011), the MAX variable is a simple and intuitive measure of investors' demand for lottery-like payoffs."* — Section 3, p.4

### 2.2 REV (PRET) — Past Weekly Return (Reversal Signal)

| Property | Detail |
|----------|--------|
| **Definition** | Stock return over week t−1 (past 1-week return) |
| **Measurement Window** | 1 week |
| **Lag** | t−1 (always 1 week before the target return) |
| **Construction** | Weekly stock return from CRSP daily data |

> *"Within each MAX quintile, we further sort stocks based on their past 1-week returns (PRET) from week t−1."* — Section 4.2.1, p.5

**Justification for temporal separation (skip-week):** MAX is measured at t−2 and PRET at t−1 to avoid mechanical contamination between the lottery proxy and the reversal signal.

> *"We first sort stocks into quintile portfolios based on their MAX in week t−2 in order to identify stocks with lottery-like features. [...] we find it important to impose this temporal separation between MAX and PRET to help with interpretation of results."* — Section 4.2.1, p.5

### 2.3 MOM — Momentum

| Property | Detail |
|----------|--------|
| **Definition** | Cumulative return from month t−2 to month t−12 |
| **Measurement Window** | 11 months (months t−2 through t−12) |

> *"MOM is the cumulative return from month t−2 to t−12."* — Table 13 footnote, p.19

**Justification:** Standard Jegadeesh and Titman (1993) momentum factor; skips the most recent month to avoid short-term reversal contamination.

### 2.4 BETA — Market Beta

| Property | Detail |
|----------|--------|
| **Definition** | CAPM beta estimated via Scholes-Williams (1977) and Dimson (1979) methodology |
| **Estimation** | Uses lag, lead, and contemporaneous market returns |

> *"BETA is the market beta. We follow Scholes and Williams (1977) and Dimson (1979) and use the lag and lead of the market portfolio as well as the current market when estimating beta."* — Table 13 footnote, p.19

**Justification:** The Scholes-Williams-Dimson adjustment corrects for nonsynchronous trading, which is critical for small/illiquid stocks that trade infrequently.

### 2.5 SIZE — Firm Size

| Property | Detail |
|----------|--------|
| **Definition** | Natural logarithm of market capitalization |

> *"SIZE is the natural logarithm of the market capitalization."* — Table 13 footnote, p.19

### 2.6 BM — Book-to-Market Ratio

| Property | Detail |
|----------|--------|
| **Definition** | Book equity divided by market equity |
| **Source** | Compustat (book equity) + CRSP (market equity) |

> *"BM is the book-to-market ratio."* — Table 13 footnote, p.19

**Justification:** Classic Fama-French (1992, 1993) value factor; captures the value premium dimension of expected returns.

### 2.7 IVOL — Idiosyncratic Volatility

| Property | Detail |
|----------|--------|
| **Definition** | Idiosyncratic volatility (residual volatility from a factor model) |

> *"TVOL and IVOL are total and idiosyncratic volatility, respectively."* — Table 13 footnote, p.19

**Justification:** Controls for the idiosyncratic volatility anomaly documented by Ang et al. (2006), which overlaps with MAX as both capture tail risk.

### 2.8 TVOL — Total Volatility

| Property | Detail |
|----------|--------|
| **Definition** | Total volatility (standard deviation of returns) |

> *"TVOL and IVOL are total and idiosyncratic volatility, respectively."* — Table 13 footnote, p.19

### 2.9 ILLIQ — Amihud Illiquidity Measure

| Property | Detail |
|----------|--------|
| **Definition** | Amihud (2002) illiquidity = |return| / dollar volume, averaged over weeks t−1 to t−4 |
| **Measurement Window** | 4 weeks (weeks t−1 to t−4) |

> *"ILLIQ is Amihud (2002)'s illiquidity measure."* — Table 13 footnote, p.19

> *"We estimate Illiquidity using daily data from weeks t−1 to t−4."* — Section 3, p.5

**Justification:** Captures the price impact dimension of liquidity, which is central to the paper's hypothesis that illiquid stocks are more susceptible to lottery-demand-induced overreaction.

---

## 3. Table 1: Replication Methodology

### 3.1 What Table 1 Shows

Table 1 presents **returns and alphas of weekly portfolios sorted on MAX**. It establishes the existence of the MAX anomaly in weekly U.S. stock returns — high-MAX stocks underperform low-MAX stocks.

### 3.2 Table Structure

| | Low | 2 | 3 | 4 | High | High minus Low |
|---|---|---|---|---|---|---|
| **Panel A** (sort on MAX from t−1) | | | | | | |
| A.1: Equal-weighted | 0.23 | 0.25 | 0.22 | 0.13 | −0.20 | −0.43 |
| *(t-stat)* | (4.65) | (5.25) | (4.27) | (2.17) | (−2.81) | (−11.71) |
| A.2: Value-weighted | 0.27 | 0.17 | 0.10 | 0.04 | −0.07 | −0.35 |
| *(t-stat)* | (6.91) | (4.33) | (2.52) | (0.83) | (−1.20) | (−7.96) |
| **Panel B** (sort on MAX from t−2, skip t−1) | | | | | | |
| B.1: Equal-weighted | 0.10 | 0.21 | 0.19 | 0.15 | −0.00 | −0.11 |
| *(t-stat)* | (2.07) | (4.48) | (3.67) | (2.57) | (−0.06) | (−3.27) |
| B.2: Value-weighted | 0.17 | 0.14 | 0.14 | 0.12 | 0.06 | −0.11 |
| *(t-stat)* | (4.55) | (3.76) | (3.32) | (2.45) | (0.92) | (−2.65) |

Also includes factor-model adjusted alphas: FF4 (α_FF4), FF6 (α_FF6), and Q-factor (α_Q).

### 3.3 Step-by-Step Replication Procedure

#### Step 1: Data Preparation
1. **Obtain daily data** from CRSP: price, return, volume, shares outstanding, exchange code, share code
2. **Filter universe**: Keep only share codes 10 and 11 (domestic common stocks) on NYSE, AMEX, NASDAQ
3. **Sample period**: July 1963 – December 2022

#### Step 2: Construct Weekly Returns
1. **Aggregate daily returns** into weekly returns using CRSP daily data
2. Weekly returns are constructed from the CRSP daily file (the paper does not specify a Wednesday-to-Tuesday convention explicitly for Table 1, but references the CRSP standard weekly return construction)

#### Step 3: Compute MAX Variable
1. For each stock in each week, compute **MAX = max(daily return)** within that week
2. Create lagged variables:
   - `MAX_{t−1}`: MAX from the prior week (for Panel A)
   - `MAX_{t−2}`: MAX from two weeks ago (for Panel B)

#### Step 4: Portfolio Sort (Cross-Sectional)
1. Each week, **sort all stocks into quintiles** (5 groups) based on MAX
   - Panel A: sort on `MAX_{t−1}`
   - Panel B: sort on `MAX_{t−2}` (skip week t−1)
2. Quintile 1 = Low MAX, Quintile 5 = High MAX

#### Step 5: Compute Portfolio Returns
1. **Equal-weighted (EW)**: For each quintile-week, compute the simple arithmetic mean of all constituent stock returns
2. **Value-weighted (VW)**: Weight by market capitalization (lagged ME)
3. The dependent variable is the **weekly excess return** (stock return minus risk-free rate)

> *"We report both equal-weighted and valued-weighted average weekly portfolio returns from week t."* — Section 4.1, p.5

#### Step 6: Compute the "High minus Low" Spread
1. Each week, compute: `H−L = return(Q5) − return(Q1)`
2. This creates a long-short portfolio time series

#### Step 7: Factor-Model Alphas
1. Regress the portfolio excess return time series on factor returns:
   - **FF4**: MKT, SMB, HML, UMD (Carhart 1997)
   - **FF6**: MKT, SMB, HML, RMW, CMA, UMD (Fama-French 2015 + momentum)
   - **Q-factor**: MKT, ME, ROE, IA (Hou, Xue, Zhang 2015)
2. The intercept (alpha) measures abnormal returns after risk adjustment

#### Step 8: Statistical Inference
1. Compute **Newey-West (1987, 1994) adjusted t-statistics** with **automatic lag selection**
2. Formula for max lag: `maxlag = floor(4 × (T/100)^(2/9))`

> *"Average returns and alphas are reported in percentage terms. Newey–West (1987, 1994) adjusted t-statistics with automatic lag selection are reported in parentheses."* — Table 1 footnote, p.6

### 3.4 Key Table 1 Footnote (Verbatim)

> *"In Panel A, quintile portfolios are formed by sorting stocks on the maximum daily return (MAX) from week t−1. We report the average weekly portfolio returns from week t. In Panel B, quintile portfolios are formed by sorting stocks on the MAX from week t−2. We skip week t−1 and report the average weekly portfolio returns from week t. Panels A.1 and A.2 (Panels B.1 and B.2) report the results of equal-weighted and value-weighted portfolios, respectively. The table also reports the average weekly excess returns as well as factor-model adjusted alphas, which are calculated based on the four-factor Fama–French–Carhart model (FF4), the six-factor Fama–French-UMD model (FF6), and Hou, Xue, and Zhang's (2015) Q-factor model. The sample period is from July 1963 to December 2022. Average returns and alphas are reported in percentage terms. Newey–West (1987, 1994) adjusted t-statistics with automatic lag selection are reported in parentheses."* — Table 1 footnote, p.6

---

## 4. Table 13: Replication Methodology

### 4.1 What Table 13 Shows

Table 13 presents **Fama-MacBeth (1973) cross-sectional regressions** that test whether the MAX-enhanced reversal effect survives after controlling for known cross-sectional return predictors. It is the multivariate confirmation of the portfolio sorts.

### 4.2 Table Structure

Table 13 has **9 columns** organized as:

| Column Group | MAX/REV Definition | Columns |
|---|---|---|
| **Monthly MAX & Monthly REV** | MAX = max daily return in past month | (1), (2), (3) |
| **Weekly MAX & Weekly REV** | MAX = max daily return in past week | (4), (5), (6) |
| **26-Week MAX & Weekly REV** | MAX = max daily return in past 26 weeks | (7), (8), (9) |

Within each group, the three columns represent:
1. **Base model**: MAX×REV + MAX + REV only
2. **Partial controls**: + SIZE, BM, BETA (subset of controls)
3. **Full controls**: + MOM, BETA, SIZE, BM, IVOL, TVOL, ILLIQ (all controls)

### 4.3 The Core Regression Model (Equation 3)

$$Ret_{i,t} = \beta_0 + \beta_1 \cdot MAX_{i,t-2} \times Ret_{i,t-1} + \beta_2 \cdot MAX_{i,t-2} + \beta_3 \cdot Ret_{i,t-1} + \gamma' CONTROLS_{i,t} + \varepsilon_{i,t}$$

> *"Ret_{i,t} = β₀ + β₁ MAX_{i,t−2} × Ret_{i,t−1} + β₂ MAX_{i,t−2} + β₃ Ret_{i,t−1} + γ' CONTROLS_{i,t} + ε_{i,t}"* — Equation 3, Section 6.5, p.19

Where:
- **Ret_{i,t}**: Stock return at time t (in percentage terms; **NOT excess return**)
- **MAX_{i,t−2}**: Maximum daily return from time t−2
- **Ret_{i,t−1}** (REV): Stock return from time t−1
- **MAX × REV**: The **interaction term** — the paper's key variable of interest
- **CONTROLS**: Vector of firm characteristics

### 4.4 Step-by-Step Replication Procedure

#### Step 1: Prepare All Variables
For each stock i in each period t, compute:

| Variable | Definition | Lag | Source |
|----------|-----------|-----|--------|
| `Ret_{i,t}` (dep. var) | Monthly/weekly stock return (%) | t | CRSP |
| `MAX_{i,t−2}` | Max daily return in month/week t−2 | t−2 | CRSP daily |
| `REV_{i,t−1}` | Stock return from month/week t−1 | t−1 | CRSP |
| `MAX × REV` | Interaction: `MAX_{i,t−2}` × `REV_{i,t−1}` | — | Computed |
| `MOM` | Cumulative return from month t−2 to t−12 | t−2 to t−12 | CRSP |
| `BETA` | Scholes-Williams-Dimson CAPM beta | — | CRSP + market returns |
| `SIZE` | ln(market cap) | — | CRSP |
| `BM` | Book-to-market ratio | — | Compustat + CRSP |
| `IVOL` | Idiosyncratic volatility | — | CRSP daily |
| `TVOL` | Total volatility | — | CRSP daily |
| `ILLIQ` | Amihud illiquidity (weeks t−1 to t−4) | t−1 to t−4 | CRSP daily |

#### Step 2: Cross-Sectional Standardization

> [!IMPORTANT]
> **All independent variables must be standardized to mean = 0 and standard deviation = 1 within each cross-section (each week/month).**

> *"Independent variables are standardized to a mean of 0 and a standard deviation of 1. The Dependent variable (i.e., stock return at month/week t) is measured in percentage terms."* — Table 13 footnote, p.19

This means: for each period t, across all stocks i, each independent variable X is transformed as:
$$X^{std}_{i,t} = \frac{X_{i,t} - \bar{X}_t}{\sigma_{X,t}}$$

**Justification:** Standardization ensures coefficient magnitudes are comparable across variables with different scales and allows direct interpretation of economic significance.

#### Step 3: Run Cross-Sectional OLS (Each Period)
For each period t, run OLS regression across all stocks:
```
Ret_{i,t} = β₀,t + β₁,t · (MAX×REV)_{i} + β₂,t · MAX_{i} + β₃,t · REV_{i} + γ'_{t} · CONTROLS_{i} + ε_{i,t}
```

Collect the vector of coefficient estimates: {β̂₀,t, β̂₁,t, β̂₂,t, β̂₃,t, γ̂'_t}

#### Step 4: Time-Series Averaging (Fama-MacBeth)
1. For each coefficient, compute the **time-series mean** across all T periods:
$$\bar{\beta}_k = \frac{1}{T} \sum_{t=1}^{T} \hat{\beta}_{k,t}$$

2. Compute **Newey-West (1987, 1994) adjusted t-statistics** with automatic lag selection:
$$t_{NW} = \frac{\bar{\beta}_k}{SE_{NW}(\bar{\beta}_k)}$$

> *"Newey–West (1987, 1994) adjusted t-statistics with automatic lag selection are reported in parentheses."* — Table 13 footnote, p.19

#### Step 5: Report Results
- Significance levels: \*\*\* (p<0.01), \*\* (p<0.05), \* (p<0.10)
- Also report adjusted R² (time-series average of cross-sectional R²)

### 4.5 Key Table 13 Results (Weekly MAX & Weekly REV — Columns 4–6)

| Variable | (4) Base | (5) +Partial | (6) Full |
|----------|----------|--------------|----------|
| **Intercept** | 0.20*** (3.67) | 0.20*** (3.67) | 0.20*** (3.67) |
| **MAX × REV** | −0.06*** (13.30) | −0.06*** (13.16) | −0.05*** (11.44) |
| **MAX** | −0.08*** (6.83) | −0.02* (1.73) | −0.25*** (15.91) |
| **REV** | −0.35*** (22.65) | −0.22*** (12.23) | −0.34*** (16.15) |
| MOM | | | 0.07*** (5.98) |
| BETA | | | 0.02 (0.69) |
| SIZE | | 0.05*** (2.67) | 0.13*** (12.57) |
| BM | | −0.02 (1.58) | 0.02** (2.27) |
| IVOL | | | 0.28*** (4.19) |
| TVOL | | | 0.34*** (4.53) |
| ILLIQ | | | −0.39*** (20.79) |
| **Adj. R²** | 0.02 | 0.11 | 0.14 |

### 4.6 Key Table 13 Footnote (Verbatim)

> *"Columns (1) to (3) report results where the dependent variable is the monthly stock return from month t. Columns (4) to (9) report results where the dependent variable is weekly stock return from week t. MAX is the maximum daily return within a month, week, or 26 weeks. We measure the Max at month/week t−2. REV is a stock's past return from month/week t−1. MOM is the cumulative return from month t−2 to t−12. BETA is the market beta. We follow Scholes and Williams (1977) and Dimson (1979) and use the lag and lead of the market portfolio as well as the current market when estimating beta. SIZE is the natural logarithm of the market capitalization. BM is the book-to-market ratio. TVOL and IVOL are total and idiosyncratic volatility, respectively. ILLIQ is Amihud (2002)'s illiquidity measure. Independent variables are standardized to a mean of 0 and a standard deviation of 1. The Dependent variable (i.e., stock return at month/week t) is measured in percentage terms. Newey–West (1987, 1994) adjusted t-statistics with automatic lag selection are reported in parentheses."* — Table 13 footnote, p.19

### 4.7 Interpretation of Key Results

> *"First and foremost, consistent with our baseline results based on portfolio analysis, we find that the interaction terms between MAX and REV (the lagged return from t−1) are significantly negative in all cases. This result verifies that the short-term reversal effect is stronger when MAX is high, and vice versa."* — Section 6.5, p.19

> *"The coefficients on both MAX and lagged return from t−1 are significantly negative. This result confirms that unconditionally both MAX and lagged returns are associated with lower returns."* — Section 6.5, p.19

---

## 5. Critical Methodological Notes for Replication

### 5.1 Dependent Variable

| Analysis | Dep. Variable | Format |
|----------|---------------|--------|
| **Table 1 (portfolio sorts)** | Weekly **excess** return (return − risk-free rate) | Percentage terms |
| **Table 13 (FM regression)** | Weekly **stock return** (raw, NOT excess) | Percentage terms |

> [!WARNING]
> Table 1 uses *excess returns* but Table 13's footnote says *"stock return at month/week t"* — strongly suggesting raw returns (not excess). The standardization of independent variables with raw return as dependent is the standard FMB convention.

### 5.2 Weekly Return Definition
The paper uses CRSP daily files to construct weekly stock returns. The standard in the literature (and what CRSP provides) follows a **Wednesday-to-Tuesday** trading week convention:

> *"The CRSP daily data files are used to help construct weekly stock returns."* — Section 3, p.4

### 5.3 Standardization is Cross-Sectional (Per Period)
The standardization to mean=0, std=1 is done **cross-sectionally within each period** (each week or month), NOT over the full sample. This is the standard FMB procedure.

### 5.4 ILLIQ Window
The Amihud illiquidity is estimated using **4 weeks** of daily data (weeks t−1 to t−4), not a single week:

> *"We estimate Illiquidity using daily data from weeks t−1 to t−4."* — Section 3, p.5

### 5.5 BETA Estimation
The Scholes-Williams-Dimson beta uses 3 regression coefficients (lag, contemporaneous, lead of market return) summed and adjusted. The paper does **not specify** the exact rolling window length for BETA in Table 13's text, but Table 12's footnote mentions:

> *"we use the stock returns in the rolling window from week t−52 to week t−1"* — Table 12 footnote, p.18

This 52-week rolling window is used for estimating residual returns for Table 12 and is likely the same window used for BETA and IVOL estimation.

### 5.6 Factor Model Data

| Factor Model | Components | Source |
|--------------|-----------|--------|
| **FF4** (Carhart 1997) | MKT-RF, SMB, HML, UMD | Ken French's website |
| **FF6** (FF5 + UMD) | MKT-RF, SMB, HML, RMW, CMA, UMD | Ken French's website |
| **Q-factor** (HXZ 2015) | MKT, ME, ROE, IA | Lu Zhang's website |

---

## 6. Replication Checklist

### Table 1 Replication Checklist

- [ ] Obtain CRSP daily file (ret, vol, shrout, prc, exchcd, shrcd)
- [ ] Filter: share codes 10, 11; exchanges NYSE, AMEX, NASDAQ
- [ ] Construct weekly returns from daily CRSP data
- [ ] Compute MAX = max(daily return) within each week
- [ ] Create lagged MAX: `MAX_{t−1}` and `MAX_{t−2}`
- [ ] Each week, sort stocks into **quintiles** on MAX
- [ ] Compute EW and VW portfolio excess returns per quintile
- [ ] Compute "High minus Low" spread (Q5 − Q1)
- [ ] Time-series regression on FF4, FF6, Q-factor models → alphas
- [ ] Compute Newey-West t-statistics with automatic lag selection
- [ ] Report all values in **percentage terms**

### Table 13 Replication Checklist

- [ ] Compute all variables: MAX, REV, MOM, BETA, SIZE, BM, IVOL, TVOL, ILLIQ
- [ ] Compute interaction: `MAX_{t−2} × REV_{t−1}`
- [ ] **Standardize** all independent variables cross-sectionally (mean=0, std=1) each period
- [ ] Dependent variable: stock return in **percentage terms** (NOT excess return)
- [ ] Run cross-sectional OLS for each period (week/month)
- [ ] Collect coefficient time series
- [ ] Compute Newey-West adjusted means and t-statistics
- [ ] Compute average adjusted R² across all cross-sections
- [ ] Report 9 columns: (1)–(3) monthly, (4)–(6) weekly, (7)–(9) 26-week MAX
- [ ] Significance: ***, **, * notation

---

## 7. Common Pitfalls for Replication

| Pitfall | Why It Matters |
|---------|---------------|
| Using **excess returns** as dep. var. in Table 13 | Paper uses raw stock returns for FMB |
| Forgetting **standardization** of independent vars | Coefficients will not match magnitudes |
| Using 1-week ILLIQ instead of **4-week** | Different liquidity measure; underestimates liquidity |
| Computing BETA with OLS only (no **Scholes-Williams-Dimson** adjustment) | Biased betas for small/illiquid stocks |
| Using **calendar weeks** instead of **Wed-to-Tue** weeks | Standard CRSP convention matters for replicability |
| Not including **MAX × REV interaction** in Table 13 | This is the paper's primary variable of interest |
| Using `MAX_{t−1}` instead of `MAX_{t−2}` in Table 13 | The skip-week is essential to the paper's identification |
| Not computing **all 9 columns** with different MAX windows | Paper tests robustness with monthly, weekly, and 26-week MAX |

---

## 8. Korean Market Data Assessment (Modified Replication)

### 8.1 Modification Summary

| Aspect | Original (Chen 2025) | Modified Replication |
|--------|---------------------|---------------------|
| **Market** | U.S. (NYSE, AMEX, NASDAQ) | **Korea (KOSPI, KOSDAQ)** |
| **Period** | Jul 1963 – Dec 2022 | **Jan 2005 – Dec 2025** |
| **Table 1** | Panels A & B with High-minus-Low | **Panels A & B excluding H−L** |
| **Table 13** | 9 columns (monthly/weekly/26-week MAX), includes REV & MAX×REV | **1 column (weekly MAX only), excludes REV & MAX×REV** |

### 8.2 Data Inventory

#### Primary Dataset: `data/processed/firm_char_weekly_clean.parquet`
- **Rows**: 2,021,661
- **Unique stocks**: 3,367 (Korean equities)
- **Period**: 2005 – 2025 (weekly frequency)
- **Columns**: 30

#### Supporting Datasets

| File | Contents | Usage |
|------|----------|-------|
| `data/raw/daily_characteristics.sas7bdat` (2.4 GB) | Daily: date, permno, ret, vold, ME + investor-type volumes | Source for weekly variable construction |
| `data/raw/ff4_weekly.sas7bdat` | Weekly FF4 factors: MKT_rf, SMB, HML, UMD, CD91 (1998–2026) | Factor-model alpha estimation |
| `data/temp2/data/raw/firm_char.sas7bdat` | Monthly firm characteristics incl. **BM**, beta, mom12, ivol | Potential BM source |

### 8.3 Variable Mapping & Coverage

#### Table 1 Variables (ALL AVAILABLE ✅)

| Required Variable | Available Column | Coverage | Status |
|------------------|-----------------|----------|--------|
| Weekly return (dep. var) | `RET` | 2,021,661 (100%) | ✅ |
| Weekly excess return | `RET_excess_firm` | 2,021,661 (100%) | ✅ |
| Risk-free rate | `CD91` | 2,019,056 (99.9%) | ✅ |
| MAX at t−1 | `MAX_t_minus_1` | 2,016,248 (99.7%) | ✅ |
| MAX at t−2 | `MAX_t_minus_2` | 2,012,881 (99.6%) | ✅ |
| Market cap (VW weights) | `ME_mean_t_minus_1` | 2,016,248 (99.7%) | ✅ |
| FF4 factors (weekly) | `MKT_rf, SMB, HML, UMD` | 2,019,056 (99.9%) | ✅ |

#### Table 13 Variables (Modified: Excludes REV, MAX×REV)

| Required Variable | Available Column | Coverage | Status |
|------------------|-----------------|----------|--------|
| Dep. var: Weekly return (%) | `RET` | 2,021,661 (100%) | ✅ |
| MAX at t−2 | `MAX_t_minus_2` | 2,012,881 (99.6%) | ✅ |
| SIZE (ln market cap) | `log_ME_t_minus_1` | 2,016,248 (99.7%) | ✅ |
| ILLIQ (Amihud) | `ILLIQ_t_minus_1` | 1,981,897 (98.0%) | ✅ |
| TVOL (total vol) | `TVOL_t_minus_1` | 2,015,838 (99.7%) | ✅ |
| BETA (market beta) | `BETA_t_minus_1` | 1,933,635 (95.6%) | ✅ |
| IVOL (idiosyncratic vol) | `IVOL_t_minus_1` | 1,933,635 (95.6%) | ✅ |
| MOM (momentum) | `MOM_raw_t_minus_1` | 1,972,899 (97.6%) | ✅ |
| **BM (book-to-market)** | **NOT in weekly data** | — | ⚠️ |
| ~~REV~~ (excluded) | — | — | N/A |
| ~~MAX×REV~~ (excluded) | — | — | N/A |

### 8.4 BM Variable: Gap Analysis

**BM is the only variable missing from the weekly dataset.** However, it exists in the monthly `firm_char.sas7bdat`:

| Dataset | BM Coverage | Notes |
|---------|------------|-------|
| `data/temp2/data/processed/firm_char_clean.parquet` | 553,391 / 1,309,728 (42.3%) | Monthly frequency; 1998–2025 |

**Options to resolve:**
1. **Forward-fill monthly BM to weekly frequency** — Since BM changes slowly (updated annually from financial statements), forward-filling the most recent monthly BM value to each week is standard practice.
2. **Drop BM from Table 13** — Run with 6 controls instead of 7. Given the user's already-simplified 1-column specification, this is acceptable.

> [!IMPORTANT]
> BM has only 42.3% coverage in the monthly data, which after merging to weekly frequency may further reduce the sample for the "full controls" specification. Consider running both with and without BM.

### 8.5 Feasibility Verdict

| Table | Verdict | Rationale |
|-------|---------|-----------|
| **Table 1** (Panels A & B, no H−L) | ✅ **Fully feasible** | All variables available with 99%+ coverage |
| **Table 13** (1 col, weekly MAX, no REV/interaction) | ✅ **Feasible with minor gap** | All controls available except BM; can be forward-filled from monthly or dropped |

### 8.6 Modified Table 1 Target Structure

| | Low | 2 | 3 | 4 | High |
|---|---|---|---|---|---|
| **Panel A** (sort on MAX from t−1) | | | | | |
| A.1: EW Excess | x.xx | x.xx | x.xx | x.xx | x.xx |
| *(t-stat)* | (x.xx) | (x.xx) | (x.xx) | (x.xx) | (x.xx) |
| A.1: EW α_FF4 | x.xx | x.xx | x.xx | x.xx | x.xx |
| *(t-stat)* | (x.xx) | (x.xx) | (x.xx) | (x.xx) | (x.xx) |
| A.2: VW Excess | x.xx | x.xx | x.xx | x.xx | x.xx |
| *(t-stat)* | (x.xx) | (x.xx) | (x.xx) | (x.xx) | (x.xx) |
| A.2: VW α_FF4 | x.xx | x.xx | x.xx | x.xx | x.xx |
| *(t-stat)* | (x.xx) | (x.xx) | (x.xx) | (x.xx) | (x.xx) |
| **Panel B** (sort on MAX from t−2, skip t−1) | | | | | |
| *(same structure)* | | | | | |

### 8.7 Modified Table 13 Target Structure (Single Column)

| Variable | Weekly MAX |
|----------|-----------|
| Intercept | x.xx (t) |
| MAX_{t−2} | x.xx (t) |
| MOM | x.xx (t) |
| BETA | x.xx (t) |
| SIZE | x.xx (t) |
| BM | x.xx (t) |
| IVOL | x.xx (t) |
| TVOL | x.xx (t) |
| ILLIQ | x.xx (t) |
| Adj. R² | x.xx |
