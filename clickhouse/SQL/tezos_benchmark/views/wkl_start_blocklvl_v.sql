CREATE VIEW IF NOT EXISTS tezos_benchmark.wkl_start_blocklvl_v
AS SELECT
       ops.name_of_chain AS exp_ID,

       -- The block level/height of the first block
       -- that includes a confirmed operation of the entire workload (= the first workload level)
       minIf(ops.block_level, ops.st_confirmed) AS wkl_start_blocklvl

FROM tezos_benchmark.operations AS ops
GROUP BY exp_ID