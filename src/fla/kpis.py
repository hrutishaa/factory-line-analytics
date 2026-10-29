VIEWS = """
CREATE OR REPLACE VIEW v_shift_kpis AS
WITH s AS (
  SELECT shift_id, COUNT(*) units, SUM(machine_failure) failed_units,
         SUM(downtime_min) downtime_min, MEDIAN(cycle_time_min) med_cycle_min,
         AVG(cycle_time_min) avg_cycle_min,
         SUM(cycle_time_min) run_min
  FROM fact_cycle GROUP BY shift_id)
SELECT *, 1 - failed_units*1.0/units AS yield,
  run_min*1.0/(run_min + downtime_min) AS availability,
  LEAST(1.0, (SELECT MEDIAN(cycle_time_min) FROM fact_cycle)/avg_cycle_min) AS performance
FROM s;
CREATE OR REPLACE VIEW v_shift_oee AS
SELECT *, availability*performance*yield AS oee FROM v_shift_kpis;
CREATE OR REPLACE VIEW v_yield_by_type AS
SELECT p.product_type, COUNT(*) units, AVG(1-machine_failure) yield
FROM fact_cycle f JOIN dim_product p USING(product_id) GROUP BY 1 ORDER BY 1;
CREATE OR REPLACE VIEW v_downtime_pareto AS
SELECT m.mode_code, m.mode_name, COUNT(*) events, SUM(m.repair_min) downtime_min
FROM fact_failure_event e JOIN dim_failure_mode m USING(mode_code)
GROUP BY 1,2 ORDER BY downtime_min DESC;
"""
def create_views(con):
    con.execute(VIEWS)
