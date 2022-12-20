import sys
import time
import glob
from functools import wraps

sys.path.append("/home/ubuntu/scripts")

from file_handler import load_json_file
from parse_system_logs import parse_system_log
from operation_constants import *
import parse_blockchain
from file_handler import export_csv_file


def combine_csv(
    dir_path: str,
    file_name: str,
):
    # Search for all experiment and log-file_name specific csv files
    file_list = glob.glob(f"{dir_path}/{file_name}_*.csv")
    first = True
    # Combine all csv files from the glob and keep the headers from the first file
    with open(f"{dir_path}/{file_name}.csv", "wb") as fileout:
        for filepath in file_list:
            if first:
                # first file with headers:
                with open(
                    filepath,
                    "rb",
                ) as filein:
                    fileout.write(filein.read())
                first = False
            else:
                # rest of the files without headers:
                with open(filepath, "rb") as filein:
                    # skip the header
                    next(filein)
                    fileout.write(filein.read())


def timing(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time

    return wrap


# extract host specific workload and convert to ordered list
def extract_host_workload(workload_protocol, hostname: str):
    workload_host = []
    for lvl, rate in workload_protocol["workload_plan"][hostname].items():
        workload_host.append([int(lvl.split("_")[3]), rate, sum(rate)])
    workload_host.sort(key=lambda lvl: lvl[0], reverse=False)
    return workload_host


def main():

    # Tezos log directory
    log_dir = sys.argv[1]  # e.g. "/home/ubuntu/tezos-logs"

    # Tezos workload directory
    workload_dir = sys.argv[2]  # e.g. "/home/ubuntu/tezos-accounts"

    # Inventory Hostname
    hostname = sys.argv[3]

    # Name of chain/experiment
    chain_name = sys.argv[4]

    # last rate_ops_lvl
    last_workload_lvl = int(sys.argv[5])

    # Hostname of the genesis host
    genesis_hostname = sys.argv[6]
    # Set genesis_host to true if this host is the genesis host
    if genesis_hostname == hostname:
        genesis_host = True
    else:
        genesis_host = False

    # RPC port to communicate with node
    tezos_rpc_port = int(sys.argv[7])

    # Load workload file
    workload_protocol = load_json_file(f"{workload_dir}/", f"workload_protocol")

    # extract host specific workload and convert to ordered list
    workload_host = extract_host_workload(workload_protocol, hostname)

    sys_log_start = time.time()
    # Parse the whole system_log and separate it into one log per attribute and export to csv
    parse_system_log(log_dir, "system_log", chain_name, hostname)
    print(f"sys_log parser time: {time.time()-sys_log_start}")

    if workload_host[last_workload_lvl][2] > 0:

        # Combine the operation logs of the different workloads / workload levels
        combine_logs_start = time.time()
        combine_csv(log_dir, "operations")

        print(f"combine logs time: {time.time()-combine_logs_start}")

        if genesis_host:
            # Check if there are any missed blocks with transactions from other hosts after the genesis host completed the last workload
            get_block_start = time.time()
            (blocks, endorsements,) = parse_blockchain.get_block_after_wl(
                log_dir,
                tezos_rpc_port,
                chain_name,
            )
            get_block_end = time.time()

            export_csv_file(f"{log_dir}/", f"blocks_last", blocks, from_type="dict")
            export_csv_file(
                f"{log_dir}/",
                f"endorsements_last",
                endorsements,
                from_type="dict",
            )
            # Combine the blocks and endorsements logs of the different workloads / workload levels
            combine_bc_start = time.time()
            combine_csv(log_dir, "blocks")
            combine_csv(log_dir, "endorsements")

            print(
                f"get_block_after_wl time: {get_block_end - get_block_start}"
                f"blockchain combine logs (genesis host only): {time.time()-combine_bc_start}"
            )


if __name__ == "__main__":
    main()
