#!/usr/bin/env python3

import pandas as pd
import numpy as np
import os
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

user_CONFIG_PATH = configDir / "userConfig.yaml"
advanced_configs_PATH = configDir / "advancedConfig.yaml"

# === LOAD CONFIGS ===
ConfigU = IO_fcts.load_config(user_CONFIG_PATH)
ConfigA = IO_fcts.load_config(advanced_configs_PATH)

# === FORCE COEFF ANALYSIS ===
filename = "postProcessing/forceCoeffs/0/coefficient.dat"
final_time = ConfigU["control"]["solver"]["endTime"]
average_start_time = ConfigU["control"]["solver"]["averageTimeStart"]
average_last_seconds = final_time - average_start_time

if not os.path.exists(filename):
    raise FileNotFoundError(f"{filename} does not exist!")

columns = [
    "Time", "Cd", "Cs", "Cl",
    "CmRoll", "CmPitch", "CmYaw",
    "Cd(f)", "Cd(r)", "Cs(f)", "Cs(r)",
    "Cl(f)", "Cl(r)"
]

df = pd.read_csv(filename, delim_whitespace=True, comment="#", names=columns)
t_start = final_time - average_last_seconds
df_filtered = df[df["Time"] >= t_start]
means = df_filtered.mean(numeric_only=True)

print(f"\nAveraged force coefficients from t = {t_start} s to {final_time} s:\n")
for col in df.columns[1:]:
    print(f"{col:8s} : {means[col]: .6f}")

