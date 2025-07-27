import os
import yaml
from pathlib import Path
import sys
import warnings
FUNCTIONS_PATH = Path(__file__).resolve().parent.joinpath("../../functions").resolve()
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
    




import os

def write_field_file(field_name: str, configU: dict, configA: dict, case_dir: str):
    """
    Generate OpenFOAM field file (e.g., U, p, k, epsilon, nut) in the '0/' directory
    based on structured YAML configuration and actual mesh patches.
    """
    import suppl_fcts

    if field_name not in configU or field_name not in configA:
        print(f"⚠️ Skipping field '{field_name}' (not found in configU or configA).")
        return


    field_cfg = configU[field_name]
    field_aux = configA[field_name]

    boundary_file_path = Path(case_dir).resolve() / "constant" / "polyMesh" / "boundary"

    mesh_boundaries = suppl_fcts.parse_boundary_names(boundary_file_path)

    # Field type & dimensions
    dimensions = ' '.join(map(str, field_aux["dimensions"]))
    internal = field_cfg["internalField"]
    if isinstance(internal, list):
        internal_field = f"({' '.join(map(str, internal))})"
        field_type = "volVectorField"
    else:
        internal_field = str(float(internal)) if not isinstance(internal, str) else internal
        field_type = "volScalarField"

    # Build boundaryField
    boundary_defs = field_cfg.get("boundaries", {})
    special_patch_types = ["symmetryPlane", "empty", "wedge", "cyclic", "processor", "symmetry"]

    boundary_field = ""
    for patch in mesh_boundaries:
        if patch in boundary_defs:
            props = boundary_defs[patch]
            patch_type = props.get("type", "zeroGradient")
            value = props.get("value", None)

            if patch_type in special_patch_types:
                value_str = ""
            elif patch_type in ["fixedValue", "calculated"]:
                value_str = f"        value           uniform ({' '.join(map(str, value))});\n" if isinstance(value, list) else f"        value           uniform {value};\n"
            elif patch_type.endswith("WallFunction"):
                value_str = f"        value           {value};\n" if isinstance(value, str) and value.startswith("uniform") else f"        value           uniform {value};\n"
            elif patch_type == "noSlip":
                patch_type = "fixedValue"
                value_str = "        value           uniform (0 0 0);\n"
            else:
                value_str = f"        value           uniform ({' '.join(map(str, value))});\n" if isinstance(value, list) else f"        value           uniform {value};\n" if value is not None else ""

        else:
            patch_type = "zeroGradient"
            value_str = ""

        boundary_field += f"""    {patch}
    {{
        type            {patch_type};
{value_str}    }}\n\n"""

    # Write to file
    os.makedirs(os.path.join(case_dir, "0"), exist_ok=True)
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

    print(f"✅ Field '{field_name}' written to 0/{field_name}")



def write_all_fields(configU: dict, configA: dict, case_dir: str):
    """
    Loop over all fields specified in both configU and configA 'fields' lists,
    writing OpenFOAM field files for each.
    """
    fields_u = set(configU.get("fields", []))
    fields_a = set(configA.get("fields", []))
    common_fields = fields_u.intersection(fields_a)

    if not common_fields:
        raise ValueError("No common fields found between configU and configA.")

    for field_name in common_fields:
        write_field_file(field_name, configU, configA, case_dir)

def populate_wallDist(ConfigU,ConfigA, case_dir):
    stream_dir = Path(case_dir) / "constant/stream"
    stream_dir.mkdir(parents=True, exist_ok=True)
    wallDist_path = stream_dir / "wallDist"

    wallDist_config = ConfigA.get("wallDist", {})
    method = wallDist_config.get("method", "meshWave")

    with open(wallDist_path, "w") as f:
        f.write(f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  2406                                  |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/

FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant/stream";
    object      wallDist;
}}

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
wallDist
{{
    method      meshWave;

    nRequired   false;

    updateInterval 1;
}}

