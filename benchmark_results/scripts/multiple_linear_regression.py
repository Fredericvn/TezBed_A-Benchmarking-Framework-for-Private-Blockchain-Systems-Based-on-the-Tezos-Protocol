import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm

## Add path to data results
DIRECTORY = "/Users/frederic/automation-of-dl-network-setup-and-testing-with-ansible/benchmark_results/data/"


def read_csv(file_path: str, level=None):
    df = pd.read_csv(
        f"{DIRECTORY}{file_path}",
        sep=",",
        header=0,
    )
    if level is not None:
        return df.loc[np.where(df["workload_lvl"] == level)[0], :]
    else:
        return df


def prepare_data(df, restr_block_delay=None, level=None):
    df = df.reset_index(drop=True)
    if restr_block_delay is not None:
        df = df.loc[np.where(df["block_creation_interval"] <= restr_block_delay)]
    if level is not None:
        input_parameters = df[
            ["block_size_limit", "block_creation_interval", "network_size"]
        ]
    else:
        input_parameters = df[
            [
                "block_size_limit",
                "block_creation_interval",
                "network_size",
                "workload_lvl",
            ]
        ]
    return df, input_parameters


# Read from file (name) and optional sort for workload level
# data = read_csv("tx_throughput_and_latency.csv", level=100)
data = read_csv("tx_throughput_and_latency.csv")

# Prepare the data and optionally restrict/filter: min block delay <= value
# data, X = prepare_data(data, 40, level=100)
data, X = prepare_data(data, 40)

# Calculate Correlation matrix
corr_matrix = data[
    [
        "block_size_limit",
        "block_creation_interval",
        "network_size",
        "Tx_throughput",
        "Tx_confirm_latency",
        "workload_lvl",
    ]
].corr()
print(f"{corr_matrix}\n")
## No high correlations


# With stats model: tps_lfl
Y = data["Tx_throughput"]
X = sm.add_constant(X)
mod_lvl = sm.OLS(Y, X)
res_lvl = mod_lvl.fit()
Y_predicted = res_lvl.predict(X)
# print(res_lvl.params)
print(res_lvl.summary())

# True Y (transaction throughput) vs predicted
plt.scatter(Y, Y_predicted, s=2)
plt.xlabel("Measured Transaction Throughput", fontsize=24, labelpad=20)
plt.ylabel("Predicted Transaction Throughput", fontsize=24, labelpad=20)
plt.xticks(fontsize=18)
plt.yticks(fontsize=18)
plt.plot(
    [np.min(Y_predicted), np.max(Y_predicted)],
    [np.min(Y_predicted), np.max(Y_predicted)],
    color="red",
)
# plt.show()
# print(X)

## latency
Y = data["Tx_confirm_latency"]
X = sm.add_constant(X)

mod_lvl = sm.OLS(Y, X)
res_lvl = mod_lvl.fit()

Y_predicted = res_lvl.predict(X)
plt.scatter(Y, Y_predicted, s=2, color="C2")
plt.xlabel("Measured Confirmation Latency", fontsize=24, labelpad=20)
plt.ylabel("Predicted Confirmation Latency", fontsize=24, labelpad=20)
plt.xticks(fontsize=18)
plt.yticks(fontsize=18)
plt.plot(
    [np.min(Y_predicted), np.max(Y_predicted)],
    [np.min(Y_predicted), np.max(Y_predicted)],
    color="red",
)
# plt.show()
print(res_lvl.summary())
