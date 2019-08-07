from pprint import pprint
from projectdata import Project, ContainerDeployment, DockerImage
from projectfiles import (
    DockerComposeFile,
    BuildspecDockerbuildFile,
    ContainerDefinitionsFile,
)


# first we setup the project data
project = Project(
    name="zendishes",
    account_id="211367837384",
    region="ap-northeast-1",
    vpc_name="vpc_central",
)

# then prepare data required for Docker image
image = DockerImage(
    name="zendishes",
    environment="production",
    description="Calculates zendishes",
    ecr_endpoint=project.ecr_endpoint,
)


#
# # then prepare data required for deployment
deployment = ContainerDeployment(project=project, image=image)

print(project)
print(image)
print(deployment)

# now setup files for CICD

# First the buildsec file
buildspec = BuildspecDockerbuildFile(image=image)
pprint(buildspec.document)
container_definitions = ContainerDefinitionsFile(deployment)
pprint(container_definitions.document)
compose_file = DockerComposeFile(image=image)

buildspec.write(
    buildspec.dump()
    # TODO find a nicer way to do this... Maybe with YAML dump options?
    .replace("'printf", "printf")
    .replace("''", "'")
    .replace("json'", "json")
)
container_definitions.write(container_definitions.dump())
compose_file.write(compose_file.dump())

# class Bootstrap:
#     def __init__(self, project: Project):
#         os.makedirs(f"containers/{project.name}")
#         os.makedir("buildspec")

# Setup terraform folder
# - generate task_definition file
# task_definition = TaskDefinitionFile(image=zendishes_image)
# - init scheduled_task module
# - init cicd module
