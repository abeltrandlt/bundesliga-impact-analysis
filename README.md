# Bundesliga Player Impact & Market Inefficiency Analysis
### Overview

This project analyzes player performance in the Bundesliga through a role-relative impact model, with the goal of identifying contributors whose on-field influence exceeds their market valuation. A Moneyball-style approach to player evaluation.

Rather than ranking players by traditional headline statistics (goals, assists), the analysis evaluates multi-phase contribution across shooting, passing, possession, and defending, while respecting the structural differences between positions.

The project is anchored on the 2024/25 Bundesliga season, with limited qualitative validation using early 2025/26 live-season data.

### Motivation

Impact in football cannot exist without opportunity, context, and role awareness.

Comparing a striker to a defensive midfielder by goal contributions alone ignores the underlying actions that enable success: ball recovery, progression, pressure, and positional discipline. As a result, certain player profiles, particularly defensive and transitional contributors, are often undervalued by the market.

This project aims to:

- Measure impact relative to role, not reputation

- Identify market inefficiencies using public data

- Demonstrate how historical impact can inform prospective evaluation

### Data Sources

- FBref (StatsBomb / Opta-derived public tables)

  - Standard, Shooting, Passing, Possession, Defending tables

  - 2024/25 season (complete)

  - 2025/26 season (partial; observational use only)

- Transfermarkt (via Kaggle dataset)

  - Player market valuations (April 2025 snapshot)

  - Used exclusively for 2024/25 value efficiency analysis

Note: Due to changes in public data availability, some advanced metrics are no longer consistently accessible for the live 2025/26 season. The project explicitly accounts for this limitation.

### Methodology
1. Data Processing

- Raw FBref tables are cleaned and standardized

- Per-90 metrics are computed

- Players with insufficient minutes are filtered to reduce noise

- Positional labels are normalized into four roles: DF, MF, FW, GK

2. Role-Relative Normalization

- Metrics are converted into within-role percentiles

- This prevents cross-role distortion (e.g., defenders vs forwards)

3. Impact Model

Two impact scores are computed:

- Impact (Raw): Aggregated role-relative contribution

- Impact (Adjusted): Reliability-weighted version accounting for minutes played

Metric weights are role-aware and emphasize:

- Defensive actions for defenders

- Progression and creation for midfielders

- Threat generation for attackers

4. Market Value Efficiency (2024/25)

- Impact scores are compared against market valuation

- Value efficiency highlights players delivering high impact per unit of cost

- Analysis is strictly retrospective to avoid misaligned valuation timing

5. Live-Season Validation (2025/26)

- A small subset of shortlisted players is manually tracked

- Used for qualitative confirmation, not model recalibration

- Observes persistence of impact signals under real-world constraints

### Key Findings

- Impact is highly role-dependent and should not be compared across positions

- Several players delivered elite impact at below-market valuations

- Defensive and transitional contributors are frequently undervalued

- Historical undervaluation provides a stable lens for prospective monitoring

- Live-season observations largely align with prior impact signals

### Limitations

- Public data availability changed mid-project, restricting advanced live-season metrics

- Market values represent snapshots, not real-time pricing

- Live-season analysis is observational rather than model-driven

These limitations are addressed transparently and do not affect the validity of the core impact model.

### Repository Structure
bundesliga-impact-analysis/
│
├── data/
│   ├── raw/            # Raw FBref CSVs
│   ├── processed/      # Cleaned & modeled datasets
│   └── external/       # Transfermarkt (Kaggle) data
│
├── notebooks/
│   └── 11_phase11_impact_storytelling.ipynb
│   └── analysis_notebook.ipynb
│
├── src/
│   ├── cleaning.py
│   ├── normalization_phase6.py
│   ├── impact_phase7.py
│   ├── impact_phase8.py
│   ├── scraping.py
│   ├── processing_phase4.py
│   ├── utils.py
│   └── phase10_moneyball.py
│
├── README.md
└── requirements.txt

### Reproducibility

The project is designed to be reproducible end-to-end:

1. Create a Python environment using requirements.txt

2. Place raw CSVs into data/raw/

3. Run cleaning, normalization, and impact scripts

4. Execute the Phase 11 notebook for analysis and visualization

Scraping is supported but may be rate-limited by source providers.

### Closing Note

This project prioritizes methodological rigor over convenience.
Rather than forcing incomplete data into the model, it demonstrates how structured reasoning, role awareness, and historical validation can surface meaningful insights — even under real-world constraints.
