// Simcenter STAR-CCM+ macro: CombinedAeroWorkflow.java
// This macro automates the entire aerodynamics simulation workflow,
// from physics setup and motion definition to reports and data export.
// It has been fixed to use specific, hard-coded object names as required
// for a robust setup.
package macro;

import java.util.*;
import java.io.FileInputStream;
import java.io.IOException;

import star.common.*;
import star.base.neo.*;
import star.material.*;
import star.base.report.*;
import star.coupledflow.*;
import star.turbulence.*;
import star.flow.*;
import star.kwturb.*;
import star.metrics.*;
import star.mapping.*;
import star.vis.*;
import star.resurfacer.*;
import star.motion.*;

public class CombinedAeroWorkflow extends StarMacro {

    private Properties props;
    private Simulation simulation;
    private PhysicsContinuum physicsContinuum;
    private Units lengthUnits;
    private Units dimensionlessUnits;
    private Units velocityUnits;
    private Units areaUnits;
    private Units densityUnits;
    private Units degUnits;
    private Units rotationRateUnits;

    public void execute() {
        execute0();
    }

    private void execute0() {
        // --- SECTION 1: INITIALIZATION AND PARAMETER LOADING ---
        simulation = getActiveSimulation();

        try {
            props = new Properties();
            FileInputStream fis = new FileInputStream(resolvePath("workflow.properties"));
            props.load(fis);
        } catch (IOException e) {
            throw new RuntimeException("Could not load workflow.properties file.", e);
        }

        // Units definition
        lengthUnits = ((Units) simulation.getUnitsManager().getObject("m"));
        dimensionlessUnits = ((Units) simulation.getUnitsManager().getObject(""));
        velocityUnits = ((Units) simulation.getUnitsManager().getObject("m/s"));
        areaUnits = ((Units) simulation.getUnitsManager().getObject("m^2"));
        densityUnits = ((Units) simulation.getUnitsManager().getObject("kg/m^3"));
        degUnits = ((Units) simulation.getUnitsManager().getObject("deg"));
        rotationRateUnits = ((Units) simulation.getUnitsManager().getObject("rpm"));
        
        // --- SECTION 2: PHYSICS, SOLVER, AND INITIAL CONDITIONS ---
        setupPhysicsAndSolver();
        setupInitialConditions();

        // --- SECTION 3: MOTION AND REFERENCE FRAME SETUP ---
        setupMotionAndReferenceFrames();

        // --- SECTION 4: REPORTS AND PLOTS ---
        setupReportsAndPlots();

        // --- SECTION 5: VISUALIZATION (DERIVED PARTS ONLY) ---
        setupDerivedParts();

        // --- SECTION 6: DATA EXPORTS AND AUTOSAVE ---
        setupDataExports();

        simulation.println("Aero Workflow setup completed successfully. The simulation is now ready to be run.");
    }
    
    // =================================================================================
    // HELPER METHODS FOR EACH WORKFLOW STAGE
    // =================================================================================

