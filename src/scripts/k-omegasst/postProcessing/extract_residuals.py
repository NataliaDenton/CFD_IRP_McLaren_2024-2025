#!/usr/bin/env python3
import argparse
import re
import os
import pandas as pd
import matplotlib.pyplot as plt

def extract_residuals(log_path):
    """Extract initial residuals from a simpleFoam log file."""
    residual_data = []
    current_time = None

    with open(log_path, 'r') as f:
        for line in f:
            time_match = re.match(r"Time = ([\dEe\+\-\.]+)", line)
            if time_match:
                current_time = float(time_match.group(1))
                continue

            match = re.search(r"Solving for (\w+), Initial residual = ([\dEe\+\-\.]+)", line)
            if match and current_time is not None:
                var, res = match.groups()
                residual_data.append({"Time": current_time, "Variable": var, "Residual": float(res)})

    return pd.DataFrame(residual_data)


def plot_residuals(df, output_plot):
    """Generate a semilog-y plot of residuals."""
    pivot_df = df.pivot(index="Time", columns="Variable", values="Residual")

    plt.figure(figsize=(10, 6))
    for col in pivot_df.columns:
        plt.semilogy(pivot_df.index, pivot_df[col], label=col)
    plt.xlabel("Simulation Time")
    plt.ylabel("Initial Residual (log scale)")
    plt.title("Residual Convergence")
    plt.legend()
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(output_plot, dpi=300)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Extract and plot OpenFOAM residuals from log file.")
    parser.add_argument("--logFile", required=True, help="Path to simpleFoam log file.")
    parser.add_argument("--outDir", required=True, help="Directory to save CSV and plot.")
    args = parser.parse_args()

    os.makedirs(args.outDir, exist_ok=True)
    csv_path = os.path.join(args.outDir, "residuals.csv")
    plot_path = os.path.join(args.outDir, "residuals_plot.png")

    print(f"📄 Parsing residuals from: {args.logFile}")
    df = extract_residuals(args.logFile)

    print(f"💾 Saving CSV to: {csv_path}")
    df.to_csv(csv_path, index=False)

    print(f"📊 Plotting residuals to: {plot_path}")
    plot_residuals(df, plot_path)

    print("✅ Residual extraction and plotting complete.")


if __name__ == "__main__":
    main()

