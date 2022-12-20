CREATE VIEW IF NOT EXISTS tezos_benchmark.host_count_v
AS SELECT
    n_hosts.exp_ID,

    -- number of hosts per experiment who uploaded the system_log_cpl -> then the host uploaded all its experiment files
    n_hosts.number_hosts AS number_hosts,
    -- number of hosts/nodes that should have participated in the experiment
    exp_v.number_nodes_exp AS number_nodes,
    -- If hosts are missing this becomes true/1
    number_hosts != number_nodes AS nodes_failed,
    -- number of hosts/nodes that are missing/failed
    number_nodes - number_hosts AS number_nodes_failed,
    -- share of nodes that are missing/failed in [%]
    round(100*number_nodes_failed/number_nodes, 2) AS share_of_nodes_failed_perc

FROM (SELECT
-- Count the number of hosts per experiment
        exp_ID,
        count() AS number_hosts
      FROM (SELECT
      -- Group the system_log_cpl data according to the experiment and level
                sys_log.name_of_chain AS exp_ID,
                sys_log.hostname AS hostname
            FROM tezos_benchmark.system_log_cpl AS sys_log
            GROUP BY hostname, exp_ID)
      GROUP BY exp_ID) AS n_hosts
INNER JOIN tezos_benchmark.experiment_vars AS exp_v
    ON exp_v.name_of_chain = n_hosts.exp_ID

