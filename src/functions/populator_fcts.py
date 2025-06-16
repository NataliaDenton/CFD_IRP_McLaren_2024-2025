import os
import yaml
from pathlib import Path
import sys
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import suppl_fcts

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




def decomposeParDict_populator(decomposeParDict_configU, decomposeParDict_configA):

    # --- configs ---
    simpleCoeffsConfig = decomposeParDict_configA["simpleCoeffs"]
    hierarchicalCoeffsConfig = decomposeParDict_configA["hierarchicalCoeffs"]

    distributed = "on" if decomposeParDict_configA['distributed'] == True else "off"

    content = f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      decomposeParDict;
}}

numberOfSubdomains {decomposeParDict_configU};

method          {decomposeParDict_configA["method"]};

simpleCoeffs
{{
    n               {simpleCoeffsConfig["n"]};   // Only used if method is 'simple'
    delta           {simpleCoeffsConfig["delta"]};
}}

hierarchicalCoeffs
{{
    n               {hierarchicalCoeffsConfig["n"]};   // For 'hierarchical' method
    delta           {hierarchicalCoeffsConfig["delta"]};
    order           {hierarchicalCoeffsConfig["order"]};
}}

distributed      {distributed};
roots            {decomposeParDict_configA["roots"]};


"""
    return content
    






def write_field_file(field_name: str, configU: dict,configA: dict, case_dir: str):
    """
    Write OpenFOAM field file (e.g., U, p, k, epsilon, nut) to the '0/' directory.

    Args:
        field_name: Name of the field (e.g., "U", "p", "k").
        config: Parsed YAML config dictionary from config_0.yaml.
        case_dir: Path to the OpenFOAM case directory.
    """

    # --- Ensure config section exists ---
    if field_name not in configU:
        raise KeyError(f"Missing '{field_name}' section in config_0.yaml.")


    field_cfg = configU[field_name]
    field_cfgA = configA[field_name]
    case_dir = os.path.join('../../',case_dir)
    dimensions = ' '.join(map(str, field_cfgA["dimensions"]))
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
    field_file_path = os.path.join(case_dir, "0", field_name)
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


def write_all_fields(ConfigU,ConfigA, case_dir):
    """
    Wrapper to write all fields listed in the config YAML.

    Args:
        config_path: Path to config_0.yaml
        case_dir: OpenFOAM case path
    """

    field_list = ConfigU.get("fields", [])
    if not field_list:
        raise ValueError("No 'fields' key found in config_0.yaml.")

    for field in field_list:
        write_field_file(field, ConfigU, ConfigA, case_dir)





def populate_transportProperties(ConfigU,ConfigA, case_dir):
    
    filepath = os.path.join('../../',case_dir, 'constant', 'transportProperties')

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
        f"nu              [0 2 -1 0 0 0 0] {ConfigU['fluid']['nu']};",
        "",
        "// ************************************************************************* //"
    ]

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))

def populate_turbulenceProperties(ConfigU,ConfigA, case_dir):
    filepath = os.path.join('../../',case_dir, 'constant', 'turbulenceProperties')
    turbulence_value = "on" if ConfigA['turbulence']['RAS']['turbulence'] == True else "off"
    printCoeffs_value = "on" if ConfigA['turbulence']['RAS']['printCoeffs'] == True else "off"
    
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
        f"simulationType  {ConfigU['turbulence']['simulationType']};",
        f"{ConfigU['turbulence']['simulationType']}",
        "{",
        f"    RASModel        {ConfigU['turbulence']['model']};",
        f"    turbulence      {turbulence_value};",
        f"    printCoeffs     {printCoeffs_value};",
        "}",
        "",
        "// ************************************************************************* //"
    ]

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))





import os

def generate_controlDict(controlDict_configU, controlDict_configA):

    runTimeModifiable = "yes" if controlDict_configA['runTimeModifiable'] == True else "no"

    return f"""\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}}

