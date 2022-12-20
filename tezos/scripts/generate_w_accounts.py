import os
import sys
import json

sys.path.append("/home/ubuntu/scripts")

from file_handler import load_json_file
from file_handler import export_json_file
from pytezos import pytezos


def gen_key():
    key = pytezos.key.generate(export=False)
    # print(f"public key hash: {key.public_key_hash()}")
    # print{"public_key": key.public_key(), "secret_key": key.secret_key()}
    return key


# Creates as many worker accounts as needed for this host
def create_worker_accounts(
    accounts_dir: str, number_worker_acc: int, all_w_accounts: list
):
    w = 1
    all_w_account_list = []
    while w <= number_worker_acc:
        keys = gen_key()
        all_w_account_list.append(
            {
                "sk": keys.secret_key(),
                "pk": keys.public_key(),
                "pkh": keys.public_key_hash(),
                "revealed": False,
            }
        )
        w += 1
    all_w_accounts = all_w_accounts + all_w_account_list
    export_json_file(f"{accounts_dir}/", f"all_worker_accounts", all_w_accounts)
    return all_w_accounts


# Copy the necessary number of worker accounts from the top of the list to an experiment specific worker account
def copy_existing_w_accounts(
    accounts_dir: str, number_worker_acc: int, all_w_accounts: list
):
    exp_w_accounts = all_w_accounts[0:number_worker_acc]
    return exp_w_accounts


# Create as many worker accounts necessary for the host and experiment
def worker_accounts(accounts_dir: str, number_worker_acc: int, new_w_accounts):
    # Check if worker_accounts exist
    files_path_all_w_accounts = f"{accounts_dir}/all_worker_accounts.json"
    all_w_accounts_exist = os.path.exists(files_path_all_w_accounts)
    # init
    all_w_accounts = []

    # If worker_accounts exist and the 'new_w_accounts' flag is 'false'
    if all_w_accounts_exist and not new_w_accounts:

        # Load existing worker accounts from file and count the number of accounts
        with open(files_path_all_w_accounts, "r") as input_file:
            all_w_accounts = json.load(input_file)
        account_counter = len(all_w_accounts)

        # If not enough accounts are available
        if account_counter < number_worker_acc:
            delta_w_acc = number_worker_acc - account_counter
            # Generate more worker_accounts and append them to the original list
            all_w_accounts = create_worker_accounts(
                accounts_dir, delta_w_acc, all_w_accounts
            )

    # If worker accounts don't exist or the 'new worker account' flag is set to TRUE
    elif not all_w_accounts_exist or new_w_accounts:

        # Create and save worker accounts (secret_key, public_key and public_key_hash)
        all_w_accounts = create_worker_accounts(
            accounts_dir, number_worker_acc, all_w_accounts
        )

    exp_w_accounts = copy_existing_w_accounts(
        accounts_dir, number_worker_acc, all_w_accounts
    )
    return exp_w_accounts


def create_destination_lists(accounts_dir: str, exp_w_accounts: list):

    # Create a list of all destinations (pkh)
    all_destinations = []
    for account in exp_w_accounts:
        all_destinations.append(account["pkh"])

    # Iterate over all accounts and add the list of destinations to it without the sender
    last_index = len(all_destinations) - 1
    for sender_i, account in enumerate(exp_w_accounts):
        if sender_i == 0:
            account["dest"] = all_destinations[sender_i + 1 :]
        elif sender_i == last_index:
            account["dest"] = all_destinations[:sender_i]
        else:
            before_sender = all_destinations[:sender_i]
            after_sender = all_destinations[sender_i + 1 :]
            account["dest"] = after_sender + before_sender

    export_json_file(
        f"{accounts_dir}/",
        f"exp_worker_accounts",
        exp_w_accounts,
    )
    export_json_file(
        f"{accounts_dir}/",
        f"exp_all_destinations",
        all_destinations,
    )
    return exp_w_accounts, all_destinations


def main():
    # scripts directory
    accounts_dir = sys.argv[1]

    # workload directory
    workload_dir = sys.argv[2]

    # Force generation of new baker accounts if set to 'True'
    new_w_accounts = sys.argv[3]
    if new_w_accounts.lower() == "false":
        new_w_accounts = False
    elif new_w_accounts.lower() == "true":
        new_w_accounts = True

    # Inventory Hostname
    hostname = sys.argv[4]

    workload_protocol = load_json_file(f"{workload_dir}/", "workload_protocol")

    # Number of blocks/cycles to run the workload
    blocks_to_run = workload_protocol["workload_properties"]["blocks_to_run"]

    # The number of worker accounts per node per experiment multiplied with the number of blocks to run / cycles
    number_worker_acc = (
        blocks_to_run
        * workload_protocol["funds_distribution"]["n_worker_acc_per_host"][hostname]
    )

    exp_worker_accounts = worker_accounts(
        accounts_dir, number_worker_acc, new_w_accounts
    )
    create_destination_lists(accounts_dir, exp_worker_accounts)


if __name__ == "__main__":
    main()
