import abc
import json
import yaml
import os
from dataclasses import dataclass


@dataclass
class DockerImage:
    ecr_endpoint: str
    name: str
    environment: str
    tag: str = "latest"
    description: str

    @property
    def uri(self):
        return f"{self.ecr_endpoint}/{self.name}_{self.environment}:{self.tag}"

    @property
    def filename(self):
        return f"Dockerfile-{self.name}"


@dataclass
class ContainerDeployment:
    region: str
    awslogs_group: str
    image: DockerImage
    essential: bool = True


class FileBase(abc.ABC):
    def render(self, folder: str, filename: str):
        """
        improve this. I don't want to have to pass folders and filenames.
        At least it should be handled by some other class.
        """
        filepath = os.path.join(folder, filename)
        with open(filepath, "rw") as f:
            f.write(yaml.dump(self.document))

    @property
    @abc.abstractmethod
    def document(self):
        return self.document


class BuildspecFile(FileBase):
    """
    Class for creating a single buildspec file
    """

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

        self._imagedefinitions = imagedefinitions
        self._phases = phases
        self._document = document

    @property
    def document(self):
        return self._document


class ContainerDefinitionsFile:
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
                        "awslogs-region": deployment.region,
                        "awslogs-stream-prefix": "ecs",
                    },
                }
                ### Not sure if the below three lines are necessary
                # "entryPoint": None,
                # "command": None,
                # "cpu": 0,
            }
        ]
        self._document = tasks

    @property
    def document(self):
        return self._document
