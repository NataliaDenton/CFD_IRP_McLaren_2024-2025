# Python-Based CFD Environment Container

This container provides a robust, Python-based computational environment for CFD post-processing, analysis, and data-driven workflows. It is designed to integrate easily with external OpenFOAM simulations while focusing on the Python scientific ecosystem.

## Included Tools

- **Base Image**: Ubuntu 22.04
- **Anaconda 2024.10** with the following packages:
  - **MPI and Parallel I/O**:
    - `mpich`, `mpi4py`
    - `hdf5` and `h5py` (MPI-enabled)
  - **Scientific Python Stack**:
    - `numpy`, `scipy`, `pandas`
    - `matplotlib`, `pyvista`, `tqdm`
    - `pyyaml`, `untangle`, `pytest`, `meshio`
  - **OpenFOAM Utilities for Python**:
    - `openfoamparser`, `ofparser`, `PyFoam`

## Conda Environment

A dedicated Conda environment named `mclaren-newenv` is automatically created during the build process and activated at runtime. All installed Python tools are available within this environment.

## Intended Use

This container is intended for:

- **CFD post-processing and visualization**
- **Workflow automation with PyFoam**
- **Custom tooling using `openfoamparser` and `ofparser`**
- **MPI-parallel I/O and analysis tasks**
- **Integration into high-performance compute environments using Apptainer/Singularity**

## Usage

To run a Python script inside the container:

```bash
apptainer run mycontainer.sif my_script.py
