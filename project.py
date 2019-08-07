from dataclasses import dataclass
from typing import Tuple
from projectdata import ProjectConfig, EcsTask
from projectfiles import (
    DockerFile,
    Pipfile,
    PythonScriptFile,
    DockerComposeFile,
    BuildspecDockerbuildFile,
    ContainerDefinitionsFile,
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
        for task in self.tasks:
            # print("making compose files")
            files.append(DockerComposeFile(task=task))
            # print("making dockerbuild buildspec file")
            files.append(BuildspecDockerbuildFile(task=task))
            # print("making container definitions file")
            files.append(ContainerDefinitionsFile(task=task))

            # Generate Dockerfiles and initiate script files
            for deployment in task.container_deployments:
                files.append(DockerFile(deployment.image))
                files.append(Pipfile(deployment.image))
                files.append(PythonScriptFile(deployment.image))

        for file in files:
            file.write(file.dump())