    private void setupPhysicsAndSolver() {
        simulation.println("Setting up physics continuum...");
        physicsContinuum = simulation.getContinuumManager().createContinuum(PhysicsContinuum.class);
        physicsContinuum.enable(ThreeDimensionalModel.class);
        physicsContinuum.enable(SteadyModel.class);
        physicsContinuum.enable(SingleComponentGasModel.class);
        physicsContinuum.enable(CoupledFlowModel.class);
        physicsContinuum.enable(ConstantDensityModel.class);
        physicsContinuum.enable(TurbulentModel.class);
        physicsContinuum.enable(RansTurbulenceModel.class);
        physicsContinuum.enable(KOmegaTurbulence.class);
        physicsContinuum.enable(SstKwTurbModel.class);
        physicsContinuum.enable(KwAllYplusWallTreatment.class);
        physicsContinuum.enable(SolutionInterpolationModel.class);
        physicsContinuum.getModelManager().getModel(CoupledFlowModel.class).getUpwindOption().setSelected(FlowUpwindOption.Type.FIRST_ORDER);
        physicsContinuum.getModelManager().getModel(SstKwTurbModel.class).getUpwindOption().setSelected(UpwindOption.Type.FIRST_ORDER);
        physicsContinuum.getModelManager().getModel(SstKwTurbModel.class).getKwTurbCurvatureCorrectionOption().setSelected(KwTurbCurvatureCorrectionOption.Type.DURBIN);

        for (Region region : simulation.getRegionManager().getRegions()) {
            physicsContinuum.add(region);
        }

        CoupledImplicitSolver coupledImplicitSolver = ((CoupledImplicitSolver) simulation.getSolverManager().getSolver(CoupledImplicitSolver.class));
        coupledImplicitSolver.getAMGLinearSolver().getCycleOption().setSelected(AMGCycleOption.Type.FLEX_CYCLE);
        coupledImplicitSolver.getExpertInitManager().getExpertInitOption().setSelected(ExpertInitOption.Type.GRID_SEQ_METHOD);
        coupledImplicitSolver.getConvergenceAcceleratorManager().getConvergenceAcceleratorOption().setSelected(ConvergenceAcceleratorOption.Type.CONTINUITY_CONVERGENCE_ACCELERATOR);
        ContinuityConvergenceAccelerator continuityAccelerator = ((ContinuityConvergenceAccelerator) coupledImplicitSolver.getConvergenceAcceleratorManager().getConvergenceAccelerator());
        continuityAccelerator.setEnhancedStabilityTreatment(true);
        continuityAccelerator.setConvergenceAcceleratorUpdateFreq(Integer.parseInt(props.getProperty("solver.convergence.accelerator.update.freq")));
        StepStoppingCriterion stepStoppingCriterion = ((StepStoppingCriterion) simulation.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Steps"));
        stepStoppingCriterion.getMaximumNumberStepsObject().getQuantity().setValue(Double.parseDouble(props.getProperty("solver.max.steps")));
    }

    private void setupInitialConditions() {
        simulation.println("Setting up initial conditions...");
        VelocityProfile velocityProfile = physicsContinuum.getInitialConditions().get(VelocityProfile.class);
        double vel_x = Double.parseDouble(props.getProperty("initial.velocity.x"));
        double vel_y = Double.parseDouble(props.getProperty("initial.velocity.y"));
        double vel_z = Double.parseDouble(props.getProperty("initial.velocity.z"));
        velocityProfile.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponentsAndUnits(vel_x, vel_y, vel_z, velocityUnits);
        physicsContinuum.getInitialConditions().get(KwTurbSpecOption.class).setSelected(KwTurbSpecOption.Type.INTENSITY_LENGTH_SCALE);
        TurbulenceIntensityProfile turbulenceIntensityProfile = physicsContinuum.getInitialConditions().get(TurbulenceIntensityProfile.class);
        double turbIntensity = Double.parseDouble(props.getProperty("initial.turbulence.intensity"));
        turbulenceIntensityProfile.getMethod(ConstantScalarProfileMethod.class).getQuantity().setValueAndUnits(turbIntensity, dimensionlessUnits);
        TurbulentLengthScaleProfile turbulentLengthScaleProfile = physicsContinuum.getInitialConditions().get(TurbulentLengthScaleProfile.class);
        double lengthScale = Double.parseDouble(props.getProperty("initial.turbulent.length.scale"));
        turbulentLengthScaleProfile.getMethod(ConstantScalarProfileMethod.class).getQuantity().setValueAndUnits(lengthScale, lengthUnits);
        TurbulentVelocityScaleProfile turbulentVelocityScaleProfile = physicsContinuum.getInitialConditions().get(TurbulentVelocityScaleProfile.class);
        double velocityScale = Double.parseDouble(props.getProperty("initial.turbulent.velocity.scale"));
        turbulentVelocityScaleProfile.getMethod(ConstantScalarProfileMethod.class).getQuantity().setValueAndUnits(velocityScale, velocityUnits);
    }

    private void setupMotionAndReferenceFrames() {
        simulation.println("Setting up rotating reference frames and motion...");

        // Get values from properties file
        double rotationRate = Double.parseDouble(props.getProperty("motion.rotation.rate"));
        double groundVelocityX = Double.parseDouble(props.getProperty("motion.ground.velocity.x"));
        double[] frontWheelCoords = Arrays.stream(props.getProperty("motion.front.wheel.center.coords").split(",")).mapToDouble(Double::parseDouble).toArray();
        double[] rearWheelCoords = Arrays.stream(props.getProperty("motion.rear.wheel.center.coords").split(",")).mapToDouble(Double::parseDouble).toArray();

        // Create coordinate systems
        CartesianCoordinateSystem frontWheelCS = simulation.getCoordinateSystemManager().getLabCoordinateSystem().getLocalCoordinateSystemManager().createLocalCoordinateSystem(CartesianCoordinateSystem.class, "Cartesian");
        frontWheelCS.setPresentationName("Rotation_Front");
        frontWheelCS.getOrigin().setCoordinate(lengthUnits, lengthUnits, lengthUnits, new DoubleVector(frontWheelCoords));

        CartesianCoordinateSystem rearWheelCS = simulation.getCoordinateSystemManager().getLabCoordinateSystem().getLocalCoordinateSystemManager().createLocalCoordinateSystem(CartesianCoordinateSystem.class, "Cartesian");
        rearWheelCS.setPresentationName("Rotation_Rear");
        rearWheelCS.getOrigin().setCoordinate(lengthUnits, lengthUnits, lengthUnits, new DoubleVector(rearWheelCoords));

        // Create rotating reference frames
        UserRotatingReferenceFrame frontRotatingRF = simulation.get(ReferenceFrameManager.class).createReferenceFrame(UserRotatingReferenceFrame.class, "Rotating");
        frontRotatingRF.setPresentationName("Rotate_Front");
        frontRotatingRF.setCoordinateSystem(frontWheelCS);
        frontRotatingRF.getAxisDirection().setComponentsAndUnits(0.0, 1.0, 0.0, dimensionlessUnits);
        frontRotatingRF.getRotationRate().setValueAndUnits(rotationRate, rotationRateUnits);

        UserRotatingReferenceFrame rearRotatingRF = simulation.get(ReferenceFrameManager.class).createReferenceFrame(UserRotatingReferenceFrame.class, "Rotating");
        rearRotatingRF.setPresentationName("Rotate_Rear");
        rearRotatingRF.setCoordinateSystem(rearWheelCS);
        rearRotatingRF.getAxisDirection().setComponentsAndUnits(0.0, 1.0, 0.0, dimensionlessUnits);
        rearRotatingRF.getRotationRate().setValueAndUnits(rotationRate, rotationRateUnits);

        // --- ADDED: Create RotatingMotion for both wheels as per the user's working macro ---
        
        // Create motion for front wheel
        RotatingMotion frontRotatingMotion = simulation.get(MotionManager.class).createMotion(RotatingMotion.class, "Rotation");
        frontRotatingMotion.setPresentationName("Rotation_Front");
        // FIX: The API requires a cast from the generic type to the specific type.
        RotationRate frontRotRate = (RotationRate) frontRotatingMotion.getRotationSpecification();
        frontRotRate.getRotationRate().setValueAndUnits(rotationRate, rotationRateUnits);
        frontRotatingMotion.setCoordinateSystem(frontWheelCS);
        frontRotatingMotion.getRotationAxis().getDirection().setComponentsAndUnits(0.0, 1.0, 0.0, dimensionlessUnits);

        // Create motion for rear wheel
        RotatingMotion rearRotatingMotion = simulation.get(MotionManager.class).createMotion(RotatingMotion.class, "Rotation");
        rearRotatingMotion.setPresentationName("Rotation_Rear");
        // FIX: The API requires a cast from the generic type to the specific type.
        RotationRate rearRotRate = (RotationRate) rearRotatingMotion.getRotationSpecification();
        rearRotRate.getRotationRate().setValueAndUnits(rotationRate, rotationRateUnits);
        rearRotatingMotion.setCoordinateSystem(rearWheelCS);
        rearRotatingMotion.getRotationAxis().getDirection().setComponentsAndUnits(0.0, 1.0, 0.0, dimensionlessUnits);

        // Apply reference frames to regions
        Region frontRotRegion = simulation.getRegionManager().getRegion(props.getProperty("region.front.rotation"));
        if (frontRotRegion != null) {
            frontRotRegion.getValues().get(MotionSpecification.class).setReferenceFrame(frontRotatingRF);
        } else {
            simulation.println("WARNING: Front rotation region not found. Skipping motion setup for front wheels.");
        }

        Region rearRotRegion = simulation.getRegionManager().getRegion(props.getProperty("region.rear.rotation"));
        if (rearRotRegion != null) {
            rearRotRegion.getValues().get(MotionSpecification.class).setReferenceFrame(rearRotatingRF);
        } else {
            simulation.println("WARNING: Rear rotation region not found. Skipping motion setup for rear wheels.");
        }
        
        // --- IMPORTANT FIX: Use hard-coded boundary names with correct regions to avoid errors ---
        // Apply motion to boundaries using specific, full path names.
        
        // Setup Inlet Boundary
        // The inlet boundary is located in the "Fluid_Static" region.
        Region staticRegion = simulation.getRegionManager().getRegion("Fluid_Static");
        if (staticRegion != null) {
            Boundary inletBoundary = staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.Domain.Inlet");
            if (inletBoundary != null) {
                VelocityMagnitudeProfile inletVelocityProfile = inletBoundary.getValues().get(VelocityMagnitudeProfile.class);
                inletVelocityProfile.getMethod(ConstantScalarProfileMethod.class).getQuantity().setValueAndUnits(groundVelocityX, velocityUnits);
            } else {
                simulation.println("WARNING: Inlet boundary not found. Skipping inlet velocity setup.");
            }
        } else {
            simulation.println("WARNING: Static region not found. Skipping inlet velocity setup.");
        }

        // Set up moving ground
        // The ground boundary is also located in the "Fluid_Static" region.
        if (staticRegion != null) {
            Boundary groundBoundary = staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.Domain.Ground");
            if (groundBoundary != null) {
                groundBoundary.getConditions().get(WallSlidingOption.class).setSelected(WallSlidingOption.Type.VECTOR);
                WallRelativeVelocityProfile wallVelocityProfile = groundBoundary.getValues().get(WallRelativeVelocityProfile.class);
                wallVelocityProfile.getMethod(ConstantVectorProfileMethod.class).getQuantity().setComponentsAndUnits(groundVelocityX, 0.0, 0.0, velocityUnits);
            } else {
                simulation.println("WARNING: Ground boundary not found. Skipping moving ground setup.");
            }
        } else {
            simulation.println("WARNING: Static region not found. Skipping moving ground setup.");
        }
        
        // Set up rotating wheels
        Boundary frontWheelBoundary = simulation.getRegionManager().getRegion(props.getProperty("region.front.rotation")).getBoundaryManager().getBoundary(props.getProperty("boundary.front.wheel"));
        if (frontWheelBoundary != null) {
            frontWheelBoundary.getConditions().get(WallSlidingOption.class).setSelected(WallSlidingOption.Type.LOCAL_ROTATION_RATE);
            frontWheelBoundary.getValues().get(LocalAxis.class).getModelPartValue().setCoordinateSystem(frontWheelCS);
            frontWheelBoundary.getValues().get(LocalAxis.class).getModelPartValue().getAxisVector().setComponentsAndUnits(0.0, 1.0, 0.0, dimensionlessUnits);
            frontWheelBoundary.getValues().get(WallRelativeRotationProfile.class).getMethod(ConstantScalarProfileMethod.class).getQuantity().setValueAndUnits(rotationRate, rotationRateUnits);
        } else {
            simulation.println("WARNING: Front wheel boundary not found. Skipping wheel motion setup.");
        }

        Boundary rearWheelBoundary = simulation.getRegionManager().getRegion(props.getProperty("region.rear.rotation")).getBoundaryManager().getBoundary(props.getProperty("boundary.rear.wheel"));
        if (rearWheelBoundary != null) {
            rearWheelBoundary.getConditions().get(WallSlidingOption.class).setSelected(WallSlidingOption.Type.LOCAL_ROTATION_RATE);
            rearWheelBoundary.getValues().get(LocalAxis.class).getModelPartValue().setCoordinateSystem(rearWheelCS);
            rearWheelBoundary.getValues().get(LocalAxis.class).getModelPartValue().getAxisVector().setComponentsAndUnits(0.0, 1.0, 0.0, dimensionlessUnits);
            rearWheelBoundary.getValues().get(WallRelativeRotationProfile.class).getMethod(ConstantScalarProfileMethod.class).getQuantity().setValueAndUnits(rotationRate, rotationRateUnits);
        } else {
            simulation.println("WARNING: Rear wheel boundary not found. Skipping wheel motion setup.");
        }
    }
    
    private List<Boundary> getForceReportBoundaries() {
        List<Boundary> boundaries = new ArrayList<>();
        
        Region rotateFrontRegion = simulation.getRegionManager().getRegion("Fluid_Rotate_Front");
        Region rotateRearRegion = simulation.getRegionManager().getRegion("Fluid_Rotate_Rear");
        Region staticRegion = simulation.getRegionManager().getRegion("Fluid_Static");

        if (rotateFrontRegion != null) {
            boundaries.add(rotateFrontRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.14_suspension_front.suspension-front"));
            boundaries.add(rotateFrontRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.17_wheels-front.wheels-front"));
        } else {
            simulation.println("WARNING: Region 'Fluid_Rotate_Front' not found. Skipping its boundaries.");
        }

        if (rotateRearRegion != null) {
            boundaries.add(rotateRearRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.15_suspension_rear.suspension-rear"));
            boundaries.add(rotateRearRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.18_wheels-rear.wheels-rear"));
        } else {
            simulation.println("WARNING: Region 'Fluid_Rotate_Rear' not found. Skipping its boundaries.");
        }
        
        if (staticRegion != null) {
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.01_body.body"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.02_side-mirrors.side-mirrors"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.03_rear-end_estate.rear-end_estate"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.08_underbody-flat.underbody-flat"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.14_suspension_front.suspension-front"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.15_suspension_rear.suspension-rear"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.17_wheels-front.wheels-front"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.18_wheels-rear.wheels-rear"));
            boundaries.add(staticRegion.getBoundaryManager().getBoundary("Fluid_Volume.SUV_Wrap.SUV.20_cooling-air-closing.cooling-air-inlet-closing"));
        } else {
            simulation.println("WARNING: Region 'Fluid_Static' not found. Skipping its boundaries.");
        }
        
        return boundaries;
    }

    private void setupReportsAndPlots() {
        simulation.println("Setting up reports and plots...");
        List<Boundary> reportBoundaries = getForceReportBoundaries();

        double refDensity = Double.parseDouble(props.getProperty("reference.density"));
        double refVelocity = Double.parseDouble(props.getProperty("reference.velocity"));
        double refArea = Double.parseDouble(props.getProperty("reference.area"));

        ForceCoefficientReport dragReport = simulation.getReportManager().create("star.flow.ForceCoefficientReport");
        dragReport.setPresentationName(props.getProperty("drag.report.name"));
        dragReport.getParts().setObjects(reportBoundaries.toArray(new Boundary[0]));
        dragReport.getReferenceDensity().setValueAndUnits(refDensity, densityUnits);
        dragReport.getReferenceVelocity().setValueAndUnits(refVelocity, velocityUnits);
        dragReport.getReferenceArea().setValueAndUnits(refArea, areaUnits);
        dragReport.getDirection().setComponents(1.0, 0.0, 0.0);
        simulation.getMonitorManager().createMonitorAndPlot(new ArrayList<>(Arrays.asList(dragReport)), true, "%1$s Plot");

        ForceCoefficientReport liftReport = simulation.getReportManager().create("star.flow.ForceCoefficientReport");
        liftReport.setPresentationName(props.getProperty("lift.report.name"));
        liftReport.getParts().setObjects(reportBoundaries.toArray(new Boundary[0]));
        liftReport.getReferenceDensity().setValueAndUnits(refDensity, densityUnits);
        liftReport.getReferenceVelocity().setValueAndUnits(refVelocity, velocityUnits);
        liftReport.getReferenceArea().setValueAndUnits(refArea, areaUnits);
        liftReport.getDirection().setComponents(0.0, 0.0, 1.0);
        simulation.getMonitorManager().createMonitorAndPlot(new ArrayList<>(Arrays.asList(liftReport)), true, "%1$s Plot");

        ForceCoefficientReport skinFrictionReport = simulation.getReportManager().create("star.flow.ForceCoefficientReport");
        skinFrictionReport.setPresentationName(props.getProperty("skin.friction.report.name"));
        skinFrictionReport.getParts().setObjects(reportBoundaries.toArray(new Boundary[0]));
        skinFrictionReport.getReferenceDensity().setValueAndUnits(refDensity, densityUnits);
        skinFrictionReport.getReferenceVelocity().setValueAndUnits(refVelocity, velocityUnits);
        skinFrictionReport.getReferenceArea().setValueAndUnits(refArea, areaUnits);
        skinFrictionReport.getForceOption().setSelected(ForceReportForceOption.Type.SHEAR);
        simulation.getMonitorManager().createMonitorAndPlot(new ArrayList<>(Arrays.asList(skinFrictionReport)), true, "%1$s Plot");
    }

    private void setupDerivedParts() {
        simulation.println("Setting up derived parts...");
        String partNamesProperty = props.getProperty("derived.parts.names");
        if (partNamesProperty != null) {
            String[] partNames = partNamesProperty.split(",");
            for (String pName : partNames) {
                String trimmedName = pName.trim();
                switch (trimmedName) {
                    case "Isosurface":
                        createIsoSurface();
                        break;
                    case "Front_Wheel_Center":
                    case "Front_Wheel_Wake":
                    case "Rear_Wheel_Center":
                    case "Rear_Wheel_Wake":
                    case "Car_Wake":
                        createPlaneSection(trimmedName);
                        break;
                    default:
                        simulation.println("WARNING: Unknown derived part name '" + trimmedName + "'. Skipping.");
                        break;
                }
            }
        }
    }

    private void createPlaneSection(String name) {
        String propertyName = "derived.part." + name.toLowerCase().replace("_", ".") + ".origin";
        String originProperty = props.getProperty(propertyName);
        if (originProperty == null) {
            simulation.println("ERROR: Missing property '" + propertyName + "'. Cannot create plane section.");
            return;
        }
        String[] originData = originProperty.split(",");
        double[] origin = Arrays.stream(originData).mapToDouble(Double::parseDouble).toArray();

        PlaneSection plane = (PlaneSection) simulation.getPartManager().createImplicitPart(
            new ArrayList<>(Collections.<NamedObject>emptyList()),
            new DoubleVector(new double[] {1.0, 0.0, 0.0}),
            new DoubleVector(new double[] {0.0, 0.0, 0.0}),
            0, 1, new DoubleVector(new double[] {0.0}), null
        );
        plane.setPresentationName(name);

        plane.getOriginCoordinate().setCoordinate(lengthUnits, lengthUnits, lengthUnits, new DoubleVector(origin));
        plane.getOrientationCoordinate().setCoordinate(lengthUnits, lengthUnits, lengthUnits, new DoubleVector(new double[] {1.0, 0.0, 0.0}));
    }

    private void createIsoSurface() {
        String isoValueProperty = props.getProperty("derived.part.isosurface.value");
        if (isoValueProperty == null) {
            simulation.println("ERROR: Missing property 'derived.part.isosurface.value'. Cannot create isosurface.");
            return;
        }
        double isoValue = Double.parseDouble(isoValueProperty);

        IsoPart isoPart = simulation.getPartManager().createIsoPart(
            new ArrayList<>(Collections.<NamedObject>emptyList()),
            simulation.getFieldFunctionManager().getFunction("Qcriterion"),
            null
        );
        isoPart.setPresentationName("Isosurface");
        isoPart.setMode(IsoMode.ISOVALUE_SINGLE);
        isoPart.getSingleIsoValue().getValueQuantity().setValue(isoValue);
        isoPart.getInputParts().setObjects(simulation.getRegionManager().getRegions().toArray(new Region[0]));
    }

    private void setupDataExports() {
        simulation.println("Setting up data exports...");
        AutoSave autoSave = simulation.getSimulationIterator().getAutoSave();
        autoSave.setMaxAutosavedFiles(Integer.parseInt(props.getProperty("autosave.max.files")));
        autoSave.getStarUpdate().setEnabled(true);
        autoSave.getStarUpdate().getIterationUpdateFrequency().getIterationFrequencyQuantity().setValue((int) Double.parseDouble(props.getProperty("autosave.frequency")));

        AutoExport autoExport = simulation.getSimulationIterator().getAutoExport();
        autoExport.getSolutionExportFormat().setSelected(SolutionExportFormat.Type.valueOf(props.getProperty("autoexport.format")));
        autoExport.setBaseName(props.getProperty("autoexport.base.name"));

        List<ClientServerObject> exportScalars = new ArrayList<>();
        String scalarNamesProperty = props.getProperty("autoexport.scalars");
        if (scalarNamesProperty != null) {
            String[] scalarNames = scalarNamesProperty.split(",");
            for (String sName : scalarNames) {
                String trimmedName = sName.trim();
                if (trimmedName.equals("VelocityMagnitude")) {
                    exportScalars.add(simulation.getFieldFunctionManager().getFunction("Velocity").getMagnitudeFunction());
                } else if (trimmedName.equals("VorticityVectorComponent")) {
                    exportScalars.add(simulation.getFieldFunctionManager().getFunction("VorticityVector").getComponentFunction(0));
                } else {
                    FieldFunction ff = simulation.getFieldFunctionManager().getFunction(trimmedName);
                    if (ff != null) {
                        exportScalars.add(ff);
                    } else {
                        simulation.println("WARNING: Field Function '" + trimmedName + "' not found. Skipping.");
                    }
                }
            }
        }
        autoExport.setScalars(exportScalars);

        // Uses the newly fixed method to get boundaries.
        List<Boundary> exportBoundaries = getForceReportBoundaries();
        autoExport.setBoundaries(exportBoundaries);

        List<Part> exportParts = new ArrayList<>();
        String partNamesProperty = props.getProperty("autoexport.parts");
        if (partNamesProperty != null) {
            String[] partNames = partNamesProperty.split(",");
            for (String pName : partNames) {
                String trimmedName = pName.trim();
                Part part = simulation.getPartManager().getObject(trimmedName);
                if (part != null) {
                    exportParts.add(part);
                } else {
                    simulation.println("WARNING: Export Part '" + trimmedName + "' not found. Skipping.");
                }
            }
        }
        autoExport.setParts(exportParts);

        autoExport.getStarUpdate().setEnabled(true);
        autoExport.getStarUpdate().getIterationUpdateFrequency().getIterationFrequencyQuantity().setValue((int) Double.parseDouble(props.getProperty("autoexport.frequency")));
    }
}
