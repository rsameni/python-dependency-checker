import os
import subprocess
import re
import shutil
import json


class CompatibilityChecker:
    def __init__(self):
        # Initialize class variables
        self.requirements_old_file = None
        self.requirements_new_file = None
        self.code_file = None
        self.data_path = None
        self.venv_name = None
        self.venv_python_version = None

    def create_venv(self):
        """
        Create a virtual environment with the specified Python version.
        """
        subprocess.run(['conda', 'create', '-n', self.venv_name, f'python={self.venv_python_version}'], check=True)

    def activate_venv(self):
        """
        Activate the virtual environment.
        """
        activate_script = 'conda' if os.name == 'nt' else 'source'
        activate_script_path = os.path.join(os.environ['CONDA_PREFIX'], 'bin', 'activate')

        subprocess.run([activate_script, activate_script_path, self.venv_name], shell=True)

    def upgrade_library(self, library, requirements):
        """
        Upgrade a specific library to the latest version available.
        """
        if requirements[library] != '':
            return  # Library version already specified

        try:
            version_specification = requirements.get(library, '')
            if version_specification.startswith('='):
                version = version_specification[1:]
                subprocess.run(['conda', 'install', '-y', f'{library}={version}'], check=True)
            else:
                subprocess.run(['conda', 'install', '-y', f'{library}{version_specification}'], check=True)

            installed_version = self.get_installed_version(library)
            if installed_version:
                requirements[library] = installed_version
                print(f"Upgraded {library} to version {installed_version}")
            else:
                print(f"Failed to upgrade {library}")

        except subprocess.CalledProcessError:
            print(f"Failed to install {library}")

    def get_installed_version(self, library):
        """
        Get the currently installed version of a library.
        """
        try:
            output = subprocess.check_output(['conda', 'list', library, '--json']).decode()
            packages = json.loads(output)
            for package in packages:
                if package['name'] == library:
                    return package['version']
        except (subprocess.CalledProcessError, ValueError):
            pass

        return None

    def upgrade_dependencies(self):
        """
        Upgrade the dependencies listed in the requirements file.
        """
        with open(self.requirements_old_file, 'r') as f:
            lines = f.readlines()

        base_python_version_line = lines[0].strip()
        python_version_match = re.search(r'\d+\.\d+(?:\.\d+)?', base_python_version_line)
        if python_version_match:
            self.venv_python_version = python_version_match.group()
        else:
            raise ValueError("Invalid Python version specification")

        requirements = {}

        for line in lines[1:]:
            line = line.strip()
            if line:
                if '==' in line:
                    library, version = line.split('==')
                else:
                    library, version = line, ''
                if version.startswith('='):
                    requirements[library] = version[1:]  # Exact version specified
                elif version.startswith('>='):
                    requirements[library] = version[2:]  # Minimum version specified
                elif version.startswith('>'):
                    requirements[library] = version[1:]  # Minimum version specified
                elif version.startswith('<'):
                    requirements[library] = version[1:]  # Maximum version specified
                else:
                    requirements[library] = ''  # Library version not specified

        self.create_venv()
        self.activate_venv()

        for library in requirements:
            self.upgrade_library(library, requirements)

        with open(self.requirements_new_file, 'w') as f:
            f.write(f"python_version={self.venv_python_version}\n")
            for library, version in requirements.items():
                f.write(f"{library}=={version}\n")
