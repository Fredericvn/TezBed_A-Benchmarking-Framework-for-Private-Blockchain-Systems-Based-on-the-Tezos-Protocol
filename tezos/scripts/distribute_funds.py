import sys
import time

sys.path.append("/home/ubuntu/scripts")

from operation_constants import *
import blockchain_operations as bc_ops
import logging
from file_handler import load_json_file
from file_handler import export_json_file

from pytezos import pytezos
from decimal import Decimal


def distribute_funds_to_workers(
    tezos_rpc_port: int,
    hostname: str,
    log_dir: str,
    number_worker_acc: int,
    amount: int,
    bulk_size: int,
    baker_account,
    blocks_to_finish: int,
    minimal_block_delay: int,
    manual=False,
    dist_funds_log=False,
):
    exec_start = time.time()

    # Count every transaction try, also failed ones
    ops_counter = 0
    # Count only initiated transactions
    ops_counter_init = 0
    # Count confirmed operations
    confirmed_ops = 0
    # Signal for baker, that transfer was initiated
    transfer_init = False
    # Set destination index = 0, to start with the first destination from the list
    dest = 0
    # Set initial try
    tries = 0

    while dest < number_worker_acc:

        bulk_ops_list = []
        # Original baker account counter
        baker_acc_counter = baker_account["counter"]
        # Set ops in bulk to 0 = empty
        ops_in_bulk = 0
        # Define transfer result
        transfer_res = {}
        # Loop (multiple times) through the destination list and create a bulk list of operations/transactions out of it
        # Loop stops when there are as many operations in a bulk as the bulk size OR all destinations have been reached OR maximum fix bulk size is reached
        while (
            ops_in_bulk < bulk_size
            and dest < number_worker_acc
            and ops_in_bulk < MAX_OPS_BULK
        ):
            # Append to bulk list the operation's data: source: baker/bootstrap acc, destination: 'worker acc pkh' and amount in Tez
            bulk_ops_list.append(
                baker_account["tezos_client"].transaction(
                    destination=baker_account["dest"][dest],
                    amount=Decimal(amount),
                )
            )
            # Increment to the next destination
            dest += 1
            # Increment the number of operations in the bulk
            ops_in_bulk += 1
        # Create a bulk operations tuple out of the bulk ops list
        bulk_operations = tuple(bulk_ops_list)

        # Configure the logging with the current event
        event = f"trx_bulk_fundsDistr.{ops_counter + 1}-{ops_counter + ops_in_bulk}"
        bc_ops.config_log(
            hostname, event, log_dir, "/funds_distribution.log", dist_funds_log
        )

        tries = 1
        while tries <= 10:
            # Initiate the transfer of multiple transactions in one bulk
            try:
                if manual:
                    transfer_res.update(
                        bc_ops.transfer_bulk_man(
                            baker_account["tezos_client"],
                            bulk_operations,
                            baker_account["counter"],
                            OPS_TTL,
                            OPS_GAS_LIMIT,
                            OPS_STORAGE_LIMIT_BULK,
                            minimal_block_delay,
                            MINIMAL_NANOTEZ_PER_GAS_UNIT,
                        )
                    )
                else:  # -> automatic
                    transfer_res.update(
                        bc_ops.transfer_bulk_auto(
                            baker_account["tezos_client"],
                            bulk_operations,
                            OPS_TTL,
                            minimal_block_delay,
                        )
                    )
                ops_counter_init += ops_in_bulk
                transfer_init = True
            except:
                bc_ops.config_log(
                    hostname,
                    event,
                    log_dir,
                    "/exp_summary.log",
                    log_file=True,
                    log_stdout=True,
                )
                logging.info(f"\nSomething went wrong with the {event} at try: {tries}")
                tries += 1
                continue
            break
        # Increment to the next operations counter
        ops_counter += ops_in_bulk

        if transfer_init:
            # activate the logging by set log_file=True
            bc_ops.config_log(
                hostname,
                "check-fundsDistr",
                log_dir,
                "/check_fundsDistr.log",
                log_file=False,
            )
            start_confirmed = time.time()
            try:
                # Check if the operation has been confirmed
                tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")
                confirmed_ops += ops_in_bulk * len(
                    tezos_client.shell.wait_operations(
                        list(op_hash for op_hash in transfer_res), OPS_TTL, 0
                    )
                )

                baker_account = bc_ops.get_account_counter(
                    hostname,
                    log_dir,
                    BAKER,
                    baker_account,
                    increment=True,
                    offset=False,
                )[0]
            # In Case of a blockchain reorg the 'wait_operations' methods throws an exception
            except:
                # Check if the bulk operation has been confirmed by checking if the account counter is incremented by the number of operations in the bulk
                block = 1

                while baker_account["counter"] != baker_acc_counter - 1 + ops_in_bulk:
                    baker_account["counter"] = bc_ops.get_account_counter(
                        hostname,
                        log_dir,
                        BAKER,
                        baker_account,
                        increment=False,
                        offset=False,
                    )[1]

                    block += 0.25

                    # break condition
                    if block == blocks_to_finish * 4:
                        bc_ops.config_log(
                            hostname,
                            f"check-fundsDistr",
                            log_dir,
                            "/exp_summary.log",
                            log_file=True,
                            log_stdout=True,
                        )
                        logging.info(
                            f"\nSomething went wrong with {event}, already waited {blocks_to_finish * 4} blocks"
                            f"\nOps(bulk size: {bulk_size}): {ops_counter} , initiated: {ops_counter_init}, confirmed: {confirmed_ops},"
                            f" failed: {ops_counter - ops_counter_init}, tries: {tries} execution time: {time.time()-exec_start}"
                        )
                        return
                    time.sleep(minimal_block_delay * 0.25)

                confirmed_ops += ops_in_bulk
                baker_account["counter"] += 1

            end_confirmed = time.time()
            print(f"Confirmed time: {end_confirmed-start_confirmed}")
        transfer_init = False

    exec_end = time.time()

    # Logging results of distribution of funds
    bc_ops.config_log(
        hostname,
        f"results-fundsDistr",
        log_dir,
        "/exp_summary.log",
        log_file=True,
        log_stdout=True,
    )
    logging.info(
        f"\nOps(bulk size: {bulk_size}): {ops_counter} , initiated: {ops_counter_init}, confirmed: {confirmed_ops},"
        f" failed: {ops_counter - ops_counter_init}, tries: {tries} execution time: {exec_end-exec_start}"
    )
    return baker_account, ops_counter_init


