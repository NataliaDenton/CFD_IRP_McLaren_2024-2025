import os
import yaml
from pathlib import Path


def generate_blockMeshDict(vertices: list[list[float]], cell_counts) -> str:
    """
    Generate the content of the blockMeshDict file from bounding box vertices.
    
    Parameters:
    -----------
    vertices : list[list[float]]
        A list of 8 bounding box vertices in OpenFOAM order.
    cell_counts : tuple[int, int, int]
        Number of cells in x, y, and z directions.
    
    Returns:
    --------
    str
        Formatted blockMeshDict file content as a string.
    """
    vert_str = "\n".join(f"    ({' '.join(map(str, v))})" for v in vertices)
    content = f"""\
FoamFile {{
    version 2.0;
    format ascii;
    class dictionary;
    object blockMeshDict;
}}

scale 1.0;

vertices (
{vert_str}
);

blocks (
    hex (0 1 2 3 4 5 6 7) ({' '.join(map(str, cell_counts))}) simpleGrading (1 1 1)
);

edges ();

boundary (
    inlet  {{ type patch; faces ((0 4 7 3)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    bottom {{ type wall; faces ((0 1 5 4)); }}
    top    {{ type symmetryPlane; faces ((3 2 6 7)); }}
    front  {{ type symmetryPlane; faces ((0 1 2 3)); }}
    back   {{ type symmetryPlane; faces ((4 5 6 7)); }}
);

mergePatchPairs ();
"""
    return content

def generate_surfaceFeatureExtractDict(geometry_path, extractAngle):
   
    geometry_filename = os.path.basename(geometry_path)

    content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      surfaceFeatureExtractDict;
}}

extractionMethod    extractFromSurface;

extractFromSurfaceCoeffs
{{
    // Name of the STL file in constant/triSurface folder
    file    "{geometry_filename}";

    // Angle to detect sharp edges, degrees
    extractAngle    {extractAngle};
}}

writeObjFeatures    yes;

"""
    return content



def write_field_file(field_name: str, config: dict, case_dir: str):
    """
    Write OpenFOAM field file (e.g., U, p, k, epsilon, nut) to the '0/' directory.

    Args:
        field_name: Name of the field (e.g., "U", "p", "k").
        config: Parsed YAML config dictionary from config_0.yaml.
        case_dir: Path to the OpenFOAM case directory.
    """

    # --- Ensure config section exists ---
    if field_name not in config:
        raise KeyError(f"Missing '{field_name}' section in config_0.yaml.")

    field_cfg = config[field_name]
    dimensions = ' '.join(map(str, field_cfg["dimensions"]))
    internal = field_cfg["internalField"]
    if isinstance(internal, list):
        internal_field = f"({ ' '.join(map(str, internal)) })"
        field_type = "volVectorField"
    else:
        internal_field = str(internal)
        field_type = "volScalarField"

    # --- Read mesh boundaries from 'constant/polyMesh/boundary' ---
    boundary_path = Path(case_dir) / "constant" / "polyMesh" / "boundary"
    with open(boundary_path, 'r') as f:
        lines = f.readlines()

    mesh_boundaries = []
    for i, line in enumerate(lines):
        if line.strip().endswith('{'):
            previous = lines[i - 1].strip()
            if previous:
                mesh_boundaries.append(previous)

    # --- Construct boundaryField ---
    boundary_field = ""
    user_boundaries = field_cfg.get("boundaries", {})

    for boundary in mesh_boundaries:
        b_type = "zeroGradient"
        b_value = ""

        if boundary in user_boundaries:
            entry = user_boundaries[boundary]
            b_type = entry["type"]
            special_pure_patch_types = [
                 "symmetryPlane", "empty", "wedge", "cyclic", "processor", "symmetry"
            ]
            
            if b_type in special_pure_patch_types:
                b_value = ""  # No value required
            elif b_type in ["fixedValue", "calculated", "nutkWallFunction",
                "kqRWallFunction", "epsilonWallFunction"]:

                val = entry.get("value", None)
                if isinstance(val, list):
                    b_value = f"        value           uniform ({' '.join(map(str, val))});\n"
                elif isinstance(val, (float, int, str)):
                    if b_type in ["nutkWallFunction", "epsilonWallFunction", "kqRWallFunction"]:
                    # Wall functions require a raw scalar, NOT 'uniform'
                        b_value = f"        value           {val};\n"
                    else:
                        b_value = f"        value           uniform {val};\n"

            elif b_type == "noSlip":
                b_type = "fixedValue"
                b_value = "        value           uniform (0 0 0);\n"

        boundary_field += f"""    {boundary}
    {{
        type            {b_type};
{b_value}    }}\n\n"""

    # --- Write file to 0/<field_name> ---
    field_file_path = Path(case_dir) / "0" / field_name
    with open(field_file_path, 'w') as f:
        f.write(f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  2312                                  |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/

FoamFile
{{
    version     2.0;
    format      ascii;
    class       {field_type};
    location    "0";
    object      {field_name};
}}

dimensions      [{dimensions}];

internalField   uniform {internal_field};

boundaryField
{{
{boundary_field}}}
""")

    print(f"✅ Generated '0/{field_name}'.")


def write_all_fields(config_path: str, case_dir: str):
    """
    Wrapper to write all fields listed in the config YAML.

    Args:
        config_path: Path to config_0.yaml
        case_dir: OpenFOAM case path
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    field_list = config.get("fields", [])
    if not field_list:
        raise ValueError("No 'fields' key found in config_0.yaml.")

    for field in field_list:
        write_field_file(field, config, case_dir)



