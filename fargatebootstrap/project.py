import subprocess
from dataclasses import dataclass
from typing import Tuple
import os
import shutil
from .projectdata import ProjectConfig, EcsTask
from .projectfiles import (
    DockerFile,
    Pipfile,
    PythonScriptFile,
    MakeFile,
    DockerComposeFile,
    BuildspecDockerbuildFile,
    ContainerDefinitionsFile,
    TerraformScheduledTaskFile,
)


@dataclass
class Project:
    """
    A project specifies where tasks are deployed
    A project contains one or more tasks.

    - one Dockerfile per Docker image
    - one buildspec file per Task
    - one compose file per task
    - one terraform file, each with cicd module and scheduled_task module, per task
    """

    config: ProjectConfig
    tasks: Tuple[EcsTask]
    # TODO turn below three vars into args and make @property def register on File classes
    buildspec_dir = "buildspec"
    containers_dir = "containers"
    terraform_dir = "terraform"

    def make_files(self):
        files = []
        files.append(MakeFile(self.tasks))
        for task in self.tasks:
            files.append(DockerComposeFile(task=task))
            files.append(BuildspecDockerbuildFile(task=task))
            cdf = ContainerDefinitionsFile(task=task)
            files.append(cdf)

            # Generate Dockerfiles and initiate script files
            for deployment in task.container_deployments:
                files.append(DockerFile(deployment.image))
                files.append(Pipfile(deployment.image))
                files.append(PythonScriptFile(deployment.image))

            files.append(
                TerraformScheduledTaskFile(
                    task=task,
                    project_config=self.config,
                    container_definitions_file=cdf,
                )
            )

        for file in files:
            file.write(file.dump())

    def copy_files(self):
        """
        Copy files from `files/` to correct destinations
        """
        root_dir = os.path.split(__file__)[0]
        modules_src = os.path.join(root_dir, "files/modules")
        buildspec_src = os.path.join(
            root_dir, "files/buildspec/buildspec-unittest-allenvs.yml"
        )
        terraform_src = os.path.join(root_dir, "files/terraform")
        try:
            shutil.copytree(
                src=modules_src, dst=os.path.join(self.containers_dir, "modules/")
            )
        except FileExistsError:
            print("modules files already copied")

        try:
            shutil.copytree(src=terraform_src, dst=self.terraform_dir)
        except FileExistsError:
            print("terraform files already copied")

        for task in self.tasks:
            try:
                if not os.path.exists(self.buildspec_dir):
                    os.mkdir(self.buildspec_dir)
                shutil.copy(
                    src=buildspec_src,
                    dst=os.path.join(
                        self.buildspec_dir,
                        f"buildspec-unittest-{task.name}-allenvs.yml",
                    ),
                )
            except FileExistsError:
                print("buildspec files already copied")
        # subprocess.run("cp -r files/terraform/* terraform/", shell=True, check=True)
        # for task in self.tasks:
        #     subprocess.run(
        #         f"cp -r files/buildspec/buildspec-unittest-allenvs.yml buildspec/buildspec-unittest-{task.name}-allenvs.yml",
        #         shell=True,
        #         check=True,
        #     )

    def build(self):
        subprocess.run("make lock_dependencies", shell=True, check=True)
        subprocess.run("make build_docker", shell=True, check=True)

    def provision(self):
        # TODO: Fix this
        subprocess.run("cd terraform && terraform init")
        # subprocess.run("make tfapply")

    def bootstrap(self):
        self.copy_files()
        self.make_files()
        print(
            """
*******************************************************************************
Project bootstrapped!
*******************************************************************************

Now run
$ make lock_dependencies && make build
"""
        )