application     {controlDict_configA["application"]};
startFrom       {controlDict_configA["startFrom"]};
startTime       {controlDict_configU["startTime"]};
stopAt          {controlDict_configA["stopAt"]};
endTime         {controlDict_configU["endTime"]};
deltaT          {controlDict_configU["deltaT"]};
writeControl    {controlDict_configU["writeControl"]};
writeInterval   {controlDict_configU["writeInterval"]};
purgeWrite      {controlDict_configU["purgeWrite"]};
writeFormat     {controlDict_configA["writeFormat"]};
writePrecision  {controlDict_configA["writePrecision"]};
writeCompression {controlDict_configA["writeCompression"]};
timeFormat      {controlDict_configA["timeFormat"]};
timePrecision   {controlDict_configA["timePrecision"]};
runTimeModifiable {runTimeModifiable};
"""

def generate_fvSchemes(fvSchemes_configU, fvSchemes_configA):
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
    default         {fvSchemes_configU["default"]};
}}

gradSchemes
{{
    default         {fvSchemes_configA["gradSchemes"]["default"]};
    grad(p)         {fvSchemes_configA["gradSchemes"]["grad(p)"]};
    grad(U)         {fvSchemes_configA["gradSchemes"]["grad(U)"]};
}}

divSchemes
{{
    div(phi,U)                      {fvSchemes_configA["divSchemes"]["div(phi,U)"]};
    div(phi,k)                      {fvSchemes_configA["divSchemes"]["div(phi,k)"]};
    div(phi,epsilon)               {fvSchemes_configA["divSchemes"]["div(phi,epsilon)"]};
    div((nuEff*dev2(T(grad(U)))))  {fvSchemes_configA["divSchemes"]["div((nuEff*dev2(T(grad(U)))))"]};
}}

laplacianSchemes
{{
    default         {fvSchemes_configA["laplacianSchemes"]["default"]};
}}

interpolationSchemes
{{
    default         {fvSchemes_configA["interpolationSchemes"]["default"]};
}}

snGradSchemes
{{
    default         {fvSchemes_configA["snGradSchemes"]["default"]};
}}

fluxRequired
{{
    default         {fvSchemes_configA["fluxRequired"]["default"]};
    p;
}}
"""
def generate_fvSolution(fvSolution_configA):

    cacheAgglomeration = "on" if fvSolution_configA['solvers']['p']['cacheAgglomeration'] == True else "off"
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
        solver          {fvSolution_configA["solvers"]["p"]["solver"]};
        tolerance       {fvSolution_configA["solvers"]["p"]["tolerance"]};
        relTol          {fvSolution_configA["solvers"]["p"]["relTol"]};
        smoother        {fvSolution_configA["solvers"]["p"]["smoother"]};
        nPreSweeps      {fvSolution_configA["solvers"]["p"]["nPreSweeps"]};
        nPostSweeps     {fvSolution_configA["solvers"]["p"]["nPostSweeps"]};
        cacheAgglomeration {cacheAgglomeration};
        nCellsInCoarsestLevel {fvSolution_configA["solvers"]["p"]["nCellsInCoarsestLevel"]};
        aggressiveCoeffs {fvSolution_configA["solvers"]["p"]["aggressiveCoeffs"]};
        agglomerator {fvSolution_configA["solvers"]["p"]["agglomerator"]};
        mergeLevels {fvSolution_configA["solvers"]["p"]["mergeLevels"]};
        
    }}

    U
    {{
        solver          {fvSolution_configA["solvers"]["U"]["solver"]};
        tolerance       {fvSolution_configA["solvers"]["U"]["tolerance"]};
        relTol          {fvSolution_configA["solvers"]["U"]["relTol"]};
        smoother        {fvSolution_configA["solvers"]["U"]["smoother"]};
    }}

    k
    {{
        solver          {fvSolution_configA["solvers"]["k"]["solver"]};
        tolerance       {fvSolution_configA["solvers"]["k"]["tolerance"]};
        relTol          {fvSolution_configA["solvers"]["k"]["relTol"]};
        smoother        {fvSolution_configA["solvers"]["k"]["smoother"]};
    }}

    epsilon
    {{
        solver          {fvSolution_configA["solvers"]["epsilon"]["solver"]};
        tolerance       {fvSolution_configA["solvers"]["epsilon"]["tolerance"]};
        relTol          {fvSolution_configA["solvers"]["epsilon"]["relTol"]};
        smoother        {fvSolution_configA["solvers"]["epsilon"]["smoother"]};
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors    {fvSolution_configA["SIMPLE"]["nNonOrthogonalCorrectors"]};
    pRefPoint                   {fvSolution_configA["SIMPLE"]["pRefPoint"]};
    pRefValue                   {fvSolution_configA["SIMPLE"]["pRefValue"]};

    residualControl
    {{
        p               {fvSolution_configA["SIMPLE"]["residualControl"]["p"]};
        U               {fvSolution_configA["SIMPLE"]["residualControl"]["U"]};
        k               {fvSolution_configA["SIMPLE"]["residualControl"]["k"]};
        epsilon         {fvSolution_configA["SIMPLE"]["residualControl"]["epsilon"]};
    }}
}}

