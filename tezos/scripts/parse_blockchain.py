import time
import logging
import os

from pytezos import pytezos
from pytezos.crypto.key import Key
from pytezos.operation.result import OperationResult
from datetime import datetime

from blockchain_operations import config_log


def read_former_block_lvl(log_dir: str, head_lvl: int):
    file_path = f"{log_dir}/former_block_lvl.txt"
    if os.path.exists(file_path):
        with open(file_path, "r+") as file:
            former_bl_lvl = int(file.readline())
            file.seek(0)
            file.write(str(head_lvl))
    else:
        with open(file_path, "w") as file:
            former_bl_lvl = 1
            file.write(str(head_lvl))
    return former_bl_lvl


# Get all necessary information about each operation out of the blockchain, by scanning every block for each operation that has been sent
def get_op_block(
    operations: dict,
    hostname: str,
    log_dir: str,
    tezos_rpc_port: int,
    start_lvl: int,
    genesis_host: bool,
    chain_name: str,
):

    ops_confirmed = 0
    ops_failed_block = 0

    blocks = []
    endorsements = []

    # initialize a new connection to the node, to get the newest head block
    tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")
    # Get level of the head/newest block
    head_lvl = tezos_client.shell.block.level()

    former_bl_lvl = read_former_block_lvl(log_dir, head_lvl)

    # Starting level
    block_lvl = former_bl_lvl + 1

    # Iterate from the lowest block level (lowest op branch) to the current head level over every block
    while block_lvl <= head_lvl:

        # Get the whole block
        b = tezos_client.shell.blocks[block_lvl]
        # Get the block header
        block_header = b.header()
        # Get the block hash
        block_id = block_header["hash"]  # type: ignore
        # Get the block timestamp
        block_ts = block_header["timestamp"].rstrip("Z")  # type: ignore
        # Convert the iso timestamp yyyy-mm-ddThh:mm:ss to unix epoch timestamp in seconds
        block_U_ts = datetime.fromisoformat(f"{block_ts.strip('Z')}").timestamp()

        # Get a list of all operations of the block
        block_operations = b.operations()  # type: ignore
        # block transactions only
        block_transactions = block_operations[3]  # type: ignore

        # Only the genesis host retrieves all block properties and stores them in 'blocks' and 'endorsements' lists of dicts
        if genesis_host:
            blocks, endorsements = get_block_properties(
                chain_name, blocks, endorsements, b, block_header, block_operations
            )
        # Only the genesis host collects properties about blocks before the actualy workload
        if block_lvl < start_lvl:
            block_lvl += 1
            continue

        for op in block_transactions:
            # The operation in the block is in the dict of operations from the log
            if op["hash"] in operations:
                operations[op["hash"]]["block_hash"] = block_id
                operations[op["hash"]]["block_level"] = block_lvl
                operations[op["hash"]]["ts_block"] = block_ts
            # The operation in the block is NOT in the dict of operations from the log
            else:
                continue

            index = 0
            confirmed = False
            # Check status of operation
            for c, status in enumerate(op["contents"]):
                confirmed = False
                if status["metadata"]["operation_result"]["status"] == "applied":
                    confirmed = True

                if status["metadata"]["operation_result"]["status"] == "failed":
                    index = c
            if confirmed:
                # Set status to 'confirmed' = True
                operations[op["hash"]]["st_confirmed"] = confirmed
                # Calculate the transaction latency, that is the time period between operation submission at the client and the block timestamp
                operations[op["hash"]]["pt_trx_latency"] = (
                    block_U_ts - operations[op["hash"]]["u_ts_client_init"]
                )
                ops_confirmed += 1
                # ops_confirmed += len(block_ops_dict[op]["contents"])
            else:
                # Set status to confirmed = False
                operations[op["hash"]]["st_confirmed"] = confirmed
                # If not confirmed, store the error message
                errors = op["contents"][index]["metadata"]["operation_result"]["errors"]
                # Save the exact error message in the status
                operations[op["hash"]]["st_errors"] = errors

                ops_failed_block += 1
                # ops_failed_block += len(block_ops_dict[op]["contents"])
                # Print the error message
                print(
                    f'(OP {operations[op["hash"]]["op_type"]}_{operations[op["hash"]]["op_send_rate_lvl"]}.'
                    + f'{operations[op["hash"]]["op_first"]}-{operations[op["hash"]]["op_last"]}): Contract validation failed: {errors[0]["id"]}'
                )

        block_lvl += 1

    # After all operations have been checked, print out all 'unconfirmed' operations
    for op in operations:
        if operations[op]["st_propagated"] and not operations[op]["st_confirmed"]:
            config_log(
                hostname, "op_check_in_block", log_dir, "/exp_summary.log", True, True
            )
            logging.info(f"\nOperation: {op} not in blockchain, -> not confirmed")
            config_log()

    return operations, blocks, endorsements, ops_confirmed, ops_failed_block


