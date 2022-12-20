CREATE VIEW IF NOT EXISTS tezos_benchmark.block_trx_summary_v
AS SELECT
    name_of_chain AS exp_ID,

    -- block height/level: first block that includes an operation of the first workload level
    wkl_s_blvl.wkl_start_blocklvl AS wkl_start_blocklvl,

    -- total number of confirmed transactions per experiment according to the DL
    sum(blocks.trx_number_confirmed) AS n_trx_conf_exp,
    -- total sum of consumed gas of confirmed transactions per experiment
    sum(blocks.trx_sum_consumed_milligas/1000) as sum_cons_gas_exp,
    -- number of invalid transactions in DL per experiment
    sum(blocks.trx_number_failed) AS n_trx_fail_exp

FROM tezos_benchmark.blocks AS blocks
INNER JOIN tezos_benchmark.wkl_start_blocklvl_v AS wkl_s_blvl
    ON blocks.name_of_chain = wkl_s_blvl.exp_ID

-- Only consider blocks that include operations of the workload (starting with the first block of the workload)
WHERE blocks.block_level >= wkl_s_blvl.wkl_start_blocklvl
GROUP BY exp_ID, wkl_s_blvl.wkl_start_blocklvl


