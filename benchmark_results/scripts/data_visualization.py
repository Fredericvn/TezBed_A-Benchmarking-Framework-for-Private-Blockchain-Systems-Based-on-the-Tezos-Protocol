import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

workload_lvl = [10, 25, 40, 55, 70, 85, 90, 95, 100, 105]
SMALL_SIZE = 11
MEDIUM_SIZE = 18
BIGGER_SIZE = 24

## Add path to data results
DIRECTORY = "/Users/frederic/automation-of-dl-network-setup-and-testing-with-ansible/benchmark_results/data/"


def read_csv(file_path: str):
    df = pd.read_csv(
        f"{DIRECTORY}{file_path}",
        sep=",",
        header=0,
    )
    return df


def convert_to_np_array(df, level: bool):
    if level:
        # create list of dataframes per workload level
        df_lvl = [
            df.query(f"workload_lvl == {lvl}", inplace=False) for lvl in workload_lvl
        ]

        pd.set_option("display.max.columns", None)
        np_arr_level = [lvl.to_numpy(dtype=None, copy=False) for lvl in df_lvl]
        return np_arr_level
    else:
        pd.set_option("display.max.columns", None)
        return df.to_numpy(dtype=None, copy=False)


def make_3d_graph(
    data_arr,
    title: str,
    level: bool,
    heatmap_i: int,
    vmin: float,
    vmax: float,
    s_size: float,
    s_invert: bool,
    hcolor=None,
    size_i=None,
):
    fig_tps = plt.figure()
    ax = fig_tps.add_subplot(111, projection="3d")

    if level:
        x = data_arr[:, 2]  # block size limit
        y = data_arr[:, 3]  # block creation interval
        z = data_arr[:, 4]  # network size
    else:
        x = data_arr[:, 1]  # block size limit
        y = data_arr[:, 2]  # block creation interval
        z = data_arr[:, 3]  # network size

    c = data_arr[:, heatmap_i]  # heatmap

    if size_i is not None:
        c_size = s_size  # circle size
        if s_invert:
            s = [c_size / x for x in data_arr[:, size_i]]  # inverted
        else:
            s = [x * c_size for x in data_arr[:, size_i]]  # classic

    else:
        s = s_size

    ax.set_xlabel(
        "Block Size Limit\n(Hard Gas Limit)", labelpad=40, fontsize=MEDIUM_SIZE
    )
    ax.set_xticks(np.append([28400], np.arange(1500000, 9000000, step=1500000)))
    ax.set_xticklabels(
        ["28,400", "1,500,000", "3,000,000", "4,500,000", "6,000,000", "7,500,000"],
        rotation=-40,
        fontsize=SMALL_SIZE,
    )

    ax.set_ylabel(
        "Block Creation Interval\n (Min Block Delay)", labelpad=20, fontsize=MEDIUM_SIZE
    )
    ax.set_yticks(np.append([7], np.arange(20, 140, step=20)))
    ax.set_yticklabels([7, 20, 40, 60, 80, 100, 120], fontsize=SMALL_SIZE)

    ax.set_zlabel("Network Size\n(Number of Nodes)", labelpad=10, fontsize=MEDIUM_SIZE)
    ax.set_zticks(np.arange(6, 146, step=20), fontsize=SMALL_SIZE)

    # Title
    ax.set_title(title, fontsize=15)

    if hcolor is None:
        img = ax.scatter(
            x, y, z, c=c, cmap=plt.hot(), s=s, vmin=vmin, vmax=vmax, marker="o"
        )
        fig_tps.colorbar(img)
    if hcolor == "gnuplot2_r":
        img = ax.scatter(
            x, y, z, c=c, cmap=plt.cm.gnuplot2_r, s=s, vmin=vmin, vmax=vmax, marker="p"
        )
        fig_tps.colorbar(img)

    plt.show()


def make_histrogram(data):
    ## set seaborn as default style
    sns.set()

    plt.rc("font", size=MEDIUM_SIZE)  # controls default text sizes
    plt.rc("axes", titlesize=MEDIUM_SIZE)  # fontsize of the axes title
    plt.rc("axes", labelsize=BIGGER_SIZE)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=MEDIUM_SIZE)  # legend fontsize
    plt.rc("figure", titlesize=BIGGER_SIZE)

    fig, ax = plt.subplots(1, 3, sharey=True)
    fig.tight_layout()

    sns.histplot(
        ax=ax[0],
        data=data,
        x="number_nodes_exp",
        label="Network Size\n(Number of Nodes)",
        color="navy",
        bins=50,
    )
    ax[0].set_ylabel("Count of Experiments", labelpad=15)
    ax[0].set_xlabel("[nodes]", labelpad=15)
    ax[0].legend()
    ax[0].set_xticks(np.arange(6, 146, step=20))

    sns.histplot(
        ax=ax[1],
        data=data,
        x="minimal_block_delay",
        label="Block Creation Interval\n(Min Block Delay)",
        color="teal",
        bins=50,
    )
    ax[1].set_ylabel("")
    ax[1].set_xlabel("[seconds]", labelpad=15)
    ax[1].legend()
    ax[1].set_xticks(np.append([7], np.arange(20, 140, step=20)))
    ax[1].set_xticklabels([7, 20, 40, 60, 80, 100, 120])

    sns.histplot(
        ax=ax[2],
        data=data,
        x="block_gas_limit",
        label="Block Size Limit\n(Hard Gas Limit)",
        color="darkred",
        bins=50,
    )
    ax[2].set_ylabel("")
    ax[2].set_xlabel("[gas]", labelpad=15)
    ax[2].legend()
    ax[2].set_xticks(np.append([28400], np.arange(1500000, 9000000, step=1500000)))
    ax[2].set_xticklabels(
        ["28,400", "1,500,000", "3,000,000", "4,500,000", "6,000,000", "7,500,000"],
        rotation=-45,
    )

    plt.legend()
    plt.show()


