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
    bottom {{ type wall; faces ((0 1 2 3)); }}
    top    {{ type symmetryPlane; faces ((4 7 6 5)); }}
    front  {{ type symmetryPlane; faces ((0 4 5 1)); }}
    back   {{ type symmetryPlane; faces ((3 2 6 7)); }}
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
    turbulence_value = "on" if config['turbulence']['RAS']['turbulence'] == True else "off"
    printCoeffs_value = "on" if config['turbulence']['RAS']['printCoeffs'] == True else "off"
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

    runTimeModifiable = "yes" if control_params['runTimeModifiable'] == True else "no"

    return f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}}

application     {control_params["application"]};
startFrom       {control_params["startFrom"]};
startTime       {control_params["startTime"]};
stopAt          {control_params["stopAt"]};
endTime         {control_params["endTime"]};
deltaT          {control_params["deltaT"]};
writeControl    {control_params["writeControl"]};
writeInterval   {control_params["writeInterval"]};
purgeWrite      {control_params["purgeWrite"]};
writeFormat     {control_params["writeFormat"]};
writePrecision  {control_params["writePrecision"]};
writeCompression {control_params["writeCompression"]};
timeFormat      {control_params["timeFormat"]};
timePrecision   {control_params["timePrecision"]};
runTimeModifiable {runTimeModifiable};
"""

def generate_fvSchemes(config):
    return f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}}

// Default discretisation schemes
ddtSchemes
{{
    default         {config["ddtSchemes"]["default"]};
}}

gradSchemes
{{
    default         {config["gradSchemes"]["default"]};
    grad(p)         {config["gradSchemes"]["grad(p)"]};
    grad(U)         {config["gradSchemes"]["grad(U)"]};
}}

divSchemes
{{
    div(phi,U)                      {config["divSchemes"]["div(phi,U)"]};
    div(phi,k)                      {config["divSchemes"]["div(phi,k)"]};
    div(phi,epsilon)               {config["divSchemes"]["div(phi,epsilon)"]};
    div((nuEff*dev2(T(grad(U)))))  {config["divSchemes"]["div((nuEff*dev2(T(grad(U)))))"]};
}}

laplacianSchemes
{{
    default         {config["laplacianSchemes"]["default"]};
}}

interpolationSchemes
{{
    default         {config["interpolationSchemes"]["default"]};
}}

snGradSchemes
{{
    default         {config["snGradSchemes"]["default"]};
}}

fluxRequired
{{
    default         {config["fluxRequired"]["default"]};
    p;
}}
"""
def generate_fvSolution(config):

    cacheAgglomeration = "on" if config['solvers']['p']['cacheAgglomeration'] == True else "off"
    return f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}}

