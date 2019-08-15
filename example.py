from pprint import pprint

import fargatebootstrap

from fargatebootstrap.projectdata import (
    EcsScheduledTask,
    TaskType,
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

conterec_image = DockerImage(
    name="conterec",
    environment=environment,
    script_name="conterec_async",
    description="Runs conterec service",
    ecr_endpoint=project_config.ecr_endpoint,
)

# # then prepare data required for deployment
conterec_deployment = ContainerDeployment(image=conterec_image, task_name="foryou")

colarec_image = DockerImage(
    name="colarec",
    environment=environment,
    script_name="colarec_async",
    description="Runs colarec service",
    ecr_endpoint=project_config.ecr_endpoint,
)

# # then prepare data required for deployment
colarec_deployment = ContainerDeployment(image=colarec_image, task_name="foryou")


task = EcsScheduledTask(
    name="foryou",
    environment=environment,
    cpu=512,
    memory=2048,
    schedule_expression="rate(5 minutes)",
    region=project_config.region,
    container_deployments=[conterec_deployment, colarec_deployment],
    subnets=["subnet1", "subnet2"],
    security_groups=["sg1", "sg2"],
)


# """
# Add a task
# """
new_environment = "staging"
task_name = "conterec"
new_image = DockerImage(
    name="conterec",
    environment=new_environment,
    script_name="main",
    description="Runs conterec",
    ecr_endpoint=project_config.ecr_endpoint,
)


# # then prepare data required for deployment
new_deployment = ContainerDeployment(image=new_image, task_name=task_name)


new_task = EcsScheduledTask(
    name=task_name,
    environment=new_environment,
    cpu=512,
    memory=2048,
    schedule_expression="rate(24 hours)",
    region=project_config.region,
    container_deployments=[new_deployment],
    subnets=["subnet1", "subnet2"],
    security_groups=["sg1", "sg2"],
)

# # first we setup the project data
project = Project(config=project_config, tasks=[task])
# project.tasks.append(new_task)
project.bootstrap()


# project.build()
# project.provision()
