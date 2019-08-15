import abc
import json
import yaml
import os
from dataclasses import dataclass
from typing import List

from .projectdata import EcsTask, ProjectConfig, DockerImage, FileType

from .templates import (
    dockerfile_template,
    pipfile_template,
    python_batch_script,
    makefile_template,
    scheduled_task_template,
)


class FileBase(abc.ABC):
    def dump(self) -> str:
        """
        improve this. I don't want to have to pass folders and filenames.
        At least it should be handled by some other class.
        """
        if self.filetype == FileType.yaml:
            dumped = yaml.dump(self.document, default_flow_style=False)
        elif self.filetype == FileType.json:
            dumped = json.dumps(self.document)
        elif self.filetype in [
            FileType.dockerfile,
            FileType.pipfile,
            FileType.python,
            FileType.makefile,
            FileType.terraform,
        ]:
            return self.document
        else:
            raise NotImplementedError()
        return dumped

    def write(self, dumped: str):
        folder, filename = os.path.split(self.filepath)
        if folder:
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.filepath) or self.overwrite_ok:
            print(f"Writing file {self.filepath}")
            with open(self.filepath, "w") as f:
                f.write(dumped)
        else:
            print(f"File already exists. {self.filepath}")

    @property
    @abc.abstractmethod
    def document(self):
        pass

    @property
    @abc.abstractmethod
    def filepath(self):
        pass

    @property
    @abc.abstractmethod
    def filetype(self):
        pass

    @property
    @abc.abstractmethod
    def overwrite_ok(self) -> bool:
        pass


class BuildspecTestFile(FileBase):
    # TODO implement this
    pass


class BuildspecDockerbuildFile(FileBase):
    """
    Class for creating a single buildspec file that
    - logs into AWS ECR
    - builds Docker image
    - pushes Docker image to ECR
    """

    filetype = FileType.yaml
    overwrite_ok = True

    def __init__(self, task: EcsTask, buildspec_version: str = "0.2"):
        """
        Args:
            name: name of the project
            environment: deployment environment, typically `production` or `staging`
        """
        name, environment = task.name, task.environment

        docker_compose_filename = f"docker-compose-{name}-{environment}-fargate.yml"
        imagedefinitions_filename = f"imagedefinitions_{name}-{environment}.json"
        imagedefinitions = [
            {"name": f"{name}", "imageUri": deployment.image.uri}
            for deployment in task.container_deployments
        ]

        phases = {
            "pre_build": {
                "commands": [
                    "$(aws ecr get-login --no-include-email --region ap-northeast-1)"
                ]
            },
            "build": {
                "commands": [f"docker-compose -f {docker_compose_filename} build"]
            },
            "post_build": [
                f"docker-compose -f {docker_compose_filename} push",
                f"printf {json.dumps(imagedefinitions)} > {imagedefinitions_filename}",
            ],
        }

        document = {
            "version": buildspec_version,
            "phases": phases,
            "artifacts": {"files": imagedefinitions_filename},
        }
        self.task = task
        self._imagedefinitions = imagedefinitions
        self._phases = phases
        self._document = document

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"buildspec/buildspec-dockerbuild-{self.task.name}-{self.task.environment}.yml"


class ContainerDefinitionsFile(FileBase):

    filetype = FileType.json
    overwrite_ok = True

    def __init__(self, task: EcsTask):
        """
        Defines a task to be run in ecs in `region`.
        Logs are sent to `awslogs_group` in CloudWatch.
        """
        # TODO add support for custom Docker tags
        tasks = [
            {
                "name": deployment.image.name,
                "image": deployment.image.uri,
                # TODO add env vars dynamically?
                "environment": [
                    {
                        "name": "RUNTIME_ENVIRONMENT",
                        "value": deployment.image.environment,
                    }
                ],
                "essential": deployment.essential,
                "dockerLabels": {
                    "name": deployment.image.name,
                    "description": deployment.image.description,
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": deployment.awslogs_group,
                        "awslogs-region": task.region,
                        "awslogs-stream-prefix": "ecs",
                    },
                }
                ### Not sure if the below three lines are necessary
                # "entryPoint": None,
                # "command": None,
                # "cpu": 0,
            }
            for deployment in task.container_deployments
        ]
        self.task = task
        self._document = tasks

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"terraform/container_definitions/container_definitions-{self.task.name}-{self.task.environment}.json"


