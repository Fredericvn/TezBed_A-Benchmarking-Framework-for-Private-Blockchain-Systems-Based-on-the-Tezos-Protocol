CREATE VIEW IF NOT EXISTS tezos_benchmark.wkl_start_blocklvl_lvl_v
AS SELECT
       ops.name_of_chain AS exp_ID,
       -- workload level
       ops.op_send_rate_lvl AS lvl,

       -- The block level/height of the first block
       -- that includes a confirmed operation for each workload level
       minIf(ops.block_level, ops.st_confirmed) AS wkl_start_blocklvl

FROM tezos_benchmark.operations AS ops
GROUP BY exp_ID, lvl