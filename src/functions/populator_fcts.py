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

def generate_surfaceFeatureExtractDict(geometry_dict, extract_angle):
    surface_entries = []

    for name, info in geometry_dict.items():
        geometry_path = info["file"]
        geometry_filename = os.path.basename(geometry_path)

        entry = f"""\
        {name}
        {{
            extractionMethod    extractFromSurface;

            extractFromSurfaceCoeffs
            {{
                file            "Geometry/{geometry_filename}";
                extractAngle   {extract_angle};
            }}

            writeObjFeatures    yes;
        }}"""
        surface_entries.append(entry)

    surfaces_block = "surfaces\n{\n" + "\n\n".join(surface_entries) + "\n}\n"

    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version: 2312                                   |
|   \\  /    A nd           | Web:      www.OpenFOAM.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/

FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      surfaceFeatureExtractDict;
}}

// ************************************************************************* //

{surfaces_block}
"""


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

def populate_transportProperties(config, case_dir):
    with open(config, 'r') as f:
        config = yaml.safe_load(f)
    transport_config = config['fluid']
    filepath = os.path.join(case_dir, 'constant', 'transportProperties')

    lines = [
        "/*--------------------------------*- C++ -*----------------------------------*\\",
        "| =========                 |                                                 |",
        "| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |",
        "|  \\    /   O peration     | Version:  v2212 or later                         |",
        "|   \\  /    A nd           | Web:      www.OpenFOAM.com                      |",
        "|    \\/     M anipulation  |                                                 |",
        "\\*---------------------------------------------------------------------------*/",
        "FoamFile",
        "{",
        "    version     2.0;",
        "    format      ascii;",
        "    class       dictionary;",
        "    location    \"constant\";",
        "    object      transportProperties;",
        "}",
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //",
        f"transportModel  Newtonian;",
        f"nu              [0 2 -1 0 0 0 0] {transport_config['nu']};",
        "",
        "// ************************************************************************* //"
    ]

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))

def populate_turbulenceProperties(config, case_dir):
    with open(config, 'r') as f:
        config = yaml.safe_load(f)
    turb_config = config['turbulence']
    filepath = os.path.join(case_dir, 'constant', 'turbulenceProperties')
    turbulence_value = "on" if config['turbulence']['RAS']['turbulence'] == "on" else "off"
    printCoeffs_value = "on" if config['turbulence']['RAS']['printCoeffs'] == "on" else "off"
    lines = [
        "/*--------------------------------*- C++ -*----------------------------------*\\",
        "| =========                 |                                                 |",
        "| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |",
        "|  \\    /   O peration     | Version:  v2212 or later                         |",
        "|   \\  /    A nd           | Web:      www.OpenFOAM.com                      |",
        "|    \\/     M anipulation  |                                                 |",
        "\\*---------------------------------------------------------------------------*/",
        "FoamFile",
        "{",
        "    version     2.0;",
        "    format      ascii;",
        "    class       dictionary;",
        "    location    \"constant\";",
        "    object      turbulenceProperties;",
        "}",
        "// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //",
        f"simulationType  {turb_config['simulationType']};",
        "",
        f"{turb_config['simulationType']}",
        "{",
        f"    RASModel        {turb_config['model']};",
        f"    turbulence      {turbulence_value};",
        f"    printCoeffs     {printCoeffs_value};",
        "}",
        "",
        "// ************************************************************************* //"
    ]

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))





import os

def generate_controlDict(control_params):
    return f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}}

application     {control_params.get("application", "snappyHexMesh")};
startFrom       startTime;
startTime       {control_params.get("startTime", 0)};
stopAt          endTime;
endTime         {control_params.get("endTime", 1)};
deltaT          {control_params.get("deltaT", 1)};
writeControl    timeStep;
writeInterval   {control_params.get("writeInterval", 1)};
purgeWrite      {control_params.get("purgeWrite", 0)};
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable yes;
"""


def generate_fvSchemes():
    return """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}

// Default discretisation schemes
ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
    grad(p)         Gauss linear;
    grad(U)         Gauss linear;
}

divSchemes
{
    div(phi,U)           Gauss linearUpwind grad(U);
    div(phi,k)           Gauss upwind;
    div(phi,epsilon)     Gauss upwind;
    div((nuEff*dev2(T(grad(U)))))  Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

fluxRequired
{
    default         no;
    p;
}
"""

def generate_fvSolution():
    return """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}

solvers
{
p
    {
        solver          GAMG;
        tolerance       1e-10;
        relTol          1e-20;
        smoother        GaussSeidel;
        nPreSweeps      0;
        nPostSweeps     2;
        cacheAgglomeration true;
        aggressiveCoeffs 1;
        mergeLevels     1;
    }


    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e8;
        relTol          1e-20;
    }

    k
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          1e-20;
    }

    epsilon
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          1e-20;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
    residualControl
    {
        p               1e-7;
        U               1e-7;
        "(k|epsilon)"   1e-8;
    }
}

relaxationFactors
{
    fields
    {
        p               0.3;
    }
    equations
    {
        U               0.7;
        k               0.7;
        epsilon         0.7;
    }
}
"""

def generate_snappyHexMeshDict(shm_config):
    # --- Build geometry and refinement entries ---
    geometry_entries = []
    refinement_entries = []

    for name, geo in shm_config["geometry"].items():
        stl_file = os.path.basename(geo["file"])
        refinement = geo["refinementLevel"]
        geometry_entries.append(
            f'    {name}\n    {{\n        type triSurfaceMesh;\n        file "{stl_file}";\n    }}'
        )
        refinement_entries.append(
            f'    {name} {{ level ({refinement[0]} {refinement[1]}); }}'
        )

    geometry_block = "\n".join(geometry_entries)
    refinement_block = "\n".join(refinement_entries)
    
    return f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}

castellatedMesh {str(shm_config.get("castellatedMesh", True)).lower()};
snap            {str(shm_config.get("snap", True)).lower()};
addLayers       {str(shm_config.get("addLayers", False)).lower()};

geometry
{{
    Geometry
    {{
        type    triSurfaceMesh;
        file    "Geometry/{stl_file}";
    }}
}}
castellatedMeshControls
{{
    maxLocalCells 1000000;
    maxGlobalCells 2000000;
    minRefinementCells 10;
    nCellsBetweenLevels 3;

    features ();

    refinementSurfaces
    {{
{refinement_block}
    }}

    resolveFeatureAngle 30;
    refinementRegions {{}}
    locationInMesh (0 0 0);
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
}}

addLayersControls
{{
    relativeSizes true;
    layers {{}}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
    nRelaxedIter 20;
}}

meshQualityControls {{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-9;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale            4;
    errorReduction          0.75;
}}

debug 0;
mergeTolerance 1E-6;
"""

