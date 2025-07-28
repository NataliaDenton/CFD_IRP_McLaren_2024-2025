import ansa
from ansa import *

# Load the config file
geomFilePath = "../../Ansa/Geometry/17_wheels-front.stl"

# Example: Load Geometry
print("Importing Geometry")
base.InputStereoLithography(
        geomFilePath , elements_id="offset-freeid"
    )
print("Cleaning Geometry")
ansa.base.CleanGeometry()

