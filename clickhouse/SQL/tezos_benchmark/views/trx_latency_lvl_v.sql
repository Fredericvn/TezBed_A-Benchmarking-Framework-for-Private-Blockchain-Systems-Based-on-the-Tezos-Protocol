CREATE VIEW IF NOT EXISTS tezos_benchmark.trx_latency_lvl_v
AS SELECT
    ops.name_of_chain AS exp_ID,
    -- workload level
    ops.op_send_rate_lvl AS lvl,

    -- average latency of all individual transaction latencies of a workload level
    round(avg(ops.pt_trx_latency), 3) AS avg_latency,

    -- block creation interval/minimal block delay
    cap_lvl.min_block_delay AS min_block_delay,

    -- Ratio of the transaction confirmation latency vs the block creation interval/minimal block delay
    round((avg_latency/min_block_delay), 3) AS lat_to_blockCrIntv_ratio,

    -- Capacity of transactions per second per workload level
    round(cap_lvl.cap_tpS_lvl, 2) AS cap_tpS_lvl,
    -- Capacity of transactions per block per workload level
    round(cap_lvl.cap_tpB_lvl) AS cap_tpB_lvl,

    -- network size/ number of nodes in the network/experiment
    cap_lvl.n_nodes_exp AS n_nodes_exp,
    -- block size
    cap_lvl.blocksize AS blocksize

FROM tezos_benchmark.operations AS ops
INNER JOIN tezos_benchmark.capacity_lvl_v AS cap_lvl
    ON ops.name_of_chain = cap_lvl.exp_ID AND op_send_rate_lvl = cap_lvl.lvl

-- only count confirmed operations
WHERE ops.st_confirmed = true
GROUP BY exp_ID, lvl, min_block_delay, cap_tpS_lvl, cap_tpB_lvl, n_nodes_exp, blocksize
ORDER BY exp_ID, lvl


