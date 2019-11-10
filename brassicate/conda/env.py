# Standard library
from pathlib import Path
import os
from stat import S_IREAD, S_IWRITE  # File permission flag settings
import subprocess  # Run shell commands (cross-platform)
from contextlib import contextmanager
from functools import wraps
import json

# External packages
import yaml


@contextmanager
def writable(
    env_name, enforce_readonly=True,  conda_prefix=Path(os.environ["conda_prefix"])
):
    """Make a named conda env temporarily writable and optionally read-only again.

    Envs should be read-only to enforce using environment.yml for specifying packages.
    If "conda-meta/history" is read-only, conda knows the env is read-only.
    (it's a "canary file" https://github.com/conda/conda/issues/4888#issuecomment-287201331)
    
    Always need to make base env writable - otherwise, conda treats child envs as read-only.
    If env_name is not "base", make the named env writable too.
    """
    # TODO Check that conda_prefix is a Path
    base_canaryfile = conda_prefix / "conda-meta" / "history"
    if not env_name == "base":
        env_canaryfile = conda_prefix / "envs" / env_name / "conda-meta" / "history"
    try:
        # *Always make base env writable
        # TODO Raise NotwritableError if can't make env writable
        Path.touch(base_canaryfile)  # create canaryfile if it doesn't exist
        os.chmod(base_canaryfile, S_IWRITE)  # make it writable
        # *In the case of a non-base env, make it writable too
        if not env_name == "base":
            # Create parent directory and canaryfile if they don't exist
            env_canaryfile.parent.mkdir(parents=True, exist_ok=True)
            Path.touch(env_canaryfile)
            os.chmod(env_canaryfile, S_IWRITE)  # make it writable
        yield
    finally:
        if enforce_readonly:
            # Make base read-only
            os.chmod(base_canaryfile, S_IREAD)
            if not env_name == "base":
                os.chmod(env_canaryfile, S_IREAD)


def find_env(env_name):
    env_path_list = json.loads(
        subprocess.run("conda info --json", shell=True, capture_output=True).stdout
    )["envs"]
    for env_path in env_path_list:
        if env_name in env_path:
            return env_path
    else:
        return None


def update_from_yml(
    yml_file: Path = Path("environment.yml"),
    enforce_readonly: bool = True,
    conda_prefix: Path = Path(os.environ["conda_prefix"]),
) -> None:  # TODO Return code based on success/failure (for command line use)
    """Given an environment.yml file that specifies a named conda env,
    update the env based on the yml file packages (or create the env if it doesn't exist).
    Make the env temporarily writable while updating,
    then make it read-only again afterwards if enforce_readonly flag is set.
    """
    # *Get env name from yml_file
    # TODO Raise exception if yml_file name field missing.
    # TODO Raise exception if no dependencies specified. This creates blank env and is bad!
    with open(yml_file) as f:
        environment_yml = yaml.load(f, Loader=yaml.FullLoader)
    env_name = environment_yml["name"]
    print(f"Found environment file for {env_name} at {yml_file.resolve()}")
    
    # *Set up path to expected location of env, and check if it exists already
    env_path = find_env(env_name)

    # *Make env writable and update or create it
    # TODO Suppress unhelpful "EnvironmentSectionNotValid" warning from conda
    with writable(env_name, enforce_readonly, conda_prefix):
        if env_path is not None:
            # ?Not sure if '--prune' flag is doing anything...
            subprocess.run("conda env update --file environment.yml --prune")
        else:
            print(f"Environment {env_name} doesn't exist, so create it...")
            subprocess.run("conda env create --file environment.yml")

# TODO Base env updater that updates conda then other packages via environment file
# ?Is update all needed for base or other envs?


# TODO Set environment variables from environment.yml
def set_env_vars(
    env_vars: dict, env_path: Path = Path(os.environ["conda_prefix"]),
):
    """Set environment variables for this conda environment.
    Based on "saving-environment-variables" section in 
    https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html
    Easiest to run this from the conda env that env vars are being set for.
    Overwrites existing vars (assumes env vars are best stored in environment.yml)
    """

    # *Set up skeleton scripts with no env vars
    # Activate
    activate_sh = ["#!/bin/sh\n"]  # Unix
    activate_bat = [""]  # Windows
    # Deactivate
    deactivate_sh = ["#!/bin/sh\n"]  # Unix
    deactivate_bat = [""]  # Windows

    # *Format input env_vars dict for Unix/Windows activate and deactivate scripts
    for var, val in env_vars.items():
        # TODO Make sure paths are output correctly for OS, especially env vars ($ %%)
        # Need generic per-OS paths
        # Effectively means paths relative to predefined OS environ vars

        # TODO Make sure that any already set variables are kept when adding new ones!
        # Unix
        activate_sh += f"export {var}={val}\n"
        deactivate_sh += f"unset {var}\n"

        # Windows
        activate_bat += f"set {var}={val}\n"
        deactivate_bat += f"set {var}=\n"

    # *Write activate scripts to files
    # Create directory if it doesn't exist
    activate_dir = (env_path / "etc/conda/activate.d").mkdir(
        parents=True, exist_ok=True
    )
    with open(activate_dir / "env_vars.sh", "w+") as f:
        f.writelines(activate_sh)
    with open(activate_dir / "env_vars.bat", "w+") as f:
        f.writelines(activate_bat)

    # *Write deactivate scripts
    # Create directory if it doesn't exist
    deactivate_dir = (env_path / "etc/conda/deactivate.d").mkdir(
        parents=True, exist_ok=True
    )
    with open(deactivate_dir / "env_vars.sh", "w+") as f:
        f.writelines(deactivate_sh)
    with open(deactivate_dir / "env_vars.bat", "w+") as f:
        f.writelines(deactivate_bat)