relaxationFactors
{{
    fields
    {{
        p               {fvSolution_configA["relaxationFactors"]["fields"]["p"]};
    }}

    equations
    {{
        U               {fvSolution_configA["relaxationFactors"]["equations"]["U"]};
        k               {fvSolution_configA["relaxationFactors"]["equations"]["k"]};
        epsilon         {fvSolution_configA["relaxationFactors"]["equations"]["epsilon"]};
    }}
}}
"""

def generate_snappyHexMeshDict(snappyHexMesh_configU, snappyHexMesh_configA):
    """
    Build snappyHexMeshDict from YAML-style Python dict.

    Supports:
      - multiple layer patches listed in shm_config["addLayersControls"]["layers"]
      - optional refinement region box
    """

    # ------------------------------------------------------------------ #
    # 1)  Convenience handles
    # ------------------------------------------------------------------ #


    cm_controlsA   = snappyHexMesh_configA["castellatedMeshControls"]
    snap_controlsA = snappyHexMesh_configA["snapControls"]
    layer_ctrlA    = snappyHexMesh_configA["addLayersControls"]
    quality_ctrlA  = snappyHexMesh_configA["meshQualityControls"]


    cm_controlsU   = snappyHexMesh_configU
    # ------------------------------------------------------------------ #
    # 2)  STL file & surface *name*
    # ------------------------------------------------------------------ #
    if "geometry" in snappyHexMesh_configA and "Geometry" in snappyHexMesh_configA["geometry"]:
        stl_file = snappyHexMesh_configA["geometry"]["Geometry"]["file"]
        surface_name = "Geometry"
    else:  # backward compatibility
        stl_file = layer_ctrl["layers"]["region"]["filePath"]
        surface_name = layer_ctrl["layers"]["region"]["name"]

    refinement = (
        layer_ctrlA.get("layers", {})
        .get(surface_name, {})
        .get("refinementLevel", [3, 4])
    )

    # ------------------------------------------------------------------ #
    # 3) Geometry & refinement-box blocks (multi-region support)        #
    # ------------------------------------------------------------------ #
    geo_entries = [
        f'    {surface_name}\n    {{\n        type triSurfaceMesh;\n'
        f'        file "{stl_file}";\n    }}'
    ]

    refinement_regions = cm_controlsA.get("refinementRegions", {})
    for region_name, box_cfg in refinement_regions.items():
        if "scaling" in box_cfg:
            bbox_min = suppl_fcts.compute_extended_bounds(
                IO_fcts.load_geometry(f'constant/triSurface/{stl_file}'),
                box_cfg["scaling"]
            )
            ref_box_block = f"""
        {box_cfg['name']}
        {{
            type {box_cfg['type']};
            min ({bbox_min['x_min']} {bbox_min['y_min']} {bbox_min['z_min']});
            max ({bbox_min['x_max']} {bbox_min['y_max']} {bbox_min['z_max']});
        }}"""
            geo_entries.append(ref_box_block)

    geometry_block = "\n".join(geo_entries)

    # ------------------------------------------------------------------ #
    # 4) refinementSurfaces + refinementRegions blocks                   #
    # ------------------------------------------------------------------ #
    refinement_block = (
        f"        {surface_name}\n"
        f"        {{\n            level ({refinement[0]} {refinement[1]});\n        }}"
    )

    refinement_regions_block = ""
    for region_name, box_cfg in refinement_regions.items():
        refinement_regions_block += (
            f"    {box_cfg['name']}\n"
            f"    {{\n        mode {box_cfg['mode']};\n"
            f"        levels (({box_cfg['levels'][0]} {box_cfg['levels'][1]}));\n    }}\n"
        )

    # ------------------------------------------------------------------ #
    # 5)  Build **layer** sub-blocks for every patch
    # ------------------------------------------------------------------ #
    layer_entries = []
    for patch, cfg in layer_ctrlA["layers"].items():
        layer_entries.append(
            f'        {patch}\n        {{\n            nSurfaceLayers {cfg["nSurfaceLayers"]};\n        }}'
        )
    layers_block = "\n".join(layer_entries)

    # ------------------------------------------------------------------ #
    # 6)  Helpers to translate bool → "on/off"
    # ------------------------------------------------------------------ #
    as_switch = lambda x: "on" if x else "off"
    castellatedMesh  = as_switch(snappyHexMesh_configU["castellatedMesh"])
    snap             = as_switch(snappyHexMesh_configU["snap"])
    addLayers        = as_switch(snappyHexMesh_configU["addLayers"])
    relativeSizes    = as_switch(layer_ctrlA["relativeSizes"])
    explicitSnap     = as_switch(snap_controlsA["explicitFeatureSnap"])
    multiRegionSnap  = as_switch(snap_controlsA["multiRegionSnap"])
    allowZones       = as_switch(cm_controlsA["allowFreeStandingZoneFaces"])

    if relativeSizes == "true":
        addLayer_block = f'''addLayersControls
{{
    relativeSizes   {relativeSizes};
    layers
    {{
{layers_block}
    }}
    expansionRatio            {layer_ctrlA['expansionRatio']};
    finalLayerThickness       {layer_ctrlA['finalLayerThickness']};
    minThickness              {layer_ctrlA['minThickness']};
    nGrow                     {layer_ctrlA['nGrow']};
    featureAngle              {layer_ctrlA['featureAngle']};
    nRelaxIter                {layer_ctrlA['nRelaxIter']};
    nSmoothSurfaceNormals     {layer_ctrlA['nSmoothSurfaceNormals']};
    nSmoothNormals            {layer_ctrlA['nSmoothNormals']};
    nSmoothThickness          {layer_ctrlA['nSmoothThickness']};
    maxFaceThicknessRatio     {layer_ctrlA['maxFaceThicknessRatio']};
    maxThicknessToMedialRatio {layer_ctrlA['maxThicknessToMedialRatio']};
    minMedialAxisAngle        {layer_ctrlA['minMedialAxisAngle']};
    nBufferCellsNoExtrude     {layer_ctrlA['nBufferCellsNoExtrude']};
    nLayerIter                {layer_ctrlA['nLayerIter']};
    nRelaxedIter              {layer_ctrlA['nRelaxedIter']};
}}'''
    else:
        addLayer_block = f'''addLayersControls
{{
    relativeSizes   {relativeSizes};
    layers
    {{
{layers_block}
    }}
    expansionRatio            {layer_ctrlA['expansionRatio']};
    finalLayerThickness       {layer_ctrlA['finalLayerThickness']};
    minThickness              {layer_ctrlA['minThickness']};
    nGrow                     {layer_ctrlA['nGrow']};
    featureAngle              {layer_ctrlA['featureAngle']};
    nRelaxIter                {layer_ctrlA['nRelaxIter']};
    nSmoothSurfaceNormals     {layer_ctrlA['nSmoothSurfaceNormals']};
    nSmoothNormals            {layer_ctrlA['nSmoothNormals']};
    nSmoothThickness          {layer_ctrlA['nSmoothThickness']};
    maxFaceThicknessRatio     {layer_ctrlA['maxFaceThicknessRatio']};
    maxThicknessToMedialRatio {layer_ctrlA['maxThicknessToMedialRatio']};
    minMedialAxisAngle        {layer_ctrlA['minMedialAxisAngle']};
    nBufferCellsNoExtrude     {layer_ctrlA['nBufferCellsNoExtrude']};
    nLayerIter                {layer_ctrlA['nLayerIter']};
    nRelaxedIter              {layer_ctrlA['nRelaxedIter']};
}}'''

    # ------------------------------------------------------------------ #
    # 7)  Assemble final snappyHexMeshDict
    # ------------------------------------------------------------------ #
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

castellatedMesh {castellatedMesh};
snap            {snap};
addLayers       {addLayers};

debug {snappyHexMesh_configA['debug']};
mergeTolerance {snappyHexMesh_configA['mergeTolerance']};

geometry
{{
{geometry_block}
}}

castellatedMeshControls
{{
    maxLocalCells        {cm_controlsA["maxLocalCells"]};
    maxGlobalCells       {cm_controlsA["maxGlobalCells"]};
    minRefinementCells   {cm_controlsA["minRefinementCells"]};
    nCellsBetweenLevels  {cm_controlsA["nCellsBetweenLevels"]};
    mergeTolerance       {cm_controlsA["mergeTolerance"]};

    features             {cm_controlsA["features"]};

    refinementSurfaces
    {{
{refinement_block}
    }}

    resolveFeatureAngle  {cm_controlsA["resolveFeatureAngle"]};

    refinementRegions
    {{
{refinement_regions_block}
    }}

    locationInMesh       {cm_controlsA["locationInMesh"]};
    allowFreeStandingZoneFaces {allowZones};
}}

snapControls
{{
    nSmoothPatch    {snap_controlsA['nSmoothPatch']};
    tolerance       {snap_controlsA['tolerance']};
    nSolveIter      {snap_controlsA['nSolveIter']};
    nRelaxIter      {snap_controlsA['nRelaxIter']};

    explicitFeatureSnap {explicitSnap};
    multiRegionSnap     {multiRegionSnap};
}}



{addLayer_block}

meshQualityControls
{{
    maxNonOrtho          {quality_ctrlA['maxNonOrtho']};
    maxBoundarySkewness  {quality_ctrlA['maxBoundarySkewness']};
    maxInternalSkewness  {quality_ctrlA['maxInternalSkewness']};
    maxConcave           {quality_ctrlA['maxConcave']};
    minVol               {quality_ctrlA['minVol']};
    minTetQuality        {quality_ctrlA['minTetQuality']};
    minArea              {quality_ctrlA['minArea']};
    minTwist             {quality_ctrlA['minTwist']};
    minDeterminant       {quality_ctrlA['minDeterminant']};
    minFaceWeight        {quality_ctrlA['minFaceWeight']};
    minVolRatio          {quality_ctrlA['minVolRatio']};
    minTriangleTwist     {quality_ctrlA['minTriangleTwist']};
    nSmoothScale         {quality_ctrlA['nSmoothScale']};
    errorReduction       {quality_ctrlA['errorReduction']};
}}

// ************************************************************************* //
"""

