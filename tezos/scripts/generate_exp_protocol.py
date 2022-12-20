import random
import sys
import os

from datetime import datetime

sys.path.append(f"{os.getcwd()}/tezos/scripts")

from file_handler import load_yaml_file
from file_handler import export_json_file
from file_handler import export_csv_file


def gen_random_number(min, max):
    random_number_seed = random.getstate()
    random_number = random.randint(min, max)
    # restore_random_number = random.setstate(random_number_seed)
    return (random_number, random_number_seed)


def gen_exp_protocol(
    vm_prefix: str,
    chain_name: str,
    min_random_nodes_exp: int,
    max_random_nodes_exp: int,
    experiments_dir: str,
):

    # Read inventory.yaml file to save the VM flavor properties/variables
    inventory = load_yaml_file(f"{os.getcwd()}/inventory/", f"{vm_prefix}_inventory")

    # Read hardware_info.yaml file to save the VM hardware info/properties
    hw_info = load_yaml_file(f"{experiments_dir}/", f"{vm_prefix}_hardware_info")

    # Read tezos vars to get protocol constants
    tezos_vars = load_yaml_file(f"{os.getcwd()}/roles/tezos/vars/", "main")

    # Read benchmark vars to get benchmark config
    benchmark_vars = load_yaml_file(f"{os.getcwd()}/roles/benchmark/vars/", "main")

    # Generate a random number of nodes per experiment
    random_node_number_and_seed = gen_random_number(
        min_random_nodes_exp, max_random_nodes_exp
    )
    # randomly generated number of nodes per experiment
    number_nodes_exp = random_node_number_and_seed[0]
    # seed to regenerate the same random number
    number_nodes_exp_seed = random_node_number_and_seed[1]
    print(
        f"The number of nodes in this experiment(range: {min_random_nodes_exp} - {max_random_nodes_exp}): {number_nodes_exp}"
    )

    # Generate random block frequency
    random_min_block_delay_and_seed = gen_random_number(
        benchmark_vars["min_rd_min_block_delay"],
        benchmark_vars["max_rd_min_block_delay"],
    )
    minimal_block_delay = random_min_block_delay_and_seed[0]
    minimal_block_delay_seed = random_min_block_delay_and_seed[1]
    # If random minimal block delay is manually overwritten
    if tezos_vars["protocol_constants"]["minimal_block_delay"] is not None:
        minimal_block_delay = int(
            tezos_vars["protocol_constants"]["minimal_block_delay"]
        )
        minimal_block_delay_seed = ""

    ## Keeping the same ratios as the mainnet constants
    min_time_between_blocks = 2 * minimal_block_delay
    # If min_time_between_blocks is manually overwritten
    if tezos_vars["protocol_constants"]["time_between_blocks"][0] is not None:
        min_time_between_blocks = int(
            tezos_vars["protocol_constants"]["time_between_blocks"][0]
        )
    print(
        f"The minimal time/delay between blocks in this experiment: {minimal_block_delay}"
    )

    ## ## Keeping the same ratios as the mainnet constants.
    # Notice: We multiply here with the min_time_between_blocks not with minimal_block_delay, thus only by a factor of (2/3)
    block_delay_per_priority = int((2 / 3) * min_time_between_blocks)
    # If block_delay_per_priority is manually overwritten
    if tezos_vars["protocol_constants"]["time_between_blocks"][1] is not None:
        block_delay_per_priority = int(
            tezos_vars["protocol_constants"]["time_between_blocks"][1]
        )

    delay_per_missing_endorsement = int(block_delay_per_priority / 10)
    # If delay_per_missing_endorsement is manually overwritten
    if tezos_vars["protocol_constants"]["delay_per_missing_endorsement"] is not None:
        delay_per_missing_endorsement = int(
            tezos_vars["protocol_constants"]["delay_per_missing_endorsement"]
        )

    # Generate random hard gas limit per block = block size
    random_gas_limit_and_seed = gen_random_number(
        benchmark_vars["min_rd_gas_limit"], benchmark_vars["max_rd_gas_limit"]
    )
    block_gas_limit = random_gas_limit_and_seed[0]
    block_gas_limit_seed = random_gas_limit_and_seed[1]
    # If block_gas_limit is manually overwritten
    if tezos_vars["protocol_constants"]["hard_gas_limit_per_block"] is not None:
        block_gas_limit = int(
            tezos_vars["protocol_constants"]["hard_gas_limit_per_block"]
        )
        block_gas_limit_seed = ""
    print(f"The hard gas limit/ blocksize in this experiment: {block_gas_limit}")

    # If the gas limit per block is lower than the default gas limit per operation, set the gas limit per op to that of the block
    hard_gas_limit_per_op_default = int(
        tezos_vars["protocol_constants"]["hard_gas_limit_per_operation"]
    )
    if block_gas_limit < hard_gas_limit_per_op_default:
        hard_gas_limit_per_op = block_gas_limit
    else:
        hard_gas_limit_per_op = hard_gas_limit_per_op_default

    # If the gas limit per block is lower than the default STORAGE gas limit per operation, set the storage limit per op to that of the block
    hard_storage_limit_per_op_default = int(
        tezos_vars["protocol_constants"]["hard_storage_limit_per_operation"]
    )
    hard_storage_limit_per_operation = hard_storage_limit_per_op_default

    # Set the number of bakers for the experiment based on the specified fraction of bakers of all nodes
    number_of_bakers = int(
        float(benchmark_vars["fraction_of_bakers"]) * number_nodes_exp
    )
    # If the fraction is too low and results in a number of bakers below 4, it is set to the minimum of 4
    if number_of_bakers < 4:
        number_of_bakers = 4

    # Sets the maximum number of endorsers per block to 80% of the number of bakers - If the number of endorsers/bakers is below 3/4 * endorsers_per_block , the next block is delayed.
    endorsers_per_block = int(0.8 * number_of_bakers)
    # If endorsers_per_block is manually overwritten, can't be set higher than bakers/endorsers in the network
    if (
        tezos_vars["protocol_constants"]["endorsers_per_block"] is not None
        and int(tezos_vars["protocol_constants"]["endorsers_per_block"])
        <= number_of_bakers
    ):
        endorsers_per_block = int(
            tezos_vars["protocol_constants"]["endorsers_per_block"]
        )

    # Sets the initial_endorsers
    initial_endorsers = int(0.75 * endorsers_per_block)
    # If initial_endorsers is manually overwritten, can't be set higher than endorsers_per_block
    if (
        tezos_vars["protocol_constants"]["initial_endorsers"] is not None
        and int(tezos_vars["protocol_constants"]["initial_endorsers"])
        <= endorsers_per_block
    ):
        initial_endorsers = int(tezos_vars["protocol_constants"]["initial_endorsers"])

    # Define the parameters for the synchronisation heuristic (see: https://tezos.gitlab.io/shell/sync.html)
    # Set the multiplication factor for the chain validation latency
    latency_factor = int(tezos_vars["latency_factor"])
    # chain validation latency (int[0, 2^16-1]) is the time interval (in seconds) used to determine, if a peer is synchronized with a chain.
    # For instance, a peer whose known head has a timestamp T is considered synchronized if T >= now - latency.
    # This parameter depends on the baking rate and the latency of the network.
    chain_val_latency = latency_factor * minimal_block_delay
    if chain_val_latency > (2**16) - 1:
        chain_val_latency = (2**16) - 1
    # synchronisation_threshold (int[0,255]) The minimal number of peers this peer should be synchronized with in order to be bootstrapped.
    # After the bootstrap phase this value is changed
    synchronisation_threshold = 0

    vm_hardware_properties = {
        "vm_hardware_properties": {
            "flavor_name": inventory["all"]["vars"]["vm_flavor"]["flavor_name"],
            # "description": ram_description,
            "ram_size_mb": inventory["all"]["vars"]["vm_flavor"]["flavor_ram"],
            # "vendor": ram_vendor,
            "cpu_architecture": hw_info["Architecture"],
            "cpu_s": inventory["all"]["vars"]["vm_flavor"]["flavor_vcpu"],
            "cpu_mhz": hw_info["CPU MHz"],
            "cpu_threads_per_core": hw_info["Thread(s) per core"],
            "cpu_cores_per_socket": hw_info["Core(s) per socket"],
            "cpu_sockets": hw_info["Socket(s)"],
            "cpu_numa_nodes": hw_info["NUMA node(s)"],
            "cpu_vendor": hw_info["Vendor ID"],
            "cpu_family": hw_info["CPU family"],
            "cpu_model": hw_info["Model"],
            "cpu_model_name": hw_info["Model name"],
            "cpu_stepping": hw_info["Stepping"],
            "cpu_bogo_mips": hw_info["BogoMIPS"],
            "cpu_hypervisor_vendor": hw_info["Hypervisor vendor"],
            "cpu_l1d_cache": hw_info["L1d cache"],
            "cpu_l1i_cache": hw_info["L1i cache"],
            "cpu_l2_cache": hw_info["L2 cache"],
            "cpu_l3_cache": hw_info["L3 cache"],
        },
    }
    experiment_vars = {
        "random_variables": {
            "number_nodes_exp": number_nodes_exp,
            "minimal_block_delay": minimal_block_delay,  # Minimal block delay if block priority = 0 [sec]
            "block_gas_limit": block_gas_limit,  # Max gas limit per block --> BLOCKSIZE
        },
        "dependent_on_random_variables": {
            "initial_endorsers_per_block": initial_endorsers,
            "maximum_endorsers_per_block": endorsers_per_block,
            "min_time_between_blocks": min_time_between_blocks,  # Minimal time between blocks priority != 0 [sec]
            "block_delay_per_priority": block_delay_per_priority,  # Block delay per block priority [sec]
            "delay_per_missing_endorsement": delay_per_missing_endorsement,  # Delay per missing endorsement [sec]
            "chain_val_latency": chain_val_latency,
        },
        "non-random_variables": {
            "fraction_of_bakers": benchmark_vars["fraction_of_bakers"],
            "number_of_bakers": number_of_bakers,
            "number_of_endorsers": number_of_bakers,
            "chain_val_latency_factor": latency_factor,
            "chain_val_sync_threshold": synchronisation_threshold,
            "trx_amount": benchmark_vars["trx_amount"],
            "blocks_to_run": benchmark_vars["blocks_to_run"],
        },
    }

    # see http://tezos.gitlab.io/active/consensus.html
    constants = {
        "protocol_constants": {
            # Number of cycles for freezing security deposits and rewards.
            "preserved_cycles": tezos_vars["protocol_constants"]["preserved_cycles"],
            # Number of blocks per consensus cycle.
            "blocks_per_cycle": tezos_vars["protocol_constants"]["blocks_per_cycle"],
            # Number of blocks between seed nonce commitments.
            "blocks_per_commitment": tezos_vars["protocol_constants"][
                "blocks_per_commitment"
            ],
            # Number of blocks between roll snapshots.
            "blocks_per_roll_snapshot": tezos_vars["protocol_constants"][
                "blocks_per_roll_snapshot"
            ],
            # Number of blocks per voting period.
            "blocks_per_voting_period": tezos_vars["protocol_constants"][
                "blocks_per_voting_period"
            ],
            # Target time between blocks in seconds.
            "time_between_blocks": list(
                (f"{min_time_between_blocks}", f"{block_delay_per_priority}")
            ),
            # (Granada, v010) Actual expected time between blocks, time_between_blocks stays unchanged.
            "minimal_block_delay": f"{minimal_block_delay}",
            # Maxumber of endorsing slots
            "endorsers_per_block": endorsers_per_block,
            # Max gas limit per single operation.
            "hard_gas_limit_per_operation": f"{hard_gas_limit_per_op}",
            # Max gas limit per block --> BLOCKSIZE
            "hard_gas_limit_per_block": f"{block_gas_limit}",
            # F Threshold for message nonce complexity. aka node identity difficulty
            "proof_of_work_threshold": tezos_vars["protocol_constants"][
                "proof_of_work_threshold"
            ],
            # 6000000000 Amount of Tezos per roll.
            "tokens_per_roll": tezos_vars["protocol_constants"]["tokens_per_roll"],
            # 125000 Rewards for publishing a seed nonce.
            "seed_nonce_revelation_tip": tezos_vars["protocol_constants"][
                "seed_nonce_revelation_tip"
            ],
            # F Origination storage requirement in bytes.
            "origination_size": tezos_vars["protocol_constants"]["origination_size"],
            # 640000000 Baker security deposit in tez.
            "block_security_deposit": tezos_vars["protocol_constants"][
                "block_security_deposit"
            ],
            # 2500000 Endorser security deposit per slot in tez.
            "endorsement_security_deposit": tezos_vars["protocol_constants"][
                "endorsement_security_deposit"
            ],
            # baking_reward_per_endorsement
            "baking_reward_per_endorsement": tezos_vars["protocol_constants"][
                "baking_reward_per_endorsement"
            ],
            # Block endorsing reward per slot
            "endorsement_reward": tezos_vars["protocol_constants"][
                "endorsement_reward"
            ],
            # Max gas limit for storage spent by an operation.
            "hard_storage_limit_per_operation": f"{hard_storage_limit_per_operation}",
            # Gas costs per data byte.
            "cost_per_byte": tezos_vars["protocol_constants"]["cost_per_byte"],
            # (Babylon, v005) Minimum threshold for voting period quorum in centile.
            "quorum_min": tezos_vars["protocol_constants"]["quorum_min"],
            # (Babylon, v005) Maximum threshold for voting period quorum in centile.
            "quorum_max": tezos_vars["protocol_constants"]["quorum_max"],
            # (Babylon, v005) Minimum quorum to accept proposals in centile (i.e. 5% = 500).
            "min_proposal_quorum": tezos_vars["protocol_constants"][
                "min_proposal_quorum"
            ],
            # F Number of initial endorsers per block
            "initial_endorsers": initial_endorsers,
            # Delay delay per (missed) endorsement in seconds
            "delay_per_missing_endorsement": f"{delay_per_missing_endorsement}",
            # (Granada, v010) Subsidy amount.
            "liquidity_baking_subsidy": tezos_vars["protocol_constants"][
                "liquidity_baking_subsidy"
            ],
            # (Granada, v010) Block at which liquidity baking stops.
            "liquidity_baking_sunset_level": tezos_vars["protocol_constants"][
                "liquidity_baking_sunset_level"
            ],
            # (Granada, v010) Threshold to disable liquidity baking.
            "liquidity_baking_escape_ema_threshold": tezos_vars["protocol_constants"][
                "liquidity_baking_escape_ema_threshold"
            ],
        }
    }

    random_gen_seeds = {
        "seeds_of_random_numbers": {
            "number_nodes_exp": str(number_nodes_exp_seed),
            "minimal_block_delay": str(minimal_block_delay_seed),
            "block_gas_limit": str(block_gas_limit_seed),
        }
    }

    workload_levels = {
        "workload_levels": benchmark_vars["workload_levels"][
            int(benchmark_vars["first_workload_lvl"]) : int(
                benchmark_vars["last_workload_lvl"]
            )
            + 1
        ]
    }

    experiment_uid = {
        "name_of_chain": chain_name,
        "ts_creation_of_protocol": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }

    experiment_protocol = {
        "experiment_protocol": {
            **experiment_uid,
            **experiment_vars,
            **constants,
            **vm_hardware_properties,
            **random_gen_seeds,
        }
    }

    # Export the experiment protocol to json file
    export_json_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_experiment_protocol",
        experiment_protocol,
    )

    ## Create CSV files for database tables
    # Export vm_hardware_properties to csv
    export_csv_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_vm_hardware_properties",
        [{**experiment_uid, **vm_hardware_properties["vm_hardware_properties"]}],
        from_type="dict",
    )

    # Export experiment_vars to csv
    export_csv_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_experiment_vars",
        [
            {
                **experiment_uid,
                **experiment_vars["random_variables"],
                **experiment_vars["dependent_on_random_variables"],
                **experiment_vars["non-random_variables"],
            }
        ],
        from_type="dict",
    )

    # Export protocol_constants to csv
    export_csv_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_protocol_constants",
        [{**experiment_uid, **constants["protocol_constants"]}],
        from_type="dict",
    )


def main():
    # Name of the chain, could be a name plus and ID for every experiment round
    chain_name = sys.argv[1]
    # Minimal number of nodes per experiment (fix value)
    min_random_nodes_exp = int(sys.argv[2])
    # Maximal number of nodes per experiment (depends on number of VMs available)
    max_random_nodes_exp = int(sys.argv[3])

    # Prefix/name of the virtual machines as registered in the openstack cloud / inventory
    vm_prefix = sys.argv[4]  # e.g. "tezos"

    experiments_dir = sys.argv[5]

    # Generate experiment protocol and set number of accounts equal to number of nodes per experiment
    gen_exp_protocol(
        vm_prefix,
        chain_name,
        min_random_nodes_exp,
        max_random_nodes_exp,
        experiments_dir,
    )


if __name__ == "__main__":
    main()
