import os
import sys
import json
import ast
import jmespath
import time

sys.path.append("/home/ubuntu/scripts")

from file_handler import export_json_file

# workload_client.log
def parse_workload_client_log(log_dir: str, file_name: str, export_json: bool) -> list:

    # Load workload_client.log
    files_path_client_log = load_log_file(log_dir, file_name)
    # Open and parse workload_client.log
    with open(files_path_client_log, "r") as client_log_file:
        lines = []
        i = -1
        split_m = '"msg":{'
        split_q = '"'
        helpers = False
        properties = False
        convert = False
        para_block = False
        for line in client_log_file.readlines():
            # Strip whitespaces
            line = line.strip()
            # Pass/delete empty lines
            if line == "":
                continue
            # Handle the properties block
            if properties:
                if line.startswith(".key"):
                    line = f'"key":"{line.lstrip(".key").lstrip()}",'
                if line.startswith(".shell"):
                    line = (
                        '"shell":"'
                        + line.lstrip(".shell").lstrip().strip("['").strip("']")
                        + '",'
                    )
                if line.startswith(".block_id"):
                    line = f'"block_id":"{line.lstrip(".block_id").lstrip()}"'
                if line == "Payload":
                    line = '},"Payload":'
                    properties = False
            if line == "Properties":
                line = '{"Properties":{'
                properties = True

            # Pass/Delete the client CLI helpers
            if helpers:
                if line.startswith(".transaction()"):
                    convert = True
                    helpers = False
                else:
                    continue
            if line == "Helpers":
                helpers = True
                continue

            # Create a new list entry for a new line indicated by '{"client'
            if line.startswith('{"client'):
                i += 1
                # split the line in the standard part and message part
                line = line.split(split_m)
                # One liners, indicated with a curly brace in the end
                if line[1].endswith("}"):
                    # Replace double quotes with single quotes inside a key or value of the message part
                    if len(line[1].split(split_q)) == 3:
                        lines.append(
                            json.loads(
                                f"{line[0]}{split_m[:6]}\"{line[1].split(split_q)[0]}'{line[1].split(split_q)[1]}'{line[1].split(split_q)[2].strip('}'+'}'+'}')}\"{line[1][-2:]}"
                            )
                        )
                    # Lines with no double quotes in the message part
                    else:
                        if line[1].find("chain_id") != -1:
                            line[1] = line[1].replace("'", '"')[:-1]
                            lines.append(json.loads(f"{line[0]}{split_m[:6]}{line[1]}"))
                        else:
                            lines.append(
                                json.loads(
                                    f'{line[0]}{split_m[:6]}"{line[1][:-3]}"{line[1][-2:]}'
                                )
                            )
                # New open line
                else:
                    # Rename the key to pytezos_operationGroup
                    if line[1].startswith("<pytezos.operation.group.OperationGroup"):
                        lines.append(f'{line[0]}{split_m}"pytezos_operationGroup":')
                    else:
                        # Delete all arrows
                        lines.append(
                            f'{line[0]}{split_m}"http_{line[1].lstrip(">>>>> ").lstrip("<<<<< ")}":'
                        )

            # Concatenate continuing lines to the current line
            elif lines:
                # Delete single quotes around object and the '\n'
                if line.startswith("'[{\""):
                    line = line.rstrip("}").strip("'").rstrip("\\n") + "}" + "}" + "}"
                # Convert the payload dict with single quotes into json double quotes notation
                if convert:
                    lines[i] = json.loads(
                        lines[i].split('"Payload":')[0]
                        + '"Payload":'
                        + json.dumps(ast.literal_eval(lines[i].split('"Payload":')[1]))
                        + "}"
                        + "}"
                        + "}"
                        + "}"
                    )
                    convert = False
                # Concatenate the closing line, indicated by two curly braces, and transform the whole line into json format
                elif line.endswith("}" + "}"):
                    lines[i] = json.loads(f"{lines[i]}{line}")
                # If neither first nor last line, concatenate
                elif not line.endswith("}" + "}"):
                    if line.startswith('"protocol_parameters":'):

                        lines[
                            i
                        ] = f'{lines[i]}"protocol_parameters": {line.split(":")[1][1:10]}..."'
                    else:
                        lines[i] = f"{lines[i]}{line}"

    if export_json:
        # Save the workload_client log list as json file
        export_json_file(f"{log_dir}/", f"{file_name}", lines)
    return lines


