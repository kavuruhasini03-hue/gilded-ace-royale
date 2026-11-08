# The Gilded Ace: luck, location, or a leak?

**TAMU Datathon 2026 · Dashboard Royale (+ Best Use of Databricks)** · Team: Srikar, Prady, Hasini

- 🎰 **Public interactive dashboard (no login):** https://gilded-ace-royale-lime.vercel.app. If `*.vercel.app` is blocked on your network, open `site/index.html` locally (see below).
- 📊 **Databricks AI/BI dashboard (7 pages, workspace sign-in):** [open](https://dbc-a3bbfca6-850a.cloud.databricks.com/dashboardsv3/01f1daeb815914e69b3ef75f86f7d789/published?o=7474653288963289)
- 📝 [Write-up (≤400 words)](WRITEUP.md) · 🔎 [Claims & Evidence appendix](CLAIMS_EVIDENCE.md) · 🤖 [AI-use disclosure](AI_DISCLOSURE.md) · 📐 [Methods](METHODS.md)

## Recommendation

> **Replace none of the GM's bottom ten in July. Inspect M-1158 ($1,200), defer the underpowered comp pilot, and keep $98,800 in reserve.**

| Finding | Evidence |
|---|---|
| 9 of the bottom ten are in the **Back Forty**; 3 were on the floor for only 49–132 of 181 days | 4-L bridge: location + lineup dominate, and the machine-specific residual is small |
| The Back Forty entrance walkway closed **Mar 3 – Apr 7** | March Back Forty coin-in per machine-day −23.6% vs. January; other zones +7.2% |
| **M-1158** paid out $36,165 above its game math | luck z = −4.57, Bonferroni p = 0.0015 across 310 machines. A lead, not an accusation |
| Ridgeline machines fault 7.2× per machine vs. 3.0 and 1.9 for the other makers | Overnight tickets wait 2.26 h |
| Comp cost per tracked theo rose from **1.11% to 1.32%** | Redemption points per face dollar fell around May 1 |

**Model.** A weekday + ridge event/holiday forecast of daily floor coin-in, fit on January–April and scored on 61 unseen May–June days, cut MAE from **$218,258** (constant baseline) to **$55,271**. It priced technician shifts, and no package pays back in July.

## How it's built

| Part | Where |
|---|---|
| Databricks medallion pipeline: bronze → silver → gold, 30+ SQL models, run as an Asset Bundle job | `databricks/`, `databricks.yml`, `scripts/deploy_phase2.py` |
| Databricks AI/BI dashboard (7 pages) | `dashboards/gilded_ace.lvdash.json`, `dashboards/build_dashboard.py` |
| Forecast, logged to MLflow | `databricks/gold/forecast.sql`, `scripts/log_forecast.py` |
| Data recon and quality checks | `analysis/recon.py` → `docs/RECON.md`, `scripts/verify_*.py` |
| Public dashboard site | `site/index.html`, `site/build_data.py` (DuckDB) |

### Run the public dashboard locally

```bash
python -m venv .venv && .venv/bin/pip install duckdb pandas pyarrow
.venv/bin/python site/build_data.py      # rebuilds site/data.json from data/
cd site && python -m http.server 8765    # open http://localhost:8765
```

Needs only Python 3.10+ and a browser. Chart.js loads from a CDN.

---

Fictional casino; synthetic data calibrated to public aggregates (TAMU Datathon 2026 release `0.9.0-draft`). The challenge brief is in [GUIDE.md](GUIDE.md).
Original documentation, scripts and synthetic data use the [MIT license](LICENSE). Third-party source tables are excluded; see [publisher terms](reference/SOURCE_TERMS.md).
