# Configuration Setup Guide

Example configuration files are provided in the `examples` folder to showcase different capabilities of the solver. 
Follow the steps below to use them:

1. **Locate the examples archive** 
   Navigate to the `examplesConfigs` directory in this folder.

2. **Extract the archive** 
   Decompress the example package (e.g., `.zip` or `.tar.gz`) to access the configuration files.

3. **Select the relevant configuration** 
   Identify the configuration folder that best suits your case (e.g., `AeroSUV`, `ahmedBody`, or any other provided examples).

4. **Copy to the configs directory** 
   Move or copy the selected configuration folder into: src/configs/


Your project structure should now look similar to:

src/
configs/
AeroSUV/
userConfig.yaml
advancedConfig.yaml
...


5. **Verify configuration** 
Ensure that `userConfig.yaml` and any required `advancedConfig.yaml` files are present. 
The solver script will automatically use these files for setup.

---

Once these steps are completed, you can run the solver pipeline, and it will detect and use your chosen configuration.


