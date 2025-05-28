# suppl_fcts.py
import numpy as np

def compute_extended_bounds(points, scale):
    """Compute bounding box based on scale factors."""
    min_bounds = np.min(points, axis=0)
    max_bounds = np.max(points, axis=0)

    length = max_bounds[0] - min_bounds[0]
    width  = max_bounds[1] - min_bounds[1]
    height = max_bounds[2] - min_bounds[2]

    return {
        "x_min": min_bounds[0] - scale["front"] * length,
        "x_max": max_bounds[0] + scale["back"] * length,
        "y_min": min_bounds[1] - scale.get("side", 0) * width,
        "y_max": max_bounds[1] + scale.get("side", 0) * width,
        "z_min": min_bounds[2],
        "z_max": max_bounds[2] + scale["top"] * height,
    }

def format_vertices(bounds):
    """Return list of 8 vertices based on bounding box limits."""
    x0, x1 = bounds["x_min"], bounds["x_max"]
    y0, y1 = bounds["y_min"], bounds["y_max"]
    z0, z1 = bounds["z_min"], bounds["z_max"]

    return [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]

def print_vertices_block(vertices):
    """Print formatted OpenFOAM-style vertex block."""
    print("vertices\n(")
    for v in vertices:
        print(f"    ({v[0]:.6f} {v[1]:.6f} {v[2]:.6f})")
    print(");")

