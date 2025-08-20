// Simcenter STAR-CCM+ macro: Wrapping.java
// This macro automates the surface wrapping process for a vehicle model.
// It reads wrapping parameters from a separate properties file (wrapping.properties),
// creates a Surface Wrapper operation, applies global and custom settings,
// and executes the operation to create a closed, watertight surface mesh.
package macro;

import java.util.*;
import java.io.FileInputStream;
import java.io.IOException;

import star.common.*;
import star.base.neo.*;
import star.meshing.*;
import star.surfacewrapper.*;

public class WrappingCommented extends StarMacro {

  private Properties props;

  public void execute() {
    execute0();
  }

  private void execute0() {

    // --- SECTION 1: INITIALIZATION AND PARAMETER LOADING ---
    Simulation simulation = getActiveSimulation();
    
    // Get the main SUV part created by the previous macro
    CompositePart suvPart = ((CompositePart) simulation.get(SimulationPartManager.class).getPart("SUV"));
    
    // Load wrapping parameters from the properties file
    try {
      props = new Properties();
      FileInputStream fis = new FileInputStream(resolvePath("wrapping.properties"));
      props.load(fis);
    } catch (IOException e) {
      throw new RuntimeException("Could not load wrapping.properties file.", e);
    }

    // --- SECTION 2: CREATE AND CONFIGURE SURFACE WRAPPER ---
    simulation.println("Creating and configuring Surface Wrapper...");
    MeshOperationManager meshOpManager = simulation.get(MeshOperationManager.class);
    
    // Create the surface wrapper operation, using only the main composite part
    SurfaceWrapperAutoMeshOperation surfaceWrapperOp = 
      (SurfaceWrapperAutoMeshOperation) meshOpManager.createSurfaceWrapperAutoMeshOperation(new ArrayList<>(Arrays.<GeometryPart>asList(suvPart)), "Surface Wrapper");
    
    // Get the mesher and units for setting parameters
    SurfaceWrapperAutoMesher surfaceWrapperMesher = 
      ((SurfaceWrapperAutoMesher) surfaceWrapperOp.getMeshers().getObject("Surface Wrapper"));
    Units mmUnits = ((Units) simulation.getUnitsManager().getObject("mm"));
    Units dimensionlessUnits = ((Units) simulation.getUnitsManager().getObject(""));

    // Enable proximity refinement
    surfaceWrapperMesher.setDoProximityRefinement(true);

    // Set global default values from the properties file
    double baseSize = Double.parseDouble(props.getProperty("wrapper.base.size"));
    double targetRelativeSize = Double.parseDouble(props.getProperty("wrapper.target.relative.size"));
    double minimumRelativeSize = Double.parseDouble(props.getProperty("wrapper.minimum.relative.size"));

    surfaceWrapperOp.getDefaultValues().get(BaseSize.class).setValueAndUnits(baseSize, mmUnits);
    surfaceWrapperOp.getDefaultValues().get(PartsTargetSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(targetRelativeSize, dimensionlessUnits);
    surfaceWrapperOp.getDefaultValues().get(PartsMinimumSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(minimumRelativeSize, dimensionlessUnits);
    
    // Set the Volume of Interest to 'EXTERNAL' to wrap the outside of the geometry
    GlobalVolumeOfInterest globalVolumeOfInterest = surfaceWrapperOp.getDefaultValues().get(GlobalVolumeOfInterest.class);
    globalVolumeOfInterest.getVolumeOfInterestOption().setSelected(GlobalVolumeOfInterestOption.Type.EXTERNAL);

    // --- SECTION 3: APPLY CUSTOM MESH CONTROLS ---
    simulation.println("Applying custom mesh control to wheels...");
    SurfaceCustomMeshControl customControl = surfaceWrapperOp.getCustomMeshControls().createSurfaceControl();
    
    // Get part names for custom control from properties file
    String[] customPartNames = props.getProperty("custom.parts.names").split(",");
    
    // Find the specific MeshPart and its corresponding PartSurface for the wheels.
    List<PartSurface> partSurfaces = new ArrayList<>();
    List<MeshPart> meshParts = new ArrayList<>();
    for (String partName : customPartNames) {
        MeshPart part = ((MeshPart) suvPart.getChildParts().getPart(partName));
        meshParts.add(part);

        // Get all surfaces for the part and assume the first one is the correct one.
        PartSurface partSurface = new ArrayList<>(part.getPartSurfaceManager().getPartSurfaces()).get(0);
        partSurfaces.add(partSurface);
    }
    
    // Set the geometry objects for the custom control.
    customControl.getGeometryObjects().setObjects(
        meshParts.get(0), partSurfaces.get(0),
        meshParts.get(1), partSurfaces.get(1)
    );

    // Enable custom settings for Target Size, Minimum Size, and Curvature
    customControl.getCustomConditions().get(PartsTargetSurfaceSizeOption.class).setSelected(PartsTargetSurfaceSizeOption.Type.CUSTOM);
    customControl.getCustomConditions().get(PartsMinimumSurfaceSizeOption.class).setSelected(PartsMinimumSurfaceSizeOption.Type.CUSTOM);
    customControl.getCustomConditions().get(PartsSurfaceCurvatureOption.class).setSelected(PartsSurfaceCurvatureOption.Type.CUSTOM_VALUES);

    // Set custom values from properties file
    double wheelsTargetSize = Double.parseDouble(props.getProperty("wheels.target.relative.size"));
    double wheelsMinimumSize = Double.parseDouble(props.getProperty("wheels.minimum.relative.size"));
    double wheelsCurvature = Double.parseDouble(props.getProperty("wheels.curvature.points"));

    customControl.getCustomValues().get(PartsTargetSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(wheelsTargetSize, dimensionlessUnits);
    customControl.getCustomValues().get(PartsMinimumSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(wheelsMinimumSize, dimensionlessUnits);
    customControl.getCustomValues().get(SurfaceCurvature.class).setNumPointsAroundCircle(wheelsCurvature);

    // --- SECTION 4: EXECUTE THE OPERATION AND RENAME THE OUTPUT PART ---
    simulation.println("Executing Surface Wrapper operation...");
    surfaceWrapperOp.execute();

    // Get the output part of the surface wrapper operation
    MeshOperationPart wrapperPart = 
      ((MeshOperationPart) simulation.get(SimulationPartManager.class).getPart("Surface Wrapper"));
      
    // Rename the wrapped part for clarity
    wrapperPart.setPresentationName("SUV_Wrap");

    simulation.println("Surface wrapping completed successfully.");
  }
}