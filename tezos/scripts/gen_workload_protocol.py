import os
import sys
import math

sys.path.append(f"{os.getcwd()}/tezos/scripts")

from file_handler import load_json_file
from file_handler import export_json_file
from operation_constants import *
from itertools import cycle


def calc_capacity(block_gaslimit: int, minimal_block_delay: int):
    # Capacity in transactions per second, based on the block gas limit, the amount of gas one transaction requires and the minimal block delay
    capacity_tps = block_gaslimit / (minimal_block_delay * OPS_GAS_LIMIT)
    # Capacity in transactions per block, based on the block gas limit and the amount of gas one transaction requires
    capacity_tpb = block_gaslimit / OPS_GAS_LIMIT
    return capacity_tps, capacity_tpb


def calc_amount_of_tez_w(amount_of_tez_w: int):
    # TO DO: calculate the minimum amount of tez per worker based on the workload plan
    return amount_of_tez_w


def calc_workload_per_host_old(
    capacity_tps: float,
    number_nodes_exp: int,
    workload_levels,
    first_gr_member: int,
    last_gr_member: int,
    minimal_block_delay: int,
    vm_prefix: str,
):
    workload_list = []
    for lvl in workload_levels:
        workload_host = int(capacity_tps * (lvl / 100) / number_nodes_exp)
        workload_rest = math.ceil(capacity_tps * (lvl / 100) % number_nodes_exp)
        workload_list.append(
            {
                "lvl": lvl,
                "workload_host": workload_host,
                "workload_rest": workload_rest,
            }
        )
    n_worker_acc_per_host = {}
    workload_plan = {"workload_plan": {}}
    for hostnumber in range(first_gr_member, last_gr_member + 1):
        workload_host_plan = {}
        number_worker_acc = 0
        for wl in workload_list:
            # Check if there is a 'rest' from the modulo division and distribute it evenly to the first hosts in the group
            if wl["workload_rest"] > 0:
                workload_host = wl["workload_host"] + 1
                wl["workload_rest"] -= 1
            else:
                workload_host = wl["workload_host"]
            workload_host_plan.update({f"rate_ops_lvl_{wl['lvl']}": workload_host})
            # Take the last workload (ops/second in the last workload level)
            # and multiply it by the minimal block delay to derive the maximum number of worker accounts needed for that specific host
            if wl == workload_list[-1]:
                number_worker_acc = workload_host * minimal_block_delay
        workload_plan["workload_plan"][f"{vm_prefix}_{hostnumber}"] = {
            **workload_host_plan
        }
        n_worker_acc_per_host[f"{vm_prefix}_{hostnumber}"] = number_worker_acc
    number_worker_acc_host = {"n_worker_acc_per_host": {**n_worker_acc_per_host}}
    return workload_plan, number_worker_acc_host


def calc_workload_per_host(
    capacity_tps: float,
    capacity_tpb: float,
    number_nodes_exp: int,
    workload_levels,
    first_gr_member: int,
    last_gr_member: int,
    minimal_block_delay: int,
    vm_prefix: str,
):
    # Create a dict with the number of worker accounts needed per host
    n_worker_acc_per_host = {}

    # Create a workload plan dict with a list of the number of operations each host sends each second for each workload level
    workload_plan = {"workload_plan": {}}

    # Iterate through all hosts of the experiment
    for hostnumber in range(first_gr_member, last_gr_member + 1):
        # Create a workload plan (dict) for each host
        workload_host_plan = {}
        # Set the number of worker accounts per host to 0
        n_worker_acc_per_host[f"{vm_prefix}_{hostnumber}"] = 0

        for lvl in workload_levels:
            # Create a list with as many zeros as there are seconds in the minimal block delay
            workload_host_plan.update(
                {f"rate_ops_lvl_{lvl}": [0] * minimal_block_delay}
            )
        # Add each workload plan per host to the global workload plan
        workload_plan["workload_plan"][f"{vm_prefix}_{hostnumber}"] = {
            **workload_host_plan
        }
    # Make a list out of the hostnumbers
    hostnumber_list = list(range(first_gr_member, last_gr_member + 1))

    for lvl in workload_levels:
        # Set the capacity in transactions per block for the workload level
        lvl_capacity_tpb = int(capacity_tpb * (lvl / 100))
        # Set the capacity in transactions per second for the workload level
        lvl_capacity_tps = math.ceil(capacity_tps * (lvl / 100))

        list_shift = 0
        for seconds in range(minimal_block_delay):
            # Each second reset the remaining capacity in transactions per second for the workload level
            lvl_cap_tps = lvl_capacity_tps

            # Iterate indefinitely through the hostnumbers until either of the capacities is consumed
            # if the iteration was stopped in between, continue there, by shifting the list to the next element
            for i, hostnumber in cycle(
                enumerate(hostnumber_list[list_shift:] + hostnumber_list[:list_shift])
            ):
                if lvl_capacity_tpb > 0 and lvl_cap_tps > 0:
                    # consume one operation of the capacities and allocate it as workload to the host
                    lvl_capacity_tpb -= 1
                    lvl_cap_tps -= 1
                    workload_plan["workload_plan"][f"{vm_prefix}_{hostnumber}"][
                        f"rate_ops_lvl_{lvl}"
                    ][seconds] += 1
                    if lvl == workload_levels[-1]:
                        # Increase the number of required worker accounts for this host by 1
                        n_worker_acc_per_host[f"{vm_prefix}_{hostnumber}"] += 1

                    # if the iteration is not at the end of the list,
                    # calculate the correct list_shift for the next iteration.
                    if lvl_capacity_tpb == 0 or lvl_cap_tps == 0:
                        if i != number_nodes_exp - 1:
                            list_shift += i + 1
                            if list_shift >= number_nodes_exp:
                                list_shift -= number_nodes_exp
                        break
                else:
                    break

    number_worker_acc_host = {"n_worker_acc_per_host": {**n_worker_acc_per_host}}

    return workload_plan, number_worker_acc_host


