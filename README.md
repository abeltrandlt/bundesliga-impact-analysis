# bundesliga-impact-analysis
Analysis of Bundesliga players’ impact using advanced stats (2024/25 season with 2023/24 comparison). Includes data scraping, cleaning, impact scoring, and visualizations.

# ⚽ Bundesliga Player Impact Analysis (2024/25 + 2023/24 Benchmark)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 📌 Overview
This project analyzes **Bundesliga player impact** using advanced statistics.  
The 2024/25 season (in progress) is the primary focus, with the 2023/24 season included as a **benchmark** for comparison.  

The key deliverable is a **Player Impact Index (PIS)** that blends offensive, defensive, and possession-based contributions to highlight the most influential players.  

## 🎯 Objectives
- Scrape, clean, and process Bundesliga data from multiple sources.  
- Engineer advanced per-90 metrics (xG/90, tackles/90, progressive passes/90).  
- Develop a **Player Impact Index** to rank players.  
- Explore correlations between player performance and team results.  
- Create interactive **visualizations and dashboards**.  

## 📂 Project Structure
```

bundesliga-impact-analysis/
│
├── data/             # raw and processed datasets
│   ├── raw/
│   ├── processed/
│
├── notebooks/        # Jupyter notebooks for each step
│   ├── 01\_scraping.ipynb
│   ├── 02\_cleaning.ipynb
│   ├── 03\_EDA.ipynb
│   ├── 04\_modeling.ipynb
│   ├── 05\_visualization.ipynb
│
├── src/              # Python scripts for modular code
│   ├── scraping.py
│   ├── cleaning.py
│   ├── analysis.py
│   ├── visualization.py
│
├── visuals/          # exported plots, Tableau screenshots
├── README.md
├── requirements.txt
└── LICENSE

````

## 📊 Data Sources
- [FBref](https://fbref.com/) → advanced player stats (xG, xA, progressive carries, pressures).  
- [Transfermarkt](https://www.transfermarkt.com/) → player market value, transfers, injuries.  
- Bundesliga official site → match results & standings.  

## 🔄 Workflow
1. **Scraping & Collection** → gather raw stats from FBref/Transfermarkt.  
2. **Cleaning & Processing** → standardize names, engineer per-90 metrics.  
3. **EDA** → distributions, correlations, positional analysis.  
4. **Modeling** → construct Player Impact Index & validate with regression.  
5. **Visualization** → radar charts, scatterplots, Tableau dashboards.  
6. **Documentation** → GitHub repo + insights.  

## 📈 Key Insights
- Who are the most impactful players in 24/25 (ongoing)?  
- Which metrics best explain team success?  
- How do current season leaders compare to 23/24?  

## ⚙️ Environment Setup
This project uses a conda environment (`data_env`).  
To replicate:  

```bash
conda env create -f environment.yml
conda activate data_env
````

Or install dependencies manually:

```bash
pip install -r requirements.txt
```

## 🚀 How to Run

* Clone the repo
* Install dependencies
* Run notebooks in order (`01_scraping.ipynb → 05_visualization.ipynb`)

## 🔮 Future Work

* Extend analysis to multiple European leagues.
* Predict player transfer values from impact scores.
* Add real-time dashboard updates.

```

---

👉 Next decision: do you want me to generate the **environment.yml** for `data_env` (so you can commit it alongside `requirements.txt`), or keep it lean with just the pip freeze file?
```
