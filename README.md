# CFD\_IRP\_McLaren\_2024-2025

## Overview

This repository contains a configurable and modular workflow for running CFD simulations on McLaren geometries using OpenFOAM.

A map of the repository can be found by running 

```bash
singularity exec containers/container.sif python3 file_path_finder.py
```

which will produce a file called structure.txt

## Example Workflow

### Step 1: Prepare Geometry Files

* Extract the geometry archive:

  ```bash
  tar -xf src/Geometrys/Geometry.tar.xz
  ```
* Move the extracted `.stl` files into the following directory:

  ```
  Openfoam/AeroSUVNDC/constant/trisurface/Geometry/
  ```

> **Note:** All OpenFOAM case directories require geometry files to be placed under their relitive path, i.e. for AeroSUVDF: Openfoam/AeroSUVDF/constant/trisurface/Geometry/.


### Step 2: Configure the Simulation

Configuration files are located in:

```
src/configs/AeroSUVNDC/
```

This directory contains two types of YAML configuration files:

#### 1. **User Configs**

* Simplified interface for ease of use.
* Customize:

  * File paths
  * Initial conditions
  * Geometry selections
  * Time control parameters
* These files include in-line comments and instructions.

#### 2. **Advanced Configs**

* Control detailed OpenFOAM parameters:

  * Mesh generation
  * Solver settings
  * Advanced controls
* Recommended for experienced users. These files are also documented internally.

### Step 3: Run the Simulation

To run the simulation locally:

```bash
cd tests
./AeroSUVNDC.sh
```

> **Tip:** Submission scripts are provided for running simulations on HPC environments.

## What Happens in the Shell Script?

The `AeroSUVNDC.sh` script performs the following steps:

1. **Clean the Case**

   * Removes old mesh and simulation files.

2. **Load and Merge Geometry Files**

   * Loads multiple STL geometries.
   * Merges them into one combined geometry.
   * Saves to:

     ```
     (case)/constant/trisurface/Geometry/mergedGeometry/
     ```

3. **Scale Geometry**

   * Converts from millimeters to meters.
   * Scaling factor: `0.004` (the input geometry is at 1/4 scale in mm).

4. **Autogenerate OpenFOAM Case Files**

   * Uses the YAML config files to populate all necessary simulation inputs.

5. **Mesh Generation**

   * Runs `snappyHexMesh` to build the computational mesh.

6. **Run Simulation**

   * Solves the steady-state flow using `simpleFoam`.

7. **Post-Processing**

   * If running locally, automatically opens results in ParaView using `paraFoam`.

---

## Notes

* Make sure all paths and filenames match those specified in your user config file and shell script.
* If using an HPC cluster, adjust the shell script and config settings as necessary to match your environment.

---

For any issues or contributions, please raise an issue or submit a pull request.