# Get all necessary information about each operation out of the blockchain, by scanning every block for each operation that has been sent
def get_block_after_wl(
    log_dir: str,
    tezos_rpc_port: int,
    chain_name: str,
):

    blocks = []
    endorsements = []

    # initialize a new connection to the node, to get the newest head block
    tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")
    # Get level of the head/newest block
    head_lvl = tezos_client.shell.block.level()

    former_bl_lvl = read_former_block_lvl(log_dir, head_lvl)

    # Starting level
    block_lvl = former_bl_lvl + 1

    # Iterate from the lowest block level (lowest op branch) to the current head level over every block
    while block_lvl <= head_lvl:

        # Get the whole block
        b = tezos_client.shell.blocks[block_lvl]
        # Get the block header
        block_header = b.header()

        # Get a list of all operations of the block
        block_operations = b.operations()  # type: ignore

        # Retrieves all block properties and stores them in 'blocks' and 'endorsements' lists of dicts
        blocks, endorsements = get_block_properties(
            chain_name, blocks, endorsements, b, block_header, block_operations
        )
        block_lvl += 1

    return blocks, endorsements


## >>> Only executed by one of the hosts <<< ##
# Retrieve all necessary information about every block
def get_block_properties(
    chain_name: str,
    blocks: list,
    endorsements: list,
    block,
    b_header,
    b_operations,
):

    # Get the block
    b = block
    # Get the block timestamp
    b_timestamp = b_header["timestamp"].rstrip("Z")  # type: ignore
    # Get the block chain ID (every experiment round has a unique chain ID)
    b_chain_id = b_header["chain_id"]  # type: ignore
    # Get the block level (double check with index)
    b_level = b_header["level"]  # type: ignore
    # Get the block hash (unique identifier over all blocks and over all experiments)
    b_hash = b_header["hash"]  # type: ignore
    # Get the block baking priority (0: the baker with priority 0 baked the block and no penality block delay,
    # non 0: a time penalty / block delay per priority, differing from 0, is induced)
    b_priority = b_header["priority"]  # type: ignore
    # Get more metadata of the block
    b_metadata = b.metadata()
    # Get the baker of the block (public_key_hash)
    b_baker_pkh = b_metadata["baker"]  # type: ignore
    # Get the amount of milligas the baker consumed for this block
    b_baker_consumed_gas = int(b_metadata["consumed_gas"])  # type: ignore
    ## b_consumed_gas_op = [b_metadata["implicit_operations_results"][0]["balance_updates"][0]["consumed_milligas"]]  # type: ignore

    b_endorsements = []
    # Iterate over all endorsement operations ( index 0)
    for endorsm in b_operations[0]:  # type: ignore
        # Check if its really an endorsement operation with a slot
        if endorsm["contents"][0]["kind"] == "endorsement_with_slot":
            # Get the block level for which the endorsement is for, should be the current block level - 1
            b_end_level = endorsm["contents"][0]["endorsement"]["operations"]["level"]  # type: ignore
            # Get the slot for which the endorser was allowed to endorse
            b_end_slot = endorsm["contents"][0]["slot"]  # type: ignore
            # Get the endorser (public_key_hash)
            b_end_pkh = endorsm["contents"][0]["metadata"]["delegate"]  # type: ignore
            # Get the list of slots that the endorser got for this block
            b_end_slots = endorsm["contents"][0]["metadata"]["slots"]  # type: ignore
            # Append the above attributes as one endorsement dict object to the list of endorsements
            b_endorsements.append(
                {
                    "name_of_chain": chain_name,
                    "block_level": b_level,
                    "block_hash": b_hash,
                    "endorser_pkh": b_end_pkh,
                    "endorser_hostname": None,
                    "endorsment_for_level": b_end_level,
                    "endorser_slot": b_end_slot,
                    "endorser_slots": b_end_slots,
                }
            )
    # Get the total number/ sum of endorsements in this block
    b_number_end = len(b_endorsements)

    b_number_failed = 0
    b_number_applied = 0
    sum_consumed_milligas = 0
    # Iterate ov all transaction operations ( index 3)
    for transactions in b_operations[3]:  # type: ignore
        # Iterate also inside the bulk transaction
        for status in transactions["contents"]:
            if status["metadata"]["operation_result"]["status"] == "failed":
                # Increase the failed counter if the status of the transaction is 'failed'
                b_number_failed += 1
            if status["metadata"]["operation_result"]["status"] == "applied":
                # Increase the 'applied' / 'confirmed' counter if the status of the transaction is 'failed'
                b_number_applied += 1
                # Add the consumed amount of milligas to the total sum of it
                sum_consumed_milligas = sum_consumed_milligas + int(
                    status["metadata"]["operation_result"]["consumed_milligas"]
                )
    # Save the above retrieved attributes in a block object
    block = {
        "name_of_chain": chain_name,
        "block_level": b_level,
        "block_hash": b_hash,
        "block_timestamp": b_timestamp,
        "block_chain_id": b_chain_id,
        "baker_pkh": b_baker_pkh,
        "baker_hostname": "",
        "baker_priority": b_priority,
        "baker_consumed_milligas": b_baker_consumed_gas,
        "number_endorsements": b_number_end,
        "trx_number_confirmed": b_number_applied,
        "trx_sum_consumed_milligas": sum_consumed_milligas,
        "trx_number_failed": b_number_failed,
    }

    # Append the block object to the list of blocks
    blocks.append(block)

    # Extend the retrieved endorsement list to the global list of endorsements
    endorsements.extend(b_endorsements)

    return blocks, endorsements


