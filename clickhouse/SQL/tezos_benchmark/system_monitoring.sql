--CPU
SELECT
    name_of_chain AS exp_ID,
    hostname AS hostname,
    datetime_u AS datetime,
    CPU.cons_CPUs_sys_mode_ct,
    CPU.cons_CPUs_user_mode_ct

FROM tezos_benchmark.system_log_cpu AS CPU
WHERE name_of_chain LIKE 'tezosExp_%' AND hostname = 'tezos_1';

--CPL
SELECT
    /*name_of_chain,*/
    hostname,
    avg(load_avg_last_min)
FROM
    (SELECT
        *
    FROM tezos_benchmark.system_log_cpl AS CPL
    WHERE name_of_chain LIKE 'tezosExp_%' AND CPL.interval = 10 /*AND name_of_chain in valid_experiments_v*/)
group by /*name_of_chain,*/ hostname;

--CPL with configuration
SELECT
    name_of_chain AS exp_ID,
    block_gas_limit,
    minimal_block_delay,
    number_nodes_exp,
    -- It is normalized with the number of processors
    avg_cpl.avg_load_last_min/n_processors AS avg_load_last_min
FROM
    (SELECT
        CPL.name_of_chain,
        avg(load_avg_last_min) AS avg_load_last_min,
        n_processors
    FROM tezos_benchmark.system_log_cpl AS CPL
    WHERE name_of_chain LIKE 'tezosExp_%' AND CPL.interval = 10 AND name_of_chain in valid_experiments_v
    group by name_of_chain, n_processors) AS avg_cpl
JOIN experiment_vars
ON avg_cpl.name_of_chain = experiment_vars.name_of_chain;

--DSK
SELECT
    name_of_chain,
    /*hostname,*/
    min(avg_io) AS max_io
FROM (
    SELECT
        name_of_chain,
        /*hostname,*/
        avg(n_milsec_spent_IO) AS avg_io
    FROM tezos_benchmark.system_log_dsk AS DSK
    WHERE name_of_chain LIKE 'tezosExp_%' AND DSK.interval = 10/* and n_milsec_spent_IO < 3000*/ AND name_of_chain in valid_experiments_v
    group by name_of_chain/*, hostname*/)
group by name_of_chain/*, hostname*/
order by max_io asc ;

--DSK with configuration
SELECT
    name_of_chain AS exp_ID,
    block_gas_limit,
    minimal_block_delay,
    number_nodes_exp,
    avg_dsk.avg_time_io
FROM
    (SELECT
        DSK.name_of_chain,
        avg(n_milsec_spent_IO) AS avg_time_io
    FROM tezos_benchmark.system_log_dsk AS DSK
    WHERE name_of_chain LIKE 'tezosExp_%' AND DSK.interval = 10 AND n_milsec_spent_IO < 3000 AND name_of_chain in valid_experiments_v
    group by name_of_chain) AS avg_dsk
JOIN experiment_vars
ON avg_dsk.name_of_chain = experiment_vars.name_of_chain;

--MEM
SELECT
    exp_ID,
    hostname,
    avg(RAM_usage_perc),
    max(RAM_usage_perc) AS max_ram_usage

FROM(
    SELECT
    MEM.name_of_chain AS exp_ID,
    MEM.hostname AS hostname,
    MEM.label AS label,
    MEM.datetime_u AS datetime,
    MEM.interval AS intval,
    MEM.phys_mem_sz_p * MEM.page_sz_b AS RAM,
    MEM.free_mem_p * MEM.page_sz_b AS FreeRAM,
    (RAM - FreeRAM)/RAM AS RAM_usage_perc,
    (MEM.page_cache_sz_p + MEM.res_shrd_mem_sz_p) * MEM.page_sz_b AS cache,
    (cache / RAM) AS cache_perc
    FROM tezos_benchmark.system_log_mem AS MEM
    WHERE name_of_chain LIKE 'tezosExp_%' AND name_of_chain in valid_experiments_v AND MEM.interval = 10) AS MEM_ALL
group by exp_ID, hostname
order by max_ram_usage desc ;

--NET UPPER
SELECT
    max(n_pkts_recv_TCP),
    max(n_pkts_transm_TCP)
FROM
    (SELECT
    *
    FROM tezos_benchmark.system_log_net_upper AS NET_UPPER
    WHERE name_of_chain LIKE 'tezos%' AND /*hostname = 'tezos_1' AND*/ NET_UPPER.interval = 10);

--PRC node
/*SELECT
    max(cons_CPUs_user_mode),
    max(cons_CPUs_sys_mode)
FROM*/
    (SELECT
        name_of_chain,
        hostname,
        datetime_u,
        PRC.name

/*        SUM(cons_CPUs_user_mode_ct) AS cons_CPUs_user_mode,
        SUM(cons_CPUs_sys_mode_ct) AS cons_CPUs_sys_mode*/
    FROM tezos_benchmark.system_log_prc AS PRC
    WHERE name_of_chain LIKE 'tezosExp_%1165' /*AND hostname = 'tezos_1'*/ AND PRC.interval = 10
    AND PRC.name = '(tezos-node)'
    GROUP BY name_of_chain, hostname, datetime_u, PRC.name);

-- PRC baker
SELECT
        name_of_chain,
        hostname,
        label,
        datetime_u,
        PRC.name,

        SUM(cons_CPUs_user_mode_ct) AS cons_CPUs_user_mode,
        SUM(cons_CPUs_sys_mode_ct) AS cons_CPUs_sys_mode
    FROM tezos_benchmark.system_log_prc AS PRC
    WHERE name_of_chain LIKE 'tezos%1160' AND hostname = 'tezos_1' AND PRC.interval = 10
    AND name LIKE '%tezos-baker%'
    GROUP BY name_of_chain, hostname, label, datetime_u, name;

-- PRM baker
SELECT
        name_of_chain,
        hostname,
        label,
        datetime_u,
        PRM.name,
        8343769088 AS RAM,
        SUM(virt_mem_sz_kb),
        SUM(res_mem_sz_kb),
        SUM(shrd_txt_mem_sz_kb)


    FROM tezos_benchmark.system_log_prm AS PRM
    WHERE name_of_chain LIKE 'tezos%1160' AND hostname = 'tezos_1' AND PRM.interval = 10
    AND name LIKE '%tezos-baker%'
    GROUP BY name_of_chain, hostname, label, datetime_u, name;