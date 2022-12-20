CREATE VIEW IF NOT EXISTS tezos_benchmark.theoretical_workload_lvl_v
AS SELECT
    cap_lvl.exp_ID AS exp_ID,
    -- workload level
    cap_lvl.lvl AS lvl,

    -- The theoretical workload per workload level: The sum of operations that should be send
    -- by all hosts together during one workload level (equals the workload plan)
    (floor(cap_lvl.cap_tpB_lvl) * cap_lvl.cycles) as theo_wkl_lvl

FROM tezos_benchmark.capacity_lvl_v AS cap_lvl