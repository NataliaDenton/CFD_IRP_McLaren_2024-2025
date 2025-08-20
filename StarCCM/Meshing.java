// Simcenter STAR-CCM+ macro: Meshing.java
// This macro sets up and executes a comprehensive meshing pipeline.
// It applies global meshing parameters, specific custom surface controls,
// and volumetric refinement controls based on values and part names
// defined in a properties file.
package macro;

import java.util.*;
import java.io.FileInputStream;
import java.io.IOException;

import star.common.*;
import star.base.neo.*;
import star.resurfacer.*;
import star.prismmesher.*;
import star.meshing.*;
import star.dualmesher.*;

public class MeshingCommented extends StarMacro {

  private Properties props;
  private Simulation simulation;
  private Units dimensionlessUnits;
  private AutoMeshOperation autoMeshOp;

  public void execute() {
    execute0();
  }

  private void execute0() {

    // --- SECTION 1: INITIALIZATION AND PARAMETER LOADING ---
    simulation = getActiveSimulation();
    
    // Load meshing parameters from the properties file
    try {
      props = new Properties();
      FileInputStream fis = new FileInputStream(resolvePath("meshing.properties"));
      props.load(fis);
    } catch (IOException e) {
      throw new RuntimeException("Could not load meshing.properties file.", e);
    }

    // Get the three fluid domains from the previous macro
    MeshOperationPart fluidRotateFront = ((MeshOperationPart) simulation.get(SimulationPartManager.class).getPart("Fluid_Rotate_Front"));
    MeshOperationPart fluidRotateRear = ((MeshOperationPart) simulation.get(SimulationPartManager.class).getPart("Fluid_Rotate_Rear"));
    MeshOperationPart fluidStatic = ((MeshOperationPart) simulation.get(SimulationPartManager.class).getPart("Fluid_Static"));
    
    // Corrected method to get dimensionless units using getObject
    dimensionlessUnits = ((Units) simulation.getUnitsManager().getObject(""));

    // --- SECTION 2: CREATE AND CONFIGURE AUTO MESH OPERATION ---
    simulation.println("Setting up Auto Mesh Operation...");
    autoMeshOp = simulation.get(MeshOperationManager.class).createAutoMeshOperation(
        new StringVector(new String[] {"star.resurfacer.ResurfacerAutoMesher", "star.resurfacer.AutomaticSurfaceRepairAutoMesher", "star.dualmesher.DualAutoMesher", "star.prismmesher.PrismAutoMesher"}), 
        new ArrayList<>(Arrays.<GeometryPart>asList(fluidRotateFront, fluidRotateRear, fluidStatic))
    );
    
    // Set meshing to run in parallel mode
    autoMeshOp.getMesherParallelModeOption().setSelected(MesherParallelModeOption.Type.PARALLEL);
    
    // Units
    Units mmUnits = ((Units) simulation.getUnitsManager().getObject("mm"));
    Units mUnits = ((Units) simulation.getUnitsManager().getObject("m"));
    
    // Set global default values from the properties file
    double baseSize = Double.parseDouble(props.getProperty("mesher.base.size"));
    autoMeshOp.getDefaultValues().get(BaseSize.class).setValueAndUnits(baseSize, mmUnits);
    
    double targetRelativeSize = Double.parseDouble(props.getProperty("mesher.target.relative.size"));
    autoMeshOp.getDefaultValues().get(PartsTargetSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(targetRelativeSize, dimensionlessUnits);
    
    double minimumRelativeSize = Double.parseDouble(props.getProperty("mesher.minimum.relative.size"));
    autoMeshOp.getDefaultValues().get(PartsMinimumSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(minimumRelativeSize, dimensionlessUnits);

    double tetPolyGrowthRate = Double.parseDouble(props.getProperty("mesher.tet.poly.growth.rate"));
    autoMeshOp.getDefaultValues().get(PartsTetPolyGrowthRate.class).setGrowthRate(tetPolyGrowthRate);

    // Set Prism Layer parameters
    PrismAutoMesher prismMesher = ((PrismAutoMesher) autoMeshOp.getMeshers().getObject("Prism Layer Mesher"));
    prismMesher.getPrismStretchingOption().setSelected(PrismStretchingOption.Type.WALL_THICKNESS);

    int numPrismLayers = Integer.parseInt(props.getProperty("prism.number.of.layers"));
    autoMeshOp.getDefaultValues().get(NumPrismLayers.class).getNumLayersValue().getQuantity().setValue(numPrismLayers);

    double prismWallThickness = Double.parseDouble(props.getProperty("prism.wall.thickness"));
    // Corrected to use mmUnits
    autoMeshOp.getDefaultValues().get(PrismWallThickness.class).setValueAndUnits(prismWallThickness, mmUnits);

    double prismReduction = Double.parseDouble(props.getProperty("prism.layer.reduction.percentage"));
    autoMeshOp.getDefaultValues().get(PrismLayerReductionPercentage.class).setValueAndUnits(prismReduction, dimensionlessUnits);
    
    double prismGapFill = Double.parseDouble(props.getProperty("prism.layer.gap.fill.percentage"));
    autoMeshOp.getDefaultValues().get(PrismLayerGapFillPercentage.class).setValueAndUnits(prismGapFill, dimensionlessUnits);
    
    double prismMinThickness = Double.parseDouble(props.getProperty("prism.layer.minimum.thickness"));
    autoMeshOp.getDefaultValues().get(PrismLayerMinimumThickness.class).setValueAndUnits(prismMinThickness, dimensionlessUnits);

    double marchAngle = Double.parseDouble(props.getProperty("prism.layer.boundary.march.angle"));
    autoMeshOp.getDefaultValues().get(PrismLayerBoundaryMarchAngle.class).setValueAndUnits(marchAngle, ((Units) simulation.getUnitsManager().getObject("deg")));

    double prismThicknessAbsolute = Double.parseDouble(props.getProperty("prism.thickness.absolute.size"));
    PrismThickness prismThickness = autoMeshOp.getDefaultValues().get(PrismThickness.class);
    prismThickness.getRelativeOrAbsoluteOption().setSelected(RelativeOrAbsoluteOption.Type.ABSOLUTE);
    
    ((ScalarPhysicalQuantity) prismThickness.getAbsoluteSizeValue()).setValueAndUnits(prismThicknessAbsolute, mUnits);

    // --- SECTION 3: APPLY CUSTOM SURFACE MESH CONTROLS ---
    simulation.println("Applying custom surface mesh controls...");
    
    // Custom control for the main vehicle body
    SurfaceCustomMeshControl bodyControl = autoMeshOp.getCustomMeshControls().createSurfaceControl();
    String[] bodyPartNames = props.getProperty("custom1.parts").split(",");
    
    List<PartSurface> bodySurfaces = new ArrayList<>();
    for (String partName : bodyPartNames) {
      PartSurface partSurface = ((PartSurface) fluidStatic.getPartSurfaceManager().getPartSurface(partName));
      bodySurfaces.add(partSurface);
    }
    bodyControl.getGeometryObjects().setObjects(bodySurfaces.toArray(new PartSurface[0]));

    bodyControl.getCustomConditions().get(PartsTargetSurfaceSizeOption.class).setSelected(PartsTargetSurfaceSizeOption.Type.CUSTOM);
    bodyControl.getCustomValues().get(PartsTargetSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(Double.parseDouble(props.getProperty("custom1.target.relative.size")), dimensionlessUnits);
    
    bodyControl.getCustomConditions().get(PartsMinimumSurfaceSizeOption.class).setSelected(PartsMinimumSurfaceSizeOption.Type.CUSTOM);
    bodyControl.getCustomValues().get(PartsMinimumSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(Double.parseDouble(props.getProperty("custom1.minimum.relative.size")), dimensionlessUnits);

    bodyControl.getCustomConditions().get(PartsSurfaceCurvatureOption.class).setSelected(PartsSurfaceCurvatureOption.Type.CUSTOM_VALUES);
    bodyControl.getCustomValues().get(SurfaceCurvature.class).setNumPointsAroundCircle(Double.parseDouble(props.getProperty("custom1.curvature.points")));

    bodyControl.getCustomConditions().get(PartsResurfacerSurfaceGrowthRateOption.class).setSelected(PartsResurfacerSurfaceGrowthRateOption.Type.CUSTOM_VALUES);
    SurfaceGrowthRate bodyGrowthRate = bodyControl.getCustomValues().get(SurfaceGrowthRate.class);
    bodyGrowthRate.setGrowthRateOption(SurfaceGrowthRate.GrowthRateOption.USER_SPECIFIED);
    bodyGrowthRate.getGrowthRateScalar().setValueAndUnits(Double.parseDouble(props.getProperty("custom1.growth.rate.scalar")), dimensionlessUnits);

    // Custom control for suspension and wheels
    SurfaceCustomMeshControl suspensionControl = autoMeshOp.getCustomMeshControls().createSurfaceControl();
    String[] suspensionPartNames = props.getProperty("custom2.parts").split(",");
    
    List<PartSurface> suspensionSurfaces = new ArrayList<>();
    for (String partName : suspensionPartNames) {
      PartSurface partSurface = ((PartSurface) fluidStatic.getPartSurfaceManager().getPartSurface(partName));
      suspensionSurfaces.add(partSurface);
    }
    suspensionControl.getGeometryObjects().setObjects(suspensionSurfaces.toArray(new PartSurface[0]));

    suspensionControl.getCustomConditions().get(PartsTargetSurfaceSizeOption.class).setSelected(PartsTargetSurfaceSizeOption.Type.CUSTOM);
    suspensionControl.getCustomValues().get(PartsTargetSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(Double.parseDouble(props.getProperty("custom2.target.relative.size")), dimensionlessUnits);

    suspensionControl.getCustomConditions().get(PartsMinimumSurfaceSizeOption.class).setSelected(PartsMinimumSurfaceSizeOption.Type.CUSTOM);
    suspensionControl.getCustomValues().get(PartsMinimumSurfaceSize.class).getRelativeSizeScalar().setValueAndUnits(Double.parseDouble(props.getProperty("custom2.minimum.relative.size")), dimensionlessUnits);

    // Custom control for the ground plane (to disable prisms)
    SurfaceCustomMeshControl groundControl = autoMeshOp.getCustomMeshControls().createSurfaceControl();
    PartSurface groundSurface = ((PartSurface) fluidStatic.getPartSurfaceManager().getPartSurface(props.getProperty("custom3.part")));
    groundControl.getGeometryObjects().setObjects(groundSurface);
    
    groundControl.getCustomConditions().get(PartsCustomizePrismMesh.class).getCustomPrismOptions().setSelected(PartsCustomPrismsOption.Type.DISABLE);
    
    // --- SECTION 4: APPLY VOLUMETRIC MESH CONTROLS ---
    simulation.println("Applying volumetric mesh controls...");
    
    // Create and configure volume control for the wheel refinement blocks
    createVolumeControl("volume.refinement.wheels");

    // Create and configure volume control for Block 2
    createVolumeControl("volume.refinement.block2");

    // Create and configure volume control for Underbody
    createVolumeControl("volume.refinement.underbody");

    // Create and configure volume control for Block 1
    createVolumeControl("volume.refinement.block1");
    
    // --- SECTION 5: EXECUTE THE MESH OPERATION ---
    simulation.println("Executing Auto Mesh Operation...");
    autoMeshOp.execute();
    simulation.println("Meshing process completed successfully.");
    simulation.println("Meshing process completed successfully. Saving state...");
    // This command saves the current state of the simulation to a file named Mesh.sim
    simulation.saveState("Mesh.sim");
    simulation.println("Simulation state saved.");
  }
  
  /**
   * Helper method to create and configure a VolumeCustomMeshControl.
   * @param propsKey The key in the properties file for this control (e.g., "volume.refinement.wheels").
   */
  private void createVolumeControl(String propsKey) {
      VolumeCustomMeshControl volumeControl = autoMeshOp.getCustomMeshControls().createVolumeControl();
      
      String[] partsAndSize = props.getProperty(propsKey).split(":");
      String[] partNames = partsAndSize[0].split(",");
      double relativeSize = Double.parseDouble(partsAndSize[1]);
      
      List<GeometryPart> refinementParts = new ArrayList<>();
      for (String name : partNames) {
          refinementParts.add(simulation.get(SimulationPartManager.class).getPart(name));
      }
      
      volumeControl.getGeometryObjects().setObjects(refinementParts.toArray(new GeometryPart[0]));
      
      volumeControl.getCustomConditions().get(VolumeControlResurfacerSizeOption.class).setVolumeControlBaseSizeOption(true);
      volumeControl.getCustomConditions().get(VolumeControlDualMesherSizeOption.class).setVolumeControlBaseSizeOption(true);
      
      VolumeControlSize volumeControlSize = volumeControl.getCustomValues().get(VolumeControlSize.class);
      volumeControlSize.getRelativeSizeScalar().setValueAndUnits(relativeSize, dimensionlessUnits);
  }
}