

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
    front  {{ type symmetryPlane; faces ((0 1 2 3); }}
    back   {{ type symmetryPlane; faces ((4 5 6 7)); }}
);

mergePatchPairs ();
"""
    return content

def generate_surfaceFeatureExtractDict(file, extractAngle):
   
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
    extractAngle    {extract_angle};
}}

writeObjFeatures    yes;

"""
    return content