def gen_workload_protocol(
    exp_protocol: dict,
    vm_prefix: str,
    first_gr_member: int,
    last_gr_member: int,
    amount_of_tez_b: int,
    amount_of_tez_w: int,
    workload_levels: list,
):

    number_nodes_exp = int(
        exp_protocol["experiment_protocol"]["random_variables"]["number_nodes_exp"]
    )

    block_gaslimit = int(
        exp_protocol["experiment_protocol"]["protocol_constants"][
            "hard_gas_limit_per_block"
        ]
    )

    minimal_block_delay = int(
        exp_protocol["experiment_protocol"]["protocol_constants"]["minimal_block_delay"]
    )

    number_of_bakers = int(
        exp_protocol["experiment_protocol"]["non-random_variables"]["number_of_bakers"]
    )

    blocks_to_run = int(
        exp_protocol["experiment_protocol"]["non-random_variables"]["blocks_to_run"]
    )

    capacity_tps, capacity_tpb = calc_capacity(block_gaslimit, minimal_block_delay)

    workload_plan, number_worker_acc_host = calc_workload_per_host(
        capacity_tps,
        capacity_tpb,
        number_nodes_exp,
        workload_levels,
        first_gr_member,
        last_gr_member,
        minimal_block_delay,
        vm_prefix,
    )

    amount_of_tez_w = calc_amount_of_tez_w(amount_of_tez_w)

    funds_accounts = calc_funds_of_accounts(
        number_of_bakers,
        number_nodes_exp,
        amount_of_tez_b,
        amount_of_tez_w,
        number_worker_acc_host,
        vm_prefix,
        first_gr_member,
        last_gr_member,
        blocks_to_run,
    )
    total_funds_baker_acc = funds_accounts[0]
    funds_worker_acc = funds_accounts[1]
    funds_baker_acc = funds_accounts[2]
    optimal_bulk_size, delay_distribution = calc_opt_bulk_size(
        block_gaslimit, number_nodes_exp
    )
    blocks_to_finish = calc_blocks_to_finish(
        optimal_bulk_size, number_worker_acc_host, blocks_to_run
    )

    funds_distribution = {
        "funds_distribution": {
            "funds_baker_acc": funds_baker_acc,
            "funds_worker_acc": funds_worker_acc,
            "optimal_bulk_size": optimal_bulk_size,
            "delay_distribution": delay_distribution,
            "blocks_to_finish": blocks_to_finish,
            **number_worker_acc_host,
            "total_funds_baker_acc": {**total_funds_baker_acc},
        }
    }
    workload_properties = {"workload_properties": {"blocks_to_run": blocks_to_run}}

    blockchain_properties = {
        "blockchain_properties": {
            "block_gas_limit": block_gaslimit,
            "minimal_block_delay": minimal_block_delay,
            "OPS_GAS_LIMIT": OPS_GAS_LIMIT,
            "capacity_tps": capacity_tps,
            "capacity_tpb": capacity_tpb,
        }
    }
    workload_protocol = {
        **blockchain_properties,
        **funds_distribution,
        **workload_properties,
        **workload_plan,
    }
    return workload_protocol