// ************************************************************************* //
""")


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

def generate_controlDict(configU, configA, subkey="solver"):
    controlDict_configU = configU['control'][subkey]
    controlDict_configA = configA['control']
    forcesCoeffs_config = configA['forceCoeffs']
    unsteadyIO_config = configA['unsteadyIO']
    runTimeModifiable = "yes" if controlDict_configA['runTimeModifiable'] else "no"
    adjustTimeStep = "yes" if controlDict_configA['adjustTimeStep'] else "no"

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
adjustTimeStep  {adjustTimeStep};
maxCo           {controlDict_configA["maxCo"]};

functions
{{

    fieldAverage
    {{
        type                fieldAverage;
        functionObjectLibs  ("libfieldFunctionObjects.so");
        enabled             true;
        outputControl       timeStep;
        outputInterval      {controlDict_configU["writeInterval"]};
        timeStart           {controlDict_configU.get("averageTimeStart", controlDict_configU.get("startTime", 0))};

//-old-timeStart {controlDict_configU.get("averageTimeStart", 0)}; // deprecated


        timeEnd             {controlDict_configU["endTime"]};

        fields
        (
            U
            {{
                mean        on;
                prime2Mean  off;
                base        time;
            }}

            p
            {{
                mean        on;
                prime2Mean  off;
                base        time;
            }}
        );
    }}
    // Continuity error diagnostics
    continuityErrors
    {{
        type            continuityError;
        functionObjectLibs ("libutilityFunctionObjects.so");
        enabled         true;
        outputControl   timeStep;
        outputInterval  {controlDict_configU["writeInterval"]};
        cumulative      true;
    }}

    // Compute drag and lift coefficients

    forceCoeffs
    {{
        type                forceCoeffs;
        functionObjectLibs  ("libforces.so");
        enabled             {str(forcesCoeffs_config["enabled"]).lower()};
        outputControl       timeStep;
        outputInterval      {controlDict_configU["writeInterval"]};
        patches             ({forcesCoeffs_config["patches"]});
        rho                 rhoInf;
        rhoInf              {forcesCoeffs_config["rhoInf"]};               // freestream density [kg/m^3]
        magUInf             {forcesCoeffs_config["magUInf"]};
        lRef                {forcesCoeffs_config["lRef"]};
        Aref                {forcesCoeffs_config["Aref"]};
        CofR                ({' '.join(map(str, forcesCoeffs_config["CofR"]))});
        liftDir             ({' '.join(map(str, forcesCoeffs_config["liftDir"]))});
        dragDir             ({' '.join(map(str, forcesCoeffs_config["dragDir"]))});
        pitchAxis           ({' '.join(map(str, forcesCoeffs_config["pitchAxis"]))});
    }}

    yPlus
    {{
        type            yPlus;
        libs            ("libfieldFunctionObjects.so");
        patches             ({forcesCoeffs_config["patches"]});
        executeControl  timeStep;
        executeInterval 1;
        writeControl    timeStep;
        writeInterval   {controlDict_configU["writeInterval"]};  // adjust as needed
        log             true;
        timeStart       0;
    }}
}}
"""
def generate_fvSchemes(fvSchemes_configU, fvSchemes_configA):

    wallDist_bool = fvSchemes_configA["wallDist"]["nRequired"]
    wallDist_nRequired = "true" if wallDist_bool else "false"

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
    div(phi,omega)                 {fvSchemes_configA["divSchemes"]["div(phi,omega)"]};
    div((nuEff*dev2(T(grad(U)))))  {fvSchemes_configA["divSchemes"]["div((nuEff*dev2(T(grad(U)))))"]};
    div(div(phi,U))                {fvSchemes_configA["divSchemes"]["div(div(phi,U))"]};
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
    p               {fvSchemes_configA["fluxRequired"].get("p", "no")};
}}

