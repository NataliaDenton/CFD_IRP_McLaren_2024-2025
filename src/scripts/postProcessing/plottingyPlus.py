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

# === RESULT DIRECTORY ===
results_dir = Path(__file__).resolve().parent / "../../../Results" / case_name
results_dir.mkdir(parents=True, exist_ok=True)

# === PATH TO yPlus.dat FILE ===
yplus_file = caseDir.parent / case_name / "postProcessing" / "yPlus" / "0" / "yPlus.dat"

if not yplus_file.exists():
    raise FileNotFoundError(f"yPlus.dat file not found: {yplus_file}")

# === FUNCTION TO LOAD AND FILTER yPlus DATA ===
def load_yplus_average(filepath):
    df = pd.read_csv(filepath, sep='\s+', header=None,
                     names=["Time", "patch", "min", "max", "average"],
                     on_bad_lines='skip')  # skip malformed lines
    df_geometry = df[df["patch"] == "Geometry"]
    return df_geometry[["Time", "average"]]

# === LOAD DATA ===
df_yplus = load_yplus_average(yplus_file)

# Optional: filter by time range if desired, e.g.
# start_time = ConfigU.get("control", {}).get("solver", {}).get("averageTimeStart", 0.0)
# end_time = ConfigU.get("control", {}).get("solver", {}).get("endTime", 10.0)
# df_yplus = df_yplus[(df_yplus["Time"] >= start_time) & (df_yplus["Time"] <= end_time)]

# === PLOTTING ===
plt.figure(figsize=(10, 6))
plt.plot(df_yplus["Time"], df_yplus["average"], label=f"{case_name} Mesh", color='blue', linewidth=1.5)
plt.xlabel("Time [s]", fontsize=12)
plt.ylabel("Average y+", fontsize=12)
plt.title(f"Average y+ vs Time for 'Geometry' Patch - {case_name}", fontsize=14)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()

# === SAVE FIGURE ===
plot_path = results_dir / "average_yPlus_vs_time.png"
plt.savefig(plot_path, dpi=300)
plt.close()

print(f"[INFO] Average y+ vs Time plot saved to: {plot_path}")

