// Simcenter STAR-CCM+ macro: GeometryAndBC.java
// This macro automates the creation of fluid regions via Boolean operations
// and assigns initial boundary conditions.
// It reads all part names and boundary settings from a properties file.
package macro;

import java.util.*;
import java.io.FileInputStream;
import java.io.IOException;

import star.common.*;
import star.base.neo.*;
import star.meshing.*;
import star.vis.*;
import star.surfacewrapper.*;

public class OperationsCommented extends StarMacro {

  private Properties props;
  private Simulation simulation;

  public void execute() {
    execute0();
  }

  private void execute0() {

    // --- SECTION 1: INITIALIZATION AND PARAMETER LOADING ---
    simulation = getActiveSimulation();
    
    // Load part names and settings from the properties file
    try {
      props = new Properties();
      FileInputStream fis = new FileInputStream(resolvePath("operations.properties"));
      props.load(fis);
    } catch (IOException e) {
      throw new RuntimeException("Could not load operations.properties file.", e);
    }

    // Get a reference to the parts created in previous macros
    SimpleBlockPart domainPart = ((SimpleBlockPart) simulation.get(SimulationPartManager.class).getPart(props.getProperty("domain.part.name")));
    MeshOperationPart suvWrapPart = ((MeshOperationPart) simulation.get(SimulationPartManager.class).getPart(props.getProperty("vehicle.wrap.name")));
    SimpleCylinderPart frontCylinder = ((SimpleCylinderPart) simulation.get(SimulationPartManager.class).getPart(props.getProperty("front.cylinder.name")));
    SimpleCylinderPart rearCylinder = ((SimpleCylinderPart) simulation.get(SimulationPartManager.class).getPart(props.getProperty("rear.cylinder.name")));
    
    MeshOperationManager meshOpManager = simulation.get(MeshOperationManager.class);
    SimulationPartManager partManager = simulation.get(SimulationPartManager.class);

    // --- SECTION 2: BOOLEAN OPERATIONS ---
    simulation.println("Performing Boolean operations to create fluid regions...");

    // Subtract the wrapped vehicle from the domain to get the main fluid volume
    SubtractPartsOperation subtractOp1 = (SubtractPartsOperation) meshOpManager.createSubtractPartsOperation(new ArrayList<>(Arrays.<GeometryPart>asList(domainPart, suvWrapPart)));
    subtractOp1.getTargetPartManager().setObjects(domainPart);
    subtractOp1.execute();
    MeshOperationPart fluidVolume = ((MeshOperationPart) partManager.getPart("Subtract"));
    fluidVolume.setPresentationName(props.getProperty("fluid.volume.name"));

    // Intersect the fluid volume with the front cylinder for the rotating region
    IntersectPartsOperation intersectOp1 = (IntersectPartsOperation) meshOpManager.createIntersectPartsOperation(new ArrayList<>(Arrays.<GeometryPart>asList(fluidVolume, frontCylinder)));
    intersectOp1.execute();
    MeshOperationPart fluidRotateFront = ((MeshOperationPart) partManager.getPart("Intersect"));
    fluidRotateFront.setPresentationName(props.getProperty("front.rotate.name"));

    // Intersect the fluid volume with the rear cylinder for the rotating region
    IntersectPartsOperation intersectOp2 = (IntersectPartsOperation) meshOpManager.createIntersectPartsOperation(new ArrayList<>(Arrays.<GeometryPart>asList(fluidVolume, rearCylinder)));
    intersectOp2.execute();
    MeshOperationPart fluidRotateRear = ((MeshOperationPart) partManager.getPart("Intersect 2"));
    fluidRotateRear.setPresentationName(props.getProperty("rear.rotate.name"));

    // Subtract the two cylinders from the main fluid volume to get the static region
    SubtractPartsOperation subtractOp2 = (SubtractPartsOperation) meshOpManager.createSubtractPartsOperation(new ArrayList<>(Arrays.<GeometryPart>asList(fluidVolume, frontCylinder, rearCylinder)));
    subtractOp2.getTargetPartManager().setObjects(fluidVolume);
    subtractOp2.execute();
    MeshOperationPart fluidStatic = ((MeshOperationPart) partManager.getPart("Subtract 2"));
    fluidStatic.setPresentationName(props.getProperty("static.fluid.name"));
    
    // Imprint all three fluid parts to ensure a conforming mesh at the interfaces
    ImprintPartsOperation imprintOp = (ImprintPartsOperation) meshOpManager.createImprintPartsOperation(new ArrayList<>(Arrays.<GeometryPart>asList(fluidRotateFront, fluidRotateRear, fluidStatic)));
    imprintOp.execute();

    // --- SECTION 3: SURFACE MANIPULATION ---
    simulation.println("Splitting and renaming fluid part surfaces...");
    
    PartSurface domainSurface = ((PartSurface) domainPart.getPartSurfaceManager().getPartSurface("Block Surface"));

    domainPart.splitPartSurfaceByPatch(domainSurface, new IntVector(new int[] {29}), "Inlet");
    domainPart.splitPartSurfaceByPatch(domainSurface, new IntVector(new int[] {28}), "Side");
    domainPart.splitPartSurfaceByPatch(domainSurface, new IntVector(new int[] {30}), "Symmetry");
    domainPart.splitPartSurfaceByPatch(domainSurface, new IntVector(new int[] {27}), "Top");
    domainPart.splitPartSurfaceByPatch(domainSurface, new IntVector(new int[] {32}), "Outlet");

    PartSurface groundSurface = ((PartSurface) domainPart.getPartSurfaceManager().getPartSurface("Block Surface"));
    groundSurface.setPresentationName("Ground");
    imprintOp.execute();

    
    // --- SECTION 4: FINALIZING THE PARTS AND CREATING REGIONS ---
    simulation.println("Updating parts and creating regions...");
    partManager.updateParts(new ArrayList<>(Arrays.<GeometryPart>asList(fluidStatic, fluidRotateFront, fluidRotateRear)));

    simulation.getRegionManager().newRegionsFromParts(new ArrayList<>(Arrays.<GeometryPart>asList(fluidRotateFront, fluidRotateRear, fluidStatic)), "OneRegionPerPart", null, "OneBoundaryPerPartSurface", null, RegionManager.CreateInterfaceMode.BOUNDARY, "OneEdgeBoundaryPerPart", null);
    
    // --- SECTION 5: ASSIGNING BOUNDARY CONDITIONS ---
    simulation.println("Assigning boundary conditions...");
    Region staticRegion = simulation.getRegionManager().getRegion(props.getProperty("static.fluid.name"));
    
    // Assign boundary types using the full boundary names
    assignBoundaryType(staticRegion, "Fluid_Volume.Domain.Inlet", props.getProperty("static.fluid.boundaries.inlet"));
    assignBoundaryType(staticRegion, "Fluid_Volume.Domain.Outlet", props.getProperty("static.fluid.boundaries.outlet"));
    assignBoundaryType(staticRegion, "Fluid_Volume.Domain.Side", props.getProperty("static.fluid.boundaries.side"));
    assignBoundaryType(staticRegion, "Fluid_Volume.Domain.Symmetry", props.getProperty("static.fluid.boundaries.symmetry"));
    assignBoundaryType(staticRegion, "Fluid_Volume.Domain.Top", props.getProperty("static.fluid.boundaries.top"));
    
    simulation.println("Geometry and boundary conditions setup complete.");
  }
  
  /**
   * Helper method to find a boundary by name and assign a new boundary type.
   * @param region The region containing the boundary.
   * @param boundaryFullName The full name of the boundary (e.g., "Fluid_Volume.Domain.Inlet").
   * @param typeName The string name of the new boundary type (e.g., "Inlet", "Pressure").
   */
  private void assignBoundaryType(Region region, String boundaryFullName, String typeName) {
      try {
          Boundary boundary = region.getBoundaryManager().getBoundary(boundaryFullName);
          BoundaryType boundaryType = (BoundaryType) simulation.get(ConditionTypeManager.class).get((Class) Class.forName("star.common." + typeName + "Boundary"));
          boundary.setBoundaryType(boundaryType);
      } catch (Exception e) {
          simulation.println("Error assigning boundary type " + typeName + " to " + boundaryFullName + ": " + e.getMessage());
      }
  }
}