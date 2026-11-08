"""Export site/data.json from the released parquet files (DuckDB).
Run from repo root: python site/build_data.py"""
import json, duckdb
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
c = duckdb.connect()
for name, p in {
    "pdv": "1_prepared_views/prepared_daily_view", "prop": "1_prepared_views/property_day",
    "md": "2_machine_decision/machine_day", "gm": "2_machine_decision/game_math",
    "mach": "2_machine_decision/machines", "ops": "2_machine_decision/operations",
    "cat": "2_machine_decision/action_catalog", "pp": "1_prepared_views/player_period",
}.items():
    c.sql(f"CREATE VIEW {name} AS SELECT * FROM '{D / p}.parquet'")

def rows(sql):
    r = c.sql(sql)
    cols = r.columns
    return [dict(zip(cols, [float(v) if hasattr(v, "as_integer_ratio") and not isinstance(v, (int, bool)) else v for v in t])) for t in r.fetchall()]

# ---- machine-level summary (active floor rows only) ----
c.sql("""
CREATE TABLE m AS
WITH base AS (
  SELECT d.machine_id, ANY_VALUE(d.manufacturer) mfr,
         MODE(d.zone_name) zone, MODE(d.zone_id) zone_id, MODE(d.bank_id) bank, MODE(d.config_id) config,
         ANY_VALUE(d.theme) theme, ANY_VALUE(d.volatility_class) vol, ANY_VALUE(CAST(d.configured_rtp AS DOUBLE)) rtp,
         COUNT(*) floor_days, SUM(d.available_hours) avail_h,
         SUM(CAST(d.coin_in_usd AS DOUBLE)) coin_in, SUM(CAST(d.house_win_usd AS DOUBLE)) house_win,
         SUM(CAST(d.theo_usd AS DOUBLE)) theo, SUM(d.faults_opened) faults,
         SUM(CAST(d.contribution_after_supplied_costs_usd AS DOUBLE)) contribution
  FROM pdv d WHERE d.location_id IS NOT NULL AND d.active GROUP BY d.machine_id
), var AS (
  SELECT md.machine_id, SUM(md.sum_bet_squared * gm.payout_multiplier_variance)/1e4 var_usd2,
         SUM(md.scheduled_seconds - md.available_seconds)/3600.0 down_h
  FROM md JOIN gm USING (config_id) WHERE md.active GROUP BY md.machine_id
)
SELECT b.*, v.down_h, b.theo/NULLIF(b.avail_h,0) rate,
       (b.house_win-b.theo) luck, (b.house_win-b.theo)/NULLIF(SQRT(v.var_usd2),0) z
FROM base b JOIN var v USING (machine_id)
""")
c.sql("""CREATE TABLE cfg AS SELECT config, MEDIAN(rate) cfg_rate FROM m GROUP BY config""")
floor_rate = c.sql("SELECT MEDIAN(rate) FROM m").fetchall()[0][0]
c.sql("""CREATE TABLE zf AS SELECT zone_id, MEDIAN(m.rate/cfg.cfg_rate) zone_factor
         FROM m JOIN cfg USING (config) GROUP BY zone_id""")
c.sql(f"""
CREATE TABLE mv AS
SELECT m.*, cfg.cfg_rate, zf.zone_factor,
       cfg.cfg_rate*zf.zone_factor*m.avail_h expected_theo,
       m.theo - cfg.cfg_rate*zf.zone_factor*m.avail_h machine_specific,
       cfg.cfg_rate*(zf.zone_factor-1)*m.avail_h location,
       (cfg.cfg_rate-{floor_rate})*m.avail_h lineup,
       -m.down_h*cfg.cfg_rate*zf.zone_factor leak,
       RANK() OVER (ORDER BY m.house_win) raw_rank
FROM m JOIN cfg USING (config) JOIN zf USING (zone_id)
""")
machines = rows("""SELECT machine_id, mfr, zone, bank, config, theme, vol, rtp, floor_days,
  ROUND(avail_h,1) avail_h, ROUND(coin_in) coin_in, ROUND(house_win) house_win, ROUND(theo) theo,
  ROUND(luck) luck, ROUND(z,2) z, faults, ROUND(down_h,1) down_h, ROUND(rate,2) rate,
  ROUND(expected_theo) expected_theo, ROUND(machine_specific) machine_specific, ROUND(location) location,
  ROUND(lineup) lineup, ROUND(leak) leak, ROUND(contribution) contribution, raw_rank
  FROM mv ORDER BY house_win""")