def make_boxplot(data_arr, indicator_i: int, indicator_name: str):
    ## set seaborn as default style
    sns.set()

    plt.rc("font", size=BIGGER_SIZE)  # controls default text sizes
    plt.rc("axes", titlesize=BIGGER_SIZE)  # fontsize of the axes title
    plt.rc("axes", labelsize=BIGGER_SIZE)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=BIGGER_SIZE)  # legend fontsize
    plt.rc("figure", titlesize=BIGGER_SIZE)
    fig, ax = plt.subplots()

    data = [x[:, indicator_i] for x in data_arr]
    ax.boxplot(data)
    ax.set_xticklabels(workload_lvl, fontsize=MEDIUM_SIZE)
    ax.set_xlabel("Workload Level [% of CTPS]", labelpad=20, fontsize=BIGGER_SIZE)
    ax.set_ylabel(f"{indicator_name}", labelpad=20, fontsize=BIGGER_SIZE)
    plt.show()


np_arr_lvl = convert_to_np_array(read_csv("tx_throughput_and_latency.csv"), True)

##################################################
## Set path to data                             ##
## Uncomment to create the corresponding plot!  ##
##                                              ##
##################################################


# 3D system configurations + throughput=heatmap + latency=size loop over all levels
# for lvl, data_lvl in enumerate(np_arr_lvl):
#     make_3d_graph(
#         data_lvl,
#         f"Transaction Throughput and Confirmation Latency - Workload Level {workload_lvl[lvl]}%",
#         True,
#         heatmap_i=5,
#         vmin=0,
#         vmax=450,
#         s_size=300,
#         s_invert=True,
#         size_i=6,
#     )


# 3D system configurations + throughput=heatmap + latency=size for one level
# make_3d_graph(
#     np_arr_lvl[9],
#     f"Transaction Throughput and Confirmation Latency - Workload Level {workload_lvl[9]}%",
#     True,
#     heatmap_i=5,
#     vmin=0,
#     vmax=450,
#     s_size=500,
#     s_invert=True,
#     size_i=6,
# )

# make_3d_graph(
#     np_arr_lvl[9],
#     f"Confirmation Latency - Workload Level {workload_lvl[9]}%",
#     True,
#     heatmap_i=6,
#     vmin=0,
#     vmax=150,
#     s_size=30,
#     s_invert=False,
# )

# make_3d_graph(
#     np_arr_lvl[9],
#     f"Ratio Transaction Throughput - Workload Level {workload_lvl[9]}%",
#     True,
#     heatmap_i=7,
#     vmin=0,
#     vmax=1,
#     s_size=50,
#     s_invert=False,
#     hcolor="gnuplot2_r",
# )

# make_3d_graph(
#     np_arr_lvl[9],
#     f"Ratio Confirmation Latency - Workload Level {workload_lvl[9]}%",
#     True,
#     heatmap_i=8,
#     vmin=0,
#     vmax=2,
#     s_size=50,
#     s_invert=False,
#     hcolor="gnuplot2_r",
# )

# np_arr = convert_to_np_array(read_csv("CPL_with_configuration.csv"), False)
# make_3d_graph(
#     np_arr,
#     "Average CPU Load per Experiment",
#     False,
#     heatmap_i=4,
#     vmin=0,
#     vmax=0.25,
#     s_size=50,
#     s_invert=False,
#     hcolor="gnuplot2_r",
# )

# np_arr = convert_to_np_array(read_csv("DSK_with_configuration.csv"), False)
# make_3d_graph(
#     np_arr,
#     "Average Disk Time Spent for I/O per Experiment",
#     False,
#     heatmap_i=4,
#     vmin=0,
#     vmax=80,
#     s_size=50,
#     s_invert=False,
#     hcolor="gnuplot2_r",
# )

dataf = read_csv("experiment_vars.csv")
make_histrogram(dataf)

# make_boxplot(np_arr_lvl, indicator_i=5, indicator_name="Transaction Throughput [Tps]")
# make_boxplot(np_arr_lvl, indicator_i=6, indicator_name="Confirmation Latency [sec]")
