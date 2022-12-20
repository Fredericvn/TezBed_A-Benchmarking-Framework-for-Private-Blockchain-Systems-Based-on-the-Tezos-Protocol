CREATE VIEW IF NOT EXISTS tezos_benchmark.ops_trx_summary_lvl_v
AS SELECT
    ops.name_of_chain AS exp_ID,
    -- workload level
    ops.op_send_rate_lvl AS lvl,

    -- total number of operations per workload level
    count(ops.op_hash) AS n_ops_exp,
    -- total number of confirmed transactions per workload level, i.e., operations included in a block
    countIf(ops.st_confirmed, ops.st_confirmed) AS n_trx_conf_exp,
    -- total number of propagated operations per workload level,
    -- i.e., operations successfully pre validated by the node, where the client injected the operation,
    -- ,and then propagated to other nodes and bakers
    countIf(ops.st_propagated, ops.st_propagated) AS n_trx_propg_exp,

    -- total number of unconfirmed operations per workload level, due to:
    -- 1. the number of operations would have exceeded the block gas limit of the next block
    countIf(ops.st_error, NOT ops.st_confirmed
                              AND ops.st_error LIKE '%gas_exhausted%') AS n_err_gas_limit_exh,
    -- 2. wrong account counter in the operation
    countIf(ops.st_error, NOT ops.st_confirmed
                              AND ops.st_error LIKE '%Counter%not yet reached%') AS n_err_acc_count,
    -- 3. any other error than the two above
    countIf(ops.st_error, NOT ops.st_confirmed
                              AND ops.st_error NOT like'%Counter%not yet reached%'
                              AND ops.st_error NOT like '%gas_exhausted%') AS n_error_other,
    -- Operations that are missing, i.e., that are neither confirmed, nor unconfirmed due to an error.
    -- Control value which must always be: 0
    n_ops_exp - (n_err_gas_limit_exh + n_err_acc_count + n_error_other + n_trx_conf_exp) AS missing_ops

FROM tezos_benchmark.operations AS ops
GROUP BY exp_ID, lvl