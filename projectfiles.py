import abc
import json
import yaml
import os
from enum import IntEnum
from dataclasses import dataclass


class FileType(IntEnum):
    yaml = 1
    json = 2


@dataclass
class DockerImage:
    name: str
    environment: str
    description: str
    ecr_endpoint: str
    tag: str = "latest"

    @property
    def uri(self):
        return f"{self.ecr_endpoint}/{self.name}_{self.environment}:{self.tag}"

    @property
    def filename(self):
        return f"Dockerfile-{self.name}"


@dataclass
class Project:
    account_id: str
    name: str
    region: str
    vpc_name: str

    @property
    def ecr_endpoint(self):
        return f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com"


@dataclass
class ContainerDeployment:
    image: DockerImage
    project: Project
    essential: bool = True

    @property
    def awslogs_group(self):
        return f"/aws/ecs/{self.project.vpc_name}/{self.image.name}/{self.image.environment}"


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
        return dumped

    def write(self, dumped: str):
        folder, filename = os.path.split(self.filepath)
        print(f"Writing file {self.filepath}")
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(self.filepath, "w") as f:
            f.write(dumped)

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


#
#
class BuildspecDockerbuildFile(FileBase):
    """
    Class for creating a single buildspec file that
    - logs into AWS ECR
    - builds Docker image
    - pushes Docker image to ECR
    """

    filetype = FileType.yaml

    def __init__(self, image: DockerImage, buildspec_version: str = "0.2"):
        """
        Args:
            name: name of the project
            environment: deployment environment, typically `production` or `staging`
        """
        name, environment = image.name, image.environment

        docker_compose_filename = f"docker-compose-{name}-{environment}-fargate.yml"
        imagedefinitions_filename = f"imagedefinitions_{name}-{environment}.json"
        imagedefinitions = [{"name": f"{name}", "imageUri": image.uri}]

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
                f"printf '{json.dumps(imagedefinitions)}' > {imagedefinitions_filename}",
            ],
        }

        document = {
            "version": buildspec_version,
            "phases": phases,
            "artifacts": imagedefinitions_filename,
        }
        self.image = image
        self._imagedefinitions = imagedefinitions
        self._phases = phases
        self._document = document

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"buildspec/{self.image.name}/buildspec-dockerbuild-{self.image.environment}.yml"


class ContainerDefinitionsFile(FileBase):

    filetype = FileType.json

    def __init__(self, deployment: ContainerDeployment):
        """
        Defines a task to be run in ecs in `region`.
        Logs are sent to `awslogs_group` in CloudWatch.
        """
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
                        "awslogs-region": deployment.project.region,
                        "awslogs-stream-prefix": "ecs",
                    },
                }
                ### Not sure if the below three lines are necessary
                # "entryPoint": None,
                # "command": None,
                # "cpu": 0,
            }
        ]
        self.deployment = deployment
        self._document = tasks

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"terraform/task_definitions/{self.deployment.image.name}_{self.deployment.image.environment}.json"


class DockerComposeFile(FileBase):
    """
    The compose files are just used in the buildspec. It's possible that
    I won't need this class in the future, but now I'm just modelling my
    current setup.
    """

    filetype = FileType.yaml

    def __init__(
        self,
        image: DockerImage,
        build_context: str = "containers/",  # TODO remove default value. Should be managed be abstraction.
        compose_version: str = "3.2",
    ):
        services = {
            "version": compose_version,
            "services": {
                image.name: {
                    "build": {"context": build_context, "dockerfile": image.filename},
                    "image": image.uri,
                    "environment": [f"RUNTIME_ENVIRONMENT={image.environment}"],
                }
            },
        }
        self.image = image
        self._document = services

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"docker-compose-{self.image.name}-{self.image.environment}.yml"
