# -*- coding: utf-8 -*-
import conda_tools

# *Initial setup
# Unblock git ssl
# VSCode extensions


# *Routine update
# conda_tools.update_base_env()
# conda_tools.update_current_env()
# Conda env variables set ok
# jupyter_tools.update_extensions()

"""Main module."""
if __name__ == "__main__":
    # *Get the user settings right

    # *Get the current project settings right
    conda_tools.update_env_from_yml()
    # print(Path.cwd())
