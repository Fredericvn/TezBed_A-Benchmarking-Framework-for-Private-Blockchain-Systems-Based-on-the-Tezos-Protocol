-- tx_throughput and latency
select
exp_ID,
lvl AS workload_lvl,
blocksize AS block_size_limit,
min_block_delay AS block_creation_interval,
n_nodes_exp AS network_size,
tps_lvl_m2 AS Tx_throughput,
avg_latency AS Tx_confirm_latency,
tps_lvl_ratio AS R_Tx_throughput,
lat_to_blockCrIntv_ratio AS R_Tx_confirm_latency

from trx_throughput_lvl_v
join trx_latency_lvl_v
on trx_throughput_lvl_v.exp_ID = trx_latency_lvl_v.exp_ID
       and trx_throughput_lvl_v.lvl = trx_latency_lvl_v.lvl
WHERE trx_throughput_lvl_v.exp_ID in valid_experiments_v and trx_throughput_lvl_v.exp_ID LIKE 'tezosExp_%'
ORDER BY lat_to_blockCrIntv_ratio desc;

-- experiment vars
SELECT
    *
FROM experiment_vars
where name_of_chain in valid_experiments_v and name_of_chain like 'tezosExp_%';

-- summarize workloads of valid experiments
select
    *
from workload_summary_v
    where exp_ID LIKE 'tezosExp_%' and exp_ID in valid_experiments_v;

-- summarize workloads of valid experiments per workload level
select
    *
from workload_summary_lvl_v
where exp_ID LIKE 'tezosExp_%' and exp_ID in valid_experiments_v;

-- count the number of submitted transactions over all experiments
SELECT
    count()
FROM operations
WHERE name_of_chain like 'tezosExp%' /*and name_of_chain in valid_experiments_v*/;

-- count the number of blocks over all experiments
SELECT
    count()
FROM blocks
WHERE name_of_chain like 'tezosExp%';

-- validity_of_experiments overview
SELECT
    name_of_chain AS exp_ID,
    ts_creation_of_protocol AS timestamp,
    if(name_of_chain in valid_experiments_v, 1, 0) AS validity
FROM experiment_vars
WHERE name_of_chain like 'tezosExp%';

-- longest valid blockchain
SELECT
    name_of_chain,
    block_level
FROM blocks
WHERE name_of_chain like 'tezosExp%' and name_of_chain in valid_experiments_v
order by block_level desc ;

-- shortest valid blockchain
SELECT
    name_of_chain,
    max(block_level) AS last_block
FROM blocks
WHERE name_of_chain like 'tezosExp%' and name_of_chain in valid_experiments_v
GROUP BY name_of_chain
ORDER BY last_block asc;

-- Create quick histograms
select sparkbar(121) (number_nodes_exp, freq)
from (select
        number_nodes_exp,
        count(number_nodes_exp) as freq
    from experiment_vars
    where name_of_chain like 'tezosExp%' and name_of_chain in valid_experiments_v
    group by number_nodes_exp);

select sparkbar(114) (minimal_block_delay, freq)
from (select
        minimal_block_delay,
        count(minimal_block_delay) as freq
    from experiment_vars
    where name_of_chain like 'tezosExp%' and name_of_chain in valid_experiments_v
    group by minimal_block_delay);

select sparkbar(100) (block_gas_limit, freq)
from (select
        block_gas_limit,
        count(block_gas_limit) as freq
    from experiment_vars
    where name_of_chain like 'tezosExp%' and name_of_chain in valid_experiments_v
    group by block_gas_limit);