def main():

    # The baker account name
    baker_account_name = sys.argv[1]  # e.g. "baker"
    # Tezos client directory
    client_dir = sys.argv[2]  # e.g. "/home/ubuntu/.tezos-client"
    # Tezos log directory
    log_dir = sys.argv[3]  # e.g. "/home/ubuntu/tezos-logs"
    # Tezos bootstrap accounts directory
    accounts_dir = sys.argv[4]  # e.g. "/home/ubuntu/tezos-accounts"
    # Tezos bootstrap accounts directory
    workload_dir = sys.argv[5]  # e.g. "/home/ubuntu/tezos-accounts"
    # Inventory Hostname
    hostname = sys.argv[6].replace("_", "-")  # e.g. "tezos_1 -> tezos-1"
    hostname_number = int(hostname.split("-")[1])

    # For debugging purposes the logging of the distribution of funds and revealing of public keys can be logged
    dist_funds_log = sys.argv[7]
    if dist_funds_log.lower() == "false":
        dist_funds_log = False
    elif dist_funds_log.lower() == "true":
        dist_funds_log = True

    tezos_rpc_port = int(sys.argv[8])

    workload_protocol = load_json_file(f"{workload_dir}/", "workload_protocol")

    # Number of blocks/cycles to run the workload
    blocks_to_run = workload_protocol["workload_properties"]["blocks_to_run"]

    # The number of worker accounts per node per experiment multiplied with the number of blocks to run / cycles
    number_worker_acc = (
        blocks_to_run
        * workload_protocol["funds_distribution"]["n_worker_acc_per_host"][
            hostname.replace("-", "_")
        ]
    )

    if number_worker_acc >= 1:

        # Amount of tez to fund the worker accounts with
        funds_worker_acc = workload_protocol["funds_distribution"]["funds_worker_acc"]

        # Optimal bulk size, so each host's transaction optimally fits in the block
        optimal_bulk_size = workload_protocol["funds_distribution"]["optimal_bulk_size"]

        # If less operations fit in one block than number of nodes take part in the experiment, hence optimal bulk size < 1,
        # delay half of the funds distributions (every node with uneven hostnumber) to not exceed the block gas limit
        delay_distribution = workload_protocol["funds_distribution"][
            "delay_distribution"
        ]

        # Number of blocks to wait until the distribution should be finished
        blocks_to_finish = workload_protocol["funds_distribution"]["blocks_to_finish"]

        # Minimal block delay
        minimal_block_delay = workload_protocol["blockchain_properties"][
            "minimal_block_delay"
        ]

        # load the destinations
        all_destinations = load_json_file(f"{accounts_dir}/", f"exp_all_destinations")

        baker_account = {"dest": all_destinations, "counter": 1}

        baker_account = bc_ops.connect_shell_and_accounts(
            tezos_rpc_port, client_dir, BAKER, baker_account, baker_account_name
        )

        # Only for nodes with an uneven hostnumber
        if delay_distribution and hostname_number % 2 == 1:
            # Start after the second block
            time.sleep(minimal_block_delay)
            # Check if the distribution of funds and revealing of accounts of all hosts with even hostnumber is complete
            bc_ops.check_node_status(
                minimal_block_delay, hostname, log_dir, tezos_rpc_port
            )
            time.sleep(5)
            bc_ops.check_node_status(
                minimal_block_delay, hostname, log_dir, tezos_rpc_port
            )

        distribution_start = time.time()
        # Distribute funds from baker/bootstrap account to workers accounts in bulk transfer
        distribute_funds_to_workers(
            tezos_rpc_port,
            hostname,
            log_dir,
            number_worker_acc,
            funds_worker_acc,
            optimal_bulk_size,
            baker_account,
            blocks_to_finish,
            minimal_block_delay,
            manual=True,
            dist_funds_log=bool(dist_funds_log),
        )
        distribution_end = time.time()

        print(f"distribution time: {distribution_end - distribution_start}")


if __name__ == "__main__":
    main()
