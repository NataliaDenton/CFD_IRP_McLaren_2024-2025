import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# ========================
# User Settings
# ========================
mesh_cases = {
    "coarse": "../../Openfoam/unitCubecoarse",
    "medium": "../../Openfoam/unitCubemedium",
    "fine": "../../Openfoam/unitCubefine"
}

force_coeff_relpath = "postProcessing/forceCoeffs/0/coefficient.dat"
time_window = (8.0, 10.0)  # Time-averaging window in seconds

# Characteristic mesh sizes (example values, must correspond to your mesh refinement)
h_values = np.array([0.35, 0.25, 0.15])  # coarse, medium, fine

# ========================
# Helper Function to Load Force Coefficients
# ========================
def load_force_coeffs(case_path):
    file_path = Path(case_path) / force_coeff_relpath
    df = pd.read_csv(file_path, delim_whitespace=True, comment='#', header=None)
    columns = ["Time", "Cd", "Cs", "Cl", "CmRoll", "CmPitch", "CmYaw",
               "Cd_f", "Cd_r", "Cs_f", "Cs_r", "Cl_f", "Cl_r"]
    df.columns = columns
    return df

# ========================
# Load and Average Cd for Each Mesh
# ========================
Cd_means = {}

for mesh, path in mesh_cases.items():
    df = load_force_coeffs(path)
    df_filtered = df[(df["Time"] >= time_window[0]) & (df["Time"] <= time_window[1])]
    Cd_means[mesh] = df_filtered["Cd"].mean()

Cd_coarse = Cd_means["coarse"]
Cd_medium = Cd_means["medium"]
Cd_fine = Cd_means["fine"]

print(f"Cd values:\n  Coarse: {Cd_coarse}\n  Medium: {Cd_medium}\n  Fine: {Cd_fine}")

# ========================
# Calculate Refinement Ratios
# ========================
r_21 = h_values[0] / h_values[1]  # coarse to medium
r_32 = h_values[1] / h_values[2]  # medium to fine

print(f"Refinement ratios:\n  r_21 = {r_21:.3f}\n  r_32 = {r_32:.3f}")

# ========================
# Calculate Apparent Order of Accuracy p with oscillation handling
# ========================
diff1 = Cd_coarse - Cd_medium
diff2 = Cd_medium - Cd_fine

print(f"Debug: Cd_coarse - Cd_medium = {diff1}")
print(f"Debug: Cd_medium - Cd_fine = {diff2}")

ratio = diff1 / diff2

if ratio <= 0:
    print("Warning: Non-positive ratio detected due to oscillatory Cd values.")
    print("Using absolute values for ratio to compute apparent order p.")
    ratio = abs(diff1) / abs(diff2)

numerator = np.log(ratio)
denominator = np.log(r_21)
p = numerator / denominator

print(f"Apparent order of accuracy p = {p:.3f}")

# ========================
# Richardson Extrapolation (Using finest two meshes)
# ========================
Cd_ext = Cd_fine + (Cd_fine - Cd_medium) / (r_32**p - 1)
print(f"Richardson extrapolated Cd: {Cd_ext:.5f}")

# ========================
# Grid Convergence Index (GCI) Calculation
# ========================
Fs = 1.25  # Safety factor

GCI_fine = Fs * abs(Cd_fine - Cd_medium) / (Cd_fine * (r_32**p - 1)) * 100
print(f"GCI (fine mesh) = {GCI_fine:.3f} %")

# ========================
# Plot Cd vs h with Richardson Extrapolation
# ========================
plt.figure(figsize=(8, 6))
plt.plot(h_values, [Cd_coarse, Cd_medium, Cd_fine], 'o-', label="Computed $C_d$")
plt.hlines(Cd_ext, h_values[-1]*0.9, h_values[0]*1.1, colors='k', linestyles='dashed', label="Richardson Extrapolated $C_d$")
plt.xlabel("Mesh Characteristic Length $h$")
plt.ylabel("Drag Coefficient $C_d$")
plt.title("Grid Convergence and Richardson Extrapolation")
plt.legend()
plt.grid(True, which='both', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

