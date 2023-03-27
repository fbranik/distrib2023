import os
import matplotlib.pyplot as plt
import numpy as np


def get_throughput_and_blocktime(file):
    with open(file, 'r') as f:
        timestamps = [float(line.strip()) for line in f.readlines()]

    timestamps = sorted(timestamps)
    total_time = timestamps[-1] - timestamps[0]
    num_transactions = len(timestamps)
    throughput = num_transactions / total_time
    block_times = np.diff(timestamps)
    avg_block_time = np.mean(block_times)

    return throughput, avg_block_time


def make_plots(nodes):
    difficulties = [4, 5]
    capacities = [1, 5, 10]

    throughputs_vs_difficulty = []
    throughputs_vs_capacity = []
    block_times_vs_difficulty = []
    block_times_vs_capacity = []

    for difficulty in difficulties:
        throughputs = []
        block_times = []
        for capacity in capacities:
            filename = f"tests_{nodes}n/test_c{capacity}_d{difficulty}.txt"
            throughput, avg_block_time = get_throughput_and_blocktime(filename)
            throughputs.append(throughput)
            block_times.append(avg_block_time)

        throughputs_vs_capacity.append(throughputs)
        block_times_vs_capacity.append(block_times)

    for capacity in capacities:
        throughputs = []
        block_times = []
        for difficulty in difficulties:
            filename = f"tests_{nodes}n/test_c{capacity}_d{difficulty}.txt"
            throughput, avg_block_time = get_throughput_and_blocktime(filename)
            throughputs.append(throughput)
            block_times.append(avg_block_time)

        throughputs_vs_difficulty.append(throughputs)
        block_times_vs_difficulty.append(block_times)

    # Throughput vs Capacity for all difficulties
    plt.figure(figsize=(10, 10))
    for i, difficulty in enumerate(difficulties):
        plt.plot(capacities, throughputs_vs_capacity[i], '-o', label=f"Difficulty {difficulty}")
        plt.xticks(capacities)
    plt.title("Throughput vs Capacity")
    plt.xlabel("Capacity")
    plt.ylabel("Throughput (transactions/second)")
    plt.legend()
    plt.grid()
    plt.savefig(f"Throughput vs Capacity_{nodes}nodes")

    # Throughput vs Difficulty for all capacities
    plt.figure(figsize=(10, 10))
    for i, capacity in enumerate(capacities):
        plt.plot(difficulties, throughputs_vs_difficulty[i], '-o', label=f"Capacity {capacity}")
        plt.xticks(difficulties)
    plt.title("Throughput vs Difficulty")
    plt.xlabel("Difficulty")
    plt.ylabel("Throughput (transactions/second)")
    plt.legend()
    plt.grid()
    plt.savefig(f"Throughput vs Difficulty_{nodes}nodes")

    # Block Time vs Capacity for all difficulties
    plt.figure(figsize=(10, 10))
    for i, difficulty in enumerate(difficulties):
        plt.plot(capacities, block_times_vs_capacity[i], '-x', label=f"Difficulty {difficulty}")
        plt.xticks(capacities)
    plt.title("Block Time vs Capacity")
    plt.xlabel("Capacity")
    plt.ylabel("Block Time (seconds)")
    plt.legend()
    plt.grid()
    plt.savefig(f"Block Time vs Capacity_{nodes}nodes")

    # Block Time vs Difficulty for all capacities
    plt.figure(figsize=(10, 10))
    for i, capacity in enumerate(capacities):
        plt.plot(difficulties, block_times_vs_difficulty[i], '-x', label=f"Capacity {capacity}")
        plt.xticks(difficulties)
    plt.title("Block Time vs Difficulty")
    plt.xlabel("Difficulty")
    plt.ylabel("Block Time (seconds)")
    plt.legend()
    plt.grid()
    plt.savefig(f"Block Time vs Difficulty_{nodes}nodes")

    return ([item for sublist in block_times_vs_difficulty for item in sublist],
            [item for sublist in throughputs_vs_difficulty for item in sublist])


n5_stasts = make_plots(5)
n10_stasts = make_plots(10)
nodes = [5, 10]
labels = ["capacity 1, difficulty 4", "capacity 1, difficulty 5", "capacity 5, difficulty 4",
          "capacity 5, difficulty 5", "capacity 10, difficulty 4", "capacity 10, difficulty 5"]

plt.figure(figsize=(10, 10))
for i, label in enumerate(labels):
    plt.plot(nodes, [n5_stasts[0][i], n10_stasts[0][i]], '-x', label=label)
    plt.xticks(nodes)
plt.title("Block Time Scalability")
plt.xlabel("Nodes")
plt.ylabel("Block Time (seconds)")
plt.legend()
plt.grid()
plt.savefig("Block Time Scalability")

plt.figure(figsize=(10, 10))
for i, label in enumerate(labels):
    plt.plot(nodes, [n5_stasts[1][i], n10_stasts[1][i]], '-o', label=label)
    plt.xticks(nodes)
plt.title("Throughput Scalability")
plt.xlabel("Nodes")
plt.ylabel("Throughput (transactions/second)")
plt.legend()
plt.grid()
plt.savefig("Thrughput Scalability")
