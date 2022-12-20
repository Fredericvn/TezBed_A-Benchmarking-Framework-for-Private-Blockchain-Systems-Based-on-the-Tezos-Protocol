CREATE VIEW IF NOT EXISTS tezos_benchmark.workload_summary_lvl_v
AS SELECT

    ops_trx.exp_ID AS exp_ID,
    -- workload level
    ops_trx.lvl AS lvl,
    -- theoretical workload per level = CTPS per level
    th_wkl_lvl.theo_wkl_lvl AS theo_wkl,
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
    round(trx_conf_in_blocks / trx_init, 2) as conf_rate,
    -- number of transactions with error: Block Gas limit exhausted
    ops_trx.n_err_gas_limit_exh,
    -- number of invalid transactions in DL per experiment and per workload level
    bl_trx.n_trx_fail_exp AS trx_fail_in_block,
    -- number of transactions with error: wrong account counter in the operation
    ops_trx.n_err_acc_count,
    -- number of transactions with any other error
    ops_trx.n_error_other,
    -- Operations that are missing, i.e., that are neither confirmed, nor unconfirmed due to an error.
    -- Control value which must always be: 0
    ops_trx.missing_ops,

    -- If the average overtime is larger than 0.1 seconds the trx initiation test fails (0)
    -- -> it took the clients(hosts) too long to submit all operations,
    -- thus the send rate per second is not as desired,
    -- else the overtime is in acceptable range and thus the test succeed (1)
    overtime.trx_init_test,
    -- Average overtime: the average excessive overtime per host to submit all operations within a workload level
    overtime.avg_overtime,
    -- Total overtime: the excessive time it took to submit all operations within a workload level
    -- The aimed time is <= the block creation interval (min block delay) * the number of cycles (blocks to run)
    overtime.total_overtime

FROM
    tezos_benchmark.ops_trx_summary_lvl_v AS ops_trx
INNER JOIN
    tezos_benchmark.block_trx_summary_lvl_v AS bl_trx
        ON ops_trx.exp_ID = bl_trx.exp_ID AND ops_trx.lvl = bl_trx.lvl
INNER JOIN
    tezos_benchmark.overtime_lvl_v AS overtime
        ON ops_trx.exp_ID = overtime.exp_ID AND ops_trx.lvl = overtime.lvl
INNER JOIN
    tezos_benchmark.theoretical_workload_lvl_v AS th_wkl_lvl
        ON ops_trx.exp_ID = th_wkl_lvl.exp_ID AND ops_trx.lvl = th_wkl_lvl.lvl
ORDER BY exp_ID, lvl
