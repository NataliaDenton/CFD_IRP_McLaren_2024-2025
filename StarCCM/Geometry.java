package macro;

import java.util.*;
import java.io.FileInputStream;
import java.io.IOException;

import star.common.*;
import star.base.neo.*;
import star.vis.*;
import star.meshing.*;

/**
 * A Star-CCM+ macro to automate the setup of a vehicle aerodynamics simulation.
 * This script performs the following steps:
 * 1. Reads geometry parameters (dimensions for blocks and cylinders) from a separate properties file.
 * 2. Imports multiple STL files to build the vehicle geometry.
 * 3. Creates and configures a geometry scene for visualization.
 * 4. Defines and creates several refinement regions (blocks and cylinders) based on the parameters.
 * 5. Composites all imported geometry parts into a single part.
 */
public class GeometryCommented extends StarMacro {

  private Properties props;

  public void execute() {
    execute0();
  }

  private void execute0() {

    // SECTION 1: INITIALIZATION AND PARAMETER LOADING
    Simulation simulation = getActiveSimulation();
    
    // Load geometry parameters from the properties file
    try {
      props = new Properties();
      FileInputStream fis = new FileInputStream(resolvePath("geometry.properties"));
      props.load(fis);
    } catch (IOException e) {
      throw new RuntimeException("Could not load geometry.properties file.", e);
    }

    // SECTION 2: GEOMETRY IMPORT 
    
    PartImportManager partImportManager = simulation.get(PartImportManager.class);
    Units lengthUnits = simulation.getUnitsManager().getPreferredUnits(Dimensions.Builder().length(1).build());
    Units mmUnits = ((Units) simulation.getUnitsManager().getObject("mm"));

    // Get STL file paths from the properties file and split them into an array
    String[] stlPaths = props.getProperty("stl.paths").split(",");
    
    // Import all STL parts listed in the properties file
    simulation.println("Importing STL geometry...");
    partImportManager.importStlParts(new StringVector(stlPaths), "OneSurfacePerPatch", "OnePartPerFile", mmUnits, true, 1.0E-5, false, false);

    // SECTION 3: SCENE AND CAMERA SETUP 
    // Create and configure a geometry scene for visualization
    simulation.println("Setting up geometry scene...");
    simulation.getSceneManager().createGeometryScene("Geometry Scene", "Outline", "Surface", 1, null);
    Scene geometryScene = simulation.getSceneManager().getScene("Geometry Scene 1");
    
    // Set hardcopy resolution for screenshots
    SceneUpdate sceneUpdate = geometryScene.getSceneUpdate();
    HardcopyProperties hardcopyProperties = sceneUpdate.getHardcopyProperties();
    hardcopyProperties.setCurrentResolutionWidth(1160);
    hardcopyProperties.setCurrentResolutionHeight(580);
    
    geometryScene.resetCamera();
    geometryScene.setTransparencyOverrideMode(SceneTransparencyOverride.MAKE_SCENE_TRANSPARENT);

    // SECTION 4: REFINEMENT REGION CREATION 
    simulation.println("Creating refinement regions");
    MeshPartFactory meshPartFactory = simulation.get(MeshPartFactory.class);
    LabCoordinateSystem labCoordinateSystem = simulation.getCoordinateSystemManager().getLabCoordinateSystem();

    // Creation of the different blocks
    createBlockFromProperties("domain", "Domain", meshPartFactory, labCoordinateSystem, lengthUnits);
    createBlockFromProperties("refinement1", "Refinement_Underbody", meshPartFactory, labCoordinateSystem, lengthUnits);
    createBlockFromProperties("refinement2", "Refinement_1", meshPartFactory, labCoordinateSystem, lengthUnits);
    createBlockFromProperties("refinement3", "Refinement_2", meshPartFactory, labCoordinateSystem, lengthUnits);
    createBlockFromProperties("refinement4", "Refinement_Front_Wheel", meshPartFactory, labCoordinateSystem, lengthUnits);
    createBlockFromProperties("refinement5", "Refinement_Rear_Wheel", meshPartFactory, labCoordinateSystem, lengthUnits);

    // Cylinder for interfaces creation
    createCylinderFromProperties("cylinder1", "Rotate_Front", meshPartFactory, labCoordinateSystem, lengthUnits);
    createCylinderFromProperties("cylinder2", "Rotate_Rear", meshPartFactory, labCoordinateSystem, lengthUnits);

    // Revert scene transparency
    geometryScene.setTransparencyOverrideMode(SceneTransparencyOverride.USE_DISPLAYER_PROPERTY);
    geometryScene.setTransparencyOverrideMode(SceneTransparencyOverride.MAKE_SCENE_TRANSPARENT);

    // SECTION 5: GEOMETRY COMPOSITING 
    simulation.println("Compositing all parts");
    SimulationPartManager partManager = simulation.get(SimulationPartManager.class);
    
    // Collect all imported parts to composite them
    List<GeometryPart> partsToComposite = new ArrayList<>();
    for (String path : stlPaths) {
      String fileName = new java.io.File(path).getName();
      String partName = fileName.replace(".stl", "");
      partsToComposite.add(partManager.getPart(partName));
    }
    
    // Perform the composite operation
    partManager.compositeParts(partsToComposite);
    
    // Rename the new composite part
    CompositePart suvPart = ((CompositePart) partManager.getPart("Composite"));
    suvPart.setPresentationName("SUV");
    
    simulation.println("Macro execution finished successfully.");
  }