# ext_node.log
def parse_ext_node_log(log_dir: str, export_json: bool) -> list:
    # load ext_node.log
    files_path_ext_node_log = load_log_file(log_dir, "ext_node")
    # Open and parse ext_node.log
    with open(files_path_ext_node_log, "r") as ext_node_log_file:
        lines = []
        for line in ext_node_log_file.readlines():
            lines.append(json.loads(line))

    if export_json:
        # Save the ext_node log list as json file
        export_json_file(f"{log_dir}/", "ext_node", lines)
    return lines


# node.log
def parse_node_log(
    log_dir: str,
    hostname: str,
    export_json=False,
    start_time=None,
) -> list:
    # Load node.log
    files_path_node_log = load_log_file(log_dir, "node")
    # Open and parse node.log
    with open(files_path_node_log, "r") as node_log_file:
        lines = []
        reached_start = False
        for line in node_log_file.readlines():

            # Skip the log lines until the start_time (exact Minute) is reached
            if start_time is not None and not reached_start:
                if not line.startswith(start_time):
                    continue
                else:
                    reached_start = True
            event = line.split("]")[1].strip()

            # Injecting operation / prevalidation (success or failure)
            if (
                event.startswith("injecting operation")
                or line.split("[")[1].split("]")[0] == "prevalidatorrequest_failed"
            ):
                lines.append(
                    {
                        "node": {
                            "hostname": hostname,
                            "time_stamp": line.split("[")[0].strip(),
                            "section": line.split("[")[1].split("]")[0],
                            "event": {
                                "injecting_operation": line.split(
                                    "injecting operation"
                                )[1].strip()[0:51],
                                "status": line.split("injecting operation")[1]
                                .strip()[52:]
                                .strip(),
                            },
                        }
                    }
                )

            # Update current head to block
            elif event.startswith("Update current head to"):
                lines.append(
                    {
                        "node": {
                            "hostname": hostname,
                            "time_stamp": line.split("[")[0].strip(),
                            "section": line.split("[")[1].split("]")[0],
                            "event": {
                                "update_current_head_to": line.split(
                                    "Update current head to"
                                )[1].strip()[0:51],
                                "level": line.split("(level")[1].split(",")[0].strip(),
                                "block_ts": line.split("timestamp")[1]
                                .split(",")[0]
                                .strip(),
                                "status": "fittnes " + line.split("fitness")[1].strip(),
                            },
                        }
                    }
                )

            # Block validated
            elif event.startswith("block B"):
                lines.append(
                    {
                        "node": {
                            "hostname": hostname,
                            "time_stamp": line.split("[")[0].strip(),
                            "section": line.split("[")[1].split("]")[0],
                            "event": {
                                "block": line.split("block")[3].strip()[0:51],
                                "status": line.split("block")[3].strip()[52:],
                            },
                        }
                    }
                )

            # Update the blockchain to new head (block)
            elif event.startswith("switching to new head"):
                lines.append(
                    {
                        "node": {
                            "hostname": hostname,
                            "time_stamp": line.split("[")[0].strip(),
                            "section": line.split("[")[1].split("]")[0],
                            "event": {
                                "switching_to_new_head": line.split(
                                    "switching to new head"
                                )[1].strip()[0:51],
                                "status": line.split("switching to new head")[1]
                                .strip()[52:]
                                .strip(),
                            },
                        }
                    }
                )
            # Worker crashed
            elif event.startswith("Worker crashed"):
                lines.append(
                    {
                        "node": {
                            "hostname": hostname,
                            "time_stamp": line.split("[")[0].strip(),
                            "section": line.split("[")[1].split("]")[0],
                            "event": "Worker crashed "
                            + line.split("Worker crashed")[1].strip(),
                        }
                    }
                )

            # All other logs
            else:
                lines.append(
                    {
                        "node": {
                            "hostname": hostname,
                            "time_stamp": line.split("[")[0].strip(),
                            "section": line.split("[")[1].split("]")[0],
                            "event": event,
                        }
                    }
                )
    # Save the node log list as json file
    if export_json:
        export_json_file(f"{log_dir}/", "node", lines)
    return lines


