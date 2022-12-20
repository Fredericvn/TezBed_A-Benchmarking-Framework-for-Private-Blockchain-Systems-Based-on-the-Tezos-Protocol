CREATE VIEW IF NOT EXISTS tezos_benchmark.ops_gas_consumption_v
AS SELECT
    -- The operation size / gas consumption equals the total amount of consumed gas of a block
    -- divided by the total number of confirmed transactions in that block.
    (trx_sum_consumed_milligas/trx_number_confirmed/1000) AS op_gas_cons

FROM tezos_benchmark.blocks AS blocks

-- Selects a block only from the set of blocks, where operations from the workload are included
-- Skips blocks that include, for example, the account revealing operations, that have different operation sizes.
INNER JOIN tezos_benchmark.operations AS operations
    ON blocks.name_of_chain = operations.name_of_chain
           AND blocks.block_level = operations.block_level
           AND trx_number_confirmed > 0
LIMIT 1

