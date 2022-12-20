CREATE VIEW IF NOT EXISTS tezos_benchmark.workload_time_host_lvl_v
AS SELECT
        exp_ID,
        -- workload level
        lvl,
        -- hostname of client submitted operation (OP)
        host,

        -- The very first operation of a workload level
        min(min_op_init_ts) as fs_op_init_ts,
        -- The very last operation of a workload level
        max(max_op_init_ts) as ls_op_init_ts,
        -- Workload time per client/host: time span between first and last OP initiated by the host per workload level
        -- Datatype Datetime64 with milliseconds must be converted to decimals for subtraction.
        (toDecimal64(ls_op_init_ts, 3) - toDecimal64(fs_op_init_ts, 3)) AS workload_time_h

FROM
    (SELECT
        name_of_chain AS exp_ID,
        -- workload level
        op_send_rate_lvl AS lvl,
        -- hostname of client submitted operation (OP)
        sc_hostname AS host,

        -- time of the first initiated/submitted operation of a host per workload level
        argMin(u_ts_client_init, op_first) AS min_op_init_ts,
        -- time of the last initiated/submitted operation of a host per workload level
        argMax(u_ts_client_init, op_last) AS max_op_init_ts

    FROM tezos_benchmark.operations AS operations
    GROUP BY exp_ID, lvl, host)

GROUP BY exp_ID, lvl, host