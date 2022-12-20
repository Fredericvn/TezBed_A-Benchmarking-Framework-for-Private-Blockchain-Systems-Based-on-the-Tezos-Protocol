CREATE VIEW IF NOT EXISTS tezos_benchmark.valid_experiments_v
AS SELECT
       ovt_lvl.exp_ID

FROM tezos_benchmark.workload_summary_v AS wkl_sum
INNER JOIN tezos_benchmark.host_count_v AS h_count
    ON wkl_sum.exp_ID = h_count.exp_ID
INNER JOIN tezos_benchmark.theoretical_workload_v AS th_wkl
    ON wkl_sum.exp_ID = th_wkl.exp_ID
INNER JOIN tezos_benchmark.overtime_lvl_v AS ovt_lvl
    ON wkl_sum.exp_ID = ovt_lvl.exp_ID

-- the experiment is valid if:
-- the confirmed operations in the operations table matches the ones in the blocks table,
-- not a single host failed
-- the number of submitted operations matches the theoretical workload (plan)
-- clients submitted operations in time, thus the average overtime of clients is in range (< 0.1 seconds)
WHERE trx_ops_eq_bl = 1 AND h_count.nodes_failed = 0 AND th_wkl.theo_wkl = wkl_sum.trx_init AND ovt_lvl.trx_init_test = 1
GROUP BY ovt_lvl.exp_ID