# baker.log
def parse_baker_log(log_dir: str, hostname: str, export_json: bool) -> list:

    # Load baker.log
    files_path_baker_log = load_log_file(log_dir, "baker")
    # Open and parse baker.log
    with open(files_path_baker_log, "r") as baker_log_file:
        i = 0
        lines = []
        new_event = 0
        operation = False
        slot = False
        inject = False
        cl_validation = False
        sh_validation = False
        error = False
        ops = 0
        baker_started = False
        for line in baker_log_file.readlines():
            if not baker_started:
                # Store the first lines without a date as events
                if len(line.split(":")) == 1:
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": "",
                                "section": "",
                                "event": line.strip(),
                            }
                        }
                    )
                    i += 1
                    if line.startswith("Baker"):
                        baker_started = True
                    continue
            else:
                # helping variables
                line_hy = line.split("-")
                logger_t2 = line_hy[2].split(":")[0]
                pos = len(line_hy[0]) + len(line_hy[1]) + len(logger_t2) + 2
                event = line[pos + 1 :].strip()

                # Start 'Found Baking slot' - line
                if event.startswith("new baking"):
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": line_hy[0].rstrip(),
                                "section": line_hy[1].lstrip() + logger_t2,
                                "event": event,
                            }
                        }
                    )
                    slot = True
                    inject = False
                    cl_validation = False
                    sh_validation = False
                    new_event = i
                    i += 1
                    continue

                # Start 'Inject block' - line
                if event.startswith("injected"):
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": line_hy[0].rstrip(),
                                "section": line_hy[1].lstrip() + logger_t2,
                                "event": {
                                    "injected": {
                                        "block": event.strip("injected block ")
                                    }
                                },
                            }
                        }
                    )
                    inject = True
                    slot = False
                    cl_validation = False
                    sh_validation = False
                    new_event = i
                    i += 1
                    continue

                # Start 'no slot found' - line
                if event.startswith("no slot found"):
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": line_hy[0].rstrip(),
                                "section": line_hy[1].lstrip() + logger_t2,
                                "event": event,
                            }
                        }
                    )
                    inject = False
                    slot = False
                    cl_validation = False
                    sh_validation = False
                    new_event = i
                    i += 1
                    continue

                # Start client-side validation
                if event.startswith("client-side validation"):
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": line_hy[0].rstrip(),
                                "section": line_hy[1].lstrip() + logger_t2,
                                "event": {"client-side_validation": event},
                            }
                        }
                    )
                    inject = False
                    slot = False
                    sh_validation = False
                    cl_validation = True
                    new_event = i
                    i += 1
                    continue

                # Start shell-side validation
                if event.startswith("shell-side validation"):
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": line_hy[0].rstrip(),
                                "section": line_hy[1].lstrip() + logger_t2,
                                "event": {
                                    "shell-side_validation": {"msg": event},
                                },
                            }
                        }
                    )
                    inject = False
                    slot = False
                    cl_validation = False
                    sh_validation = True
                    new_event = i
                    i += 1
                    continue

                # Continue the 'client-side validation' line
                if cl_validation:
                    lines[new_event]["baker"]["event"]["client-side_validation"] = (
                        lines[new_event]["baker"]["event"]["client-side_validation"]
                        + " "
                        + event
                    )

                # Continue the 'shell-side validation' line
                if sh_validation:
                    if error:
                        if event.startswith("It is likely"):
                            lines[new_event]["baker"]["event"]["shell-side_validation"][
                                "msg"
                            ] = (
                                lines[new_event]["baker"]["event"][
                                    "shell-side_validation"
                                ]["msg"]
                                + " "
                                + event
                            )
                            error = False
                            sh_validation = False
                            lines[new_event]["baker"]["event"]["shell-side_validation"][
                                "error"
                            ] = json.loads(
                                lines[new_event]["baker"]["event"][
                                    "shell-side_validation"
                                ]["error"]
                            )
                            continue
                        else:
                            lines[new_event]["baker"]["event"]["shell-side_validation"][
                                "error"
                            ] = (
                                lines[new_event]["baker"]["event"][
                                    "shell-side_validation"
                                ]["error"]
                                + " "
                                + event
                            )
                            continue
                    # Starts the 'error' block
                    if event.startswith("{") and not error:
                        lines[new_event]["baker"]["event"]["shell-side_validation"][
                            "error"
                        ] = event
                        error = True
                    elif not error:
                        lines[new_event]["baker"]["event"]["shell-side_validation"][
                            "msg"
                        ] = (
                            lines[new_event]["baker"]["event"]["shell-side_validation"][
                                "msg"
                            ]
                            + " "
                            + event
                        )

                # Continue the 'baking slot' line
                if slot:
                    lines[new_event]["baker"]["event"] = (
                        lines[new_event]["baker"]["event"] + " " + event
                    )

                # Continue the 'Injected' line
                if inject:
                    # For the 'operations' block
                    if operation:
                        # Continue the 'operations' block if not beginning or end of block
                        if not event.startswith("{") and not event.strip(")").endswith(
                            "}"
                        ):
                            lines[new_event]["baker"]["event"]["injected"][
                                "operations"
                            ][ops] = (
                                lines[new_event]["baker"]["event"]["injected"][
                                    "operations"
                                ][ops]
                                + event
                            )
                        # End the dict list element and transform it to json
                        if event.endswith("}"):
                            lines[new_event]["baker"]["event"]["injected"][
                                "operations"
                            ][ops] = json.loads(
                                lines[new_event]["baker"]["event"]["injected"][
                                    "operations"
                                ][ops]
                                + event
                            )
                        # Start the next list element in the 'operations' block
                        if event.startswith("{"):
                            lines[new_event]["baker"]["event"]["injected"][
                                "operations"
                            ].append(event)
                            ops += 1
                        # End the 'operations' block and transform the dict list element to json
                        if event.endswith("})"):
                            lines[new_event]["baker"]["event"]["injected"][
                                "operations"
                            ][ops] = json.loads(
                                lines[new_event]["baker"]["event"]["injected"][
                                    "operations"
                                ][ops]
                                + event.rstrip(")")
                            )
                            operation = False
                    # Continue the 'Injected' line and if the word operations is aparent at the end of line, strip it of
                    elif not event.startswith("{"):
                        lines[new_event]["baker"]["event"]["injected"]["block"] = (
                            lines[new_event]["baker"]["event"]["injected"]["block"]
                            + " "
                            + event.lstrip().rstrip("operations ,"[::-1])
                        )

                    # Starts the 'operations' block
                    if event.startswith("{") and not operation:
                        lines[new_event]["baker"]["event"]["injected"]["operations"] = [
                            event
                        ]
                        operation = True
                        ops = 0

    if export_json:
        # Save the baker log list as json file
        export_json_file(f"{log_dir}/", "baker", lines)
    return lines