wallDist
{{
    method         {fvSchemes_configA["wallDist"]["method"]};
    nRequired      {fvSchemes_configA["wallDist"]["nRequired"]};
    updateInterval {fvSchemes_configA["wallDist"]["updateInterval"]};
}}
"""

def generate_fvSolution(fvSolution_configA):
    cacheAgglomeration = "on" if fvSolution_configA["solvers"]["p"]["cacheAgglomeration"] else "off"

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
        solver              {fvSolution_configA["solvers"]["p"]["solver"]};
        tolerance           {fvSolution_configA["solvers"]["p"]["tolerance"]};
        relTol              {fvSolution_configA["solvers"]["p"]["relTol"]};
        smoother            {fvSolution_configA["solvers"]["p"]["smoother"]};
        nPreSweeps          {fvSolution_configA["solvers"]["p"]["nPreSweeps"]};
        nPostSweeps         {fvSolution_configA["solvers"]["p"]["nPostSweeps"]};
        cacheAgglomeration  {cacheAgglomeration};
        nCellsInCoarsestLevel {fvSolution_configA["solvers"]["p"]["nCellsInCoarsestLevel"]};
        aggressiveCoeffs    {fvSolution_configA["solvers"]["p"]["aggressiveCoeffs"]};
        agglomerator        {fvSolution_configA["solvers"]["p"]["agglomerator"]};
        mergeLevels         {fvSolution_configA["solvers"]["p"]["mergeLevels"]};
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

    omega
    {{
        solver          {fvSolution_configA["solvers"]["omega"]["solver"]};
        tolerance       {fvSolution_configA["solvers"]["omega"]["tolerance"]};
        relTol          {fvSolution_configA["solvers"]["omega"]["relTol"]};
        smoother        {fvSolution_configA["solvers"]["omega"]["smoother"]};
    }}

    Phi
    {{
        solver          {fvSolution_configA["solvers"]["Phi"]["solver"]};
        tolerance       {fvSolution_configA["solvers"]["Phi"]["tolerance"]};
        relTol          {fvSolution_configA["solvers"]["Phi"]["relTol"]};
        smoother        {fvSolution_configA["solvers"]["Phi"]["smoother"]};
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors    {fvSolution_configA["SIMPLE"]["nNonOrthogonalCorrectors"]};
    pRefPoint                   {fvSolution_configA["SIMPLE"]["pRefPoint"]};
    pRefValue                   {fvSolution_configA["SIMPLE"]["pRefValue"]};

    residualControl
    {{
        p       {fvSolution_configA["SIMPLE"]["residualControl"]["p"]};
        U       {fvSolution_configA["SIMPLE"]["residualControl"]["U"]};
        k       {fvSolution_configA["SIMPLE"]["residualControl"]["k"]};
        omega   {fvSolution_configA["SIMPLE"]["residualControl"]["omega"]};
    }}
}}

relaxationFactors
{{
    fields
    {{
        p       {fvSolution_configA["relaxationFactors"]["fields"]["p"]};
    }}

    equations
    {{
        U       {fvSolution_configA["relaxationFactors"]["equations"]["U"]};
        k       {fvSolution_configA["relaxationFactors"]["equations"]["k"]};
        omega   {fvSolution_configA["relaxationFactors"]["equations"]["omega"]};
    }}
}}
"""





