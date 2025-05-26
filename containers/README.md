# CFD Environment Container

This container provides a ready-to-use computational environment for CFD workflows, combining OpenFOAM with a Python-based scientific stack via Conda.

## Included Tools

- **Ubuntu 22.04**
- **OpenFOAM 10** (installed system-wide)
- **Anaconda 2024.10** with:
  - MPI support (`mpich`, `mpi4py`)
  - Parallel HDF5 I/O (`hdf5`, `h5py`)
  - Scientific Python stack:
    - `numpy`, `scipy`, `pandas`
    - `pyvista`, `meshio`, `tqdm`, `pytest`
    - `pyyaml`, `untangle`

## Conda Environment

A Conda environment named `mclaren-newenv` is automatically created and activated on container start.

## Usage

This container is designed for use with **Apptainer** or **Singularity**.

To run a script inside the container:
```bash
apptainer run mycontainer.sif my_script.py

