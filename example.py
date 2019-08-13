from pprint import pprint

import fargatebootstrap

from fargatebootstrap.projectdata import (
    EcsTask,
    ProjectConfig,
    DockerImage,
    ContainerDeployment,
)

#
from fargatebootstrap.project import Project

project_config = ProjectConfig(
    account_id="211367837384",
    region="ap-northeast-1",
    vpc_name="vpc_central",
    ecs_cluster_name="persistent-cluster",
    git_repo_name="my_repo",
    git_repo_branch="production",
)


# then prepare data required for Docker image
environment = "production"

annoy_image = DockerImage(
    name="annoy",
    environment=environment,
    script_name="annoy_async",
    description="Runs annoy service",
    ecr_endpoint=project_config.ecr_endpoint,
)

# # then prepare data required for deployment
annoy_deployment = ContainerDeployment(image=annoy_image, task_name="slimdish")

d2v_image = DockerImage(
    name="d2v",
    environment=environment,
    script_name="d2v_async",
    description="Runs d2v service",
    ecr_endpoint=project_config.ecr_endpoint,
)

# # then prepare data required for deployment
d2v_deployment = ContainerDeployment(image=d2v_image, task_name="slimdish")


task = EcsTask(
    name="slimdish",
    environment=environment,
    cpu=512,
    memory=2048,
    region=project_config.region,
    container_deployments=[annoy_deployment, d2v_deployment],
    subnets=["subnet1", "subnet2"],
    security_groups=["sg1", "sg2"],
)


"""
Add a task
"""
# new_environment = "staging"
# task_name = "my_new_task"
# new_image = DockerImage(
#     name="new_image",
#     environment=new_environment,
#     script_name="main",
#     description="Runs the new service",
#     ecr_endpoint=project_config.ecr_endpoint,
# )
#
#
# # # then prepare data required for deployment
# new_deployment = ContainerDeployment(
#     image=new_image, task_name=task_name, cpu=512, memory=2048
# )
#
#
# new_task = EcsTask(
#     name=task_name,
#     environment=new_environment,
#     region=project_config.region,
#     container_deployments=[new_deployment],
#     subnets=["subnet1", "subnet2"],
#     security_groups=["sg1", "sg2"],
# )
#
#
# # first we setup the project data
project = Project(config=project_config, tasks=[task])

project.make_files()
project.copy_files()
# project.build()
# project.provision()
