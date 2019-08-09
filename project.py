import subprocess
from dataclasses import dataclass
from typing import Tuple
from projectdata import ProjectConfig, EcsTask
from projectfiles import (
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

    def make_files(self):
        files = []
        files.append(MakeFile(self.tasks))
        for task in self.tasks:
            # print("making compose files")
            files.append(DockerComposeFile(task=task))
            # print("making dockerbuild buildspec file")
            files.append(BuildspecDockerbuildFile(task=task))
            # print("making container definitions file")
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

    def post_setup(self, build: bool = False):
        """
        - copy fles from `files/` to correct destinations
        - build docker images
        """
        subprocess.run("cp -r files/modules containers/", shell=True, check=True)
        subprocess.run("cp -r files/terraform/* terraform/", shell=True, check=True)
        for task in self.tasks:
            subprocess.run(
                f"cp -r files/buildspec/buildspec-unittest-allenvs.yml buildspec/buildspec-unittest-{task.name}-allenvs.yml",
                shell=True,
                check=True,
            )
        if build:
            subprocess.run("make lock_dependencies", shell=True, check=True)
            subprocess.run("make build_docker", shell=True, check=True)