## >>> Only executed by one of the hosts <<< ##
# Scan the entire blockchain and retrieve all necessary information about every block
def get_all_blocks(chain_name: str, tezos_rpc_port: int):
    # initialize a new connection to the node, to get the newest head block
    tezos_client = pytezos.using(shell=f"http://localhost:{tezos_rpc_port}")

    # Get level of the head/newest block
    head_lvl = tezos_client.shell.block.level()
    blocks = []
    endorsements = []
    l = 1
    # Iterate over every block starting with the first after the genesis at level 1 and incrementally by 1 block move up to the head block
    while l < head_lvl:
        # Get the block
        b = tezos_client.shell.blocks[1 + l]
        # Get the header of the block
        b_header = b.header()
        # Get the block timestamp
        b_timestamp = b_header["timestamp"].rstrip("Z")  # type: ignore
        # Get the block chain ID (every experiment round has a unique chain ID)
        b_chain_id = b_header["chain_id"]  # type: ignore
        # Get the block level (double check with index)
        b_level = b_header["level"]  # type: ignore
        # Get the block hash (unique identifier over all blocks and over all experiments)
        b_hash = b_header["hash"]  # type: ignore
        # Get the block baking priority (0: the baker with priority 0 baked the block and no penality block delay,
        # non 0: a time penalty / block delay per priority, differing from 0, is induced)
        b_priority = b_header["priority"]  # type: ignore
        # Get more metadata of the block
        b_metadata = b.metadata()
        # Get the baker of the block (public_key_hash)
        b_baker_pkh = b_metadata["baker"]  # type: ignore
        # Get the amount of milligas the baker consumed for this block
        b_baker_consumed_gas = int(b_metadata["consumed_gas"])  # type: ignore
        ## b_consumed_gas_op = [b_metadata["implicit_operations_results"][0]["balance_updates"][0]["consumed_milligas"]]  # type: ignore

        # Get the operations of the block
        b_operations = b.operations()
        b_endorsements = []
        # Iterate over all endorsement operations ( index 0)
        for endorsm in b_operations[0]:  # type: ignore
            # Check if its really an endorsement operation with a slot
            if endorsm["contents"][0]["kind"] == "endorsement_with_slot":
                # Get the block level for which the endorsement is for, should be the current block level - 1
                b_end_level = endorsm["contents"][0]["endorsement"]["operations"]["level"]  # type: ignore
                # Get the slot for which the endorser was allowed to endors
                b_end_slot = endorsm["contents"][0]["slot"]  # type: ignore
                # Get the endorser (public_key_hash)
                b_end_pkh = endorsm["contents"][0]["metadata"]["delegate"]  # type: ignore
                # Get the list of slots that the endorser got for this block
                b_end_slots = endorsm["contents"][0]["metadata"]["slots"]  # type: ignore
                # Append the above attributes as one endorsement dict object to the list of endorsements
                b_endorsements.append(
                    {
                        "name_of_chain": chain_name,
                        "block_level": b_level,
                        "block_hash": b_hash,
                        "endorser_pkh": b_end_pkh,
                        "endorser_hostname": None,
                        "endorsment_for_level": b_end_level,
                        "endorser_slot": b_end_slot,
                        "endorser_slots": b_end_slots,
                    }
                )
        # Get the total number/ sum of endorsements in this block
        b_number_end = len(b_endorsements)

        b_number_failed = 0
        b_number_applied = 0
        sum_consumed_milligas = 0
        # Iterate ov all transaction operations ( index 3)
        for transactions in b_operations[3]:  # type: ignore
            # Iterate also inside the bulk transaction
            for status in transactions["contents"]:
                if status["metadata"]["operation_result"]["status"] == "failed":
                    # Increase the failed counter if the status of the transaction is 'failed'
                    b_number_failed += 1
                if status["metadata"]["operation_result"]["status"] == "applied":
                    # Increase the 'applied' / 'confirmed' counter if the status of the transaction is 'failed'
                    b_number_applied += 1
                    # Add the consumed amount of milligas to the total sum of it
                    sum_consumed_milligas = sum_consumed_milligas + int(
                        status["metadata"]["operation_result"]["consumed_milligas"]
                    )
        # Save the above retrieved attributes in a block object
        block = {
            "name_of_chain": chain_name,
            "block_level": b_level,
            "block_hash": b_hash,
            "block_timestamp": b_timestamp,
            "block_chain_id": b_chain_id,
            "baker_pkh": b_baker_pkh,
            "baker_hostname": "",
            "baker_priority": b_priority,
            "baker_consumed_milligas": b_baker_consumed_gas,
            "number_endorsements": b_number_end,
            "trx_number_confirmed": b_number_applied,
            "trx_sum_consumed_milligas": sum_consumed_milligas,
            "trx_number_failed": b_number_failed,
        }

        # Append the block object to the list of blocks
        blocks.append(block)

        # Extend the retrieved endorsment list to the global list of endorsements
        endorsements.extend(b_endorsements)

        # Increment to the next block level
        l += 1
    return blocks, endorsements
