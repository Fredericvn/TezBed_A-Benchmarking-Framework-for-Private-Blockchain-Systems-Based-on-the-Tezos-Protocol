CREATE VIEW IF NOT EXISTS tezos_benchmark.trx_throughput_lvl_v
AS SELECT
    exp_ID,
    -- workload level
    lvl,

    -- Capacity of transactions per second per workload level (theoretical throughput)
    round(cap_lvl.cap_tpS_lvl, 3) AS cap_tpS_lvl,
    -- Actual measured throughput in transactions per second per workload level (method_1)
    round((throughput.number_trx / (throughput.total_time + cap_lvl.min_block_delay)), 3) AS tps_lvl_m1,
    -- Actual measured throughput in transactions per second per workload level (method_2)
    round((throughput.n_trx_avg / throughput.time_intval_avg), 3) AS tps_lvl_m2,
    -- ratio between the actual and the theoretical throughput
    round(tps_lvl_m2/cap_lvl.cap_tpS_lvl, 3) AS tps_lvl_ratio,

    -- Capacity of transactions per block per workload level (theoretical block space)
    round(cap_lvl.cap_tpB_lvl, 3) AS cap_tpB_lvl,
    -- The average number of transactions per block
    -- in the range of the first and last block which includes transactions of the workload level
    round(n_trx_avg, 3) AS number_trx_avg,
    -- The total number of transactions in all blocks
    -- in the range of the first and last block which includes transactions of the workload level
    number_trx,
    -- The average time interval between consecutive blocks
    -- in the range of the first and last block which includes transactions of the workload level
    time_intval_avg AS avg_time_interval_sec,
    -- Network size/ number of nodes in the network
    cap_lvl.n_nodes_exp AS n_nodes_exp,
    -- Block creation interval/ minimal block delay
    cap_lvl.min_block_delay AS min_block_delay,
    -- Block size limit / hard block gas limit
    cap_lvl.blocksize

FROM (
    SELECT
        interval_lvl.exp_ID AS exp_ID,
        -- workload level
        interval_lvl.lvl AS lvl,
        -- The average number of transactions per block
        -- in the range of the first and last block which includes transactions of the workload level
        sumIf((trx_number_confirmed/(interval_lvl.ls_op_blvl - interval_lvl.fs_op_blvl + 1)),
            (block_level between interval_lvl.fs_op_blvl AND interval_lvl.ls_op_blvl )) AS n_trx_avg,
        -- The total number of transactions in all blocks
        -- in the range of the first and last block which includes transactions of the workload level
        sumIf(trx_number_confirmed,
            (block_level between interval_lvl.fs_op_blvl AND interval_lvl.ls_op_blvl )) AS number_trx,
        -- The average time interval between consecutive blocks
        -- in the range of the first and last block which includes transactions of the workload level
        ((interval_lvl.ls_op_ts - interval_lvl.fs_op_ts)/(interval_lvl.ls_op_blvl - interval_lvl.fs_op_blvl)) AS time_intval_avg,
        -- The total time interval between the first and the last block
        -- in the range of the first and last block which includes transactions of the workload level
        (interval_lvl.ls_op_ts - interval_lvl.fs_op_ts) AS total_time

    FROM tezos_benchmark.blocks AS blocks
    INNER JOIN tezos_benchmark.wkl_interval_lvl_v AS interval_lvl
        ON blocks.name_of_chain = interval_lvl.exp_ID AND (ls_op_blvl - fs_op_blvl) > 0
    GROUP BY exp_ID, lvl,time_intval_avg, total_time
    ) AS throughput

INNER JOIN tezos_benchmark.capacity_lvl_v AS cap_lvl
    ON throughput.exp_ID = cap_lvl.exp_ID AND throughput.lvl = cap_lvl.lvl
ORDER BY exp_ID,lvl
