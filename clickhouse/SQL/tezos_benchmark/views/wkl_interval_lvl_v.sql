CREATE VIEW IF NOT EXISTS tezos_benchmark.wkl_interval_lvl_v
AS SELECT
       exp_ID,
       -- workload level
       lvl,

       -- block level(height) of the first block that includes an operation of the workload level
       min(min_op_blvl) as fs_op_blvl,
       -- block level(height) of the last block that includes an operation of the workload level
       max(max_op_blvl) as ls_op_blvl,
       -- block timestamp of the first block that includes an operation of the workload level
       min(min_op_bl_ts) as fs_op_ts,
       -- block timestamp of the last block that includes an operation of the workload level
       max(max_op_bl_ts) as ls_op_ts,
       -- time of the first initiated/submitted operation of the workload level
       min(min_op_init_ts) as fs_op_init_ts,
       -- time of the last initiated/submitted operation of the workload level
       max(max_op_init_ts) as ls_op_init_ts

FROM
    (SELECT
        name_of_chain AS exp_ID,
        -- workload level
        op_send_rate_lvl AS lvl,

        -- block level(height) of the block that includes the first operation of a host per workload level
        argMin(block_level, op_first) AS min_op_blvl,
        -- block level(height) of the block that includes the last operation of a host per workload level
        argMax(block_level, op_last) AS max_op_blvl,
        -- block timestamp of the block that includes the first operation of a host per workload level
        argMin(ts_block, op_first) AS min_op_bl_ts,
        -- block timestamp of the block that includes the last operation of a host per workload level
        argMax(ts_block, op_last) AS max_op_bl_ts,
        -- time of the first initiated/submitted operation of a host per workload level
        argMin(u_ts_client_init, op_first) AS min_op_init_ts,
        -- time of the last initiated/submitted operation of a host per workload level
        argMax(u_ts_client_init, op_last) AS max_op_init_ts

    FROM tezos_benchmark.operations AS operations
    -- only blocks/timestamps of confirmed operations count,
    -- as failed transactions have a block level/height of 0
    WHERE st_confirmed
    GROUP BY exp_ID, lvl, block_level, st_confirmed)

GROUP BY exp_ID, lvl