import sys
import logging
import logging.config
import time
from functools import wraps

sys.path.append("/home/ubuntu/scripts")

from file_handler import load_json_file
from file_handler import export_json_file
from file_handler import export_csv_file
from operation_constants import *
import parse_logs
import parse_blockchain
import blockchain_operations as bc_ops

from pytezos import pytezos


def timing(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time

    return wrap


# execute the workload, that fits in one block
def run_workload_lvl_one_block(
    hostname: str,
    log_dir: str,
    trx_amount: int,
    rate_ops_lvl_i: int,
    rate_ops_lvl: int,
    lvl_ops_counter: int,
    minimal_block_delay: int,
    worker_accounts: list,
    workload_host: list,
    ops_counter: int,
    ops_counter_init: int,
    account_index_start: int,
    trx_bulk_size: int,
):
    interval_sec = 0
    interval_sec_results = {}
    # if the workload plan doesn't require the host/client to send anything, stop the process
    if workload_host[rate_ops_lvl_i][2] == 0:
        return (
            worker_accounts,
            ops_counter,
            ops_counter_init,
            lvl_ops_counter,
            interval_sec_results,
            account_index_start,
        )

    workload_start = time.time()

    # One interval_sec should take 1 real second, if the workload takes less than 1 second, sleep the rest of the time
    while interval_sec < minimal_block_delay:
        interval_sec_start = time.time()
        # Defines the last index of the list of accounts to choose from for the operations,
        # which is the start_index + the number of operations to send per second per host for the given level
        account_index_end = (
            account_index_start + workload_host[rate_ops_lvl_i][1][interval_sec]
        )
        # print(f"interval_sec {interval_sec} start: {interval_sec_start}")
        # Send workload from worker to workers according to the workload plan of each host
        if trx_bulk_size >= 2:
            send_result = bc_ops.send_workload_in_bulks(
                hostname,
                log_dir,
                rate_ops_lvl,
                workload_host[rate_ops_lvl_i][1][interval_sec],
                trx_amount,
                WORKER,
                worker_accounts[account_index_start:account_index_end],
                lvl_ops_counter,
                minimal_block_delay,
                trx_bulk_size,
                manual=True,
            )
        else:
            send_result = bc_ops.send_workload_singly(
                hostname,
                log_dir,
                rate_ops_lvl,
                workload_host[rate_ops_lvl_i][1][interval_sec],
                trx_amount,
                WORKER,
                worker_accounts[account_index_start:account_index_end],
                lvl_ops_counter,
                minimal_block_delay,
                manual=True,
            )
        # updated_worker_acc = send_result[0]
        ops_counter += send_result[1]
        ops_counter_init += send_result[2]
        interval_sec_results.update(send_result[3])
        lvl_ops_counter += send_result[1]
        interval_sec_finished = time.time()

        interval_sec += 1
        account_index_start = account_index_end

        # Each interval_sec should take exactly 1 second, thus wait until the 1 second is over, before continuing
        if (1 - (interval_sec_finished - interval_sec_start)) >= 0:
            # print("sleep until 1 second is over")
            time.sleep(1 - (interval_sec_finished - interval_sec_start))
    workload_end = time.time()
    print(f"workload time: {workload_end - workload_start}")
    return (
        worker_accounts,
        ops_counter,
        ops_counter_init,
        lvl_ops_counter,
        interval_sec_results,
        account_index_start,
    )


# create the workload of one workload level, that fits in one block
def create_workload_lvl_one_block(
    trx_amount: int,
    rate_ops_lvl_i: int,
    minimal_block_delay: int,
    worker_accounts: list,
    workload_host: list,
    account_index_start: int,
    trx_bulk_size: int,
):
    artificial_sec = 0
    ops_per_sec = []
    # if the workload plan doesn't require the host/client to send anything, stop the process
    if workload_host[rate_ops_lvl_i][2] == 0:
        return (
            ops_per_sec,
            account_index_start,
        )

    create_wl_start = time.time()

    # The interval_sec here
    while artificial_sec < minimal_block_delay:
        # Defines the last index of the list of accounts to choose from for the operations,
        # which is the start_index + the number of operations to send per second per host for the given level
        account_index_end = (
            account_index_start + workload_host[rate_ops_lvl_i][1][artificial_sec]
        )

        # Send workload from worker to workers according to the workload plan of each host
        if trx_bulk_size >= 2:
            # send_result = bc_ops.send_workload_in_bulks(
            #     hostname,
            #     log_dir,
            #     workload_host[rate_ops_lvl_i][0],
            #     workload_host[rate_ops_lvl_i][1][artificial_sec],
            #     trx_amount,
            #     WORKER,
            #     worker_accounts[account_index_start:account_index_end],
            #     lvl_ops_counter,
            #     minimal_block_delay,
            #     trx_bulk_size,
            #     manual=True,
            # )
            pass
        else:
            ops_per_sec.append(
                bc_ops.create_all_ops_singly(
                    workload_host[rate_ops_lvl_i][1][artificial_sec],
                    trx_amount,
                    WORKER,
                    worker_accounts[account_index_start:account_index_end],
                    manual=True,
                )
            )

        artificial_sec += 1
        account_index_start = account_index_end

    create_wl_end = time.time()
    print(f"create workload lvl one cycle time: {create_wl_end - create_wl_start}")
    return (
        ops_per_sec,
        account_index_start,
    )


def run_workload_lvl(
    blocks_to_run: int,
    hostname_log: str,
    log_dir: str,
    trx_amount: int,
    rate_ops_lvl_i: int,
    rate_ops_lvl: int,
    minimal_block_delay: int,
    worker_accounts,
    workload_host: list,
    transfer_results: dict,
    ops_counter: int,
    ops_counter_init: int,
    trx_bulk_size: int,
):
    complete_blocks = 0
    lvl_ops_counter = 0
    # Defines the starting index of the list of accounts to choose from for the operations
    account_index_start = 0
    while complete_blocks < blocks_to_run:

        workload_result = run_workload_lvl_one_block(
            hostname_log,
            log_dir,
            trx_amount,
            rate_ops_lvl_i,
            rate_ops_lvl,
            lvl_ops_counter,
            minimal_block_delay,
            worker_accounts,
            workload_host,
            ops_counter,
            ops_counter_init,
            account_index_start,
            trx_bulk_size,
        )
        worker_accounts = workload_result[0]
        ops_counter = workload_result[1]
        ops_counter_init = workload_result[2]
        lvl_ops_counter = workload_result[3]
        transfer_results.update(workload_result[4])
        account_index_start = workload_result[5]
        complete_blocks += 1
    return ops_counter, ops_counter_init


def inject_workload_lvl(
    hostname_log: str,
    log_dir: str,
    rate_ops_lvl: int,
    minimal_block_delay: int,
    transfer_results: dict,
    ops_counter: int,
    ops_counter_init: int,
    workload: list,
    manual=True,
):

    # Iterate through workload of one block/cycle with the length of the minimal_block_delay
    for block in workload:
        # Time the execution of the workload in one cycle
        workload_start = time.time()

        # Iterate through the workload of each second of the block
        for ops_sec in block:
            # Time the execution of operations in one second
            interval_sec_start = time.time()
            for op in ops_sec:

                # Set the event for the operation
                event = f"trx_single_{rate_ops_lvl}.{ops_counter + 1}"

                # Configure the logging with the current event
                bc_ops.config_log(
                    hostname_log, event, log_dir, "/workload_client.log", log_file=True
                )

                # Inject the transfer operation
                try:
                    if manual:
                        transfer_results.update(
                            bc_ops.inject_single_man(
                                op[0],
                                OPS_TTL,
                                minimal_block_delay,
                            )
                        )
                    # else:  # -> automatic
                    #     transfer_result.update(
                    #         transfer_single_auto(
                    #             worker_accounts[acc]["tezos_client"],
                    #             worker_accounts[acc]["dest"][0],
                    #             amount,
                    #             OPS_TTL,
                    #             minimal_block_delay,
                    #         )
                    #     )
                    # Count the initialized operations
                    ops_counter_init += 1
                except:
                    print(f"Something went wrong with the worker {op[1]} at {event}")
                # Count every operation, also failed ones
                ops_counter += 1

            interval_sec_finished = time.time()
            # Each interval_sec should take exactly 1 second, thus wait until the 1 second is over, before continuing
            if (1 - (interval_sec_finished - interval_sec_start)) >= 0:
                time.sleep(1 - (interval_sec_finished - interval_sec_start))

        print(f"workload one block time: {time.time() - workload_start}")

    return ops_counter, ops_counter_init


def create_workload_lvl(
    blocks_to_run: int,
    trx_amount: int,
    rate_ops_lvl_i: int,
    minimal_block_delay: int,
    worker_accounts,
    workload_host: list,
    trx_bulk_size: int,
):
    complete_blocks = 0
    # Defines the starting index of the list of accounts to choose from for the operations
    account_index_start = 0

    # Initialize the list of created and signed operations
    workload = []

    while complete_blocks < blocks_to_run:
        create_wl_block_result = create_workload_lvl_one_block(
            trx_amount,
            rate_ops_lvl_i,
            minimal_block_delay,
            worker_accounts,
            workload_host,
            account_index_start,
            trx_bulk_size,
        )
        workload.append(create_wl_block_result[0])
        account_index_start = create_wl_block_result[1]
        complete_blocks += 1
    return workload


# extract host specific workload and convert to ordered list
def extract_host_workload(workload_protocol, hostname: str):
    workload_host = []

    for lvl, rate in workload_protocol["workload_plan"][hostname].items():
        workload_host.append([int(lvl.split("_")[3]), rate, sum(rate)])

    workload_host.sort(key=lambda lvl: lvl[0], reverse=False)
    return workload_host


def check_lvl_complete(
    tezos_rpc_port: int,
    workload_host: list,
    rate_ops_lvl_i: int,
    rate_ops_lvl: int,
    log_dir: str,
    hostname: str,
    transfer_results: dict,
    minimal_block_delay: int,
    blocks_to_run: int,
    start_block_lvl: int,
    time_start_workload: str,
    chain_name: str,
    genesis_host: bool,
    workload_check_log=True,
):

    ops_confirmed = 0
    ops_failed_block = 0
    ops_preval_failed = 0
    operations = {}

    # If according to the workload plan no transactions have been sent, return directly
    if workload_host[rate_ops_lvl_i][2] == 0:
        return (
            ops_confirmed,
            ops_failed_block,
            ops_preval_failed,
        )

    # Configure the logging for the check
    event = f"workload_check_lvl_{workload_host[rate_ops_lvl_i][0]}"
    bc_ops.config_log(
        hostname, event, log_dir, "/workload_check.log", workload_check_log
    )

    ## Check if the operations were injected by the node or an error occurred during prevalidation
    start_check_preval = time.time()
    check_preval_complete = False
    check_preval_timeout = 0
    while not check_preval_complete and check_preval_timeout < 60:
        # Assume the check will be completed in this iteration until an operation has not been found in the log yet
        check_preval_complete = True

        client_log = parse_logs.parse_workload_client_log(
            log_dir, "workload_client", export_json=False
        )

        # Parse the node log file, skip till the start of the workload level (time_start_workload)
        node_log = parse_logs.parse_node_log(
            log_dir,
            hostname,
            export_json=True,
            # start_time=time_start_workload,
        )

        ext_node_log = parse_logs.parse_ext_node_log(log_dir, export_json=True)

        ops_client_log_tmp = parse_logs.get_ops_client_log(
            client_log, hostname, chain_name
        )

        # Create a new dict that only contains operations from this workload (transfer_result) and the associated client log
        ops_client_log = {}
        ops_missing = 0
        # print(f"transfer result: {transfer_results}")
        # print(f"ops_client_log: {ops_client_log_tmp}")
        for op in transfer_results:
            if op in ops_client_log_tmp:
                ops_client_log.update({op: ops_client_log_tmp[op]})
            # In case there is a lag in the client log and an operation is missing, repeat the whole parsing process
            else:
                check_preval_complete = False
                ops_missing += 1

        (
            operations,
            ops_preval_failed,
        ) = parse_logs.get_ops_node_log(node_log, ext_node_log, ops_client_log)

        if not check_preval_complete:
            check_preval_timeout += 10
            time.sleep(10)
        print(f"check_preval_timeout: {check_preval_timeout}")

    end_check_preval = time.time()

    # Check if the workload is completely initiated and processed by the blockchain -> no more pending operations in the mempool
    bc_ops.check_node_status(minimal_block_delay, hostname, log_dir, tezos_rpc_port)

    # Configure the logging for the check of the workload
    event = f"workload_check_lvl_{rate_ops_lvl}"
    bc_ops.config_log(
        hostname, event, log_dir, "/workload_check.log", workload_check_log
    )

    get_block_start = time.time()
    (
        operations,
        blocks,
        endorsements,
        ops_confirmed,
        ops_failed_block,
    ) = parse_blockchain.get_op_block(
        operations,
        hostname,
        log_dir,
        tezos_rpc_port,
        start_block_lvl,
        genesis_host,
        chain_name,
    )
    get_block_end = time.time()

    # Export operations, blocks and endorsements (only genesis host)of this workload level
    export_csv_file(
        f"{log_dir}/",
        f"operations_{rate_ops_lvl_i}",
        operations.values(),
        from_type="dict",
    )
    if genesis_host:
        export_csv_file(
            f"{log_dir}/", f"blocks_{rate_ops_lvl_i}", blocks, from_type="dict"
        )
        export_csv_file(
            f"{log_dir}/",
            f"endorsements_{rate_ops_lvl_i}",
            endorsements,
            from_type="dict",
        )

    # Configure the logging for the check of the workload
    event = f"workload_check_lvl_{rate_ops_lvl}"
    bc_ops.config_log(hostname, event, log_dir, "/exp_summary.log", True, True)
    logging.info(
        f"\nTime to check prevalidation: {end_check_preval-start_check_preval}, "
        f"get_block (check if confirmed) time: {get_block_end - get_block_start}"
    )

    return (
        ops_confirmed,
        ops_failed_block,
        ops_preval_failed,
    )


def wait_to_start(
    start_time: float, minimal_block_delay: int, tezos_rpc_port: int
) -> int:

    # initialize a new connection to the node
    tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")
    # Get level of the head/newest block
    start_block_lvl = tezos_client.shell.head.level()
    # Check the host time to calculate how long to sleep before global start time is reached
    host_time = time.time()
    delta_st_ht = start_time - host_time
    if delta_st_ht >= 0:
        time.sleep(delta_st_ht)
    return start_block_lvl


def run_workload_complete(
    tezos_rpc_port: int,
    hostname: str,
    log_dir: str,
    start_time: float,
    minimal_block_delay: int,
    blocks_to_run: int,
    hostname_log: str,
    trx_amount: int,
    workload_host: list,
    worker_accounts,
    prepare_ops: bool,
    trx_bulk_size: int,
    chain_name: str,
    genesis_host: bool,
    first_workload_lvl_i=0,
    last_workload_lvl_i=9,
):
    # Number of all operations (initiated ones and failed ones)
    ops_counter = 0
    # Number of successfully initiated operations
    ops_counter_init = 0

    for rate_ops_lvl_i in range(first_workload_lvl_i, last_workload_lvl_i + 1):

        rate_ops_lvl = workload_host[rate_ops_lvl_i][0]

        create_start = time.time()
        workload = create_workload_lvl(
            blocks_to_run,
            trx_amount,
            rate_ops_lvl_i,
            minimal_block_delay,
            worker_accounts,
            workload_host,
            trx_bulk_size,
        )
        print(
            f"creation and signing of complete workload: {time.time() - create_start}"
        )

        transfer_results = {}
        start_block_lvl = wait_to_start(start_time, minimal_block_delay, tezos_rpc_port)
        # Convert the start time to the format of the node.log to set a start time for the parser
        time_start_workload = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
        time_start_workload_s = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

        bc_ops.config_log(
            hostname,
            "workload_start",
            log_dir,
            "/exp_summary.log",
            True,
            True,
        )
        logging.info(
            f"\nStart workload rate level: {workload_host[rate_ops_lvl_i][0]} % at: {time_start_workload_s}"
        )

        if prepare_ops:
            ops_counter, ops_counter_init = inject_workload_lvl(
                hostname_log,
                log_dir,
                rate_ops_lvl,
                minimal_block_delay,
                transfer_results,
                ops_counter,
                ops_counter_init,
                workload,
                manual=True,
            )

        else:
            # Run the workload of the specific rate level
            ops_counter, ops_counter_init = run_workload_lvl(
                blocks_to_run,
                hostname_log,
                log_dir,
                trx_amount,
                rate_ops_lvl_i,
                rate_ops_lvl,
                minimal_block_delay,
                worker_accounts,
                workload_host,
                transfer_results,
                ops_counter,
                ops_counter_init,
                trx_bulk_size,
            )

        # Check if the workload rate_ops_lvl was completed, hence all transactions initiated, confirmed/failed and all nodes synced
        ops_confirmed, ops_failed_block, ops_preval_failed = check_lvl_complete(
            tezos_rpc_port,
            workload_host,
            rate_ops_lvl_i,
            rate_ops_lvl,
            log_dir,
            hostname,
            transfer_results,
            minimal_block_delay,
            blocks_to_run,
            start_block_lvl,
            time_start_workload,
            chain_name,
            genesis_host,
            workload_check_log=False,
        )

        counter_start = time.time()
        if workload_host[rate_ops_lvl_i][2] != 0:
            # Set the account counter for every worker account
            worker_accounts = bc_ops.get_account_counter(
                hostname, log_dir, WORKER, worker_accounts, True, True, False
            )[0]
        counter_end = time.time()
        bc_ops.config_log(
            hostname,
            "workload_end",
            log_dir,
            "/exp_summary.log",
            True,
            True,
        )
        logging.info(
            f"\nRate level: {workload_host[rate_ops_lvl_i][0]} % capacity -- Operations total (bulksize: {'single' if trx_bulk_size < 2 else trx_bulk_size}, over {blocks_to_run} blocks): "
            f"{ops_counter} , initiated: {ops_counter_init}, injected and confirmed {'(bulks)' if trx_bulk_size > 1 else ''}: {ops_confirmed} "
            f"\nfailed initiation: {ops_counter - ops_counter_init}, failed prevalidation: {ops_preval_failed}, "
            f"{ops_failed_block} failed in block"
            f"\ncounter time: {counter_end-counter_start}"
        )


def main():

    # Tezos client directory
    client_dir = sys.argv[1]  # e.g. "/home/ubuntu/.tezos-client"

    # Tezos log directory
    log_dir = sys.argv[2]  # e.g. "/home/ubuntu/tezos-logs"

    # Tezos bootstrap accounts directory
    accounts_dir = sys.argv[3]  # e.g. "/home/ubuntu/tezos-accounts"

    # Tezos workload directory
    workload_dir = sys.argv[4]  # e.g. "/home/ubuntu/tezos-accounts"

    # Inventory Hostname
    hostname = sys.argv[5]
    hostname_log = hostname.replace("_", "-")  # e.g. "tezos_1 -> tezos-1"
    hostname_number = int(hostname.split("_")[1])

    # Amount in Tez to transfer
    trx_amount = int(sys.argv[6])

    # Send operations as single op one after the other ((bulk_size = 1))
    # or as a bulk together (bulk_size >= 2)
    trx_bulk_size = int(sys.argv[7])

    # Time, when to start the workload
    start_time = float(sys.argv[8])

    # first rate_ops_lvl -- IMPORTANT pass send_rate_lvl if only one level should be executed
    first_workload_lvl_index = int(sys.argv[9])

    # last rate_ops_lvl -- IMPORTANT pass send_rate_lvl if only one level should be executed
    last_workload_lvl_index = int(sys.argv[10])

    # Hostname of the genesis host
    genesis_hostname = sys.argv[11]
    # Set genesis_host to true if this host is the genesis host
    if genesis_hostname == hostname:
        genesis_host = True
    else:
        genesis_host = False

    # RPC port to communicate with node
    tezos_rpc_port = int(sys.argv[12])

    # Name of chain/experiment
    chain_name = sys.argv[13]

    # In the 'old' version, for smaller operation capacities per block and per second the first few hosts got all the workload to do.
    # In the new version, the workload is independent of the capacities better distributed over all hosts.
    prepare_ops = sys.argv[14]
    if prepare_ops.lower() == "false":
        prepare_ops = False
    elif prepare_ops.lower() == "true":
        prepare_ops = True

    # Load list of all workers (sources) with destinations for the other accounts (pkh) and up-to-date account counters
    worker_accounts = load_json_file(f"{accounts_dir}/", f"exp_worker_accounts")
    # Load workload file
    workload_protocol = load_json_file(f"{workload_dir}/", f"workload_protocol")
    # Minimal block delay
    minimal_block_delay = workload_protocol["blockchain_properties"][
        "minimal_block_delay"
    ]
    # blocks/cycles to run
    blocks_to_run = workload_protocol["workload_properties"]["blocks_to_run"]

    workload_host = extract_host_workload(workload_protocol, hostname)

    # Connect the worker accounts to the node
    worker_accounts = bc_ops.connect_shell_and_accounts(
        tezos_rpc_port, client_dir, WORKER, worker_accounts
    )

    run_workload_complete(
        tezos_rpc_port,
        hostname,
        log_dir,
        start_time,
        minimal_block_delay,
        blocks_to_run,
        hostname_log,
        trx_amount,
        workload_host,
        worker_accounts,
        bool(prepare_ops),
        trx_bulk_size,
        chain_name,
        genesis_host,
        first_workload_lvl_index,
        last_workload_lvl_index,
    )

    # Remove the connection to the node and store the accounts back in the file
    for acc in worker_accounts:
        acc.pop("tezos_client")
    export_json_file(f"{accounts_dir}/", f"exp_worker_accounts", worker_accounts)

    end_time = time.time()
    print(f"execution time: {end_time-start_time}")


if __name__ == "__main__":
    main()
