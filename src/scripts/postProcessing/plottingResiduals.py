#!/usr/bin/env python3
import re
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
case_name = meshCase.name  # folder name for results

# === RESULT DIRECTORY ===
results_dir = Path(__file__).resolve().parent / "../../../Results" / case_name
results_dir.mkdir(parents=True, exist_ok=True)

# === LOG FILE PATH ===
log_file = meshCase / "log" / "simpleFoam.log"
if not log_file.exists():
    raise FileNotFoundError(f"Log file not found: {log_file}")

# === EXTRACT Ux RESIDUALS ===
pattern_Ux = re.compile(r"Solving for Ux.*Initial residual = ([\deE\.\+-]+)")
residuals_Ux = []

with open(log_file, 'r') as f:
    for line in f:
        match = pattern_Ux.search(line)
        if match:
            residuals_Ux.append(float(match.group(1)))

if not residuals_Ux:
    raise ValueError("No Ux residuals found in the log file!")

# === PLOT ===
plt.figure(figsize=(10, 6))
plt.semilogy(range(1, len(residuals_Ux)+1), residuals_Ux, label="Ux Residual", color='b', linewidth=2)

# Convergence threshold
plt.axhline(y=1e-4, color="black", linestyle="--", linewidth=1, label="Convergence Threshold")

plt.xlabel("Solver Iteration", fontsize=12)
plt.ylabel("Ux Residual (log scale)", fontsize=12)
plt.title(f"Ux Residual Convergence ({case_name})", fontsize=14)
plt.legend(loc="upper right", fontsize=10)
plt.grid(True, which="both", linestyle='--', alpha=0.6)
plt.tight_layout()

# === SAVE PLOT ===
plot_path = results_dir / "Ux_residuals.png"
plt.savefig(plot_path, dpi=300)
plt.close()
print(f"[INFO] Residual plot saved to: {plot_path}")

