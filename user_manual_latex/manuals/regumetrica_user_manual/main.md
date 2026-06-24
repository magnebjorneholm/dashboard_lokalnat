---
title: Regumetrica
subtitle: User manual
version: "1.0"
status: beta
url: https://www.regumetrica.com/um
---

## Introduction

Regumetrica simulates counterfactual revenue frames for electricity distribution networks in Sweden, based on a wide range of regulatory specifications. The current version computes revenue frames for the ongoing regulatory period, 2024–2027.

To get started, create an account at [www.regumetrica.com/newuser](https://www.regumetrica.com/newuser). You will need a valid email address, which will also serve as your username. During registration, you will be asked to indicate your primary concession area of interest. Concession areas are the smallest geographical units for which revenue frames are determined. You can change your preferred concession area at any time. Several accounts may be connected to the same concession area. Each area has both a name and an identification number assigned by the regulator.

After logging in, you enter the main environment by opening a *case*. A case is a workspace that contains all assumptions for a specific regulatory simulation. Each case represents one set of assumptions and therefore produces one revenue frame. Cases must be named; by default they are labeled consecutively ("Case 1," "Case 2," etc.), but you can also assign custom names as well as longer case notes. Initially, all regulatory assumptions are set according to the current regulatory model.

Once you have adjusted the assumptions to your preferred levels, the model is run. Simulations usually complete within a few seconds, though more complex configurations may take longer. Regumetrica then provides downloadable data detailing the revenue frame for the selected concession area, along with all underlying calculation components. In addition to data downloads, results can also be displayed graphically, for example as charts decomposing different components of the revenue frame. After running a model, you may choose to save the case for later use.

### Model Components

The regulatory model is organized into *Base modules* and *Add-on modules*. Base modules represent the core components of the revenue frame calculation: Regulatory asset base valuation, Depreciation, Cost of capital, Operating expenditures, and the Efficiency incentive (benchmarking). Modules contain *Parameters* and *Variables*:

- *Parameters* are fixed values that define the structural relationships within the regulatory model. They capture assumptions or policy choices that apply uniformly across all regulated entities. For example, the regulatory *WACC* (Weighted Average Cost of Capital) determines the allowed rate of return on capital and is itself derived from a set of *sub-parameters*, such as the risk-free rate of return. Another example of a parameter is the *economic lifetime* assigned to a specific asset category, which determines the rate of capital depreciation over time. **A change to a parameter applies to every company in the model.**

- *Variables* are measurable inputs that vary across regulated entities. They correspond to real-world data, such as asset quantities, operating costs, or energy delivered, that the model uses to calculate revenue frames. Most variables are reported to the regulator through the KENT excel reporting template. **A change to a variable applies only to your own concession area.** Regumetrica users have the option of adjusting such variables manually, or by uploading standardized KENT excel sheets.

*Add-on modules* extend the base regulatory model with analyses that fall outside the scope of the current regulatory framework. Each add-on is delivered as a separate tool with its own user manual. The first is the *New benchmarking model*, which estimates how a network's efficiency requirement would change under Ei's proposed total-expenditure (TOTEX) benchmarking model for the 2028–2031 regulatory period. For more information, see its separate user manual. Further add-on modules will be added over time.

### How to use this manual

The revenue cap tool is organized as a four-step workflow, and this manual follows that order. You move through the steps using the sidebar:

1. **Create and select case**: create a new case or open a saved one.
2. **Case Setup**: choose which modules you want to configure.
3. **Specification**: adjust the parameters and variables of the selected modules.
4. **Revenue Frame**: run the calculation and read, compare, and export the results.

Two conventions recur throughout. First, anything you do not change keeps its *baseline* value, the value implied by the current regulatory model. Modules you do not select in Case Setup, and individual fields you do not edit, are all computed on baseline. Second, every adjustable input is identified by a *Parameter-ID* (e.g. 1.1.1) or a *Variable-ID* (e.g. 10.2). These IDs are cited next to each field in the tool and used consistently in this manual; the complete catalogue is collected in the Appendix.

---

## 1. Create and select case

This is the entry page of the revenue cap tool. Here you create the case you want to work on, or reopen one you saved earlier. All later steps act on the case that is currently open.

### 1.1 Creating a case

To start a new simulation, give the case a name (and, optionally, a note describing its purpose) and create it. The case opens immediately with all assumptions on baseline, ready to be configured in the following steps. You can store several cases and return to them later.

### 1.2 Working with saved cases

Select any saved case to see a short summary (its name, notes, computed revenue frame if it has been run, and which modules were configured) and to act on it:

- **Load**: open the case, making it the active case for the rest of the workflow.
- **Edit**: rename the case or change its notes.
- **Duplicate**: copy the case under a new name, for instance to explore a variation without altering the original.
- **Delete**: remove the case permanently.

### 1.3 Comparing cases

Cases that have been computed can be compared side by side. Selecting two or more produces a table that places their key figures next to each other, which is the quickest way to see how different sets of assumptions move the revenue frame.

---

## 2. Case Setup

Case Setup is where you decide *which* parts of the regulatory model you want to configure for the open case. You select modules (and, within most modules, individual sections) and only the selected items are opened for editing in the next step.

The guiding rule is simple: **anything you do not select is computed on its baseline value.** Selecting a module does not by itself change any result; it merely makes that module's parameters and variables available for adjustment. A case with nothing selected reproduces the baseline revenue frame.

The base modules correspond to the components of the revenue frame:

- **M1: Regulatory asset base valuation**
- **M2: Depreciation**
- **M3: Cost of capital**
- **M4: Operating expenditures**
- **M5: Efficiency incentive (benchmarking)**

The revenue cap tool has no add-on modules of its own: the benchmarking analysis is a section within the efficiency incentive (M5), not a separate module. Add-on modules, such as the New benchmarking model, are delivered as separate tools with their own manuals (see the Introduction).

Most modules are divided into sections so that you can, for example, adjust cost-of-capital *parameters* without also opening the company-specific *variables*, or configure the benchmarking specification of the efficiency incentive separately from its requirement parameters. Sections that adjust parameters affect all companies; sections that adjust variables affect only your own concession area. The individual sections are described together with their fields in Section 3.

---

## 3. Specification

This is where you set the assumptions of the case. The page presents one tab per module; only the modules you selected in Case Setup are active. Each adjustable field shows its Parameter-ID or Variable-ID and its baseline value, and is flagged when it differs from baseline so that your changes are easy to track. You can save the case at any point from this page.

Changes have to be saved manually: a case is written to storage only when you save it explicitly. Until then your edits are kept in the current session, so they survive moving between pages and reloading the browser. For a typed value to register, confirm it by pressing Enter (or moving focus out of the field) after entering it; a value left uncommitted in an open field may be lost. To make changes permanent across sessions, save the case.

### 3.1 M1: Regulatory asset base valuation

This module determines the valuation of the regulatory asset base. You can rescale the regulated norm values, rescale your own asset quantities, or replace the underlying asset data entirely by uploading a KENT file.

#### 3.1.1 Norm value scaling (parameters)

Norm values are the per-unit asset values set by the regulator. Two kinds of scaling factors are available, both applying to all companies:

- **General scaling factor (1.1.1)**: a single multiplier applied to *all* asset norm values. Baseline 1.00.
- **Category scaling factors (1.2.1–1.2.17)**: one multiplier per asset category, applied on top of the general factor. Baseline 1.00 for every category.

A factor of 1.00 leaves the norm value unchanged; 1.20 raises it by 20%, 0.80 lowers it by 20%. The 17 asset categories are listed in Table C1 in Appendix C.

#### 3.1.2 Asset quantities (variables)

Here you scale the quantity of assets in your own concession area, by category, relative to the reported baseline (Variable-IDs 10.2–10.18). This changes the size of your asset base without touching the norm values. Scaling affects the ordinary portion of the capital base only.

#### 3.1.3 KENT upload

Instead of scaling quantities, you can upload a KENT excel file to supply the asset data for your concession area directly. A KENT upload replaces the asset-quantity adjustments above; the norm value scaling factors (1.1.1 and 1.2.x) still apply on top of the uploaded data.

### 3.2 M2: Depreciation

This module sets the economic lifetimes used to depreciate the asset base. For each of the 17 asset categories you can set two parameters, both applying to all companies:

- **Ordinary lifetime (2.X.1)**: the economic lifetime over which an asset is depreciated.
- **Tail period (2.X.2)**: the additional period during which an asset remains in service beyond its ordinary lifetime.

Lifetimes are edited in a table, one row per category. The tail period cannot exceed the ordinary lifetime; if you enter a larger value it is treated as equal to the ordinary lifetime in the calculation. Baseline lifetimes are listed in Table C1 in Appendix C.

### 3.3 M3: Cost of capital

This module covers the allowed return on capital, the WACC, and the incentive schemes that adjust that return for network losses, capacity utilization, and quality of supply. It has three sections: the WACC parameters, the incentive parameters, and the company-specific incentive variables.

#### 3.3.1 WACC (parameters)

The WACC is the real, pre-tax weighted average cost of capital. You can specify it in three ways; in every case the result is an "active WACC" that you apply to the case.

- **Base parameters**: enter the underlying CAPM inputs (debt ratio, asset beta, risk-free rate, market risk premium, credit risk premium, tax rate, and inflation) and let the tool derive the WACC, displaying the resulting equity beta, cost of equity, cost of debt, and the final real, pre-tax WACC used in the calculations.
- **Derived**: modify the intermediate quantities directly, such as the cost of equity, cost of debt, debt ratio, tax rate, and inflation. Use this when you want to set, say, the cost of equity without specifying the full CAPM chain behind it.
- **Direct input**: enter the real, pre-tax WACC directly.

Baseline values for all WACC parameters, with their Parameter-IDs, are given in Table A2 in Appendix A. When you set a derived quantity directly, that value overrides any sub-parameters behind it.

#### 3.3.2 Incentive parameters

The allowed return is adjusted by three incentive schemes, each of which can be switched on or off:

- **Quality (3.3)**: compensates for the quality of supply, based on interruptions. You can adjust the maximum CEMI4 correction and the underlying interruption cost tables for interruption energy (ILE, kr/kWh) and interruption power (ILEffekt, kr/kW), listed by customer type in Table A4 in Appendix A.
- **Network loss (3.4)**: rewards or penalizes network losses relative to a norm. You can set the sharing factor, i.e. the share of the gain or loss retained by the company, and the electricity price used to value losses, per year.
- **Utilization rate (3.5)**: rewards higher capacity utilization. This scheme is computed automatically from company data; here you only enable or disable it.

In addition, you can set the cap on the **total** incentive adjustment per year, expressed as a share of the allowed return, and the KPI factors used to index interruption costs to the price level of the reference year (one per year).

#### 3.3.3 Incentive variables (own area)

These are the company-specific inputs to the incentive schemes for your concession area (Variable-IDs 30.x). An override you enter here applies to all years of the regulatory period. They are grouped as:

- **Network loss (30.2)**: norm and observed loss levels and energy input.
- **Utilization rate (30.3)**: norm and observed utilization and the cost of the upstream network.
- **Interruptions (30.4)**: the CEMI4 measure, and, per customer type, the average interruption time (AIT), average interruption frequency (AIF), and annual average power.

The full set of interruption variables, broken down by customer type and by planned/unplanned and norm/observed, is listed in Table B2 in Appendix B.

### 3.4 M4: Operating expenditures

This module covers operating expenditures. You can rescale cost components for your company, or override their levels directly.

#### 3.4.1 Cost scaling (parameters)

Three multipliers are available (baseline 1.00 each):

- **Adjustable OPEX (4.1.1)**: the operating expenditure subject to the efficiency requirement.
- **Flexibility services (4.1.2)**: the cost of flexibility services.
- **Non-adjustable OPEX (4.1.3)**: costs outside the operator's direct control.

#### 3.4.2 OPEX variables (own area)

Instead of scaling, you can set the level of each component directly for your concession area, in tkr: adjustable OPEX (40.1.1), flexibility services (40.1.2), and non-adjustable costs (40.2.1). A direct override takes precedence over the corresponding scaling factor for your company.

### 3.5 M5: Efficiency incentive (benchmarking)

This module measures each company's efficiency by benchmarking and converts the resulting efficiency potential into an annual efficiency requirement. It has two sections: the *benchmarking* specification, which defines the model that measures efficiency, and the *efficiency requirement*, which sets how the measured potential is translated into an annual requirement.

#### 3.5.1 Benchmarking (DEA specification)

The benchmarking section lets you define a custom Data Envelopment Analysis (DEA) specification, the model that measures each company's efficiency relative to the frontier. You can change:

- **Input variables**: the cost measures used as DEA inputs (e.g. capital cost, adjustable OPEX, or TOTEX).
- **Output variables**: the service measures used as DEA outputs (number of connections, subscribed power, substations, and energy delivered at low and high voltage).
- **Returns to scale**: constant (CRS) or variable (VRS).
- **Outlier identification (5.1.1)**: the lower and upper percentiles and the multiplier of the interquartile range that define which firms are treated as outliers.

You can run the DEA directly from this section to preview efficiency scores before computing the full revenue frame. Two points are worth noting. First, the DEA always operates on the original, historical cost data; changes you make to OPEX, capital costs, or WACC elsewhere do not alter the benchmarking. Only the model specification (inputs, outputs, returns to scale, and outlier treatment) changes the result. Second, the resulting efficiency potential feeds the efficiency requirement below.

#### 3.5.2 Efficiency requirement

The efficiency requirement section converts the efficiency potential measured by the benchmarking into an annual efficiency requirement. The adjustable parameters are:

- **Maximum efficiency potential cap (5.2.1)**: an upper bound on the assessed potential. Baseline 30%.
- **Realization time (5.2.2)**: the number of years over which the potential is expected to be realized. Baseline 8 years.
- **Customer sharing factor (5.2.3)**: the share of the efficiency gain passed on to customers. Baseline 50%.
- **Minimum annual requirement (5.3.1)**: a floor on the annual requirement. Baseline 1%.
- **Cost base (5.4.1)**: whether the efficiency requirement is applied to OPEX only (baseline) or to TOTEX (including capital costs).

The tool shows the resulting range of the annual efficiency requirement as you change these values. The outlier threshold that excludes extreme firms (5.1.1) is set in the benchmarking section above.

---

## 4. Revenue Frame

This page runs the calculation and presents the results. Computing a case produces a revenue frame for your concession area, shown alongside the baseline so that the effect of your assumptions is always visible.

### 4.1 Running and saving

Compute the revenue frame to run the model with the current configuration. You can then save the case to keep the configuration and its results, or discard your changes to return to the last saved state. If you change the configuration after computing, recompute to bring the results up to date.

### 4.2 Reading the results

The results are presented in several complementary ways:

- **Revenue frame summary**: the total revenue frame for the case, the baseline total, and the difference between them.
- **Decomposition**: a breakdown of the revenue frame into its components (capital costs, depreciation, return, operating expenditures, efficiency and incentive adjustments, flexibility services, interruption compensation, and deductions), each labeled with its Variable-ID.
- **Geographic comparison**: a map placing your concession area in the context of all areas for a selected result variable.
- **Module outputs**: per-module detail (asset base, depreciation, cost of capital, and the efficiency incentive), each compared against baseline. The output variables shown here are catalogued in Table B4 in Appendix B.

### 4.3 Export

The full revenue frame and all underlying calculation components can be downloaded for your own analysis and documentation.

---

## Appendix

### A. Parameter reference

This appendix lists the adjustable parameters by module, with their baseline values. Parameters apply to all companies.

#### Table A1. M1: Asset base valuation parameters

| Description | Baseline | Parameter-ID |
|---|:---:|---|
| General scaling factor for asset valuation | 1.00 | 1.1.1 |
| *Category scaling factors (baseline 1.00 each)* | | |
| Andra markarbeten och byggnader, linjekoncession | 1.00 | 1.2.1 |
| Annan ledning, linjekoncession | 1.00 | 1.2.2 |
| Annan ledning, områdeskoncession | 1.00 | 1.2.3 |
| Annan luftledning, linjekoncession | 1.00 | 1.2.4 |
| It-system | 1.00 | 1.2.5 |
| Kabelskåp | 1.00 | 1.2.6 |
| Ledning $\geq$ 220 kV (ej luftledning), linjekoncession | 1.00 | 1.2.7 |
| Luftledning $\geq$ 220 kV, linjekoncession | 1.00 | 1.2.8 |
| Luftledning, områdeskoncession | 1.00 | 1.2.9 |
| Markarbeten och byggnader, ledningsnät $\geq$ 220 kV, linjekoncession | 1.00 | 1.2.10 |
| Markarbeten och byggnader, områdeskoncession | 1.00 | 1.2.11 |
| Mätare | 1.00 | 1.2.12 |
| Nätstation | 1.00 | 1.2.13 |
| Shuntreaktor | 1.00 | 1.2.14 |
| Styr- och kontrollutrustning | 1.00 | 1.2.15 |
| Ställverk utan sekundärapparater | 1.00 | 1.2.16 |
| Transformator | 1.00 | 1.2.17 |

*Scaling factors are applied multiplicatively to the asset norm values. Full category names are given in Table C1 in Appendix C.*

#### Table A2. M3: Cost of capital (WACC) parameters

| Description | Baseline | Parameter-ID |
|---|:---:|---|
| *Base parameters* | | |
| Debt ratio | 0.36 | 3.1.1 |
| Asset beta | 0.37 | 3.1.2 |
| Risk-free rate | 0.0287 | 3.1.3 |
| Market risk premium | 0.0668 | 3.1.4 |
| Credit risk premium | 0.0114 | 3.1.5 |
| Tax rate | 0.206 | 3.1.6 |
| Inflation, CPIF forecast | 0.0202 | 3.1.7 |
| *Derived parameters* | | |
| Equity beta | 0.54 | 3.2.1 |
| Nominal cost of equity after tax | 0.0645 | 3.2.2 |
| Nominal cost of debt after tax | 0.0318 | 3.2.3 |
| Nominal WACC before tax | 0.0664 | 3.2.4 |
| Real WACC before tax | 0.0453 | 3.2.5 |

*Setting a derived parameter directly overrides changes to the base parameters behind it.*

#### Table A3. M3: Incentive adjustment parameters

| Description | Baseline | Parameter-ID |
|---|:---:|---|
| Max total adjustment (share of allowed return) | 0.333 | 3.3.1 |
| Network loss incentive sharing factor | 0.75 | 3.4.2 |
| Average network loss cost (kr/MWh) | 734 | 3.4.3 |
| CEMI4 correction factor | 0.25 | 3.6.6 |
| KPI indexation factor (per year) | 1.1546 | 3.7.1–3.7.4 |

*The electricity price (3.4.3) and the KPI indexation factors (3.7.1–3.7.4) are set per year. The interruption cost tables (ILE/ILEffekt) underlying the quality scheme are listed by customer type in Table A4 in Appendix A.*

#### Table A4. M3: Interruption cost tables (ILE/ILEffekt) by customer type

| Order | Customer type | ILE unplanned (kr/kWh) | ILE planned (kr/kWh) | ILEffekt unplanned (kr/kW) | ILEffekt planned (kr/kW) |
|:---:|---|---:|---:|---:|---:|
| 1 | Household | 5.84 | 4.98 | 1.95 | 1.85 |
| 2 | Agriculture | 34.35 | 14.10 | 9.78 | 1.72 |
| 3 | Trade/Services | 175.06 | 79.31 | 17.78 | 5.94 |
| 4 | Industry | 159.96 | 76.00 | 70.75 | 20.71 |
| 5 | Public sector | 96.97 | 43.70 | 7.65 | 0.92 |
| 6 | Boundary points | 96.01 | 45.16 | 22.18 | 7.08 |

*ILE (interruption energy cost, kr/kWh) and ILEffekt (interruption power cost, kr/kW) are the per-customer-type cost rates underlying the quality (interruption) incentive (M3, Section 3.3); each is reported for unplanned and planned interruptions. They are adjustable parameters, Parameter-IDs 3.6.7–3.6.18 (ILE) and 3.6.19–3.6.30 (ILEffekt), two per customer type in the order shown (unplanned then planned). The same six customer types index the interruption variables (30.4.x) in Table B2 in Appendix B.*

#### Table A5. M4: Operating expenditure parameters

| Description | Baseline | Parameter-ID |
|---|:---:|---|
| Scaling factor adjustable OPEX | 1.00 | 4.1.1 |
| Scaling factor flexibility services | 1.00 | 4.1.2 |
| Scaling factor non-adjustable OPEX | 1.00 | 4.1.3 |

#### Table A6. M5: Efficiency incentive parameters

| Description | Baseline | Parameter-ID |
|---|:---:|---|
| Outlier threshold (IQRs above $Q_{3}$) <sup>a</sup> | 2.00 | 5.1.1 |
| Maximum efficiency potential cap | 0.30 | 5.2.1 |
| Realization time (years) | 8 | 5.2.2 |
| Customer sharing factor | 0.50 | 5.2.3 |
| Minimum annual efficiency requirement | 0.0100 | 5.3.1 |
| Apply efficiency requirement on TOTEX | No (OPEX only) | 5.4.1 |

*<sup>a</sup> The outlier threshold is configured in the benchmarking section of the efficiency incentive (M5, Section 3.5.1) as part of the DEA specification.*

### B. Variable reference

This appendix lists the input variables you can adjust and the main output variables shown in the results. Input variables apply only to your own concession area.

#### Table B1. M1: Asset quantity variables (input)

| Description | Variable-ID |
|---|---|
| Andra markarbeten och byggnader, linjekoncession | 10.2 |
| Annan ledning, linjekoncession | 10.3 |
| Annan ledning, områdeskoncession | 10.4 |
| Annan luftledning, linjekoncession | 10.5 |
| It-system | 10.6 |
| Kabelskåp | 10.7 |
| Ledning $\geq$ 220 kV (ej luftledning), linjekoncession | 10.8 |
| Luftledning $\geq$ 220 kV, linjekoncession | 10.9 |
| Luftledning, områdeskoncession | 10.10 |
| Markarbeten och byggnader, ledningsnät $\geq$ 220 kV, linjekoncession | 10.11 |
| Markarbeten och byggnader, områdeskoncession | 10.12 |
| Mätare | 10.13 |
| Nätstation | 10.14 |
| Shuntreaktor | 10.15 |
| Styr- och kontrollutrustning | 10.16 |
| Ställverk utan sekundärapparater | 10.17 |
| Transformator | 10.18 |

*Asset quantities are sourced from the KENT reporting template; units vary by asset type.*

#### Table B2. M3: Incentive variables (input, own area)

| Description | Variable-ID |
|---|---|
| *30.2 Network loss* | |
| Network loss norm level | 30.2.1 |
| Network loss observed level | 30.2.2 |
| Energy input | 30.2.3 |
| *30.3 Utilization rate* | |
| Utilization rate norm level | 30.3.1 |
| Utilization rate observed level | 30.3.2 |
| Cost for upstream network | 30.3.3 |
| *30.4 Interruptions* | |
| CEMI4 norm / observed | 30.4.1 / 30.4.2 |
| Annual average power, per customer type | 30.4.3–30.4.8 |
| Average interruption time (AIT), norm and observed, per customer type | 30.4.9–30.4.32 |
| Average interruption frequency (AIF), norm and observed, per customer type | 30.4.33–30.4.56 |

*Customer types: Household, Agriculture, Trade/Services, Industry, Public sector, Boundary points (Table A4 in Appendix A). AIT and AIF are reported for planned and unplanned interruptions, each as a norm and an observed value. An override applies to all years 2024–2027.*

#### Table B3. M4: OPEX variables (input, own area)

| Description | Variable-ID |
|---|---|
| Adjustable OPEX | 40.1.1 |
| Flexibility service cost | 40.1.2 |
| Total non-adjustable costs | 40.2.1 |

*Values in tkr. A direct override takes precedence over the corresponding scaling factor (4.1.x).*

#### Table B4. Main output variables (shown in results)

| Description | Variable-ID |
|---|---|
| Asset value, total and per category | 11.1; 11.2–11.18 |
| Depreciation cost, total and per category | 20.1; 20.2–20.18 |
| Capital cost (return), total and per category | 30.1.1; 30.1.2–30.1.18 |
| Network loss adjustment | 30.2.4 / 30.2.5 |
| Utilization rate adjustment | 30.3.4 / 30.3.5 |
| Interruption adjustment | 30.4.57–30.4.59 |
| Total incentive adjustment | 30.5.1 / 30.5.2 |
| Efficiency score / super-efficiency | 50.3.1 / 50.3.2 |
| Efficiency potential / applied potential | 50.3.3 / 50.3.4 |
| Efficiency adjustment, OPEX / CAPEX | 50.4.1 / 50.4.2 |

*Output variables are computed by the model and shown in the results; they are not directly editable. Values in kr unless noted. For each adjustment, the variants shown are before and after the applicable cap.*

### C. Asset categories

#### Table C1. Asset categories and baseline lifetimes

| Code | Category | Ordinary | Tail | Parameter-IDs |
|:---:|---|:---:|:---:|---|
| 1 | Andra markarbeten och byggnader, linjekoncession | 100 | 24 | 2.1.1; 2.1.2 |
| 2 | Annan ledning, linjekoncession | 100 | 24 | 2.2.1; 2.2.2 |
| 3 | Annan ledning, områdeskoncession | 100 | 24 | 2.3.1; 2.3.2 |
| 4 | Annan luftledning, linjekoncession | 100 | 24 | 2.4.1; 2.4.2 |
| 5 | It-system | 20 | 4 | 2.5.1; 2.5.2 |
| 6 | Kabelskåp | 60 | 14 | 2.6.1; 2.6.2 |
| 7 | Ledning $\geq$ 220 kV (ej luftledning), linjekoncession | 80 | 20 | 2.7.1; 2.7.2 |
| 8 | Luftledning $\geq$ 220 kV, linjekoncession | 120 | 30 | 2.8.1; 2.8.2 |
| 9 | Luftledning, områdeskoncession | 80 | 20 | 2.9.1; 2.9.2 |
| 10 | Markarbeten och byggnader, ledningsnät $\geq$ 220 kV, linjekoncession | 80 | 20 | 2.10.1; 2.10.2 |
| 11 | Markarbeten och byggnader, områdeskoncession | 100 | 24 | 2.11.1; 2.11.2 |
| 12 | Mätare | 20 | 4 | 2.12.1; 2.12.2 |
| 13 | Nätstation | 80 | 20 | 2.13.1; 2.13.2 |
| 14 | Shuntreaktor | 80 | 20 | 2.14.1; 2.14.2 |
| 15 | Styr- och kontrollutrustning | 30 | 6 | 2.15.1; 2.15.2 |
| 16 | Ställverk utan sekundärapparater | 80 | 20 | 2.16.1; 2.16.2 |
| 17 | Transformator | 100 | 24 | 2.17.1; 2.17.2 |

*Ordinary and tail lifetimes in years. The category code is used throughout the scaling (1.2.x), quantity (10.x), and lifetime (2.x) parameters and variables.*