def calc_opt_bulk_size(block_gaslimit: int, number_nodes_exp: int):
    delay_distribution = False
    # The optimal bulk size, hence the number of funds-distribution-operations one baker should combine in one operation/bulk
    optimal_bulk_size = int((block_gaslimit / OPS_GAS_LIMIT) / number_nodes_exp)
    # If less operations fit in one block than number of nodes take part in the experiment, hence optimal bulk size < 1,
    # set bulk size to 1 and delay half of the funds distributions (every node with uneven hostnumber) to not exceed the block gas limit
    if optimal_bulk_size < 1:
        optimal_bulk_size = 1
        delay_distribution = True
    if optimal_bulk_size > MAX_OPS_BULK:
        optimal_bulk_size = MAX_OPS_BULK

    return optimal_bulk_size, delay_distribution


# Calculate how many blocks it theoretically takes to transfer funds from all baker accounts to all worker accounts
def calc_blocks_to_finish(
    optimal_bulk_size: int, number_worker_acc_host: dict, blocks_to_run: int
):
    blocks_to_finish = int(
        math.ceil(
            next(iter(number_worker_acc_host["n_worker_acc_per_host"].values()))
            / optimal_bulk_size
        )
        * 1.5
        * blocks_to_run
    )
    return blocks_to_finish


def calc_funds_of_accounts(
    number_of_bakers: int,
    number_nodes_exp: int,
    amount_of_tez_b: int,
    amount_of_tez_w: int,
    number_worker_acc_host: dict,
    vm_prefix: str,
    first_gr_member: int,
    last_gr_member: int,
    blocks_to_run: int,
):

    # Required number of worker accounts for all nodes in experiment together
    total_number_worker_acc = 0
    for number in number_worker_acc_host["n_worker_acc_per_host"].values():
        total_number_worker_acc += number

    # For every block/cycle to run we need fresh worker accounts
    total_number_worker_acc = total_number_worker_acc * blocks_to_run

    # If the desired amount of tez for the bakers exceeds the max supply limit divided by the number of bakers, then use the default amount for bakers
    if amount_of_tez_b > int(MAX_BOOTSTRAP_SUPPLY_TEZ / number_of_bakers):
        amount_of_tez_b = AMOUNT_OF_TEZ_B_DEFAULT

    # Default amount of tez per worker account
    if total_number_worker_acc > 0:
        max_amount_of_tez_w = int(
            (MAX_BOOTSTRAP_SUPPLY_TEZ - (number_of_bakers * amount_of_tez_b))
            / total_number_worker_acc
        )
    # No workers, no funds to distribute
    else:
        max_amount_of_tez_w = 0

    # If the desired amount of tez per worker exceeds the maximum available amount, set it to the maximum
    if amount_of_tez_w > max_amount_of_tez_w:
        amount_of_tez_w = max_amount_of_tez_w

    # The funds for the workers get equally distributed to all baker accounts, to later distribute it through them
    total_funds_baker_acc = {}
    for hostnumber in range(first_gr_member, last_gr_member + 1):
        total_funds_baker_acc[f"{vm_prefix}_{hostnumber}"] = amount_of_tez_b + int(
            amount_of_tez_w
            * number_worker_acc_host["n_worker_acc_per_host"][
                f"{vm_prefix}_{hostnumber}"
            ]
            * blocks_to_run
        )
    return total_funds_baker_acc, amount_of_tez_w, amount_of_tez_b


def main():

    # Prefix/name of the virtual machines as registered in the openstack cloud / inventory
    vm_prefix = sys.argv[1]  # e.g. "tezos"

    # Name of the chain, could be a name plus and ID for every experiment round
    chain_name = sys.argv[2]

    # first and last group member/host of the network per experiment
    first_gr_member = int(sys.argv[3])
    last_gr_member = int(sys.argv[4])

    # Required amount of tez per baker account
    amount_of_tez_b = int(sys.argv[5])
    # Required amount of tez per worker account
    amount_of_tez_w = int(sys.argv[6])

    # Send rate levels in % of the theoretical possible transaction throughput
    workload_levels = [int(x) for x in (sys.argv[7]).split(",")]

    experiments_dir = sys.argv[8]

    exp_protocol = load_json_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_experiment_protocol",
    )

    workload_protocol = gen_workload_protocol(
        exp_protocol,
        vm_prefix,
        first_gr_member,
        last_gr_member,
        amount_of_tez_b,
        amount_of_tez_w,
        workload_levels,
    )

    export_json_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_workload_protocol",
        workload_protocol,
    )


if __name__ == "__main__":
    main()
