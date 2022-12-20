CREATE VIEW IF NOT EXISTS tezos_benchmark.not_valid_experiments_v
AS SELECT
       ovt_lvl.exp_ID

FROM tezos_benchmark.workload_summary_v AS wkl_sum
INNER JOIN tezos_benchmark.host_count_v AS h_count
    ON wkl_sum.exp_ID = h_count.exp_ID
INNER JOIN tezos_benchmark.theoretical_workload_v AS th_wkl
    ON wkl_sum.exp_ID = th_wkl.exp_ID
INNER JOIN tezos_benchmark.overtime_lvl_v AS ovt_lvl
    ON wkl_sum.exp_ID = ovt_lvl.exp_ID

-- the experiment is invalid if:
-- the confirmed operations in the operations table does not match the ones in the blocks table,
-- some hosts failed
-- the number of submitted operations does not match the theoretical workload (plan)
-- clients submitted operations too slow, thus the average overtime of clients is too high
WHERE trx_ops_eq_bl = 0 OR h_count.nodes_failed = 1 OR th_wkl.theo_wkl != wkl_sum.trx_init OR ovt_lvl.trx_init_test = 0
GROUP BY ovt_lvl.exp_ID