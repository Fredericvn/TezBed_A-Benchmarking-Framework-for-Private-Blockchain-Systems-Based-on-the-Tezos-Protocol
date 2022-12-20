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


def reveal_worker_accounts(
    tezos_rpc_port: int,
    hostname: str,
    log_dir: str,
    worker_accounts: list,
    minimal_block_delay: int,
    number_worker_acc: int,
    manual=False,
    reveal_log=True,
) -> list:

    revealed = 0
    reveal_ops = {}
    not_revealed = []
    tries = 0

    while revealed < number_worker_acc:
        # If the revealing of pkh was not successful at first try and manual mode is active, get the account counter
        if tries >= 1 and manual:
            worker_accounts = bc_ops.get_account_counter(
                hostname, log_dir, WORKER, worker_accounts, True, True, False
            )[0]

        for a, acc in enumerate(worker_accounts):
            if not acc["revealed"]:
                # Provide the first and last three characters of the public key hash of the account
                event = f"reveal-acc-{acc['pkh'][:3]}-{acc['pkh'][-3:]}"
                # Configure the logging with the current event
                bc_ops.config_log(
                    hostname, event, log_dir, "/reveal_pkh.log", reveal_log
                )
                # Reveal the public key hash of the desired account
                try:
                    if manual:
                        reveal_ops.update(
                            bc_ops.reveal_acc_man(
                                acc["tezos_client"],
                                acc["counter"],
                                OPS_TTL,
                                1000,
                                0,
                                minimal_block_delay,
                            )
                        )
                    else:  # -> automatic
                        reveal_ops.update(
                            bc_ops.reveal_acc_auto(
                                acc["tezos_client"], OPS_TTL, minimal_block_delay
                            )
                        )
                except:
                    not_revealed.append(acc["pkh"])
            # Make a pause in between to crash less nodes
            # if a % 10 == 0 and tries < 1:
            #     time.sleep(5)
        tries += 1
        # Check if accounts have been revealed
        worker_accounts, revealed = check_revealed(
            worker_accounts,
            minimal_block_delay,
            revealed,
            reveal_ops,
            number_worker_acc,
            hostname,
            log_dir,
            tezos_rpc_port,
        )

    # Logging results of revealing public keys
    bc_ops.config_log(
        hostname, "results_reveal-acc", log_dir, "/exp_summary.log", reveal_log, True
    )
    if tries > 0:
        logging.info(
            f"\nIt took {tries} {'try' if tries == 1 else 'tries'} to reveal all {revealed} accounts"
        )
    if tries == 0:
        logging.info(f"\nNo accounts to reveal")
    return worker_accounts


def check_revealed(
    worker_accounts: list,
    minimal_block_delay: int,
    revealed: int,
    reveal_ops: dict,
    number_worker_acc: int,
    hostname: str,
    log_dir: str,
    tezos_rpc_port: int,
):

    for pos, acc in enumerate(worker_accounts):
        for ops in reveal_ops.values():
            if acc["pkh"] == ops["contents"][0]["source"]:
                ops["position"] = pos
                ops["revealed"] = acc["revealed"]

    # Check if no more operations need to be included in the blockchain
    bc_ops.check_node_status(minimal_block_delay, hostname, log_dir, tezos_rpc_port)

    # reveal_ops_tmp = reveal_ops.copy()
    block_timeout = 0
    last_head_lvl = 0
    # start_block_lvl = 5
    revealed_failed = 0
    check_reveal_time = 0
    ## Check if the operations have been applied/confirmed in a block
    while block_timeout < 10 and revealed != number_worker_acc:
        bc_ops.config_log()
        # initialize a new connection to the node, to get the newest head block
        tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")
        # Get level of the head/newest block
        head_lvl = tezos_client.shell.head.level()
        # If new head_lvl is the same as the last head_lvl, wait a moment and continue
        if last_head_lvl == head_lvl:
            time.sleep(minimal_block_delay * 0.125)
            block_timeout += 0.125
            continue
        block_timeout += 1
        start_block_lvl = 2
        check_reveal_start = time.time()

        # Iterate from the start block level to the current head level over every block
        while start_block_lvl <= head_lvl:

            # activate the logging by set log_file=True
            bc_ops.config_log(
                hostname,
                "check-reveal-acc",
                log_dir,
                "/check_reveal_acc.log",
                log_file=False,
            )

            # Get a LIST of all operations (transactions only) of the block
            block_operations = tezos_client.shell.blocks[start_block_lvl].operations()[3]  # type: ignore
            for op in block_operations:
                # The operation in the block is in the dict of operations from the reveal_ops_tmp
                try:
                    # if reveal_ops_tmp[op["hash"]]:
                    if reveal_ops[op["hash"]]:
                        confirmed = False
                        # Check status of operation
                        for status in op["contents"]:
                            confirmed = False
                            if (
                                status["metadata"]["operation_result"]["status"]
                                == "applied"
                            ):
                                confirmed = True
                        # Set revealed status - will also change the original reveal_ops nested element
                        # reveal_ops_tmp[op["hash"]]["revealed"] = confirmed
                        reveal_ops[op["hash"]]["revealed"] = confirmed
                        # worker_accounts[reveal_ops_tmp[op["hash"]]["position"]][
                        worker_accounts[reveal_ops[op["hash"]]["position"]][
                            "revealed"
                        ] = confirmed
                        # reveal_ops_tmp.pop(op["hash"])
                        reveal_ops.pop(op["hash"])
                        if confirmed:
                            revealed += 1
                        else:
                            revealed_failed += 1
                # The operation in the block is NOT in the dict of operations from the reveal_ops
                except (KeyError):
                    continue
            # continue with the next block
            start_block_lvl += 1

            check_reveal_end = time.time()
            check_reveal_time += check_reveal_end - check_reveal_start
        # store the head lvl of this iteration
        last_head_lvl = head_lvl

    bc_ops.config_log(
        hostname, "check-reveal-acc", log_dir, "/exp_summary.log", True, True
    )
    logging.info(
        f"\nrevealed accounts: {revealed}, waited {block_timeout} blocks for confirmation, check_reveal_time: {check_reveal_time}"
    )
    return worker_accounts, revealed


