import os
import sys

sys.path.append(f"{os.getcwd()}/tezos/scripts")

from file_handler import load_json_file
from file_handler import export_json_file
from pytezos import pytezos


def gen_key():
    key = pytezos.key.generate(export=False)
    # print(f"public key hash: {key.public_key_hash()}")
    # print{"public_key": key.public_key(), "secret_key": key.secret_key()}
    return key


# create json file of baker_accounts and return dict baker_accounts
def create_baker_accounts(vm_prefix: str, number_of_hosts: int, experiments_dir: str):
    creation_accounts = {}

    # generate new accounts and save required number of keypairs in creation_account dictionary
    for n in range(1, number_of_hosts + 1):
        key_pair = gen_key()
        creation_accounts[f"baker_account_{n}"] = {
            "public_key": key_pair.public_key(),
            "secret_key": key_pair.secret_key(),
            "public_key_hash": key_pair.public_key_hash(),
        }

    # create json file from dict
    export_json_file(
        f"{experiments_dir}/",
        f"{vm_prefix}_all_baker_accounts",
        creation_accounts,
    )

    return creation_accounts


# Copies the existing baker accounts to new file and keeps only the required accounts for this experiment
def copy_existing_b_accounts(
    chain_name: str,
    all_b_accounts: dict,
    first_gr_member: int,
    last_gr_member: int,
    experiments_dir: str,
):

    # Copy all baker account and delete all accounts not required for this experiment
    b_accounts = all_b_accounts.copy()
    for accounts in all_b_accounts.keys():
        if int(accounts.split("_")[2]) < first_gr_member or last_gr_member < int(
            accounts.split("_")[2]
        ):
            del b_accounts[accounts]

    # Create new baker account json file
    export_json_file(
        f"{experiments_dir}/{chain_name}/accounts/",
        f"{chain_name}_baker_accounts",
        b_accounts,
    )

    return b_accounts


def baker_accounts(
    vm_prefix: str,
    chain_name: str,
    number_of_hosts: int,
    number_baker_acc: int,
    new_b_accounts,
    first_gr_member: int,
    last_gr_member: int,
    experiments_dir: str,
):
    if new_b_accounts:
        # Generate new all_baker_accounts file
        all_b_accounts = create_baker_accounts(
            vm_prefix, number_of_hosts, experiments_dir
        )
    else:
        all_b_accounts = load_json_file(
            f"{experiments_dir}/", f"{vm_prefix}_all_baker_accounts"
        )
    # Extract the required accounts for this experiment
    if number_baker_acc < number_of_hosts:
        last_gr_member = first_gr_member + number_baker_acc - 1
    b_accounts = copy_existing_b_accounts(
        chain_name, all_b_accounts, first_gr_member, last_gr_member, experiments_dir
    )
    return b_accounts


def main():

    # Prefix/name of the virtual machines as registered in the openstack cloud / inventory
    vm_prefix = sys.argv[1]  # e.g. "tezos"

    # Name of the chain, could be a name plus and ID for every experiment round
    chain_name = sys.argv[2]

    # Required number of baker accounts in total equals number of host
    number_of_hosts = int(sys.argv[3])
    number_baker_acc = int(sys.argv[4])

    # first and last group member/host of the network per experiment
    first_gr_member = int(sys.argv[5])
    last_gr_member = int(sys.argv[6])

    # Force generation of new baker accounts if set to 'True'
    new_b_accounts = sys.argv[7]
    if new_b_accounts.lower() == "false":
        new_b_accounts = False
    elif new_b_accounts.lower() == "true":
        new_b_accounts = True

    experiments_dir = sys.argv[8]

    baker_accounts(
        vm_prefix,
        chain_name,
        number_of_hosts,
        number_baker_acc,
        new_b_accounts,
        first_gr_member,
        last_gr_member,
        experiments_dir,
    )


if __name__ == "__main__":
    main()
