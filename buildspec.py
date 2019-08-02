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


class BuildspecFile:
    """
    Class for creating a single buildspec file
    """

    def __init__(self, image: DockerImage):
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
            "version": 0.2,
            "phases": phases,
            "artifacts": imagedefinitions_filename,
        }
        self.docker_compose_filename = docker_compose_filename
        self.imagedefinitions = imagedefinitions
        self.phases = phases
        self.document = document

    def render(self, folder: str, filename: str):
        filepath = os.path.join(folder, filename)
        with open(filepath, "rw") as f:
            f.write(yaml.dump(self.document))