# endorser.log
def parse_endorser_log(log_dir: str, hostname: str, export_json: bool) -> list:

    # Load endorser.log
    files_path_endorser_log = load_log_file(log_dir, "endorser")
    # Open and parse endorser.log
    with open(files_path_endorser_log, "r") as endorser_log_file:
        i = 0
        lines = []
        new = 0
        inject = False
        para = 0
        endorser_started = False
        for line in endorser_log_file.readlines():
            # Store the first two lines as events
            if not endorser_started:
                lines.append(
                    {
                        "baker": {
                            "hostname": hostname,
                            "time_stamp": "",
                            "section": "",
                            "event": line.strip(),
                        }
                    }
                )
                i += 1
                if line.startswith("Endorser"):
                    endorser_started = True
                continue
            else:
                # helping variables
                line_hy = line.split("-")
                logger_t2 = line_hy[2].split(":")[0]
                pos = len(line_hy[0]) + len(line_hy[1]) + len(logger_t2) + 2
                event = line[pos + 1 :].strip()

                # New block starts with 'injected'
                if event.startswith("injected"):
                    lines.append(
                        {
                            "baker": {
                                "hostname": hostname,
                                "time_stamp": line_hy[0].rstrip(),
                                "section": line_hy[1].lstrip() + logger_t2,
                                "event": {"injected endorsement": {"block": {}}},
                            }
                        }
                    )
                    inject = True
                    new = i
                    i += 1
                    para = 1
                    continue

                if inject:
                    # first paragraph in block, retrieve the 'block'-hash and 'level'
                    if para == 1:
                        lines[new]["baker"]["event"]["injected endorsement"][
                            "block"
                        ] = (event.split("(level")[0].strip().strip("'"))
                        lines[new]["baker"]["event"]["injected endorsement"][
                            "level"
                        ] = event.split("(level")[1].split(",")[0]
                        para += 1
                        continue
                    # second paragraph in block, retrieve the 'contract baker'
                    if para == 2:
                        lines[new]["baker"]["event"]["injected endorsement"][
                            "contract baker"
                        ] = (event.split("baker)")[1].strip().strip("'"))
                        para += 1
                        continue
                    # third paragraph in block, retrieve the 'baker'
                    if para == 3:
                        lines[new]["baker"]["event"]["injected endorsement"][
                            "baker"
                        ] = event.split("(baker = ")[1].strip(")")
                        inject = False

    if export_json:
        # Save the endorser log list as json file
        export_json_file(f"{log_dir}/", "endorser", lines)
    return lines