def main():

    # Tezos client directory
    client_dir = sys.argv[1]  # e.g. "/home/ubuntu/.tezos-client"
    # Tezos log directory
    log_dir = sys.argv[2]  # e.g. "/home/ubuntu/tezos-logs"
    # Tezos bootstrap accounts directory
    accounts_dir = sys.argv[3]  # e.g. "/home/ubuntu/tezos-accounts"
    # Tezos bootstrap accounts directory
    workload_dir = sys.argv[4]  # e.g. "/home/ubuntu/tezos-accounts"
    # Inventory Hostname
    hostname = sys.argv[5].replace("_", "-")  # e.g. "tezos_1 -> tezos-1"

    reveal_log = sys.argv[6]
    if reveal_log.lower() == "false":
        reveal_log = False
    elif reveal_log.lower() == "true":
        reveal_log = True

    tezos_rpc_port = int(sys.argv[7])

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

        # If less operations fit in one block than number of nodes take part in the experiment, hence optimal bulk size < 1,
        # delay half of the funds distributions (every node with uneven hostnumber) to not exceed the block gas limit
        delay_distribution = workload_protocol["funds_distribution"][
            "delay_distribution"
        ]

        # Minimal block delay
        minimal_block_delay = workload_protocol["blockchain_properties"][
            "minimal_block_delay"
        ]

        # List of all workers (sources) with each a list of destinations (public key hash)
        worker_accounts = load_json_file(f"{accounts_dir}/", f"exp_worker_accounts")

        # Connect the accounts (secret keys) with the node
        worker_accounts = bc_ops.connect_shell_and_accounts(
            tezos_rpc_port, client_dir, WORKER, worker_accounts
        )

        # # Only for nodes with an uneven hostnumber
        # if delay_distribution and hostname_number % 2 == 1:
        #     # Start after the second block
        #     time.sleep(minimal_block_delay)
        #     # Check if the distribution of funds and revealing of accounts of all hosts with even hostnumber is complete
        #     bc_ops.check_node_status(minimal_block_delay, hostname, log_dir, tezos_rpc_port)
        #     time.sleep(5)
        #     bc_ops.check_node_status(minimal_block_delay, hostname, log_dir, tezos_rpc_port)

        reveal_start = time.time()
        # Reveal public keys of worker accounts in order to send transactions
        worker_accounts = reveal_worker_accounts(
            tezos_rpc_port,
            hostname,
            log_dir,
            worker_accounts,
            minimal_block_delay,
            number_worker_acc,
            manual=False,
            reveal_log=bool(reveal_log),
        )
        reveal_end = time.time()

        counter_start = time.time()
        # Set the account counter for every worker account
        worker_accounts = bc_ops.get_account_counter(
            hostname, log_dir, WORKER, worker_accounts, True, False, False
        )[0]
        counter_end = time.time()

        for acc in worker_accounts:
            # Remove the shell connections from worker accounts to export it as json.
            acc.pop("tezos_client")
        export_json_file(f"{accounts_dir}/", f"exp_worker_accounts", worker_accounts)

        print(
            f"Reveal account time: {reveal_end - reveal_start}, counter time: {counter_end - counter_start}"
        )


if __name__ == "__main__":
    main()
