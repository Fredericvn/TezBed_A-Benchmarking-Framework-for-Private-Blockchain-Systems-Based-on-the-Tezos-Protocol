CREATE VIEW IF NOT EXISTS tezos_benchmark.workload_summary_v
AS SELECT
    ops_trx.exp_ID AS exp_ID,
    -- theoretical workload CTPS
    th_wkl.theo_wkl AS theo_wkl,
    -- number of operations/transactions initiated by clients
    ops_trx.n_ops_exp AS trx_init,
    -- number of transactions propagated by node
    ops_trx.n_trx_propg_exp AS trx_propg,
    -- number of confirmed operations = transactions from view of node
    ops_trx.n_trx_conf_exp AS trx_conf_in_ops,
    -- number of confirmed operations = transactions reality in blockchain
    bl_trx.n_trx_conf_exp AS trx_conf_in_blocks,

    -- check if node view and blockchain reality are equal
    trx_conf_in_ops = trx_conf_in_blocks AS trx_ops_eq_bl,
    -- ratio of confirmed transactions in the blockchain vs the initiated ops
    round(trx_conf_in_blocks / trx_init, 3) AS conf_rate,
    -- number of transactions with error: Block Gas limit exhausted
    ops_trx.n_err_gas_limit_exh,
    -- number of invalid transactions in DL per experiment
    bl_trx.n_trx_fail_exp AS trx_fail_in_block,
    -- number of transactions with error: wrong account counter in the operation
    ops_trx.n_err_acc_count,
    -- number of transactions with any other error
    ops_trx.n_error_other,
    -- Operations that are missing, i.e., that are neither confirmed, nor unconfirmed due to an error.
    -- Control value which must always be: 0
    ops_trx.missing_ops

FROM
    tezos_benchmark.ops_trx_summary_v AS ops_trx
INNER JOIN
    tezos_benchmark.block_trx_summary_v AS bl_trx
        ON ops_trx.exp_ID = bl_trx.exp_ID
INNER JOIN
    tezos_benchmark.theoretical_workload_v AS th_wkl
        ON ops_trx.exp_ID = th_wkl.exp_ID
ORDER BY exp_ID