class DockerComposeFile(FileBase):
    """
    The compose files are just used in the buildspec. It's possible that
    I won't need this class in the future, but now I'm just modelling my
    current setup.
    """

    filetype = FileType.yaml
    overwrite_ok = True

    def __init__(
        self,
        task: EcsTask,
        build_context: str = "containers/",  # TODO remove default value. Should be managed be abstraction.
        compose_version: str = "3.2",
    ):
        services = {
            "version": compose_version,
            "services": {
                deployment.image.name: {
                    "build": {
                        "context": build_context,
                        "dockerfile": deployment.image.filename,
                    },
                    "image": deployment.image.uri,
                    "environment": [
                        f"RUNTIME_ENVIRONMENT={deployment.image.environment}"
                    ],
                }
                for deployment in task.container_deployments
            },
        }
        self.task = task
        self._document = services

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"docker-compose-{self.task.name}-{self.task.environment}.yml"


@dataclass
class DockerFile(FileBase):

    image: DockerImage
    script_name: str = "main"
    python_version: str = "3.7.4"

    filetype = FileType.dockerfile
    overwrite_ok = True
    dockerfile = dockerfile_template

    @property
    def document(self):
        return self.dockerfile.render(image=self.image)

    @property
    def filepath(self):
        return f"containers/Dockerfile-{self.image.name}"


@dataclass
class Pipfile(FileBase):
    image: DockerImage
    python_version: str = "3.7"

    filetype = FileType.pipfile
    overwrite_ok = False
    pipfile = pipfile_template

    @property
    def document(self):
        return self.pipfile.render(python_version=self.python_version)

    @property
    def filepath(self):
        return f"containers/{self.image.name}/Pipfile"


@dataclass
class PythonScriptFile(FileBase):
    image: DockerImage

    filetype = FileType.python
    overwrite_ok = False
    script = python_batch_script

    @property
    def document(self):
        return self.script.render(image=self.image)

    @property
    def filepath(self):
        return f"containers/{self.image.name}/{self.image.script_name}.py"


@dataclass
class MakeFile(FileBase):
    tasks: List[EcsTask]

    filetype = FileType.makefile
    overwrite_ok = True
    template = makefile_template

    @property
    def document(self):
        return self.template.render(tasks=self.tasks)

    @property
    def filepath(self):
        return f"Makefile"


@dataclass
class TerraformScheduledTaskFile(FileBase):
    task: EcsTask
    project_config: ProjectConfig
    container_definitions_file: ContainerDefinitionsFile
    schedule_expression: str

    filetype = FileType.terraform
    overwrite_ok = True
    template = scheduled_task_template

    @property
    def document(self):
        # create the filepath to the container definitions file
        # so that the terraform module can read it.
        cd_folder, cd_filename = os.path.split(self.container_definitions_file.filepath)
        cd_filepath = os.path.join(*os.path.split(cd_folder)[1:], cd_filename)
        return self.template.render(
            task=self.task,
            project_config=self.project_config,
            schedule_expression=self.schedule_expression,
            container_definitions_filename=cd_filepath,
            subnets=json.dumps(self.task.subnets),
            security_groups=json.dumps(self.task.security_groups),
            unittest_subnets=json.dumps(self.task.pipeline.unittest_subnets),
            unittest_security_groups=json.dumps(
                self.task.pipeline.unittest_security_groups
            ),
        )

    @property
    def filepath(self):
        return f"terraform/{self.task.name}-{self.task.environment}.tf"
