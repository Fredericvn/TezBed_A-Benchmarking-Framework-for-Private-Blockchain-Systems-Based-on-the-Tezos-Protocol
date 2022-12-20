import os
import sys
import pandas as pd
import re
import time
import csv

# sys.path.append(f"{os.getcwd()}/tezos/scripts")
sys.path.append("/home/ubuntu/scripts")

from file_handler import load_yaml_file
from file_handler import export_csv_file
from io import StringIO

# Slower variant
def parse_system_log_old(log_dir: str, file_name: str, chain_name: str, hostname: str):

    sys_log_desc = load_yaml_file(f"{log_dir}/", "sys_log_description")
    system_log_attr = sys_log_desc["system_log_attr"]
    main_labels = sys_log_desc["main_labels"]

    sort_logs_st = time.time()
    # Load system_log.csv
    files_path_system_log = load_log_file(log_dir, file_name)
    # Open and parse system_log.csv
    with open(files_path_system_log, "r") as system_log_file:
        # Iterate through each line
        for line in system_log_file.readlines():
            # Skip the 'RESET' and 'SEP' lines
            if line.startswith("RESET") or line.startswith("SEP"):
                continue

            # Check if any spaces are inside the brackets/name and remove those
            brackets = re.findall(r"\(\S*? \S*?\)", line)
            if brackets:
                line = f"{line.split('(')[0]}{brackets[0].replace(' ', '')}{line.split(')')[1]}"

            # Create a pandas dataframe out of the line
            dataframe = pd.read_csv(
                StringIO(line),
                sep=" ",
                header=None,
            )
            # Check to what attribute the line is assigned
            for attr in system_log_attr.keys():
                if line.startswith(attr):
                    # The 'NET' attribute has an extra 'upper layer for TCP / IP Stack' with extra labels, thus its separated
                    if attr == "NET" and line.find("upper") != -1:
                        attr = "NET_upper"
                    # Add the dataframe to the appropriate attribute list
                    system_log_attr[attr]["log"].append(dataframe)
                    break

    print(f"time to sort sys logs: {time.time() - sort_logs_st}")

    export_logs_st = time.time()
    # For all attributes do:
    for attr in system_log_attr:
        # Concatenate the list of dataframes to one single dataframe
        df_complete = pd.concat(system_log_attr[attr]["log"])
        # Add the appropriate labels to the dataframe
        df_complete.columns = main_labels + system_log_attr[attr]["labels"]
        # Add the name_of_chain and the hostname to the dataframe
        df_complete.insert(0, "name_of_chain", chain_name)
        df_complete.insert(1, "hostname", hostname)
        # df_complete.insert(
        #     2, "datetime", df_complete[["date", "time"]].agg("T".join, axis=1)
        # )
        df_complete.drop("date", axis=1, inplace=True)
        df_complete.drop("time", axis=1, inplace=True)
        df_complete.drop("host", axis=1, inplace=True)
        # Export the dataframes to a csv per attribute/dataframe
        export_csv_file(f"{log_dir}/", f"system_log_{attr.lower()}", df_complete)
    print(f"time export sys logs: {time.time() - export_logs_st}")


def load_log_file(log_dir: str, file_name: str) -> str:
    files_path = f"{log_dir}/{file_name}.csv"
    os.makedirs(os.path.dirname(files_path), exist_ok=True)
    return files_path


# Fastest way to parse, sort, correct and output system logs
def parse_system_log(log_dir: str, file_name: str, chain_name: str, hostname: str):

    sys_log_desc = load_yaml_file(f"{log_dir}/", "sys_log_description")
    sys_log = sys_log_desc["system_log_attr"]
    main_labels = sys_log_desc["main_labels"]

    sort_logs_st = time.time()
    # Load system_log.csv
    files_path_system_log = load_log_file(log_dir, file_name)
    # Open and parse system_log.csv
    with open(files_path_system_log, "r") as system_log_file:
        # Iterate through each line
        for line in system_log_file.readlines():
            # Skip the 'RESET' and 'SEP' lines
            if line.startswith("RESET") or line.startswith("SEP"):
                continue

            # Check if any spaces are inside the brackets/name and remove those
            brackets = re.findall(r"\(\S*? \S*?\)", line)
            if brackets:
                line = f"{line.split('(')[0]}{brackets[0].replace(' ', '')}{line.split(')')[1]}"

            attr = line[0:3]
            # The 'NET' attribute has an extra 'upper layer for TCP / IP Stack' with extra labels, thus its separated
            if attr == "NET" and line.find("upper") != -1:
                attr = "NET_upper"

            sys_log[attr]["log"].append(line)

    for attr in sys_log:
        # Create raw, unlabeled csv files for each system log from the list of strings (tab separated)
        with open(
            f"{log_dir}/system_log_{attr.lower()}.csv", "w", newline=""
        ) as sys_log_file:
            wr = csv.writer(sys_log_file, delimiter=",", quoting=csv.QUOTE_MINIMAL)
            wr.writerows(csv.reader(sys_log[attr]["log"], delimiter=" "))

        # Read the CSV file back in (faster than direct read with pandas StringIO)
        df_sys_log = pd.read_csv(
            f"{log_dir}/system_log_{attr.lower()}.csv", sep=",", header=None
        )

        # Add the correct labels to the dataframe
        df_sys_log.columns = main_labels + sys_log[attr]["labels"]

        # Add the name_of_chain and the hostname to the dataframe
        df_sys_log.insert(0, "name_of_chain", chain_name)
        df_sys_log.insert(1, "hostname", hostname)

        # Delete the not required columns 'date', 'time' and 'host'
        df_sys_log.drop("date", axis=1, inplace=True)
        df_sys_log.drop("time", axis=1, inplace=True)
        df_sys_log.drop("host", axis=1, inplace=True)

        # Export the dataframes to a csv per attribute/dataframe
        export_csv_file(f"{log_dir}/", f"system_log_{attr.lower()}", df_sys_log)

    print(f"time to parse, sort and export sys logs: {time.time() - sort_logs_st}")