def generate_snappyHexMeshDict(configU, configA, snappyHexMesh_configU, snappyHexMesh_configA):
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
        if "scaling" not in box_cfg:
            continue

        # Determine which STL to load
        if "geometry" in box_cfg:
            geom_key = box_cfg["geometry"]
            geometries = configU["filePath"].get("geometries", {})

            if geom_key in geometries:
               stl_file = geometries[geom_key]["file"]
            else:
                warnings.warn(
                    f"Geometry '{geom_key}' not found in userConfig['filePath']['geometries']; "
                "falling back to full-car geometry."
                )
            # fall back to full-car STL (assumes key 'body' or a dedicated fullCar entry)
                stl_file = geometries.get("body", {}).get("file", 
                            stl_file)
        # Load geometry and compute bounds
                mesh = IO_fcts.load_geometry(f"{stl_file}")
                bbox_min = suppl_fcts.compute_extended_bounds(mesh, box_cfg["scaling"])

        else:
            warnings.warn(
                f"No 'geometry' specified for refinement region '{region_name}'; "
            "using full-car geometry."
            )
    # Load geometry and compute bounds
            mesh = IO_fcts.load_geometry(f"constant/triSurface/{stl_file}")
            bbox_min = suppl_fcts.compute_extended_bounds(mesh, box_cfg["scaling"])

    # Build the snappyHexMesh refinement region entry
        ref_box_block = f"""
    {box_cfg['name']}
    {{
        type        {box_cfg['type']};
        min         ({bbox_min['x_min']} {bbox_min['y_min']} {bbox_min['z_min']});
        max         ({bbox_min['x_max']} {bbox_min['y_max']} {bbox_min['z_max']});
        mode        {box_cfg.get('mode', 'inside')};
        levels      ({' '.join(map(str, box_cfg.get('levels', [])))});
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
    relaxed
    {{
        maxNonOrtho           {quality_ctrlA['maxNonOrtho']};
        maxBoundarySkewness  {quality_ctrlA['maxBoundarySkewness']};
        maxInternalSkewness  {quality_ctrlA['maxInternalSkewness']};
        maxConcave           {quality_ctrlA['maxConcave']};
        minVol               {quality_ctrlA['minVol']};
        minTetQuality        {quality_ctrlA['minTetQuality']};
    }}
}}

// ************************************************************************* //
"""

