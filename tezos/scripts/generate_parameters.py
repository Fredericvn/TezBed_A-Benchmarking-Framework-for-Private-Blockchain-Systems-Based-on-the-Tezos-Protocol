import os
import sys

sys.path.append(f"{os.getcwd()}/tezos/scripts")

from file_handler import load_json_file
from file_handler import export_json_file
from operation_constants import *

# Creates and write parameter.json file with funded baker and worker accounts
def write_parameters_file(chain_name: str, vm_prefix: str, experiments_dir: str):

    # Load the experiment workload protocol
    workload_protocol = load_json_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_workload_protocol",
    )
    total_funds_baker_acc = workload_protocol["funds_distribution"][
        "total_funds_baker_acc"
    ]

    # Load the experiment related BAKER accounts
    b_accounts = load_json_file(
        f"{experiments_dir}/{chain_name}/accounts/",
        f"{chain_name}_baker_accounts",
    )

    vm_prefix = f"{vm_prefix}_"
    b_accounts_list = [
        [
            b_accounts[b_acc]["public_key"],
            f"{total_funds_baker_acc[''.join([vm_prefix, b_acc.split('_')[2]])] * MLTP}",
        ]
        for b_acc in b_accounts.keys()
    ]
    accounts = {"bootstrap_accounts": b_accounts_list}

    # Load the constants from the experiment protocol
    exp_protocol = load_json_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_experiment_protocol",
    )
    constants = exp_protocol["experiment_protocol"]["protocol_constants"]

    # Output the final parameters json file
    parameters = {**accounts, **constants}
    export_json_file(
        f"{experiments_dir}/{chain_name}/configs/",
        f"{chain_name}_parameters",
        parameters,
    )


def main():

    # Name of the chain, could be a name plus and ID for every experiment round
    chain_name = sys.argv[1]

    # Prefix/name of the virtual machines as registered in the openstack cloud / inventory
    vm_prefix = sys.argv[2]  # e.g. "tezos"

    experiments_dir = sys.argv[3]

    # Call function to create parameters.json and baker account file
    write_parameters_file(chain_name, vm_prefix, experiments_dir)


if __name__ == "__main__":
    main()
