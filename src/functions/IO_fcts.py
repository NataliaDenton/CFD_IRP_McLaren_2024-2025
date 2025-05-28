# IO_fcts.py
import yaml
from stl import mesh
import json
import numpy as np
import os

def load_config(config_path):
    """Load YAML configuration file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def load_geometry(stl_path):
    """Load STL file and return reshaped vertex array."""
    geometry = mesh.Mesh.from_file(stl_path)
    return geometry.vectors.reshape(-1, 3)


def save_vertices(vertices, out_path):
    # Convert all elements in vertices to native Python float
    cleaned_vertices = [[float(coord) for coord in vertex] for vertex in vertices]
    data = {"vertices": cleaned_vertices}
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Bounding box vertices saved to: {out_path}")


def load_vertices(json_path: str) -> np.ndarray:
    """
    Load bounding box vertices from a JSON file.
    """
    with open(json_path, "r") as f:
        data = json.load(f)
    return np.array(data["vertices"])

