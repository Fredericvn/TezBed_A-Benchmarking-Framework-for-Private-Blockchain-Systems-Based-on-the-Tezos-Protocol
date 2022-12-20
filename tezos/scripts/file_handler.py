import os
import json
import yaml
import pandas as pd

# Loads file content from dir_path/file_name
def load_yaml_file(dir_path: str, file_name: str):
    files_path = f"{ dir_path}{file_name}.yaml"
    os.makedirs(os.path.dirname(files_path), exist_ok=True)
    with open(files_path, "r") as infile:
        file_content = yaml.full_load(infile)
    return file_content


# Loads file content from dir_path/file_name
def load_json_file(dir_path: str, file_name: str):
    files_path = f"{ dir_path}{file_name}.json"
    os.makedirs(os.path.dirname(files_path), exist_ok=True)
    with open(files_path, "r") as infile:
        file_content = json.load(infile)
    return file_content


# Exports the 'content' to dir_path/file_name.yaml
def export_yaml_file(dir_path: str, file_name: str, content):
    files_path = f"{ dir_path}{file_name}.yaml"
    os.makedirs(os.path.dirname(dir_path), exist_ok=True)
    with open(f"{files_path}", "w") as outfile:
        yaml.dump(content, outfile)
        print(f"Wrote {file_name} to {files_path}")


# Exports the 'content' to dir_path/file_name.json
def export_json_file(dir_path: str, file_name: str, content):
    files_path = f"{ dir_path}{file_name}.json"
    os.makedirs(os.path.dirname(dir_path), exist_ok=True)
    with open(f"{files_path}", "w") as outfile:
        json.dump(content, outfile, indent=2)
        print(f"Wrote {file_name} to {files_path}")


# Exports the 'content' to dir_path/file_name.csv
def export_csv_file(dir_path: str, file_name: str, content, from_type="df"):
    files_path = f"{ dir_path}{file_name}.csv"
    os.makedirs(os.path.dirname(dir_path), exist_ok=True)
    if from_type == "dict":
        # Transform dict to pandas dataframes
        df_content = pd.DataFrame.from_dict(content)
    else:
        df_content = content
    df_content.to_csv(files_path, index=False, header=True)
    print(f"Wrote {file_name} to {files_path}")
