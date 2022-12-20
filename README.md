# TezBed - A Benchmarking Framework for Private Blockchain Systems Based on the Tezos Protocol

**Agenda**: 

- [x] VM Cluster Setup: Configuration of cloud, VM instantiation, software installation.
  - [Network Setup - Overview](#network-setup---overview)
  - [1. Setup and Preparation of the Controller Host](#1-setup-and-preparation-of-the-controller-host)
  - [2. Orchestrating Setup of Target Host VM Instances](#2-orchestrating-setup-of-target-host-vm-instances)

- [x] Execution of DLT performance benchmark under various configurations.
  - [3. Execution of Benchmark](#3-execution-of-benchmark)
  - [4. Access to the Database](#4-access-to-the-database)

- [Directory Pattern and Explanation](#directory-pattern-and-explanation)

## Network Setup - Overview

- One VM (running Ubuntu) in the BW-Cloud acts as the Ansible controller host (**CH**), which gets the Ansible Playbooks and necessary files over this git repository and controls the other host vms/ target hosts (**TH**) in the cloud.
- The VM with the Ansible Controller is controlled through SSH via a local machine.

## 1. Setup and Preparation of the Controller Host

1. Configuring the operating system:
    - Setup manually a new instance (with Ubuntu 20.04) over the BW-Cloud portal for the CH
    - Log into the CH via SSH (user: _ubuntu_) `ssh ubuntu@IP-Address`
    - Update package source lists: `sudo apt update`
    - Upgrade the system packages and kernel: `sudo apt dist-upgrade`, then Reboot the host `sudo reboot` and reconnect via SSH

2. Install Ansible and Plugins:
    - (only if Docker is required) Installing Ansible on Ubuntu via Python Package Manager (PIP) globally, in order to avoid a python interpreter problem with the python-docker SDK (you can ignore the warnings):
        - Install PIP: `curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py`  `sudo python3 get-pip.py`
        - Install Ansible: `sudo python3 -m pip install ansible`
    - (recommended) Installing Ansible on Ubuntu:
    ```
        sudo apt update
        sudo apt install software-properties-common
        sudo add-apt-repository --yes --update ppa:ansible/ansible
        sudo apt install ansible
    ```
    - Install Python Library Shade to interact with OpenStack (BW-Cloud): `sudo apt-get install -y python3-shade`
    - To interact with OpenStack Clouds (BW-Cloud) we use the openstack.cloud module that is included in the ansible-galaxy collection. To install the newest version run: `ansible-galaxy collection install openstack.cloud`
    - To install the newest community.general collection run: `ansible-galaxy collection install community.general`
    - To interact with Docker we need the Docker module that is included in the ansible-galaxy collection. To install the newest version run: `ansible-galaxy collection install community.docker`
    - To check what plugins are install, run: `ansible-galaxy collection list`

3. Clone the git repository via HTTPS (password is required for every pull) or via SSH Deploy Keys
    - Independent of the method, you have to register your git account:
        - Run: `git config --global user.name "FIRST_NAME LAST_NAME"`
        - Run: `git config --global user.email "MY_NAME@example.com"`
    - Quick method via HTTPS (not recommend if you want to continue work in this repository and have multiple pulls and pushes)
        - Go to the Gitlab project in the web browser and copy the address under 'Clone' -> 'Clone with HTTPS'
        - Run: `git clone CopiedAddress` (e.g. git clone https://git...) and enter your username and password for git
    - SSH Deploy Key method (recommended)
        - Create an SSH key (see: https://git.scc.kit.edu/help/ssh/index.md) on your CH with a strong passphrase, Run: `ssh-keygen -t ed25519` 
        - Create a new Deploy Key (see: https://git.scc.kit.edu/help/user/project/deploy_keys/index.md) in your gitlab under 'Project' -> 'Settings' -> 'Repository' -> 'Deploy keys'. Provide a title (e.g. controller host), grant optionally write permissions and paste the public key of your newly generated SSH key. To find your public Key, run: `cat ~/.ssh/id_ed25519.pub` and copy the whole output in the key field. Click 'Add key'
        - Before you clone the repository, the key on the CH has to be added to the authorized keys, run: `ssh-agent bash` `ssh-add ~/.ssh/id_ed25519` and enter your passphrase. **Note:** In order to not require to manually starting a new ssh-agent for every new terminal session add the ssh key to the keychain following step 5.
        - To clone the repository, go to the Gitlab project in the web browser and copy the address under 'Clone' -> 'Clone with SSH'
        - Run: `git clone CopiedAddress` (e.g. git clone git@git.scc...) and confirm the connection with `yes`
    - **If the repository was cloned to a different directory than '/home/ubuntu/', adapt the 'git_project_dir' in roles/project_directories/vars/main.yaml**

4. Provide CH with BW-Cloud API    
    - Option 1: (recommended and necessary for /vm_setup Playbooks)
        - Download Openstack clouds.yaml file in the BW-Cloud Dashboard -> API Access
        - Add the clouds.yaml file to the openStack_config folder in this repository
        - When new instances are deployed via the ansible playbook you will get prompted to enter your login password for the openstack (BW) cloud.
    - Option 2: (not supported by /vm_setup Playbooks)
        - Download Openstack RC-File in the BW-Cloud Dashboard -> API Access
        - Send/Copy RC-File to the CH and run the file (script): `. projectName-openrc.sh` The script will ask for the login password for the openstack (BW) cloud.
        - **Note:** The script has to run every time you open a new shell of the CH again and you need to type in the password for the BW-cloud user login

**Note:** For the execution of ansible playbooks, we assume you are in the directory of this repository

5. Create SSH key for target hosts vms, install keychain and add SSH keys to keychain
    - To create a SSH key for the target host and add it to the openstack BW cloud, run: `ansible-playbook ./vm_setup/create_ssh_key.yaml`
        - You will get prompted to enter:
            - Your password for the openstack (BW) cloud login    
            - The name of the SSH key you want to create
            - A new passphrase for the SSH key (passphrase is optional, but strongly recommended)
    - To install keychain and add SSH key for target host and (optional) SSH key for git, run: `ansible-playbook ./vm_setup/setup_keychain.yaml`
        - You will get prompted to enter:
            - The name of the target host SSH key you want to add to the keychain    
            - The name of the Git SSH key, leave blank if you don't want to add the git key to the keychain
    - Open a new terminal session and enter your ssh key passphrases when prompted, the keys will be loaded into the keychain and you will only get asked for the passphrase if you reboot the controller host.

6. Install the required python packages and libraries for various python scripts:
    - Run: `ansible-playbook ./vm_setup/install_py_lib.yaml`

7. Create (or delete) and mount a volume (persistent data storage) to the controller host for saving log files in a database. (min 100GiB)
    - To create and mount a new volume, run: `ansible-playbook ./vm_setup/create_and_mount_volume.yaml`
        - You will get prompted to enter:
            - Your password for the openstack (BW) cloud login    
            - The name of the volume / data storage you want to create
            - The size (in GiB) your volume / data storage should have, enter integer number
        - The directory, where the volume is mounted, is set in the directories role (e.g. logs_database)
    - To unmount and delete a present volume, run: `ansible-playbook ./vm_setup/delete_volume.yaml` **WARNING: All files on the volume will be lost**
        - You will get prompted to enter:
            - Your password for the openstack (BW) cloud login    
            - The name of the volume / data storage you want to delete
            - The absolute path of the mounting point (directory), your volume was mounted to (e.g. /home/ubuntu/logs_database)

8. Create a directory to store the ansible log file in and change the path in the ansible config files under 'log_path' (Default: ~/ansible_logs/ansible.log). Run: e.g. : `mkdir /home/ubuntu/logs_database/ansible_logs/`

9. To install the clickhouse Database (Server & Client) on the CH run: `ansible-playbook ./vm_setup/install_clickhouse_CH.yaml`

10. To install tmux, to run ansible playbooks in the background after closing the terminal session, run: `ansible-playbook ./vm_setup/install_tmux.yaml`

11. (Optional, if Docker is necessary) Install Docker on the CH by following the official guideline for ubuntu: https://docs.docker.com/engine/install/ubuntu/#installation-methods


## 2. Orchestrating Setup of Target Host VM Instances

**Note:** All further commands assume you are in the directory of this repository to shorten the commands for better readability

> The playbook automatically checks if your desired number of VMs with your selected flavor does not exceed the quota (minus already deployed VMs) of the BW-Cloud regarding the maximum number of VMs, the total amount of RAM and total number of vCPUs. If your selection exceeds the quota the playbook will determinate immediately and provide you the appropriate reason for it. **Since querying the quota requires admin permission, you have to manually set/update the correct quota (see BW-cloud Dashboard) in the openstack_config/cloud_quota.yaml file!**

1. To setup an openstack security group with the required ports (defined in Ansible roles: os_security_gr (default ports), clickhouse (secure TCP) and tezos (p2p and RPC)) run:  `ansible-playbook ./vm_setup/configure_ports.yaml`
    You will get prompted to enter:
    - Your password for the openstack (BW) cloud login
    - The name of the network security group you want to create (e.g. tezos_benchmark)
    - An optional description for the purpose of the security group

2. To deploy new VM instances/target hosts run: `ansible-playbook ./vm_setup/deployVM.yaml`
    The VMs get assigned with the TargetHost privateKey

    You will get prompted to enter:
    - Your password for the openstack (BW) cloud login    
    - A Prefix/Name for the VMs [one word, no underscore] (recommended to use a name regarding the distributed ledger/ blockchain design you want to setup e.g. ethereum, tezos). The VMs are named then with Prefix_ascendingNumber (e.g. ethereum_1, ethereum_2,...)
        - If you choose a name that already exist in the cloud, the name counter will continue at the highest number and the hosts are added to the existent inventory. 
    - The hardware flavor/type you want to use for all your VM instances (consider the quota).
    - How many VM instances/target hosts you want to deploy
    - The name of the security group you created before

      
    The playbook will then deploy these VM instances and save its IP-addresses in a new inventory file in the inventory folder (./inventory/vmPrefix_inventory.yaml). This inventory file is used in all following playbooks to address the target hosts.
    
    **Note:** If you run the playbook again to deploy further VM instances with the same flavor and same prefix/name, you have to enter only the desired number of new VMs, that should be added. The already deployed VMs will persist and the newly added VMs will be appended to the inventory file. To check the inventory list (list of target hosts) run : `ansible-inventory --list -y -i ./inventory/vmPrefix_inventory.yaml`

    **For RESET purpose only:**
    To delete VM instances run `ansible-playbook ./vm_setup/deleteVM.yaml`
    
    You will get prompted to enter:
    - Your password for the openstack (BW) cloud login
    - The Prefix/Name for the VMs instances you want to delete (e.g. eth)
    - If you want to delete all VM instances with the same prefix/name, then type 'all', otherwise type the 'number' of the VM (e.g. 3 -> eth_3 is deleted)
        - If all VMs are deleted, the specific inventory file is deleted
        - If only once VM is deleted, the VMs name and IP is removed from the inventory file

3. To prepare the Target Hosts'/VMs' run: `ansible-playbook ./vm_setup/prepare_TargetHosts.yaml -i ./inventory/vmPrefix_inventory.yaml` (If a failure occurs, that the apt-package manager can't connect, restart the host via the BW-cloud portal)
    - This will update Ubuntu and all packages
    - Reboot the VMs
    - Synchronize the time between the CH and the THs by configuring the CH as NTP-server and the THs as NTP-clients (To check delay & offset run: `ntpq -p`)
    - Install Tezos-Client, Tezos-Node, Tezos-Baker, Tezos-baker-011-pthangz2, Tezos-endorser-011-pthangz2 and Tezos-accuser-011-pthangz2
    - Install the pytezos python library (forked version with low 'MAX_OPERATIONS_TTL'=6) and further python libraries
    - Install Clickhouse Client and prerequisites
    - Fetch hardware information from target host and save to file.
    - Install atop for system performance logging/monitoring
    - (Optional, if Docker is necessary) to install Docker and the Docker python SDK to use the docker ansible modules, uncomment "import_playbook: install_docker.yaml" in "prepare_targetHosts.yaml" or run: `ansible-playbook ./vm_setup/install_docker.yaml -i ./inventory/vmPrefix_inventory.yaml`
    - **Note:**: If you want to run the playbook only on one, or a selected few hosts, run: `ansible-playbook ./vm_setup/prepare_TargetHosts.yaml -i ./inventory/vmPrefix_inventory.yaml --limit "host1, host2,..."`. Run on all, except a host: `... --limit 'all:!host1`


4. To get secure remote access via TCP (TSL) to the clickhouse database create the necessary TSL self signed certificates first, run: `ansible-playbook ./clickhouse/configure_TSL.yaml`
    - You will get asked, if you want to create a new Diffie-Hellman parameters file, choose 'yes', if you run the playbook the first time and haven't created one yet.
    - As of now, the private keys are not password protected, since there is a problem with reading password protected private keys from clickhouse ssl. (--> to do)

5. To setup the clickhouse server (sv_config.xml), user (sv_users.xml) and client (cl_config.xml) configuration and start the clickhouse server run:
    `ansible-playbook ./clickhouse/setup_clickhouse.yaml -i inventory/vmPrefix_inventory.yaml`
    - You get prompted to choose a password for the clickhouse user.

6. To Create the benchmark database and the necessary tables run: `ansible-playbook ./clickhouse/create_database_and_tables.yaml`. This includes the following tables:
    - protocol_constants
    - vm_hardware_properties
    - experiment_vars
    - blocks
    - operations
    - several system logs (e.g. : sys_log_cpl)


## 3. Execution of Benchmark

1. When you execute the benchmark the first time, set in the 'benchmark' role the 'minimum_nodes_exp' to 'all', then run: `ansible-playbook run_benchmark.yaml -i inventory/inventory/vmPrefix_inventory.yaml`

    - **Important Note:** In all subsequent executions, set 'minimum_nodes_exp' to minimum 6, you should skip the creation of new baker accounts, in order to speed up the network setup process, run: `ansible-playbook run_benchmark.yaml -i inventory/inventory/vmPrefix_inventory.yaml --skip-tags "new_baker_accounts"`
    - If you want to limit the hosts, that take part in the benchmark, add the `--limit "[hostname]"` flag with a list of all hosts to include in the benchmark to the command above, e.g.: `--limit "hostname_1, hostname_2, hostname_3, hostname_4, hostname_5"` -> The benchmark will run only on those 5 hosts.
    - To only setup the network and blockchain, without distributing the funds to the workers, sending any transactions between them (no workload) and therefore no process of logs and insertion into the database, add `funds_distribution` to the skip-tags list. If you only want to skip the workload and process of logs, but have funds distributed add `workload`. If you only want to skip the last part, the process of logs add 'process_logs' e.g.: `--skip-tags "new_baker_accounts, workload" or --skip-tags "process_logs"`

    **Run in background**
    To execute the benchmark in the background and be able to close the terminal, run: `tmux` ,run the above ansible-playbook inside tmux.
    - To leave/detach the tmux session: type Ctrl+b and then d
    - To check the status of the last opened session (e.g. in a new terminal window) run: `tmux attach`
    - To get a list of all currently running tmux sessions run: `tmux ls`
    - To attach to a specific tmux session run: `tmux attach-session -t <session-name>`
    - To kill the current pane / tmux session: type ctrl+b and then x, confirm with y


2. To delete all files and folders (and optionally baker accounts) of an experiment/benchmark : `ansible-playbook ./tezos/network_setup/delete_experiment_folders.yaml`

## 4. Access to the Database

In order to access the database with the results of the benchmark there are two different methods. Independent of the method a new clickhouse user must be created, if the admin password for the 'tezos' user is unknown - for more information see official clickhouse documentation: https://clickhouse.com/docs/en/operations/settings/settings-users/; https://clickhouse.com/docs/en/operations/configuration-files.
- Create a new (read only) user in the users config file following the paradigm of the 'tezos' user: `sudo nano /etc/clickhouse-server/users.d/ch_sv_users.xml`
- Add at least the localhost (127.0.0.1) to the user's network section or your IP - address (see method 2)
- Choose and hash the user password: `echo -n YourUserPassword | sha256sum | tr -d '-'` and write the hash in the users config file.
- Save the user's config file and restart the clickhouse-server to apply the changes: `sudo systemctl restart clickhouse-server`.
- Check if the server runs correctly: `systemctl status clickhouse-server`

1. If your local machine doesn't have a static IP and you have access to the CH via SSH:
    - To access the database via a database IDE (e.g., DataGrip), create an SSH tunnel to the CH:
        - For example, in DataGrip configure the SSH tunnel to your CH with the SSH private key. Then configure the database with the localhost IP of the CH (127.0.0.1), the clickhouse driver, your user name and password.
        - Increase the socket_timeout to query the prepared views, in DataGrip write this in the config URL: `jdbc:clickhouse://127.0.0.1/tezos_benchmark?socket_timeout=300000`

2. If the local machine, from which you want to access the database, has a static public IP - address:
    - Add your IP - address to the clickhouse user config to the new user you created above: `sudo nano /etc/clickhouse-server/users.d/ch_sv_users.xml` and restart the server.
    - Copy the following three TSL certificates (ca.pem, client.pem, client.key) from the CH directory: `/etc/ssl/` to a directory on your local machine. (Due to security reasons, the certificates are not included in this repository)
    - A: To access the database via the native CLI clickhouse-client:
        - Copy the clickhouse client config from the CH: `/home/ubuntu/.clickhouse-client/config.xml` to your local machine and adapt to your settings (CH public host IP, your user and certificate/key directories).
        - Ensure that the external access over the secure TCP port 9440 is enabled for your IP address in the BW-Cloud security group settings 
        - Access the database via CLI with: `clickhouse-client -C 'PathToClientConfig' --password 'YourUserPassword'`
    - B: To access the database via the HTTP API with a database IDE (e.g., DataGrip):
        - Uncomment the '<https_port>8443</https_port>' in the server config file: `sudo nano /etc/clickhouse-server/config.d/ch_sv_config.xml` and restart the server.
        - Ensure that the external access over the HTTP port 8443 is enabled for your IP address in the BW-Cloud security group settings
        - Access the database via database IDE, for example, in DataGrip configure the database with the clickhouse driver, your user name, password, IP of the CH, https port, SSL settings: path to certificates/keys.
        - Increase the socket_timeout to query the prepared views, in DataGrip write this in the config URL: `jdbc:clickhouse://127.0.0.1/tezos_benchmark?socket_timeout=300000`


## Directory Pattern and Explanation
```
📦TezBed
 ┣ 📂benchmark_results ----- Results and analysis of the benchmark
 ┃ ┣ 📂data ------------------ Queried results from database, exported as CSV files
 ┃ ┣ 📂regression ------------ Output/Results of OLS regressions
 ┃ ┣ 📂scripts --------------- (Python) scripts to visualize results and execute regressions
 ┣ 📂clickhouse ------------ Clickhouse database management 
 ┃ ┣ 📂SQL ------------------- SQL queries and views
 ┃ ┃ ┗ 📂tezos_benchmark ------- Database of the Tezos benchmark
 ┃ ┃ ┃ ┣ 📂views ----------------- SQL views for the validation and analysis of results
 ┃ ┣ 📂table_description ----- Definition of each database table: variable names and clickhouse datatype
 ┃ ┣ 📂tasks ----------------- Ansible tasks to create tables, insert data into tables and create the views
 ┃ ┣ 📂templates ------------- Jinja templates to create TSL certificate and clickhouse - client, server and user config
 ┣ 📂ibm_spectrum_protect -- Backup Service for data volume (database + raw logs)
 ┃ ┣ 📂tasks ----------------- Ansible tasks to execute backup via VPN
 ┃ ┣ 📂templates ------------- Jinja templates to output backup log
 ┣ 📂inventory ------------- Ansible inventory file (list of IP-addresses of THs and host variables)
 ┣ 📂kit_vpn --------------- KIT vpn config files
 ┣ 📂openstack_config ------ Config file for the BW-Cloud/openstack environment, project's cloud quota
 ┣ 📂roles ----------------- Ansible roles (only used to define variables)
 ┃ ┣ 📂benchmark ------------- Initialization of variables regarding the general execution of the benchmark
 ┃ ┣ 📂clickhouse ------------ Initialization of database name and user, full table descriptions for Ansible create_table task
 ┃ ┣ 📂os_security_gr -------- Initialization of open ports/protocols for the security group in the BW-Cloud/openstack cloud 
 ┃ ┣ 📂project_directories --- Initialization of all directories, including the location of this repository
 ┃ ┣ 📂system_log ------------ Labels for the system monitoring logs
 ┃ ┗ 📂tezos ----------------- Initialization of Tezos related variables and PROTOCOL-CONFIG/ CONSTANTS
 ┣ 📂tezos ----------------- Main Ansible tasks and script files for the setup of the blockchain network and the execution of the benchmark
 ┃ ┣ 📂network_setup --------- Tasks and templates for the experiment setup, blockchain setup, load model and monitoring 
 ┃ ┃ ┣ 📂tasks ----------------- All the relevant Ansible task files
 ┃ ┃ ┣ 📂templates ------------- Jinja templates for various benchmark and tezos related processes
 ┃ ┣ 📂scripts --------------- All Python scripts regarding the experiment setup, blockchain setup, load model and monitoring
 ┣ 📂tezos-software -------- List of installed software on the TH and tezos software package of the now publicly unavailable version we use.
 ┣ 📂vm_setup -------------- Ansible Playbooks to configure, setup and prepare the VM cluster in the cloud including all software installations 
 ┃ ┣ 
 ┣ 📜ansible.cfg ----------- Main Ansible config file used by the 'run_benchmark' Playbook
 ┗ 📜run_benchmark.yaml ---- Main Ansible Playbook to execute the benchmark
 ```