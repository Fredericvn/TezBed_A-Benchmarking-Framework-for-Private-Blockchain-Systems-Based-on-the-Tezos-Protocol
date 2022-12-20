import sys
import logging
import logging.config
import time
import os
import subprocess

sys.path.append("/home/ubuntu/scripts")

from operation_constants import *

from pytezos import pytezos
from pytezos.crypto.key import Key
from decimal import Decimal
from datetime import datetime


def load_log_file(log_dir: str, file_name: str) -> str:
    files_path = f"{log_dir}/{file_name}"
    os.makedirs(os.path.dirname(files_path), exist_ok=True)
    return files_path


# Initialize the connection between pytezos client and the node and set the account(s) to utilize
def connect_shell_and_accounts(
    tezos_rpc_port: int, client_dir: str, worker: bool, accounts, account_name="baker"
):
    if worker:
        for acc in accounts:
            acc["tezos_client"] = pytezos.using(
                shell=f"http://localhost:{tezos_rpc_port}",
                key=Key.from_encoded_key(acc["sk"]),
            )
    if not worker:
        accounts["tezos_client"] = pytezos.using(
            shell=f"http://localhost:{tezos_rpc_port}",
            key=Key.from_alias(alias=account_name, tezos_client_dir=client_dir),
        )
        accounts["pkh"] = accounts["tezos_client"].key.public_key_hash()
    return accounts


# Get the account counter from the blockchain for each account
def get_account_counter(
    hostname: str,
    log_dir: str,
    worker: bool,
    accounts,
    increment: bool,
    offset: bool,
    acc_counter_log=False,
):
    # Set the logging
    config_log(
        hostname, "account_counter", log_dir, "/account_counter.log", acc_counter_log
    )

    counter = 0
    acc_counter_offset = 0
    if worker:
        for acc in accounts:
            # Retrieve account transaction counter (only confirmed transactions are counted)
            counter = int(acc["tezos_client"].account()["counter"])
            # Increment account counter by 1
            if increment:
                counter += 1
                if offset:
                    # Account for transaction counter offset, returns current account counter of pending transactions in mempool
                    acc_counter_offset = int(
                        acc["tezos_client"].context.get_counter_offset()
                    )
                    # Increase the account transaction counter by the offset, if pending transactions are in mempool
                    counter += acc_counter_offset
            acc["counter"] = counter

    if not worker:
        # Retrieve account transaction counter (only confirmed transactions are counted)
        counter = int(accounts["tezos_client"].account()["counter"])
        # Increment account counter by 1
        if increment:
            counter += 1
            if offset:
                # Account for transaction counter offset, returns current account counter of pending transactions in mempool
                acc_counter_offset = int(
                    accounts["tezos_client"].context.get_counter_offset()
                )
                # Increase the account transaction counter by the offset, if pending transactions are in mempool
                counter += acc_counter_offset
        accounts["counter"] = counter
    return accounts, counter


def set_worker_acc_counter(
    hostname: str, log_dir: str, worker_accounts: list, bulk_size: int
):
    worker_accounts = get_account_counter(
        hostname, log_dir, WORKER, worker_accounts, True, False
    )[0]
    for acc in worker_accounts:
        # Remove the shell connections from worker accounts to export it as json.
        acc.pop("tezos_client")
    return worker_accounts


# Reveal the public key of an account to the network in order to send transactions afterwards, all parameters needs to be set manually (fast)
def reveal_acc_man(
    tezos_client,
    acc_counter: int,
    ops_ttl: int,
    ops_gas_limit: int,
    ops_storage_limit: int,
    minimal_block_delay: int,
) -> dict:
    op_result = (
        tezos_client.reveal()
        .fill(
            ttl=ops_ttl,
            counter=acc_counter,
            gas_limit=ops_gas_limit,
            storage_limit=ops_storage_limit,
        )
        .sign()
        .inject(
            num_blocks_wait=ops_ttl,
            time_between_blocks=minimal_block_delay,
            prevalidate=False,
        )
    )
    logging.info(op_result)
    # Until the operation is confirmed in a block the status is set to 'false'
    op_result["revealed"] = False
    op_result = {op_result["hash"]: op_result}
    return op_result


