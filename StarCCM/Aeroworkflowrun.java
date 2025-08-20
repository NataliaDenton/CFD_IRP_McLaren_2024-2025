// Simcenter STAR-CCM+ macro: AeroWorkflowRun.java
// This macro manages the simulation run phases: steady-state first-order,
// steady-state second-order, and transient, including the transition
// to rotating motion for the wheels.
package macro;

import java.util.*;
import java.io.FileInputStream;
import java.io.IOException;

import star.common.*;
import star.base.neo.*;
import star.coupledflow.*;
import star.turbulence.*;
import star.flow.*;
import star.kwturb.*;
import star.saturb.*;
import star.metrics.*;
import star.motion.*;

public class CombinedAeroWorkflowRun extends StarMacro {

    private Properties props;
    private Simulation simulation;
    private PhysicsContinuum physicsContinuum;
    private Units timeUnits;

    public void execute() {
        execute0();
    }

    private void execute0() {

        // --- SECTION 1: INITIALIZATION AND PARAMETER LOADING ---
        simulation = getActiveSimulation();

        try {
            props = new Properties();
            FileInputStream fis = new FileInputStream(resolvePath("run.properties"));
            props.load(fis);
        } catch (IOException e) {
            throw new RuntimeException("Could not load run.properties file.", e);
        }

        physicsContinuum = simulation.getContinuumManager().getContinuum("Physics 1");
        if (physicsContinuum == null) {
            throw new RuntimeException("Could not find 'Physics 1' continuum.");
        }
        timeUnits = ((Units) simulation.getUnitsManager().getObject("s"));

        // --- SECTION 2: STEADY-STATE RUNS ---
        runSteadyState();

        // --- SECTION 3: SWITCH TO TRANSIENT ---
        switchToTransient();

        // --- SECTION 4: START TRANSIENT RUN ---
        // This is the command that starts the transient simulation.
        simulation.println("Starting transient simulation...");
        simulation.getSimulationIterator().run();

        simulation.println("Aero Workflow run completed successfully.");
    }

    // =================================================================================
    // RUN METHODS FOR EACH STAGE
    // =================================================================================

    private void runSteadyState() {
        simulation.println("Starting steady-state run...");

        // Stage 1: First-Order Iterations
        simulation.println("Setting FIRST ORDER convection and initializing...");
        CoupledFlowModel coupledFlowModel = physicsContinuum.getModelManager().getModel(CoupledFlowModel.class);
        SstKwTurbModel sstKwTurbModel = physicsContinuum.getModelManager().getModel(SstKwTurbModel.class);
        coupledFlowModel.getUpwindOption().setSelected(FlowUpwindOption.Type.FIRST_ORDER);
        sstKwTurbModel.getUpwindOption().setSelected(UpwindOption.Type.FIRST_ORDER);

        simulation.getSolution().initializeSolution();

        simulation.println("Running " + props.getProperty("first.order.iterations") + " first-order iterations...");
        StepStoppingCriterion stepStoppingCriterion = simulation.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Steps");
        stepStoppingCriterion.getMaximumNumberStepsObject().getQuantity().setValue(Double.parseDouble(props.getProperty("first.order.iterations")));

        simulation.getSimulationIterator().run();

        // Stage 2: Second-Order Iterations
        simulation.println("Switching to SECOND ORDER convection and running " + props.getProperty("second.order.iterations") + " iterations...");
        coupledFlowModel.getUpwindOption().setSelected(FlowUpwindOption.Type.SECOND_ORDER);
        sstKwTurbModel.getUpwindOption().setSelected(UpwindOption.Type.FIRST_ORDER);
        stepStoppingCriterion.getMaximumNumberStepsObject().getQuantity().setValue(Double.parseDouble(props.getProperty("second.order.iterations")));

        simulation.getSimulationIterator().run();
    }

    private void switchToTransient() {
        simulation.println("Switching to transient simulation...");

        // Disable steady-state models
        simulation.println(" Disabling Steady Model...");
        physicsContinuum.disableModel(physicsContinuum.getModelManager().getModel(SteadyModel.class));

        // Enable transient models
        simulation.println(" Enabling Implicit Unsteady and DES Models...");
        physicsContinuum.enable(ImplicitUnsteadyModel.class);
        physicsContinuum.enable(DesTurbulenceModel.class);
        physicsContinuum.enable(SstKwTurbDesModel.class);

        // Configure transient solver settings
        simulation.println("Configuring transient solver settings...");
        ImplicitUnsteadySolver implicitUnsteadySolver = ((ImplicitUnsteadySolver) simulation.getSolverManager().getSolver(ImplicitUnsteadySolver.class));
        implicitUnsteadySolver.getTimeStep().setValueAndUnits(Double.parseDouble(props.getProperty("transient.time.step")), timeUnits);

        // Configure stopping criteria for transient run
        StepStoppingCriterion stepStoppingCriterion = ((StepStoppingCriterion) simulation.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Steps"));
        stepStoppingCriterion.getMaximumNumberStepsObject().getQuantity().setValue(Double.parseDouble(props.getProperty("transient.max.steps")));

        InnerIterationStoppingCriterion innerIterationStoppingCriterion = ((InnerIterationStoppingCriterion) simulation.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Inner Iterations"));
        innerIterationStoppingCriterion.getMaxIterations().getQuantity().setValue(Double.parseDouble(props.getProperty("transient.max.inner.iterations")));

        PhysicalTimeStoppingCriterion physicalTimeStoppingCriterion = ((PhysicalTimeStoppingCriterion) simulation.getSolverStoppingCriterionManager().getSolverStoppingCriterion("Maximum Physical Time"));
        physicalTimeStoppingCriterion.getMaximumTime().setValueAndUnits(Double.parseDouble(props.getProperty("transient.max.physical.time")), timeUnits);

        // Enable rotating motion for wheel regions
        simulation.println("Applying rotating motion to wheel regions...");
        Region rotateFrontRegion = simulation.getRegionManager().getRegion("Fluid_Rotate_Front");
        Region rotateRearRegion = simulation.getRegionManager().getRegion("Fluid_Rotate_Rear");

        if (rotateFrontRegion != null) {
            simulation.println("Configuring motion for 'Fluid_Rotate_Front'...");
            MotionManager motionManager = rotateFrontRegion.getMotionManager();
            if (motionManager.has(RotatingMotion.class)) {
                RotatingMotion rotatingMotion = (RotatingMotion) motionManager.getObject("Rotating Motion");
                if (rotatingMotion != null) {
                    rotatingMotion.getRotationRate().setValueAndUnits(Double.parseDouble(props.getProperty("wheel.rotation.rate")), (Units) simulation.getUnitsManager().getObject("rad/s"));
                }
            }
        } else {
            simulation.println("WARNING: Region 'Fluid_Rotate_Front' not found. Skipping motion setup.");
        }

        if (rotateRearRegion != null) {
            simulation.println("Configuring motion for 'Fluid_Rotate_Rear'...");
            MotionManager motionManager = rotateRearRegion.getMotionManager();
            if (motionManager.has(RotatingMotion.class)) {
                RotatingMotion rotatingMotion = (RotatingMotion) motionManager.getObject("Rotating Motion");
                if (rotatingMotion != null) {
                    rotatingMotion.getRotationRate().setValueAndUnits(Double.parseDouble(props.getProperty("wheel.rotation.rate")), (Units) simulation.getUnitsManager().getObject("rad/s"));
                }
            }
        } else {
            simulation.println("WARNING: Region 'Fluid_Rotate_Rear' not found. Skipping motion setup.");
        }

        simulation.println("Transient setup complete.");
    }
}