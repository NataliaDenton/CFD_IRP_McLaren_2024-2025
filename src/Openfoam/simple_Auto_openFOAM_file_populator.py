import os

BASE_DIR = "AeroSUV_case"

# Define directory structure
dirs = [
    "0",
    "constant/polyMesh",
    "constant/triSurface",
    "system"
]

# Template content for files
field_U = """\
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform (10 0 0);
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            noSlip;
    }
}
"""

field_p = """\
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet
    {
        type            zeroGradient;
    }
    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }
    walls
    {
        type            zeroGradient;
    }
}
"""

field_k = """\
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0.06;
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 0.06;
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            kqRWallFunction;
        value           uniform 0.06;
    }
}
"""

field_epsilon = """\
dimensions      [0 2 -3 0 0 0 0];
internalField   uniform 0.09;
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 0.09;
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            epsilonWallFunction;
        value           uniform 0.09;
    }
}
"""

transport_properties = """\
transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] 1e-05;
"""

turbulence_properties = """\
simulationType  RAS;

RAS
{
    RASModel        kEpsilon;
    turbulence      on;
    printCoeffs     on;
}
"""

control_dict = """\
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1000;
deltaT          1;
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
"""

fv_schemes = """\
ddtSchemes
{
    default         steadyState;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,k)      Gauss upwind;
    div(phi,epsilon) Gauss upwind;
    div((nuEff*dev(T(grad(U))))) Gauss linear;
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
"""

fv_solution = """\
solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0;
    }
    U
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
    }
    "(k|epsilon)"
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-05;
        relTol          0.1;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 0;
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

# File write mapping
file_map = {
    "0/U": field_U,
    "0/p": field_p,
    "0/k": field_k,
    "0/epsilon": field_epsilon,
    "constant/transportProperties": transport_properties,
    "constant/turbulenceProperties": turbulence_properties,
    "system/controlDict": control_dict,
    "system/fvSchemes": fv_schemes,
    "system/fvSolution": fv_solution
}

# Create directories
for d in dirs:
    os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)

# Write files
for rel_path, content in file_map.items():
    abs_path = os.path.join(BASE_DIR, rel_path)
    with open(abs_path, "w") as f:
        f.write(content)

print(f"✅ OpenFOAM case '{BASE_DIR}' initialized successfully.")

