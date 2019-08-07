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