def verdict(r):
    if r["z"] is not None and abs(r["z"]) >= 3: return "INSPECT"
    comps = {"LOCATION": r["location"], "LEAK": r["leak"], "LINEUP": r["lineup"], "LUCK": r["luck"]}
    worst = min(comps, key=comps.get)
    if comps[worst] >= 0 and r["machine_specific"] >= 0: return "LUCK"
    if r["machine_specific"] < min(comps.values()): return "MACHINE"
    return worst
for r in machines: r["suit"] = verdict(r)

daily = rows("""SELECT gaming_date::VARCHAR d, ROUND(CAST(coin_in_usd AS DOUBLE)) coin_in,
  ROUND(CAST(house_win_usd AS DOUBLE)) house_win, ROUND(CAST(theo_usd AS DOUBLE)) theo, active_machines,
  faults_opened faults, events_active ev, ROUND(CAST(comp_cost_usd AS DOUBLE)) comp_cost
  FROM prop ORDER BY gaming_date""")
zone_month = rows("""SELECT zone_name AS zone, "month" AS mon, ROUND(SUM(CAST(coin_in_usd AS DOUBLE))/COUNT(*)) AS coin_in_per_md
  FROM pdv WHERE location_id IS NOT NULL AND active GROUP BY 1, 2 ORDER BY 1, 2""")
mfr = rows("""SELECT mfr, COUNT(*) machines, SUM(faults) faults, ROUND(SUM(faults)/COUNT(*),2) per_machine,
  ROUND(SUM(down_h)/COUNT(*),1) down_h_per_machine FROM m GROUP BY mfr ORDER BY per_machine DESC""")
comp = rows("""SELECT strftime(gaming_date,'%Y-%m') AS mon, ROUND(SUM(CAST(comp_cost_usd AS DOUBLE))) AS comp_cost,
  ROUND(SUM(CAST(theo_usd AS DOUBLE))) AS floor_theo FROM prop GROUP BY 1 ORDER BY 1""")
catalog = rows("""SELECT action_type_id id, name, unit, unit_cost_cents/100.0 unit_cost,
  recurring_cost_cents_per_day/100.0 per_day, lead_days, quantity_limit, notes FROM cat ORDER BY id""")
tot = rows("""SELECT ROUND(SUM(coin_in)) coin_in, ROUND(SUM(house_win)) house_win, ROUND(SUM(theo)) theo,
  COUNT(*) machines FROM m""")[0]
tot["floor_rate"] = round(floor_rate, 2)

out = dict(totals=tot, machines=machines, daily=daily, zone_month=zone_month, mfr=mfr, comp=comp, catalog=catalog)
(ROOT / "site" / "data.json").write_text(json.dumps(out, default=str, separators=(",", ":")))
print("machines", len(machines), "days", len(daily), tot)
for r in machines[:10]: print(r["machine_id"], r["zone"], r["house_win"], r["z"], r["suit"], r["machine_specific"], r["location"], r["leak"], r["lineup"])