# Reveal the public key of an account to the network in order to send transactions afterwards, all parameters will be set automatically (slower)
def reveal_acc_auto(tezos_client, ops_ttl: int, minimal_block_delay: int) -> dict:
    op_result = (
        tezos_client.reveal()
        .autofill(ttl=ops_ttl)
        .sign()
        .inject(num_blocks_wait=ops_ttl, time_between_blocks=minimal_block_delay)
    )
    logging.info(op_result)
    # Until the operation is confirmed in a block the status is set to 'false'
    op_result["revealed"] = False
    op_result = {op_result["hash"]: op_result}
    return op_result


# Transfers 'amount' of Tez from the connected account (stored account in tezos-client) to the 'destinations' account. Gas Fees and other params are set automatically
def transfer_single_auto(
    tezos_client,
    destination: str,
    amount: int,
    ops_ttl: int,
    minimal_block_delay: int,
) -> dict:
    op_result = (
        tezos_client.transaction(destination=destination, amount=Decimal(amount))
        .autofill(ttl=ops_ttl)
        .sign()
        .inject(num_blocks_wait=ops_ttl, time_between_blocks=minimal_block_delay)
    )
    logging.info(op_result)
    op_result = {op_result["hash"]: op_result}
    return op_result


# Transfers 'amount' of Tez async from the connected account to the 'destinations' account. Account transaction Counter has to be set correctly
def transfer_single_man(
    tezos_client,
    destination: str,
    amount: int,
    acc_counter: int,
    ops_ttl: int,
    ops_gas_limit: int,
    ops_storage_limit: int,
    minimal_block_delay: int,
    minimal_nanotez_per_gas_unit: int,
) -> dict:
    op_result = (
        tezos_client.transaction(destination=destination, amount=Decimal(amount))
        .fill(
            ttl=ops_ttl,
            counter=acc_counter,
            gas_limit=ops_gas_limit,
            storage_limit=ops_storage_limit,
            minimal_nanotez_per_gas_unit=minimal_nanotez_per_gas_unit,
        )
        .sign()
        .inject(
            check_result=False,
            num_blocks_wait=ops_ttl,
            time_between_blocks=minimal_block_delay,
            prevalidate=False,
        )
    )
    logging.info(op_result)
    op_result = {op_result["hash"]: op_result}
    return op_result


# Create and sign the operation to transfer 'amount' of Tez async from the connected account to the 'destinations' account.
# Account transaction Counter has to be set correctly
def create_op_single_man(
    tezos_client,
    destination: str,
    pkh: str,
    amount: int,
    acc_counter: int,
    ops_ttl: int,
    ops_gas_limit: int,
    ops_storage_limit: int,
    minimal_nanotez_per_gas_unit: int,
):
    operation = [
        (
            tezos_client.transaction(destination=destination, amount=Decimal(amount))
            .fill(
                ttl=ops_ttl,
                counter=acc_counter,
                gas_limit=ops_gas_limit,
                storage_limit=ops_storage_limit,
                minimal_nanotez_per_gas_unit=minimal_nanotez_per_gas_unit,
            )
            .sign()
        ),
        pkh,
    ]
    return operation


# Inject the pre-created and presigned operation into the node
def inject_single_man(
    operation,
    ops_ttl: int,
    minimal_block_delay: int,
) -> dict:
    op_result = operation.inject(
        check_result=False,
        num_blocks_wait=ops_ttl,
        time_between_blocks=minimal_block_delay,
        prevalidate=False,
    )
    logging.info(op_result)
    op_result = {op_result["hash"]: op_result}
    return op_result


# Transfers bulk of operations. Gas Fees and other params are set automatically
def transfer_bulk_auto(
    tezos_client, bulk_operations: tuple, ops_ttl: int, minimal_block_delay: int
):
    bulk_result = (
        tezos_client.bulk(*bulk_operations)
        .autofill(ttl=ops_ttl)
        .sign()
        .inject(num_blocks_wait=ops_ttl, time_between_blocks=minimal_block_delay)
    )
    logging.info(bulk_result)
    bulk_result = {bulk_result["hash"]: bulk_result}
    return bulk_result


