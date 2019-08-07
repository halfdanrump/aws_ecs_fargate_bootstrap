from pprint import pprint

from projectdata import EcsTask, ProjectConfig, DockerImage, ContainerDeployment

from project import Project

project_config = ProjectConfig(
    account_id="211367837384",
    region="ap-northeast-1",
    vpc_name="vpc_central",
    ecs_cluster_name="persistent-cluster",
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
annoy_deployment = ContainerDeployment(
    image=annoy_image, task_name="slimdish", cpu=512, memory=2048
)

d2v_image = DockerImage(
    name="d2v",
    environment=environment,
    script_name="d2v_async",
    description="Runs d2v service",
    ecr_endpoint=project_config.ecr_endpoint,
)

# # then prepare data required for deployment
d2v_deployment = ContainerDeployment(
    image=d2v_image, task_name="slimdish", cpu=512, memory=2048
)


task = EcsTask(
    name="slimdish",
    environment=environment,
    region=project_config.region,
    container_deployments=[annoy_deployment, d2v_deployment],
    subnets=["subnet1", "subnet2"],
    security_groups=["sg1", "sg2"],
)
#
#
# # first we setup the project data
project = Project(config=project_config, tasks=[task])

project.make_files()

# print(project)
# print(image)
# print(deployment)
#
# # now setup files for CICD
#
# # First the buildsec file
# buildspec = BuildspecDockerbuildFile(image=image)
# pprint(buildspec.document)
# container_definitions = ContainerDefinitionsFile(deployment)
# pprint(container_definitions.document)
# compose_file = DockerComposeFile(image=image)
#
# buildspec.write(
#     buildspec.dump()
#     # TODO find a nicer way to do this... Maybe with YAML dump options?
#     .replace("'printf", "printf")
#     .replace("''", "'")
#     .replace("json'", "json")
# )
# container_definitions.write(container_definitions.dump())
# compose_file.write(compose_file.dump())
#
# # class Bootstrap:
# #     def __init__(self, project: Project):
# #         os.makedirs(f"containers/{project.name}")
# #         os.makedir("buildspec")
#
# # Setup terraform folder
# # - generate task_definition file
# # task_definition = TaskDefinitionFile(image=zendishes_image)
# # - init scheduled_task module
# # - init cicd module
