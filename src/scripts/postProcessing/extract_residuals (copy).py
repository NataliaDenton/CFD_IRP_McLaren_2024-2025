import matplotlib.pyplot as plt
import pandas as pd

# Path to your .dat file
file_path = "forces.dat"

# Load the data while skipping header lines that start with '#'
df = pd.read_csv(file_path, 
                 delim_whitespace=True, 
                 comment='#', 
                 header=None)

# Assign column names according to the file structure
columns = ["Time", "Cd", "Cs", "Cl", "CmRoll", "CmPitch", "CmYaw",
           "Cd_f", "Cd_r", "Cs_f", "Cs_r", "Cl_f", "Cl_r"]
df.columns = columns

# Plot Cd, Cs, and Cl vs Time
plt.figure(figsize=(10, 6))
plt.plot(df["Time"], df["Cd"], label="$C_d$", color='r', linewidth=1.5)
plt.plot(df["Time"], df["Cs"], label="$C_s$", color='g', linewidth=1.5)
plt.plot(df["Time"], df["Cl"], label="$C_l$", color='b', linewidth=1.5)

plt.xlabel("Pseudo Time [s]", fontsize=12)
plt.ylabel("Force Coefficients", fontsize=12)
plt.title("Convergence of Force Coefficients vs Pseudo Time", fontsize=14)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()

