CREATE VIEW IF NOT EXISTS tezos_benchmark.overtime_lvl_v
AS SELECT
    exp_ID,
    -- workload level
    lvl,

    -- If the average overtime is larger than 0.1 seconds the trx initiation test fails (0)
    -- -> it took the clients(hosts) too long to submit all operations,
    -- thus the send rate per second is not as desired,
    -- else the overtime is in acceptable range and thus the test succeed (1)
    if (avg_overtime > 0.1, 0, 1) AS trx_init_test,

    -- Workload time: the time span between the first and the last operation of the workload level
    -- Datatype Datetime64 with milliseconds must be converted to decimals for subtraction.
    (toDecimal64(last_op_init, 3) - toDecimal64(first_op_init, 3)) AS workload_time,
    -- Average of the individual workload times of the hosts per workload level,
    -- the host workload time: time span between first and last OP initiated by the host per workload level
    round(avg(workload_h.workload_time_h), 3) AS avg_workload_time_h,
    -- Total overtime: the excessive time it took to submit all operations within a workload level
    -- The aimed time is <= the block creation interval (min block delay) * the number of cycles (blocks to run)
    (workload_time - (exp_vars.minimal_block_delay * exp_vars.blocks_to_run)) AS total_overtime,
    -- Average overtime: the average excessive overtime per host to submit all operations within a workload level
    round((avg_workload_time_h - (exp_vars.minimal_block_delay * exp_vars.blocks_to_run)), 3) AS avg_overtime,

    -- The very first operation of a workload level
    min(workload_h.fs_op_init_ts) AS first_op_init,
    -- The very last operation of a workload level
    max(workload_h.ls_op_init_ts) AS last_op_init

FROM
    tezos_benchmark.workload_time_host_lvl_v AS workload_h
INNER JOIN tezos_benchmark.experiment_vars AS exp_vars
    ON exp_vars.name_of_chain = workload_h.exp_ID
GROUP BY exp_ID, lvl, minimal_block_delay, blocks_to_run
ORDER BY exp_ID, lvl