# Retrieve operations properties
def get_ops_client_log(client_log: list, hostname: str, chain_name: str) -> dict:
    operations_client_log = {}
    op_start = False
    client_init = True
    ts_i = 0
    u_ts_i = 0
    u_ts_jp = 0
    u_ts_jc = 0

    # Iterate through the logs
    for i, log in enumerate(client_log):
        op = "{}"
        acc_pkh = ""
        if log["client"]["event"].startswith("trx") and client_init:
            # Get timestamp of operation initialization
            ts_i = log["client"]["time_stamp"]
            u_ts_i = log["client"]["U_ts"]
            client_init = False
            op_start = False
            continue

        try:
            # Last line of operation
            acc_pkh = log["client"]["msg"]["contents"][0]["source"]
            op_start = True
        # When the log element doesn't have the queried keys, it raises TypeError and KeyError
        except (TypeError, KeyError):
            continue

        if op_start and not client_init:
            # Get operation hash
            ops_hash = client_log[i - 1]["client"]["msg"]["http_200"]
            # Get timestamp of operation injection to node (when client calls http POST method)
            u_ts_jp = client_log[i - 2]["client"]["U_ts"]
            # Get timestamp of operation injection to node (when client recieves confirmation http code 200)
            u_ts_jc = client_log[i - 1]["client"]["U_ts"]
            # Get type of transaction - single or bulk
            ops_type = log["client"]["event"].split("_")[1]
            # Get workload level of operation
            ops_lvl = int(log["client"]["event"].split("_")[2].split(".")[0])
            # Get first transaction (of bulk)
            ops_ft = int(log["client"]["event"].split(".")[1].split("-")[0])
            # Get last transaction of bulk (for single: same as first)
            if ops_type == "bulk":
                ops_lt = int(log["client"]["event"].split("-")[1])
            else:
                ops_lt = ops_ft
            # Store the operations properties in dict
            op = {
                ops_hash: {
                    "name_of_chain": chain_name,
                    "op_send_rate_lvl": ops_lvl,
                    "op_first": ops_ft,
                    "op_last": ops_lt,
                    "op_hash": ops_hash,
                    "op_type": ops_type,
                    "sc_hostname": hostname,
                    "sc_account_pkh": acc_pkh,
                    "ts_client_init": ts_i,
                    "ts_node_start_preval": None,
                    "ts_block": None,
                    "u_ts_client_init": u_ts_i,
                    "u_ts_client_inject_post": u_ts_jp,
                    "u_ts_client_inject_complete": u_ts_jc,
                    "st_propagated": False,
                    "st_confirmed": False,
                    "st_error": None,
                    "pt_node_completed_preval": None,
                    "pt_trx_latency": None,
                    "block_hash": None,
                    "block_level": 0,
                    "branch_hash": None,
                }
            }
            # Add operation object to dict
            operations_client_log.update(op)
            client_init = True
    return operations_client_log


def json_query(inp_filter: str, outp_filter: str, ls_dict):
    search = f"[{inp_filter}].{outp_filter}"
    expr = jmespath.compile(f"{search}")
    result = expr.search(ls_dict)
    return result


