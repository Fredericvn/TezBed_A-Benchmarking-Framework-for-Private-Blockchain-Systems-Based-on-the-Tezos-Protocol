CREATE VIEW IF NOT EXISTS tezos_benchmark.block_trx_summary_lvl_v
AS SELECT
    name_of_chain AS exp_ID,
    -- workload level
    interval_lvl.lvl AS lvl,

    -- block height/level: first block that includes an operation of a workload level
    interval_lvl.fs_op_blvl AS first_block,
    -- block height/level: last block that includes an operation of a workload level
    interval_lvl.ls_op_blvl AS last_block,
    -- timestamp: submitting time of first operation of workload level
    interval_lvl.fs_op_init_ts AS first_op_init,
    -- timestamp: submitting time of last operation of workload level
    interval_lvl.ls_op_init_ts AS last_op_init,

    -- number of confirmed transactions per experiment and per workload level according to the DL
    sum(blocks.trx_number_confirmed) AS n_trx_conf_exp,
    -- sum of consumed gas of confirmed transactions per experiment and per workload level
    sum(blocks.trx_sum_consumed_milligas/1000) as sum_cons_gas_exp,
    -- number of invalid transactions in DL per experiment and per workload level
    sum(blocks.trx_number_failed) AS n_trx_fail_exp

FROM tezos_benchmark.blocks AS blocks
INNER JOIN tezos_benchmark.wkl_interval_lvl_v AS interval_lvl
    ON blocks.name_of_chain = interval_lvl.exp_ID

-- Only consider blocks that include operations of the workload
WHERE blocks.block_level >= interval_lvl.fs_op_blvl AND blocks.block_level <= interval_lvl.ls_op_blvl
GROUP BY exp_ID, lvl, first_block, last_block, first_op_init, last_op_init