def generate_cfMeshDict(meshDict_configU, meshDict_configA):
    """
    Build cfMesh meshDict from YAML-style Python dicts.

    Supports:
      - multiple layer patches listed in shm_config["addLayersControls"]["layers"]
      - optional refinement region box with computed bounds
    """

    # 1) Convenience handles
    stl_file = meshDict_configA["geometry"]["Geometry"]["file"]
    surface_name = meshDict_configA["geometry"]["Geometry"].get("name", "Geometry")
    surface_type = meshDict_configA["geometry"]["Geometry"].get("type", "triSurfaceMesh")
    refinement_surfaces = meshDict_configA.get("refinementSurfaces", {})
    refinement_regions = meshDict_configA.get("refinementRegions", {})

    # 2) Geometry block - surface mesh
    geometry_entries = [
        f'    {surface_name}\n'
        f'    {{\n'
        f'        type {surface_type};\n'
        f'        file "{stl_file}";\n'
    ]

    # Add refinement surface levels if available
    if "Geometry" in refinement_surfaces:
        level = refinement_surfaces["Geometry"].get("level", 3)
        geometry_entries.append(
            f'        regions\n        {{\n'
            f'            Geometry\n            {{\n'
            f'                name {surface_name};\n'
            f'                refinementLevel {level};\n'
            f'            }}\n'
            f'        }}\n'
        )
    geometry_entries.append('    }')  # close Geometry block

    # 3) refinementBoxes blocks (multiple)
    # For each refinementRegion defined, compute bounding box min/max and add block
    for region_key, box_cfg in refinement_regions.items():
        # Load points from STL file for bounding box calculation
        points = IO_fcts.load_geometry(f'constant/triSurface/{stl_file}')

        # Compute extended bounding box based on scaling factors from config
        bbox_minmax = suppl_fcts.compute_extended_bounds(points, box_cfg.get("scaling", {}))

        # Compose min and max lines
        min_str = f'({bbox_minmax["x_min"]:.6f} {bbox_minmax["y_min"]:.6f} {bbox_minmax["z_min"]:.6f})'
        max_str = f'({bbox_minmax["x_max"]:.6f} {bbox_minmax["y_max"]:.6f} {bbox_minmax["z_max"]:.6f})'

        # Handle refinement levels: can be int or list of ints
        levels = box_cfg.get("levels", box_cfg.get("level", 4))
        # If levels is a list, take max (usually max level is relevant for meshDict)
        if isinstance(levels, list):
            ref_level = max(levels)
        else:
            ref_level = levels

        # Append refinement box block string
        geometry_entries.append(
            f'    {box_cfg["name"]}\n'
            f'    {{\n'
            f'        type {box_cfg["type"]};\n'
            f'        min {min_str};\n'
            f'        max {max_str};\n'
            f'        refinementLevel {ref_level};\n'
            f'    }}'
        )

    geometry_block = "\n".join(geometry_entries)

    # 4) meshSettings block from meshDict_configU (or default fallback)
    meshSettings = meshDict_configU.get("meshSettings", {})
    nCellsBetweenLevels = meshSettings.get("nCellsBetweenLevels", 3)
    maxCellSize = meshSettings.get("maxCellSize", 0.1)
    minCellSize = meshSettings.get("minCellSize", 0.001)
    boundaryCellSize = meshSettings.get("boundaryCellSize", 0.02)
    surfaceMeshRefinement_enable = meshSettings.get("surfaceMeshRefinement", {}).get("enable", 1)
    internalRefinement_enable = meshSettings.get("internalRefinement", {}).get("enable", 1)

    # 5) boundaryLayers block from meshDict_configU or meshDict_configA
    boundaryLayers = meshDict_configA.get("boundaryLayers", {})
    nLayers = boundaryLayers.get("nLayers", 10)
    thicknessRatio = boundaryLayers.get("thicknessRatio", 0.3)
    maxFirstLayerThickness = boundaryLayers.get("maxFirstLayerThickness", 0.05)
    allowDiscontinuity = boundaryLayers.get("allowDiscontinuity", 0)
    featureAngle = boundaryLayers.get("featureAngle", 60)

    # 6) Compose final meshDict text output
    return f"""/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \    /   O peration     | Version: dev-cfMesh                             |
|   \  /    A nd           | Web:      https://sourceforge.net/projects/cfmesh|
|    \/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/

FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      meshDict;
}}

surfaceFile "constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl"; // STL surface

// Global cell size controls
maxCellSize     0.3;     // Base size
minCellSize     0.001;    // Smallest size allowed

// Geometry definition
geometry
{{
    Geometry
    {{
        type triSurfaceMesh;
        file "constant/triSurface/Geometry/mergedGeometry/mergedGeometry.stl";
    }}
}}

// Background mesh for external domain
backgroundMesh
{{
    box
    {{
        type searchableBox;
        min (-5 -5 -5);
        max (5 5 5);
    }}
    cellSize 0.1;
}}

// Refinement boxes (make sure these are in external fluid domain)
refinementBoxes
{{
    refinementBox
    {{
        type searchableBox;
        min (-1.3622519969940186 -0.5119140148162842 -0.0059986598789691925);
        max (3.258755922317505 0.5119140148162842 0.596733808517456);
        insideLevel 4;
    }}

    refinementBox2
    {{
        type searchableBox;
        min (-0.43805038928985596 -0.3583398163318634 -0.0059986598789691925);
        max (1.8146910667419434 0.3583398163318634 0.4761873483657837);
        insideLevel 6;
    }}
}}

// Surface mesh refinement
meshSettings
{{
    nCellsBetweenLevels 5; // analogous to snappy’s nCellsBetweenLevels
    boundaryCellSize 0.02; // approximate surface refinement

    surfaceMeshRefinement
    {{
        enable 1;
        levels
        {{
            Geometry
            {{
                level (3 4);
            }}
        }}
    }}

    // Optionally, enable external refinement if your cfMesh version supports it
    externalRefinement
    {{
        enable 1;
    }}
}}

// Boundary layers
boundaryLayers
{{
    nLayers                10;
    thicknessRatio         0.3;
    maxFirstLayerThickness 0.05;
    allowDiscontinuity     0;
    featureAngle           60;
}}

"""