def get_ops_prevalidated(op_hash: str, node_log: list):
    inp_filter = f'? node.event."injecting_operation"==`{op_hash}`'
    outp_filter = "{status: " + "node.event.status, section: node.section}"
    operation = json_query(inp_filter, outp_filter, node_log)
    return operation


def get_ops_node_log(
    node_log: list,
    ext_node_log: list,
    ops_client_log: dict,
):

    # Count the operations that failed the prevalidation
    ops_preval_failed = 0
    # Create dict of successful operations in the node log
    ops_node_log_suc = {}
    # Create dict of failed operations in the node log
    ops_node_log_fail = {}

    for n_log in node_log:

        # Only check logs regarding 'injecting_operation'
        if "injecting_operation" in n_log["node"]["event"]:
            # Get the operation hash
            op_hash = n_log["node"]["event"]["injecting_operation"]
            # Get the timestamp when the op injection (op_hash) was pushed on/ node started prevalidation
            req_pushed_ts = (
                n_log["node"]["event"]["status"]
                .split("Request pushed on")[1]
                .split(",")[0]
                .rstrip("-00:00")
                .lstrip()
            )

            # If the prevalidation was successful add the operation and its properties to the dict of successful ops in node log
            if n_log["node"]["section"] == "prevalidatorrequest_completed_notice":
                ops_node_log_suc.update(
                    {op_hash: {"ts_node_start_preval": req_pushed_ts}}
                )
                continue
            # If the prevalidation failed add the operation and its properties to the dict of failed ops in node log
            if n_log["node"]["section"] == "prevalidatorrequest_failed":
                ops_node_log_fail.update(
                    {op_hash: {"ts_node_start_preval": req_pushed_ts}}
                )

    # Create dict of successful operations in the extended node log
    ops_ext_node_log_suc = {}
    # Create dict of failed operations in the extended node log
    ops_ext_node_log_fail = {}

    for exn_log in ext_node_log:

        # Check logs regarding 'inject' operations and  successfully completed prevalidation
        if "request_completed_notice.v0" in exn_log["fd-sink-item.v0"]["event"]:
            if (
                exn_log["fd-sink-item.v0"]["event"]["request_completed_notice.v0"][
                    "view"
                ]["request"]
                == "inject"
            ):
                # Get the timestamp when the op injection (op_hash) was pushed on/ node started prevalidation
                req_pushed_ts = (
                    exn_log["fd-sink-item.v0"]["event"]["request_completed_notice.v0"][
                        "worker_status"
                    ]["pushed"]
                    .rstrip("-00:00")
                    .lstrip()
                )
                # Get the hash of the branch/ block that the operation is build upon
                branch_hash = exn_log["fd-sink-item.v0"]["event"][
                    "request_completed_notice.v0"
                ]["view"]["operation"]["branch"]
                # Get the process time of the node to complete the prevalidation
                completed_in = exn_log["fd-sink-item.v0"]["event"][
                    "request_completed_notice.v0"
                ]["worker_status"]["completed"]
                # Add the operation and its properties to the dict of successful ops in the extended node log
                ops_ext_node_log_suc.update(
                    {
                        req_pushed_ts: {
                            "branch_hash": branch_hash,
                            "pt_node_completed_preval": completed_in,
                        }
                    }
                )

        # Check logs regarding 'inject' operations and failed prevalidation
        if "request_failed.v0" in exn_log["fd-sink-item.v0"]["event"]:
            if (
                exn_log["fd-sink-item.v0"]["event"]["request_failed.v0"]["view"][
                    "request"
                ]
                == "inject"
            ):
                # Get the timestamp when the op injection (op_hash) was pushed on/ node started prevalidation
                req_pushed_ts = (
                    exn_log["fd-sink-item.v0"]["event"]["request_failed.v0"][
                        "worker_status"
                    ]["pushed"]
                    .rstrip("-00:00")
                    .lstrip()
                )
                # Get the hash of the branch/ block that the operation is build upon
                branch_hash = exn_log["fd-sink-item.v0"]["event"]["request_failed.v0"][
                    "view"
                ]["operation"]["branch"]
                # Get the process time of the node to complete the prevalidation
                completed_in = exn_log["fd-sink-item.v0"]["event"]["request_failed.v0"][
                    "worker_status"
                ]["completed"]
                # Get the cause for the error/ failed prevalidation
                errors = exn_log["fd-sink-item.v0"]["event"]["request_failed.v0"][
                    "errors"
                ]

                # Read the operation hash out of the error message
                try:
                    op_hash = (
                        errors[0]["msg"].split("operation ")[1].split(":")[0].strip()
                    )
                except IndexError:
                    op_hash = (
                        errors[0]["msg"].split("Operation ")[1].split(" ")[0].strip()
                    )
                # Add the operation and its properties to the dict of failed ops in the  extended node log
                ops_ext_node_log_fail.update(
                    {
                        op_hash: {
                            "branch_hash": branch_hash,
                            "pt_node_completed_preval": completed_in,
                            "st_error": errors,
                        }
                    }
                )

    # Iterate through the failed operations in the node log and add the properties of the matched operation (equal timestamp for the start of the prevalidation)
    # in the extended node log to the dict
    # Delete the operation from the extended node log in the process
    for op_fail in ops_node_log_fail:
        ops_node_log_fail[op_fail].update(
            ops_ext_node_log_fail.pop(
                op_fail,
                {}
                # ops_node_log_fail[op_fail]["ts_node_start_preval"], {}
            )
        )

    # Iterate through the successful operations in the node log and add the properties of the matched operation (equal timestamp for the start of the prevalidation)
    # in the extended node log to the dict
    # Delete the operation from the extended node log in the process
    for op_suc in ops_node_log_suc:
        ops_node_log_suc[op_suc].update(
            ops_ext_node_log_suc.pop(
                ops_node_log_suc[op_suc]["ts_node_start_preval"], {}
            )
        )

    # Iterate through the operations in the client log and add the properties from the matched operations (equal operation hashes) in the node log to the dict
    for op in ops_client_log:
        try:
            ops_client_log[op].update(
                ops_node_log_suc.pop(ops_client_log[op]["op_hash"])
            )
            # If the prevalidation of the operation was successful
            ops_client_log[op]["st_propagated"] = True
        except KeyError:
            ops_client_log[op].update(
                ops_node_log_fail.pop(ops_client_log[op]["op_hash"], {})
            )
            ops_preval_failed += 1
            # print(
            #     f'(OP {ops_client_log[op]["op_type"]}_{ops_client_log[op]["op_send_rate_lvl"]}.'
            #     + f'{ops_client_log[op]["op_first"]}-{ops_client_log[op]["op_last"]}): Prevalidation failed: {ops_client_log[op]["st_error"]}'
            # )

    return ops_client_log, ops_preval_failed


