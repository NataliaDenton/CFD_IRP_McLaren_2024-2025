import yaml
from ansa import base, constants

# Load the config file
with open("config/ansaConfig.yaml", 'r') as f:
    config = yaml.safe_load(f)

# Example: Load Geometry
for geom in config['geometry']['files']:
    base.ImportGeom(geom['path'])

# Run cleanup
if config['cleanup']['enable']:
    for op in config['cleanup']['operations']:
        if op == "fillHoles":
            base.CleanupHole()
        elif op == "removeDoubleEntities":
            base.RemoveDoubles()
        # Add checks here...

# Surface Meshing
surf_mesh = config['meshing']['surfaceMesh']
base.SetMeshParams(type="CFD_Tria", target_length=surf_mesh['targetLength'])
base.RunMeshing()

# Save Project
base.SaveAs(config['project']['savePath'] + config['project']['name'] + ".ansa")