# Transfers bulk of operations. Account transaction Counter has to be set correctly
def transfer_bulk_man(
    tezos_client,
    bulk_operations: tuple,
    acc_counter: int,
    ops_ttl: int,
    ops_gas_limit: int,
    ops_storage_limit: int,
    minimal_block_delay: int,
    minimal_nanotez_per_gas_unit: int,
):
    bulk_result = (
        tezos_client.bulk(*bulk_operations)
        .fill(
            ttl=ops_ttl,
            counter=acc_counter,
            gas_limit=ops_gas_limit,
            storage_limit=ops_storage_limit,
            minimal_nanotez_per_gas_unit=minimal_nanotez_per_gas_unit,
        )
        .sign()
        .inject(
            num_blocks_wait=ops_ttl,
            time_between_blocks=minimal_block_delay,
            prevalidate=False,
        )
    )
    logging.info(bulk_result)
    bulk_result = {bulk_result["hash"]: bulk_result}
    return bulk_result


# Configure the logging
def config_log(
    hostname="",
    event="",
    log_dir="",
    file_name="",
    log_file=False,
    log_stdout=False,
):
    # Delete all previous logging configs/handlers
    logging.root.handlers = []

    # Log to file and standard out
    if log_file and log_stdout:
        # Define the logging output format, file and level
        logging.basicConfig(
            force=True,
            format='{"client":{"hostname":"'
            + hostname
            + '","time_stamp":"%(asctime)s","U_ts":%(created)f,"logger":"%(name)s","event":"'
            + event
            + '","msg":{%(message)s}}}',
            datefmt="%Y-%m-%dT%H:%M:%S.%03d",
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler(log_dir + file_name),
                logging.StreamHandler(stream=sys.stdout),
            ],
        )
    # Only log to standard out
    if log_stdout and not log_file:
        # Define the logging output format, file and level
        logging.basicConfig(
            force=True,
            format='{"client":{"hostname":"'
            + hostname
            + '","time_stamp":"%(asctime)s","U_ts":%(created)f,"logger":"%(name)s","event":"'
            + event
            + '","msg":{%(message)s}}}',
            datefmt="%Y-%m-%dT%H:%M:%S.%03d",
            level=logging.DEBUG,
            handlers=[
                logging.StreamHandler(stream=sys.stdout),
            ],
        )
    # Only log to file
    if log_file and not log_stdout:
        # Define the logging output format, file and level
        logging.basicConfig(
            force=True,
            format='{"client":{"hostname":"'
            + hostname
            + '","time_stamp":"%(asctime)s","U_ts":%(created)f,"logger":"%(name)s","event":"'
            + event
            + '","msg":{%(message)s}}}',
            datefmt="%Y-%m-%dT%H:%M:%S.%03d",
            level=logging.DEBUG,
            handlers=[logging.FileHandler(log_dir + file_name)],
        )


# Send the desired number of operations each from a different worker account to a different destination (next account)
# in manual or automatic mode (no counter required)
def send_workload_singly(
    hostname: str,
    log_dir: str,
    rate_ops_lvl: int,
    number_of_ops: int,
    amount: int,
    worker: bool,
    worker_accounts: list,
    lvl_ops_counter: int,
    minimal_block_delay: int,
    manual=False,
):
    if not worker:
        return worker_accounts

    # start = time.time()
    # Count every transaction try, also failed ones
    ops_counter = 0
    # Count only initiated transactions
    ops_counter_init = 0
    # Create dict of ops from the transfer result
    transfer_result = {}
    # Loop (multiple times) through the account list until the number of operations/trx is reached.
    # IMPORTANT: per block only one transaction per account (PKH) is allowed, due to the account counter
    acc = 0
    while ops_counter < number_of_ops:
        lvl_ops_counter += 1
        event = f"trx_single_{rate_ops_lvl}.{lvl_ops_counter}"

        # Configure the logging with the current event
        config_log(hostname, event, log_dir, "/workload_client.log", log_file=True)

        # Transfer from worker account a to first destination in the list the desired amount of Tez
        try:
            if manual:
                transfer_result.update(
                    transfer_single_man(
                        worker_accounts[acc]["tezos_client"],
                        worker_accounts[acc]["dest"][0],
                        amount,
                        worker_accounts[acc]["counter"],
                        OPS_TTL,
                        OPS_GAS_LIMIT,
                        OPS_STORAGE_LIMIT,
                        minimal_block_delay,
                        MINIMAL_NANOTEZ_PER_GAS_UNIT,
                    )
                )
            else:  # -> automatic
                transfer_result.update(
                    transfer_single_auto(
                        worker_accounts[acc]["tezos_client"],
                        worker_accounts[acc]["dest"][0],
                        amount,
                        OPS_TTL,
                        minimal_block_delay,
                    )
                )
            ops_counter_init += 1
            # worker_accounts[acc]["counter"] += 1
        except:
            print(
                f'Something went wrong with the worker {worker_accounts[acc]["pkh"]} at {event}'
            )
        ops_counter += 1
        acc += 1

    return worker_accounts, ops_counter, ops_counter_init, transfer_result