def parse_all_logs(
    log_dir: str, hostname: str, client_log_file: str, export_json=False
) -> dict:
    client_log = parse_workload_client_log(log_dir, client_log_file, export_json)
    ext_node_log = parse_ext_node_log(log_dir, export_json)
    node_log = parse_node_log(log_dir, hostname, export_json)
    baker_log = parse_baker_log(log_dir, hostname, export_json)
    endorser_log = parse_endorser_log(log_dir, hostname, export_json)
    print("The log files have been parsed and saved as json")
    return {
        "client": client_log,
        "ext_node": ext_node_log,
        "node": node_log,
        "baker": baker_log,
        "endorser": endorser_log,
    }


def get_operations(
    client_log: list, node_log: list, ext_node_log: list, hostname: str, chain_name: str
):
    ops_client_log_start = time.time()
    ops_client_log = get_ops_client_log(client_log, hostname, chain_name)
    ops_client_log_end = time.time()
    ops_node_log_start = time.time()
    operations, ops_preval_failed = get_ops_node_log(
        node_log, ext_node_log, ops_client_log
    )
    ops_node_log_end = time.time()
    print(
        f"get_ops_client_log time: {ops_client_log_end-ops_client_log_start}, get_ops_node_log time: {ops_node_log_end-ops_node_log_start}"
    )
    return operations, ops_preval_failed


def load_log_file(log_dir: str, file_name: str) -> str:
    files_path = f"{log_dir}/{file_name}.log"
    os.makedirs(os.path.dirname(files_path), exist_ok=True)
    return files_path
