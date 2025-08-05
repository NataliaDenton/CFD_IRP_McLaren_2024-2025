#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import argparse
from pathlib import Path

# === PATH SETUP ===
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts

# === ARGUMENTS ===
p = argparse.ArgumentParser()
p.add_argument("--configDir", required=True)
args = p.parse_args()
configDir = Path(__file__).parent / args.configDir

# === LOAD CONFIGS ===
ConfigU = IO_fcts.load_config(configDir / "userConfig.yaml")
ConfigA = IO_fcts.load_config(configDir / "advancedConfig.yaml")

# === SINGLE CASE DIRECTORY ===
meshCase = Path(ConfigU["filePath"]["caseDir"])
case_name = meshCase.name  # use folder name for results

# === TIME WINDOW FOR AVERAGING ===
final_time = ConfigU["control"]["solver"]["endTime"]
average_start_time = ConfigU["control"]["solver"]["averageTimeStart"]
time_window = (average_start_time, final_time)

# === RESULT DIRECTORY ===
results_dir = Path(__file__).resolve().parent / "../../../Results" / case_name
results_dir.mkdir(parents=True, exist_ok=True)

# === FUNCTION: Load forceCoeffs data ===
def load_force_coeffs(case_path):
    file_path = Path(case_path) / "postProcessing/forceCoeffs/0/coefficient.dat"
    df = pd.read_csv(file_path, delim_whitespace=True, comment='#', header=None)
    columns = [
        "Time", "Cd", "Cs", "Cl", "CmRoll", "CmPitch", "CmYaw",
        "Cd_f", "Cd_r", "Cs_f", "Cs_r", "Cl_f", "Cl_r"
    ]
    df.columns = columns
    return df

# === LOAD DATA ===
df = load_force_coeffs(meshCase)

# === FILTER TIME WINDOW ===
df_filtered = df[(df["Time"] >= time_window[0]) & (df["Time"] <= time_window[1])]

# === COMPUTE MEAN & STD ===
coeffs = ["Cd", "Cs", "CmYaw"]
means = df_filtered[coeffs].mean()
stds = df_filtered[coeffs].std()

# === SAVE CSV ===
stats_df = pd.DataFrame({"Mean": means, "Std": stds})
csv_path = results_dir / "forceCoeffs_stats.csv"
stats_df.to_csv(csv_path)
print(f"[INFO] Saved statistics to: {csv_path}")

# === PLOT: Coefficients vs Time ===
plt.figure(figsize=(10, 6))
plt.plot(df["Time"], df["Cd"], label="$C_d$", color='r', linewidth=1.5)
plt.plot(df["Time"], df["Cs"], label="$C_s$", color='g', linewidth=1.5)
plt.plot(df["Time"], df["CmYaw"], label="$C_{m,yaw}$", color='b', linewidth=1.5)

plt.axvline(average_start_time, color='k', linestyle='--', alpha=0.5, label='Averaging Start')
plt.xlabel("Time [s]", fontsize=12)
plt.ylabel("Force Coefficients", fontsize=12)
plt.title(f"Force Coefficients vs Time ({case_name})", fontsize=14)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()

plot_path = results_dir / "forceCoeffs_vs_time.png"
plt.savefig(plot_path, dpi=300)
plt.close()
print(f"[INFO] Saved plot to: {plot_path}")

