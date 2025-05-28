

def generate_blockMeshDict(vertices: list[list[float]], cell_counts=(20, 20, 20)) -> str:
    """
    Generate the content of the blockMeshDict file from bounding box vertices.
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
    inlet {{ type patch; faces ((0 4 7 3)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    walls {{ type wall; faces ((0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7)); }}
);

mergePatchPairs ();
"""
    return content

