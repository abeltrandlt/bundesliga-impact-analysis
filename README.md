# Bundesliga Player Impact & Market Inefficiency Analysis

**TL;DR:** A **Moneyball-inspired** analysis that builds a **role-relative impact model** for the **2024/25 Bundesliga** and compares impact to market value to identify **undervalued contributors**. Live-season (2025/26) notes are used for **qualitative validation** under public data constraints.

**Tech:** Python (pandas, numpy), Jupyter, matplotlib/seaborn, FBref tables, Transfermarkt valuations (Kaggle)

---

## Overview

This project evaluates player performance through a **role-relative impact model** with the goal of identifying contributors whose on-field influence exceeds their market valuation.

Rather than ranking players via headline statistics (goals, assists), the analysis measures **multi-phase contribution** across **shooting, passing, possession, and defending**, while respecting structural differences between positions.

The project is anchored on the **2024/25 Bundesliga season**, with limited qualitative validation using early **2025/26** observations.

---

<img width="846" height="550" alt="image" src="https://github.com/user-attachments/assets/b4829d15-d188-46f6-b9c6-04d8ad10034d" />

---

## Motivation

Impact in football cannot exist without **opportunity, context, and role awareness**.

Comparing a striker to a defensive midfielder by goals alone ignores actions that enable team success: ball recovery, progression, pressure, and positional discipline. These contributions are often underrepresented in market narratives, creating potential **market inefficiencies**.

This project aims to:
- Measure impact **relative to role**, not reputation
- Identify **market inefficiencies** using public data
- Show how **historical impact** can inform prospective monitoring

---

## Data Sources

- **FBref (public tables)**
  - Standard, Shooting, Passing, Possession, Defending
  - **2024/25** (complete)
  - **2025/26** (partial; used for observational validation)

- **Transfermarkt (via Kaggle)**
  - Player market valuations (snapshot: **April 2025**)
  - Used for **2024/25** value efficiency analysis

> **Note:** Public data availability changed during development, limiting advanced live-season metrics. The project explicitly accounts for this and avoids forcing incomplete live data into the core model.

---

## Methodology

### 1) Data Processing
- Clean and standardize raw FBref tables
- Compute per-90 metrics
- Filter low-minute players to reduce noise
- Normalize positional labels into roles: **DF, MF, FW, GK**

### 2) Role-Relative Normalization
- Convert key metrics to **within-role percentiles**
- Prevent cross-role distortion (e.g., defenders vs forwards)

### 3) Impact Model
Two scores are computed:
- **Impact (Raw):** aggregated role-relative contribution
- **Impact (Adjusted):** reliability-weighted version accounting for minutes played

Weights are role-aware:
- defense emphasis for **DF**
- progression/creation for **MF**
- threat generation for **FW**

### 4) Market Value Efficiency (2024/25)
- Compare impact vs market value
- **Value efficiency** highlights players delivering high impact per unit cost
- Analysis is retrospective to avoid valuation timing mismatch

### 5) Live-Season Validation (2025/26)
- Manually track a small subset of shortlisted players
- Used for qualitative confirmation, not model recalibration

---

## Key Outputs

- **Role-relative impact tables** for 2024/25 (DF/MF/FW)
- **Value-efficiency shortlist** by role (impact vs market valuation)
- **Phase 11 notebook**: narrative visuals + findings + live validation notes

---

## Limitations

- Public data availability changed mid-project, restricting advanced live-season stats
- Market values are snapshots (not real-time pricing)
- Live-season validation is observational rather than model-driven

---

## Repository Structure

```text
bundesliga-impact-analysis/
├── data/
│   ├── raw/            # Raw FBref CSVs (not committed)
│   ├── processed/      # Modeled outputs (not committed)
│   └── external/       # Transfermarkt (Kaggle) data (not committed)
├── notebooks/
│   └── 11_phase11_impact_storytelling.ipynb
├── src/
│   ├── scraping.py
│   ├── processing_phase4.py
│   ├── cleaning.py
│   ├── normalization_phase6.py
│   ├── impact_phase8.py
│   └── phase10_moneyball.py
├── README.md
└── requirements.txt
