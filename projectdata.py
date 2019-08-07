from enum import IntEnum
from dataclasses import dataclass
from typing import List, Tuple


class FileType(IntEnum):
    yaml = 1
    json = 2


@dataclass
class ProjectConfig:
    """

    """

    account_id: str
    region: str  # TODO move to EcsTask?
    vpc_name: str
    ecs_cluster_name: str  # TODO move to EcsTask?

    @property
    def ecr_endpoint(self):
        return f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com"

    @property
    def ecs_cluster_arn(self):
        return f"arn:aws:ecs:{self.region}:{self.account_id}:cluster/{self.ecs_cluster_name}"


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
    task_name: str
    image: DockerImage
    cpu: int
    memory: int
    essential: bool = True

    @property
    def awslogs_group(self):
        return f"/aws/ecs/{self.task_name}/{self.image.name}/{self.image.environment}"


@dataclass
class EcsTask:
    """
    A task is one or more container deployments
    """

    name: str
    environment: str
    region: str
    container_deployments: List[ContainerDeployment]
    subnets: List[str] = ()
    security_groups: Tuple[str] = ()
