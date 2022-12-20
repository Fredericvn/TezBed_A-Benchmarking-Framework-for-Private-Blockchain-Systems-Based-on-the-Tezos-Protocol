CREATE VIEW IF NOT EXISTS tezos_benchmark.capacity_lvl_v
AS SELECT
    name_of_chain AS exp_ID,
    -- workload level
    ops.op_send_rate_lvl AS lvl,

    -- block size
    exp_v.block_gas_limit AS blocksize,
    -- block creation interval/minimal block delay
    exp_v.minimal_block_delay AS min_block_delay,
    -- network size/ number of nodes in the network/experiment
    exp_v.number_nodes_exp AS n_nodes_exp,
    -- workload cycles
    exp_v.blocks_to_run AS cycles,

    -- Capacity of transactions per block per workload level,
    -- based on the block size and the operation size (gas consumption)
    blocksize / (SELECT op_gas_cons FROM tezos_benchmark.ops_gas_consumption_v) * (lvl / 100) AS cap_tpB_lvl,
    -- Capacity of transactions per second per workload level,
    -- based on the block size, the operation size (gas consumption) and the block creation interval/ min block delay
    cap_tpB_lvl / min_block_delay AS cap_tpS_lvl

FROM tezos_benchmark.experiment_vars AS exp_v
INNER JOIN tezos_benchmark.operations AS ops
    ON exp_v.name_of_chain = ops.name_of_chain
GROUP BY exp_ID, lvl, blocksize, min_block_delay, n_nodes_exp, cycles