solvers
{{
    p
    {{
        solver          {config["solvers"]["p"]["solver"]};
        tolerance       {config["solvers"]["p"]["tolerance"]};
        relTol          {config["solvers"]["p"]["relTol"]};
        smoother        {config["solvers"]["p"]["smoother"]};
        nPreSweeps      {config["solvers"]["p"]["nPreSweeps"]};
        nPostSweeps     {config["solvers"]["p"]["nPostSweeps"]};
        cacheAgglomeration {cacheAgglomeration};
        nCellsInCoarsestLevel {config["solvers"]["p"]["nCellsInCoarsestLevel"]};
        aggressiveCoeffs {config["solvers"]["p"]["aggressiveCoeffs"]};
        agglomerator {config["solvers"]["p"]["agglomerator"]};
        mergeLevels {config["solvers"]["p"]["mergeLevels"]};
        
    }}

    U
    {{
        solver          {config["solvers"]["U"]["solver"]};
        tolerance       {config["solvers"]["U"]["tolerance"]};
        relTol          {config["solvers"]["U"]["relTol"]};
        smoother        {config["solvers"]["U"]["smoother"]};
    }}

    k
    {{
        solver          {config["solvers"]["k"]["solver"]};
        tolerance       {config["solvers"]["k"]["tolerance"]};
        relTol          {config["solvers"]["k"]["relTol"]};
        smoother        {config["solvers"]["k"]["smoother"]};
    }}

    epsilon
    {{
        solver          {config["solvers"]["epsilon"]["solver"]};
        tolerance       {config["solvers"]["epsilon"]["tolerance"]};
        relTol          {config["solvers"]["epsilon"]["relTol"]};
        smoother        {config["solvers"]["epsilon"]["smoother"]};
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors    {config["SIMPLE"]["nNonOrthogonalCorrectors"]};
    pRefPoint                   {config["SIMPLE"]["pRefPoint"]};
    pRefValue                   {config["SIMPLE"]["pRefValue"]};

    residualControl
    {{
        p               {config["SIMPLE"]["residualControl"]["p"]};
        U               {config["SIMPLE"]["residualControl"]["U"]};
        k               {config["SIMPLE"]["residualControl"]["k"]};
        epsilon         {config["SIMPLE"]["residualControl"]["epsilon"]};
    }}
}}

relaxationFactors
{{
    fields
    {{
        p               {config["relaxationFactors"]["fields"]["p"]};
    }}

    equations
    {{
        U               {config["relaxationFactors"]["equations"]["U"]};
        k               {config["relaxationFactors"]["equations"]["k"]};
        epsilon         {config["relaxationFactors"]["equations"]["epsilon"]};
    }}
}}
"""


def generate_snappyHexMeshDict(shm_config):

    geometry_entries = []
    refinement_entries = []

    
    stl_file = shm_config["addLayersControls"]["layers"]["region"]["filePath"]
    name = shm_config["addLayersControls"]["layers"]["region"]["name"]
    refinement = shm_config["addLayersControls"]["layers"]["region"]["refinementLevel"]

    castellatedMeshcontrols_config = shm_config["castellatedMeshControls"]
    snapControls_config = shm_config["snapControls"]
    addLayersControls_config = shm_config["addLayersControls"]
    meshQualityControls_config = shm_config["meshQualityControls"]





    geometry_entries.append(
            f'    {name}\n    {{\n        type triSurfaceMesh;\n        file "{stl_file}";\n    }}'
        )
    refinement_entries.append(
            f'        {name}\n        {{\n            level ({refinement[0]} {refinement[1]});\n        }}'
        )

    castellatedMesh = "on" if shm_config['castellatedMesh'] == True else "off"
    allowFreeStandingZoneFaces = "on" if castellatedMeshcontrols_config['allowFreeStandingZoneFaces'] == True else "off"
    snap = "on" if shm_config['snap'] == True else "off"
    addLayers = "on" if shm_config['addLayers'] == True else "off"
    relativeSizes = "on" if addLayersControls_config['relativeSizes'] == True else "off"
 
   

    


    geometry_block = "\n".join(geometry_entries)
    refinement_block = "\n".join(refinement_entries)

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
    object      snappyHexMeshDict;
}}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh {castellatedMesh};
snap            {snap};
addLayers       {addLayers};

debug {shm_config['debug']};
mergeTolerance {shm_config['mergeTolerance']};

geometry
{{
{geometry_block}
}}

castellatedMeshControls
{{
    maxLocalCells {castellatedMeshcontrols_config["maxLocalCells"]};
    maxGlobalCells {castellatedMeshcontrols_config["maxGlobalCells"]};
    minRefinementCells {castellatedMeshcontrols_config["minRefinementCells"]};
    nCellsBetweenLevels {castellatedMeshcontrols_config["nCellsBetweenLevels"]};
    mergeTolerance     {castellatedMeshcontrols_config["mergeTolerance"]};    

    features {castellatedMeshcontrols_config["features"]};
    
    refinementSurfaces
    {{
    {refinement_block}
    }}

    resolveFeatureAngle {castellatedMeshcontrols_config["resolveFeatureAngle"]};
    refinementRegions {castellatedMeshcontrols_config["refinementRegions"]};

    locationInMesh {castellatedMeshcontrols_config["locationInMesh"]};
    allowFreeStandingZoneFaces {allowFreeStandingZoneFaces};
}}

snapControls
{{
    nSmoothPatch {snapControls_config['nSmoothPatch']};
    tolerance {snapControls_config['tolerance']};
    nSolveIter {snapControls_config['nSolveIter']};
    nRelaxIter {snapControls_config['nRelaxIter']};
}}

addLayersControls
{{
    relativeSizes {relativeSizes};
    layers 
    {{
        "{addLayersControls_config['layers']['region']['name']}.*"
        {{
            nSurfaceLayers {addLayersControls_config['layers']['region']['nSurfaceLayers']};
        }}
    }}
    expansionRatio {addLayersControls_config['expansionRatio']};
    finalLayerThickness {addLayersControls_config['finalLayerThickness']};
    minThickness {addLayersControls_config['minThickness']};
    nGrow {addLayersControls_config['nGrow']};
    featureAngle {addLayersControls_config['featureAngle']};
    nRelaxIter {addLayersControls_config['nRelaxIter']};
    nSmoothSurfaceNormals {addLayersControls_config['nSmoothSurfaceNormals']};
    nSmoothNormals {addLayersControls_config['nSmoothNormals']};
    nSmoothThickness {addLayersControls_config['nSmoothThickness']};
    maxFaceThicknessRatio {addLayersControls_config['maxFaceThicknessRatio']};
    maxThicknessToMedialRatio {addLayersControls_config['maxThicknessToMedialRatio']};
    minMedialAxisAngle {addLayersControls_config['minMedialAxisAngle']};
    nBufferCellsNoExtrude {addLayersControls_config['nBufferCellsNoExtrude']};
    nLayerIter {addLayersControls_config['nLayerIter']};
    nRelaxedIter {addLayersControls_config['nRelaxedIter']};
}}

meshQualityControls
{{
    maxNonOrtho {meshQualityControls_config['maxNonOrtho']};
    maxBoundarySkewness {meshQualityControls_config['maxBoundarySkewness']};
    maxInternalSkewness {meshQualityControls_config['maxInternalSkewness']};
    maxConcave {meshQualityControls_config['maxConcave']};
    minVol {meshQualityControls_config['minVol']};
    minTetQuality {meshQualityControls_config['minTetQuality']};
    minArea {meshQualityControls_config['minArea']};
    minTwist {meshQualityControls_config['minTwist']};
    minDeterminant {meshQualityControls_config['minDeterminant']};
    minFaceWeight {meshQualityControls_config['minFaceWeight']};
    minVolRatio {meshQualityControls_config['minVolRatio']};
    minTriangleTwist {meshQualityControls_config['minTriangleTwist']};
    nSmoothScale            {meshQualityControls_config['nSmoothScale']};
    errorReduction          {meshQualityControls_config['errorReduction']};
}}



// ************************************************************************* //
"""


