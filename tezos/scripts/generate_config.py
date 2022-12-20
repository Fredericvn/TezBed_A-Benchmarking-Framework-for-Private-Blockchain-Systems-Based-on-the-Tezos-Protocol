import os
import json
import yaml
import sys
import math

from secrets import token_bytes

sys.path.append(f"{os.getcwd()}/tezos/scripts")

from file_handler import load_yaml_file
from file_handler import load_json_file
from file_handler import export_json_file

# pytezos docu: https://pytezos.org/quick_start.html
from pytezos import pytezos
from pytezos.crypto.encoding import base58_encode
from datetime import datetime, timezone


def gen_key():
    # generate a Tezos key pair
    key = pytezos.key.generate(export=False)
    return {"public_key": key.public_key(), "secret_key": key.secret_key()}


def get_genesis_vanity_chain_id():
    # generate a vanity id for the genesis block
    vanity_id = base58_encode(token_bytes(32), b"B").decode("utf-8")
    return vanity_id


# write the node config files
def write_config_file(
    vm_prefix: str,
    chain_name: str,
    first_gr_member: int,
    last_gr_member: int,
    min_nodes_exp: int,
    identity_difficulty,
    node_dir: str,
    log_dir: str,
    log_level: str,
    log_prettyprint,
    experiments_dir: str,
    tezos_p2p_port: int,
):

    # Generate a new key pair
    key_pair = gen_key()

    # Read inventory.yaml file and save the IP-addresses as bootstrap-peers
    inventory = load_yaml_file(f"{os.getcwd()}/inventory/", f"{vm_prefix}_inventory")

    ip_list = {}
    ip_list["all"] = inventory["all"]["hosts"]
    b_accounts_ip_list = []

    # Extract the IP addresses from the inventory file (only from THs participating in the network) and add them to the b_accounts_ip_list
    for hosts in ip_list["all"].keys():
        if first_gr_member <= int(hosts.split("_")[1]) <= last_gr_member:
            for ip_address in ip_list["all"][hosts].keys():
                b_accounts_ip_list.append(ip_list["all"][hosts][ip_address])

    # Read experiment protocol
    exp_protocol = load_json_file(
        f"{experiments_dir}/{chain_name}/",
        f"{chain_name}_experiment_protocol",
    )
    # Read chain_val_latency from experiment protocol
    chain_val_latency = exp_protocol["experiment_protocol"][
        "dependent_on_random_variables"
    ]["chain_val_latency"]
    # Read synchronization_threshold from experiment protocol
    synchronisation_threshold = exp_protocol["experiment_protocol"][
        "non-random_variables"
    ]["chain_val_sync_threshold"]

    min_connections = min_nodes_exp - 1 if min_nodes_exp - 1 < 20 else 20
    expected_connections = math.ceil((last_gr_member - first_gr_member) / 2)

    p2p = {
        "p2p": {
            "expected-proof-of-work": float(identity_difficulty),
            "bootstrap-peers": b_accounts_ip_list,
            "listen-addr": f"[::]:{tezos_p2p_port}",
            # "private-mode": True
            "limits": {
                "min-connections": min_connections,  # in number of peers
                "expected-connections": expected_connections  # in number of peers
                if (expected_connections > min_connections)
                else min_connections + 1,
                "backlog": 20,
                "max-incoming-connections": 20,  # in number of peers
                "max-connections": 2 * expected_connections + 1,  # in number of peers
                "max-download-speed": 10000,  # in KiB/s
            },
        }
    }

    if log_prettyprint:
        # If desired the node will only output the log at 'level' = 'notice' very-pretty-printed with JSON-Object over multiple lines to node.log
        log = {
            "log": {
                "output": log_dir + "/node.log",
                "level": "info",
                "rules": "client* -> debug; net -> debug; * -> notice",
            }
        }
    else:
        # The node will output the log at 'level' = 'notice' in JSON-Object-one-per-line to ext_node.log
        # and in pretty-printed-one-per-line compatible with RFC-5424 (or Syslog) to node.log
        log = {
            "internal-events": {
                "active_sinks": [
                    "file-descriptor-path://"
                    + log_dir
                    + "/ext_node.log?format=one-per-line&section-prefix=client*:debug&\
                                    section-prefix=net:debug&level-at-least=notice",
                    "file-descriptor-path://"
                    + log_dir
                    + "/node.log?format=pp&level-at-least="
                    + log_level,
                ]
            }
        }

    shell = {
        "shell": {
            "chain_validator": {
                "latency": chain_val_latency,
                "synchronisation_threshold": synchronisation_threshold,
            }
        }
    }

    network = {
        "network": {
            "genesis": {
                "block": get_genesis_vanity_chain_id(),
                "protocol": "Ps9mPmXaRzmzk35gbAYNCAw6UXdE2qoABTHbN2oEEc1qM7CwT9P",
                "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            },
            "genesis_parameters": {
                "values": {"genesis_pubkey": key_pair["public_key"]}
            },
            "chain_name": chain_name,
            "old_chain_name": chain_name,
            "incompatible_chain_name": "INCOMPATIBLE",
            "sandboxed_chain_name": f"SANDBOXED_{chain_name}",
        }
    }

    config = {"data-dir": node_dir, **p2p, **log, **shell, **network}

    # create config.json file
    export_json_file(
        f"{experiments_dir}/{chain_name}/configs/",
        f"{chain_name}_config",
        config,
    )

    # create genesis_account.json file
    export_json_file(
        f"{experiments_dir}/{chain_name}/accounts/",
        f"{chain_name}_genesis_account",
        key_pair,
    )


def main():
    # Prefix/name of the virtual machines as registered in the openstack cloud / inventory
    vm_prefix = sys.argv[1]

    # Name of the chain
    chain_name = sys.argv[2]

    # first and last group member/host of the network per experiment
    first_gr_member = int(sys.argv[3])
    last_gr_member = int(sys.argv[4])

    # Minimum number of nodes in experiment
    min_nodes_exp = int(sys.argv[5])

    # Expected Proof of Work difficulty of the generation of node identity, floating point number represents leading zeros
    identity_difficulty = sys.argv[6]

    # Node directory
    node_dir = sys.argv[7]

    # Log directory
    log_dir = sys.argv[8]

    # Log level, 'debug', 'info', 'notice', 'warning', 'error', or 'fatal'
    log_level = sys.argv[9]

    # print node.log prettyprint with realtime timestamp (default: JSON one-per-line with UNIX timestamp)
    log_prettyprint = sys.argv[10]
    if log_prettyprint.lower() == "false":
        log_prettyprint = False
    elif log_prettyprint.lower() == "true":
        log_prettyprint = True
    print(f"Prettyprinted: {log_prettyprint}")

    experiments_dir = sys.argv[11]

    tezos_p2p_port = int(sys.argv[12])

    write_config_file(
        vm_prefix,
        chain_name,
        first_gr_member,
        last_gr_member,
        min_nodes_exp,
        identity_difficulty,
        node_dir,
        log_dir,
        log_level,
        log_prettyprint,
        experiments_dir,
        tezos_p2p_port,
    )


if __name__ == "__main__":
    main()
