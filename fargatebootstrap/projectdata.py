from enum import IntEnum
from dataclasses import dataclass
from typing import List, Tuple
import abc


class FileType(IntEnum):
    yaml = 1
    json = 2
    dockerfile = 3
    pipfile = 4
    python = 5
    makefile = 6
    terraform = 7


class TaskType(IntEnum):
    scheduled = 1
    service = 2


@dataclass
class ProjectConfig:
    """

    """

    account_id: str
    region: str  # TODO move to EcsTask?
    vpc_name: str
    ecs_cluster_name: str  # TODO move to EcsTask?
    git_repo_name: str
    git_repo_branch: str

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
    script_name: str
    ecr_endpoint: str
    python_version: str = "3.7.4"
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
    essential: bool = True

    @property
    def awslogs_group(self):
        return f"/aws/ecs/{self.task_name}/{self.image.name}/{self.image.environment}"


@dataclass
class EcsTask(abc.ABC):
    """
    A task is one or more container deployments
    """

    name: str
    environment: str
    cpu: int
    memory: int
    region: str
    container_deployments: List[ContainerDeployment]
    subnets: List[str]
    security_groups: Tuple[str]


@dataclass
class EcsScheduledTask(EcsTask):
    """
    A scheduled task
    """

    schedule_expression: str
    task_type = TaskType.scheduled


# @dataclass
# class EcsServiceTask:
#     """
#     A task is one or more container deployments
#     """
#
#     name: str
#     environment: str
#     cpu: int
#     memory: int
#     region: str
#     container_deployments: List[ContainerDeployment]
#     subnets: List[str] = ()
# security_groups: Tuple[str] = ()
