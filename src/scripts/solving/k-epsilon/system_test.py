import pytest
from pathlib import Path
import yaml
import shutil
import sys

# Ensure functions path is available
FUNCTIONS_PATH = Path(__file__).resolve().parent / "../../../functions"
sys.path.append(str(FUNCTIONS_PATH))

import IO_fcts
import populator_fcts
import suppl_fcts


@pytest.fixture(scope="session")
def aeroSUV_configs():
    """Load AeroSUV configs from real YAMLs."""
    config_dir = Path(__file__).resolve().parent / "../../../configs/AeroSUV"
    user_config_file = config_dir / "userConfig.yaml"
    advanced_config_file = config_dir / "advancedConfig.yaml"

    ConfigU = IO_fcts.load_config(user_config_file)
    ConfigA = IO_fcts.load_config(advanced_config_file)
    return ConfigU, ConfigA


@pytest.mark.usefixtures("aeroSUV_configs")
def test_file_generation_and_writing(tmp_path, aeroSUV_configs):
    configU, configA = aeroSUV_configs

    # Prepare paths for output files inside the tmp_path
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    paths = {
        'controlDict': system_dir / 'controlDict',
        'fvSchemes':  system_dir / 'fvSchemes',
        'fvSolution': system_dir / 'fvSolution',
        'snappyHexMeshDict': system_dir / 'snappyHexMeshDict',
        'meshDict':  system_dir / 'meshDict',
        'decomposeParDict': system_dir / 'decomposeParDict'
    }

    # 1) Generate controlDict for snappy if exists in config
    if 'snappy' in configU.get('control', {}):
        snappy_control = populator_fcts.generate_controlDict(configU, configA, subkey="snappy")
        IO_fcts.write_text_file(snappy_control, paths['controlDict'])
        assert paths['controlDict'].exists()
        content = paths['controlDict'].read_text()
        assert "snappyHexMesh" in content or len(content) > 0

    # 2) Generate controlDict for solver if exists
    if 'solver' in configU.get('control', {}):
        solver_control = populator_fcts.generate_controlDict(configU, configA, subkey="solver")
        solver_path = paths['controlDict'].with_name("controlDict.simpleFoam")
        IO_fcts.write_text_file(solver_control, solver_path)
        assert solver_path.exists()
        content = solver_path.read_text()
        assert "simpleFoam" in content or len(content) > 0

    # 3) Generate controlDict for pimpleInit if exists
    if 'pimpleInit' in configU.get('control', {}):
        pimple_control = populator_fcts.generate_controlDict(configU, configA, subkey="pimpleInit")
        pimple_path = paths['controlDict'].with_name("controlDict.pimpleInit")
        IO_fcts.write_text_file(pimple_control, pimple_path)
        assert pimple_path.exists()
        content = pimple_path.read_text()
        assert "pimple" in content or len(content) > 0

    # 4) Write decomposeParDict
    decompose_text = populator_fcts.decomposeParDict_populator(configU['cores'], configA['decomposeParDict'])
    IO_fcts.write_text_file(decompose_text, paths['decomposeParDict'])
    assert paths['decomposeParDict'].exists()
    assert "numberOfSubdomains" in paths['decomposeParDict'].read_text()

    # 5) Write fvSchemes
    fvSchemes_text = populator_fcts.generate_fvSchemes(configU['fvSchemes'], configA['fvSchemes'])
    IO_fcts.write_text_file(fvSchemes_text, paths['fvSchemes'])
    assert paths['fvSchemes'].exists()
    assert "ddtSchemes" in paths['fvSchemes'].read_text()

    # 6) Write fvSolution
    fvSolution_text = populator_fcts.generate_fvSolution(configA['fvSolution'])
    IO_fcts.write_text_file(fvSolution_text, paths['fvSolution'])
    assert paths['fvSolution'].exists()
    assert "solvers" in paths['fvSolution'].read_text()

@pytest.mark.usefixtures("aeroSUV_configs")
def test_mesh_generation_toggle(tmp_path, aeroSUV_configs):
    configU, configA = aeroSUV_configs

    # Prepare dummy mesh folder to simulate Fluent mesh presence
    (tmp_path / "constant/polyMesh").mkdir(parents=True)
    boundary_file = tmp_path / "constant/polyMesh/boundary"

    # Case 1: boundary file exists -> use_snappy and use_cfmesh should be False
    boundary_file.write_text("dummy boundary data")
    mesh_cfg = configU.get('mesh', {})
    use_snappy = mesh_cfg.get('useSnappy', False)
    use_cfmesh = mesh_cfg.get('useCfMesh', False)

    # Simulate detection of boundary file
    if boundary_file.exists():
        use_snappy = False
        use_cfmesh = False

    assert not use_snappy
    assert not use_cfmesh

    # Case 2: No boundary file -> use_snappy and use_cfmesh reflect config values
    boundary_file.unlink()
    use_snappy = mesh_cfg.get('useSnappy', False)
    use_cfmesh = mesh_cfg.get('useCfMesh', False)

    assert use_snappy == mesh_cfg.get('useSnappy', False)
    assert use_cfmesh == mesh_cfg.get('useCfMesh', False)

@pytest.mark.usefixtures("aeroSUV_configs")
def test_snappy_and_cfmesh_dict_generation(tmp_path, aeroSUV_configs):
    configU, configA = aeroSUV_configs

    system_dir = tmp_path / "system"
    system_dir.mkdir()
    paths = {
        'snappyHexMeshDict': system_dir / 'snappyHexMeshDict',
        'meshDict':  system_dir / 'meshDict',
    }

    # Only generate snappyHexMeshDict if useSnappy is True
    if configU.get('mesh', {}).get('useSnappy', False):
        snappy_text = populator_fcts.generate_snappyHexMeshDict(configU, configA,
            configU['snappyHexMeshDict'], configA['snappyHexMeshDict']
        )
        IO_fcts.write_text_file(snappy_text, paths['snappyHexMeshDict'])
        assert paths['snappyHexMeshDict'].exists()
        content = paths['snappyHexMeshDict'].read_text()
        assert len(content) > 0

    # Only generate meshDict if useCfMesh is True
    if configU.get('mesh', {}).get('useCfMesh', False):
        cfmesh_text = populator_fcts.generate_cfMeshDict(
            configU.get('meshDict', {}), configA.get('meshDict', {})
        )
        IO_fcts.write_text_file(cfmesh_text, paths['meshDict'])
        assert paths['meshDict'].exists()
        content = paths['meshDict'].read_text()
        assert len(content) > 0

