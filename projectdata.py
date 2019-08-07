from enum import IntEnum
from dataclasses import dataclass
from typing import List


class FileType(IntEnum):
    yaml = 1
    json = 2


@dataclass
class DockerImage:
    """
    Data for a single Docker image
    """

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
class ContainerDeployment:
    """
    A container deployment specifies how a single Docker image is deployed
    """

    # TODO add support for multiple Docker images
    image: DockerImage
    essential: bool = True
    cpu: int
    memory: int

    @property
    def awslogs_group(self):
        return f"/aws/ecs/{self.name}/{self.image.name}/{self.image.environment}"


@dataclass
class EcsTask:
    """
    A task is one or more container deployments
    """

    name: str
    containers: List[ContainerDeployment]
    subnets: List[str] = []
    security_groups: List[str] = []


@dataclass
class Project:
    """
    A project specifies where tasks are deployed
    A project contains one or more tasks
    """

    account_id: str
    name: str
    region: str
    vpc_name: str
    ecs_cluster_arn: str
    tasks: List[EcsTask]

    @property
    def ecr_endpoint(self):
        return f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com"
