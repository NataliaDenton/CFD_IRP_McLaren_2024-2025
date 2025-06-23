# Create points at the corners of a square (unit square for example)
set p1 [Glyph Point Create 0.0 0.0 0.0]
set p2 [Glyph Point Create 1.0 0.0 0.0]
set p3 [Glyph Point Create 1.0 1.0 0.0]
set p4 [Glyph Point Create 0.0 1.0 0.0]

# Create connectors (edges) between points to form the square perimeter
set c1 [Glyph Connector Create $p1 $p2]
set c2 [Glyph Connector Create $p2 $p3]
set c3 [Glyph Connector Create $p3 $p4]
set c4 [Glyph Connector Create $p4 $p1]

# Define number of divisions (mesh density) on each connector
Glyph Connector Divide $c1 10
Glyph Connector Divide $c2 10
Glyph Connector Divide $c3 10
Glyph Connector Divide $c4 10

# Create a domain (surface) bounded by the connectors
set d1 [Glyph Domain Create $c1 $c2 $c3 $c4]

# Set grid type for the domain (structured grid)
Glyph Domain GridType $d1 Structured

# Generate the grid on the domain
Glyph Domain GridGenerate $d1

# Export the mesh (optional)
Glyph Export SetFormat "CGNS" ;# Choose file format
Glyph Export Write "simple_square.cgns"

# Print confirmation
Glyph Print "Mesh generation complete and exported."