# ---- forecast: frozen Jan–Apr fits scored on May–Jun (mirrors databricks/gold/forecast.sql) ----
c.sql(f"CREATE VIEW cal AS SELECT * FROM '{D / '2_machine_decision/calendar_day'}.parquet'")
c.sql(f"CREATE VIEW ev AS SELECT * FROM '{D / '4_context/events'}.parquet'")
c.sql("""CREATE TABLE fday AS
SELECT c.gaming_date, c.local_weekday,
  CAST(c.federal_holiday IS NOT NULL AND TRIM(c.federal_holiday) <> '' AS DOUBLE) h,
  CAST(EXISTS (SELECT 1 FROM ev e WHERE c.gaming_date BETWEEN e.start_date AND e.end_date AND e.announced_date < c.gaming_date) AS DOUBLE) e,
  fl.y
FROM cal c JOIN (SELECT gaming_date, SUM(CAST(coin_in_usd AS DOUBLE)) y FROM pdv WHERE location_id IS NOT NULL AND active GROUP BY 1) fl USING (gaming_date)
WHERE c.gaming_date BETWEEN DATE '2025-01-01' AND DATE '2025-06-30'""")
c.sql("""CREATE TABLE params AS
WITH train AS (SELECT * FROM fday WHERE gaming_date < DATE '2025-05-01'),
w AS (SELECT local_weekday, AVG(y) y_bar, AVG(e) e_bar, AVG(h) h_bar FROM train GROUP BY 1),
ce AS (SELECT t.y - w.y_bar y, t.e - w.e_bar e, t.h - w.h_bar h FROM train t JOIN w USING (local_weekday)),
ne AS (SELECT SUM(e*e)+1 ee, SUM(h*h)+1 hh, SUM(e*h) eh, SUM(e*y) ey, SUM(h*y) hy FROM ce),
ef AS (SELECT (hh*ey-eh*hy)/(ee*hh-eh*eh) be, (ee*hy-eh*ey)/(ee*hh-eh*eh) bh FROM ne),
b AS (SELECT AVG(y) base FROM train)
SELECT w.local_weekday, w.y_bar - w.e_bar*ef.be - w.h_bar*ef.bh wk, ef.be, ef.bh, b.base FROM w, ef, b""")
fc = rows("""SELECT f.gaming_date::VARCHAR d, f.local_weekday wd, ROUND(f.y) actual, ROUND(p.base) baseline,
  ROUND(p.wk + f.e*p.be + f.h*p.bh) model, f.gaming_date >= DATE '2025-05-01' holdout, f.e ev, f.h hol
  FROM fday f JOIN params p USING (local_weekday) ORDER BY 1""")
met = rows("""WITH x AS (SELECT f.y, p.base, p.wk + f.e*p.be + f.h*p.bh m FROM fday f JOIN params p USING (local_weekday) WHERE f.gaming_date >= DATE '2025-05-01')
  SELECT COUNT(*) n, ROUND(AVG(ABS(y-base))) mae_base, ROUND(AVG(ABS(y-m))) mae_model,
  ROUND(100*AVG(ABS(y-base)/y),1) mape_base, ROUND(100*AVG(ABS(y-m)/y),1) mape_model FROM x""")[0]
eff = rows("SELECT ROUND(ANY_VALUE(be)) event_effect, ROUND(ANY_VALUE(bh)) holiday_effect FROM params")[0]
met.update(eff)
wkres = rows("""SELECT local_weekday wd, ROUND(AVG(y - (p.wk + f.e*p.be + f.h*p.bh))) model_bias, ROUND(AVG(y - p.base)) base_bias
  FROM fday f JOIN params p USING (local_weekday) WHERE f.gaming_date >= DATE '2025-05-01' GROUP BY 1""")

# ---- inspection screen: Bonferroni over all machines with a valid z ----
import math
zs = [r["z"] for r in machines if r["z"] is not None]
p2 = lambda z: math.erfc(abs(z) / math.sqrt(2))
m1158 = next(r for r in machines if r["machine_id"] == "M-1158")
insp = dict(machines_tested=len(zs), z=m1158["z"], p_two_sided=p2(m1158["z"]),
            p_bonferroni=min(1, p2(m1158["z"]) * len(zs)), luck=m1158["luck"], days=m1158["floor_days"],
            daily_shortfall=round(m1158["luck"] / m1158["floor_days"]))
banks = sorted({r["bank"] for r in machines if r["bank"]})
out.update(forecast=fc, forecast_metrics=met, weekday_bias=wkres, inspection=insp)
(ROOT / "site" / "data.json").write_text(json.dumps(out, default=str, separators=(",", ":")))
print("forecast", met); print("inspection", insp); print("banks", len(banks))