# Create and sign all operations of the workload of one cycle (block to run)
def create_all_ops_singly(
    number_of_ops: int,
    amount: int,
    worker: bool,
    worker_accounts: list,
    manual=False,
) -> list:
    if not worker:
        return worker_accounts

    # start = time.time()
    # Count only created and signed operations
    ops_counter_created = 0
    # Create dict of ops from the transfer result
    operations = []
    # Loop (multiple times) through the account list until the number of operations/trx is reached.
    # IMPORTANT: per block only one transaction per account (PKH) is allowed, due to the account counter
    acc = 0
    while ops_counter_created < number_of_ops:

        # Transfer from worker account to first destination in the list the desired amount of Tez
        if manual:
            operations.append(
                create_op_single_man(
                    worker_accounts[acc]["tezos_client"],
                    worker_accounts[acc]["dest"][0],
                    worker_accounts[acc]["pkh"],
                    amount,
                    worker_accounts[acc]["counter"],
                    OPS_TTL,
                    OPS_GAS_LIMIT,
                    OPS_STORAGE_LIMIT,
                    MINIMAL_NANOTEZ_PER_GAS_UNIT,
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
        ops_counter_created += 1
        acc += 1

    return operations


# Not up to date -> Don't use at this stage
def send_workload_in_bulks(
    hostname: str,
    log_dir: str,
    rate_ops_lvl: int,
    number_of_ops: int,
    amount: int,
    worker: bool,
    worker_accounts: list,
    lvl_ops_counter: int,
    minimal_block_delay: int,
    bulk_size: int,
    manual=False,
):
    if not worker:
        return worker_accounts

    # Count every transaction try, also failed ones
    ops_counter = 0
    # Count only initiated transactions
    ops_counter_init = 0
    # Create dict of ops from the transfer result
    transfer_result = {}

    # Start with account index 0
    acc = 0
    # Execute bulk transfers until the desired number of operations have been fullfilled
    while ops_counter < number_of_ops:

        bulk_ops_list = []
        # Set ops in bulk to 0 = empty
        ops_in_bulk = 0
        # Start with destination index 0
        dest = 0
        # Loop (multiple times) through the destination list and create a bulk list of operations/transactions out of it
        # While loop stops when there are as many operations in a bulk as the bulk size OR desired number of ops to send is reached OR maximum fix bulk size is reached
        while (
            ops_in_bulk < bulk_size
            and ops_counter < number_of_ops
            and ops_in_bulk < MAX_OPS_BULK
        ):

            # Append to bulk list the operation's data: source, destination and amount in Tez
            bulk_ops_list.append(
                worker_accounts[acc]["tezos_client"].transaction(
                    destination=worker_accounts[acc]["dest"][dest],
                    amount=Decimal(amount),
                )
            )

            # Increment to the next destination
            dest += 1
            # Increment the number of operations in the bulk
            ops_in_bulk += 1
        # Create a bulk operations tuple out of the bulk ops list
        bulk_operations = tuple(bulk_ops_list)

        # The log event description ends with the range of the first and last ops_counter number of the bulk of transcations
        event = f"trx_bulk_{rate_ops_lvl}.{lvl_ops_counter + 1}-{lvl_ops_counter + ops_in_bulk}"
        # Configure the logging with the current event
        config_log(hostname, event, log_dir, "/workload_client.log", log_file=True)

        # Initiate the transfer of multiple transactions in one bulk
        try:
            if manual:
                transfer_result.update(
                    transfer_bulk_man(
                        worker_accounts[acc]["tezos_client"],
                        bulk_operations,
                        worker_accounts[acc]["counter"],
                        OPS_TTL,
                        OPS_GAS_LIMIT,
                        OPS_STORAGE_LIMIT,
                        minimal_block_delay,
                        MINIMAL_NANOTEZ_PER_GAS_UNIT,
                    )
                )
            else:  # -> automatic
                transfer_result.update(
                    transfer_bulk_auto(
                        worker_accounts[acc]["tezos_client"],
                        bulk_operations,
                        OPS_TTL,
                        minimal_block_delay,
                    )
                )
            ops_counter_init += ops_in_bulk
            worker_accounts[acc]["counter"] += ops_in_bulk
        except:
            print(
                f'Something went wrong with the worker {worker_accounts[acc]["pkh"]} {event}'
            )
        ops_counter += ops_in_bulk
        lvl_ops_counter = ops_counter
        acc += 1

    return worker_accounts, ops_counter, ops_counter_init, transfer_result


def check_node_status(
    minimal_block_delay: int, hostname: str, log_dir: str, tezos_rpc_port: int
):

    # Set parameter log_file = True, to activate the full logging
    config_log(
        hostname,
        "check_node_status",
        log_dir,
        "/check_node_status.log",
        log_file=False,
        log_stdout=False,
    )
    # Counts the number of blocks until the node does not process anymore workload
    block_counter = 0
    # Stores the block head level of the last iteration
    last_head_lvl = 0

    start_check_status = time.time()

    # initialize a new connection to the node, to get the newest head block
    tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")
    # Stores the first level of the check status to calculate the number of blocks it took.
    first_lvl = tezos_client.shell.head.level()

    ## Check if the node is synced, no more new operations in the head block and no more transactions in the mempool (applied, unprocessed, branch_delayed)
    while True:
        # Get the newest head block
        head_block = tezos_client.shell.head
        # Get the newest block head level
        head_lvl = head_block.level()

        # Calculate if the head_lvl is not more than minimal block delay + 5 seconds old, to check if the node is up to date
        # Get the iso timestamp of the block in unix epoch timestamp in seconds
        block_u_ts = datetime.fromisoformat(f"{head_block.header()['timestamp'].rstrip('Z')}").timestamp()  # type: ignore
        delta_ts_now = time.time() - block_u_ts

        # Check if the head level has changed since the last iteration, if not sleep some time and continue
        if last_head_lvl == head_lvl or delta_ts_now > (minimal_block_delay + 5):
            time.sleep(minimal_block_delay * 0.125)
            continue

        # Check if node is bootstrapped and synced
        status = subprocess.run(
            ["tezos-client", "rpc", "get", "/chains/main/is_bootstrapped"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        # bootstrapped status
        b_status = status.stdout.split('"bootstrapped": ')[1].split(",")[0]
        # print(f"bootstrapped: {b_status}")
        # sync status
        s_status = (
            status.stdout.split('"sync_state": ')[1].strip().rstrip("} ").strip('"')
        )

        # print(f"synced status: {s_status}")

        if b_status == "true" and s_status == "synced":

            # Get a list of all operations (transcations only) of the block
            head_operations = tezos_client.shell.head.operations()[3]  # type: ignore

            # Check if number of new transactions in the head block is zero
            if not head_operations:

                ## Check the mempool ({'applied':[...], 'refused': [...], 'outdated':[...], 'branch_refused': [...], 'branch_delayed':[...], 'unprocessed':[...]}
                ## for pending transactions in 'applied', 'branch_delayed' and 'unprocessed'
                # Get mempool
                mempool = tezos_client.shell.mempool.pending_operations()
                # Iterate through the 'applied' list and check for operations with 'kind' = transaction
                op_applied = False
                for op in mempool["applied"]:  # type: ignore
                    # If only one transaction is found, set 'op_applied' to True and stop the iteration
                    if op["contents"][0]["kind"] == "transaction":
                        op_applied = True
                        break

                if not op_applied:
                    # Check 'branch_delayed' and 'unprocessed' for transactions
                    if not mempool["branch_delayed"] and not mempool["unprocessed"]:  # type: ignore
                        # The workload is finished!
                        # Calculate the number of blocks it took
                        block_counter = head_lvl - first_lvl
                        time_check_status = time.time() - start_check_status

                        config_log(
                            hostname,
                            "check_node_status",
                            log_dir,
                            "/exp_summary.log",
                            log_file=True,
                            log_stdout=True,
                        )
                        logging.info(
                            f"\nstatus_counter (blocks waited): {block_counter}, status_time: {time_check_status}"
                        )
                        config_log()
                        return block_counter, time_check_status

                # Save the head_lvl and continue with the check at the next block
                last_head_lvl = head_lvl
                continue
