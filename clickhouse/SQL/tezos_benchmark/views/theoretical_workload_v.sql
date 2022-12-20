CREATE VIEW IF NOT EXISTS tezos_benchmark.theoretical_workload_v
AS SELECT
    th_wkl_lvl.exp_ID AS exp_ID,

    -- The theoretical total workload over all workload levels: The sum of operations that should be send
    -- by all hosts together over all workload levels (equals the entire workload plan)
    sum(th_wkl_lvl.theo_wkl_lvl) AS theo_wkl

FROM tezos_benchmark.theoretical_workload_lvl_v AS th_wkl_lvl
GROUP BY exp_ID