  // Helper method to create a block part from properties
  private void createBlockFromProperties(String prefix, String partName, MeshPartFactory meshPartFactory, LabCoordinateSystem cs, Units units) {
    SimpleBlockPart block = meshPartFactory.createNewBlockPart(getActiveSimulation().get(SimulationPartManager.class));
    block.setDoNotRetessellate(true);
    block.setPresentationName(partName);
    block.setCoordinateSystem(cs);

    // Set corner 1 coordinates from the properties file
    block.getCorner1().setCoordinateSystem(cs);
    double c1_x = Double.parseDouble(props.getProperty(prefix + ".corner1.x"));
    double c1_y = Double.parseDouble(props.getProperty(prefix + ".corner1.y"));
    double c1_z = Double.parseDouble(props.getProperty(prefix + ".corner1.z"));
    block.getCorner1().setCoordinate(units, units, units, new DoubleVector(new double[] {c1_x, c1_y, c1_z}));

    // Set corner 2 coordinates from the properties file
    block.getCorner2().setCoordinateSystem(cs);
    double c2_x = Double.parseDouble(props.getProperty(prefix + ".corner2.x"));
    double c2_y = Double.parseDouble(props.getProperty(prefix + ".corner2.y"));
    double c2_z = Double.parseDouble(props.getProperty(prefix + ".corner2.z"));
    block.getCorner2().setCoordinate(units, units, units, new DoubleVector(new double[] {c2_x, c2_y, c2_z}));

    block.rebuildSimpleShapePart();
    block.setDoNotRetessellate(false);
  }

  // Helper method to create a cylinder part from properties
  private void createCylinderFromProperties(String prefix, String partName, MeshPartFactory meshPartFactory, LabCoordinateSystem cs, Units units) {
    SimpleCylinderPart cylinder = meshPartFactory.createNewCylinderPart(getActiveSimulation().get(SimulationPartManager.class));
    cylinder.setDoNotRetessellate(true);
    cylinder.setPresentationName(partName);
    cylinder.setCoordinateSystem(cs);

    // Set start coordinates from properties
    cylinder.getStartCoordinate().setCoordinateSystem(cs);
    double s_x = Double.parseDouble(props.getProperty(prefix + ".start.x"));
    double s_y = Double.parseDouble(props.getProperty(prefix + ".start.y"));
    double s_z = Double.parseDouble(props.getProperty(prefix + ".start.z"));
    cylinder.getStartCoordinate().setCoordinate(units, units, units, new DoubleVector(new double[] {s_x, s_y, s_z}));

    // Set end coordinates from properties
    cylinder.getEndCoordinate().setCoordinateSystem(cs);
    double e_x = Double.parseDouble(props.getProperty(prefix + ".end.x"));
    double e_y = Double.parseDouble(props.getProperty(prefix + ".end.y"));
    double e_z = Double.parseDouble(props.getProperty(prefix + ".end.z"));
    cylinder.getEndCoordinate().setCoordinate(units, units, units, new DoubleVector(new double[] {e_x, e_y, e_z}));

    // Set radius from properties
    double radius = Double.parseDouble(props.getProperty(prefix + ".radius"));
    cylinder.getRadius().setUnits(units);
    cylinder.getRadius().setValue(radius);

    cylinder.getTessellationDensityOption().setSelected(TessellationDensityOption.Type.FINE);
    cylinder.rebuildSimpleShapePart();
    cylinder.setDoNotRetessellate(false);
  }
}