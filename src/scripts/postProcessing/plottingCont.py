#!/usr/bin/env python3
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import argparse
import sys

# === ARGUMENTS ===
p = argparse.ArgumentParser()
p.add_argument("--configDir", required=True, help="Path to config directory containing userConfig.yaml")
args = p.parse_args()
configDir = Path(__file__).parent / args.configDir

# === LOAD CONFIGS ===
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))
import IO_fcts

ConfigU = IO_fcts.load_config(configDir / "userConfig.yaml")

# === SINGLE MESH CASE DIRECTORY ===
caseDir = Path(ConfigU["filePath"]["caseDir"])
case_name = caseDir.name

# === TIME WINDOW FOR FILTERING ===
start_time = ConfigU.get("control", {}).get("solver", {}).get("averageTimeStart", 0.0)
end_time = ConfigU.get("control", {}).get("solver", {}).get("endTime", 10.0)

# === RESULT DIRECTORY ===
results_dir = Path(__file__).resolve().parent / "../../../Results" / case_name
results_dir.mkdir(parents=True, exist_ok=True)

# === Path to continuity error file for the single mesh ===
continuity_file = caseDir.parent / case_name / "postProcessing" / "continuityErrors" / "0" / "continuityError.dat"

if not continuity_file.exists():
    raise FileNotFoundError(f"Continuity error file not found: {continuity_file}")

# === LOAD DATA ===
df = pd.read_csv(continuity_file, delim_whitespace=True, comment='#', header=None)
df.columns = ["Time", "local", "Global", "Cumulative"]

# === FILTER BY TIME WINDOW ===
df_filtered = df[(df["Time"] >= start_time) & (df["Time"] <= end_time)]

# === PLOTTING ===
plt.figure(figsize=(10, 6))
plt.plot(df_filtered["Time"], df_filtered["Cumulative"], label="Cumulative", color='r', linewidth=1.5)
plt.xlabel("Pseudo Time [s]", fontsize=12)
plt.ylabel("Cumulative errors", fontsize=12)
plt.title(f"Continuity Error Convergence for {case_name}", fontsize=14)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()

# === SAVE FIGURE ===
plot_path = results_dir / "continuityError_convergence.png"
plt.savefig(plot_path, dpi=300)
plt.close()

print(f"[INFO] Continuity error convergence plot saved to: {plot_path}")

