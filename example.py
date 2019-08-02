import os
from pprint import pprint
from projectfiles import (
    ContainerDeployment,
    Project,
    DockerImage,
    DockerComposeFile,
    BuildspecDockerbuildFile,
    ContainerDefinitionsFile,
)

# name = "zendishes"
# environment = "production"
# region = "ap-northeast-1"
# account_id = "211367837384"
# awslogs_group = "/aws/ecs/vpc_central/zendishes/production"
# files = {"buildspec": [BuildspecDockerbuildFile(name=name, environment=environment)]}
#

# "211367837384.dkr.ecr.ap-northeast-1.amazonaws.com/zendishes_production:latest",
# image url used in task definition, compose file and buildspec file

# first we setup the project
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

pprint("*" * 100)

pprint(buildspec.filepath)
pprint(container_definitions.filepath)
pprint(compose_file.filepath)

buildspec.write(
    buildspec.dump()
    .replace("'printf", "printf")
    .replace("''", "'")
    .replace("json'", "json")
)
container_definitions.write(container_definitions.dump())
compose_file.write(compose_file.dump())
# folders = {
#     'compose_files': 'compose_files'
#     ''
# }


# class Bootstrap:
#     def __init__(self, project: Project):
#         os.makedirs(f"containers/{project.name}")
#         os.makedir("buildspec")


# folders = {'containers/{zendishes}}

# Create buildspec files
# buildspec = BuildspecDockerbuildFile(image=zendishes_image)

# Create compose files

# Setup modules folder with config parser

# Setup project folders with
# - config files

# Setup terraform folder
# - generate task_definition file
# task_definition = TaskDefinitionFile(image=zendishes_image)
# - init scheduled_task module
# - init cicd module
