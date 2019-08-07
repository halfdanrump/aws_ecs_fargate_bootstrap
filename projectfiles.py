import abc
import json
import yaml
import os
from dataclasses import dataclass

from jinja2 import Template

from projectdata import (
    Project,
    ProjectConfig,
    ContainerDeployment,
    DockerImage,
    FileType,
)


class FileBase(abc.ABC):
    def dump(self) -> str:
        """
        improve this. I don't want to have to pass folders and filenames.
        At least it should be handled by some other class.
        """
        if self.filetype == FileType.yaml:
            dumped = yaml.dump(self.document, default_flow_style=False)
        elif self.filetype == FileType.json:
            dumped = json.dumps(self.document)
        return dumped

    def write(self, dumped: str):
        folder, filename = os.path.split(self.filepath)
        print(f"Writing file {self.filepath}")
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(self.filepath, "w") as f:
            f.write(dumped)

    @property
    @abc.abstractmethod
    def document(self):
        pass

    @property
    @abc.abstractmethod
    def filepath(self):
        pass

    @property
    @abc.abstractmethod
    def filetype(self):
        pass


class BuildspecTestFile(FileBase):
    # TODO implement this
    pass


class BuildspecDockerbuildFile(FileBase):
    """
    Class for creating a single buildspec file that
    - logs into AWS ECR
    - builds Docker image
    - pushes Docker image to ECR
    """

    filetype = FileType.yaml

    def __init__(self, image: DockerImage, buildspec_version: str = "0.2"):
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
            "version": buildspec_version,
            "phases": phases,
            "artifacts": imagedefinitions_filename,
        }
        self.image = image
        self._imagedefinitions = imagedefinitions
        self._phases = phases
        self._document = document

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"buildspec/{self.image.name}/buildspec-dockerbuild-{self.image.environment}.yml"


class ContainerDefinitionsFile(FileBase):

    filetype = FileType.json

    def __init__(self, deployment: ContainerDeployment):
        """
        Defines a task to be run in ecs in `region`.
        Logs are sent to `awslogs_group` in CloudWatch.
        """
        # TODO add support for custom Docker tags
        # TODO add support for multiple Docker images
        tasks = [
            {
                "name": deployment.image.name,
                "image": deployment.image.uri,
                # TODO add env vars dynamically?
                "environment": [
                    {
                        "name": "RUNTIME_ENVIRONMENT",
                        "value": deployment.image.environment,
                    }
                ],
                "essential": deployment.essential,
                "dockerLabels": {
                    "name": deployment.image.name,
                    "description": deployment.image.description,
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": deployment.awslogs_group,
                        "awslogs-region": deployment.project.region,
                        "awslogs-stream-prefix": "ecs",
                    },
                }
                ### Not sure if the below three lines are necessary
                # "entryPoint": None,
                # "command": None,
                # "cpu": 0,
            }
        ]
        self.deployment = deployment
        self._document = tasks

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"terraform/container_definitions/{self.deployment.image.name}_{self.deployment.image.environment}.json"


class DockerComposeFile(FileBase):
    """
    The compose files are just used in the buildspec. It's possible that
    I won't need this class in the future, but now I'm just modelling my
    current setup.
    """

    filetype = FileType.yaml

    def __init__(
        self,
        image: DockerImage,
        build_context: str = "containers/",  # TODO remove default value. Should be managed be abstraction.
        compose_version: str = "3.2",
    ):
        services = {
            "version": compose_version,
            "services": {
                image.name: {
                    "build": {"context": build_context, "dockerfile": image.filename},
                    "image": image.uri,
                    "environment": [f"RUNTIME_ENVIRONMENT={image.environment}"],
                }
            },
        }
        self.image = image
        self._document = services

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"docker-compose-{self.image.name}-{self.image.environment}.yml"


@dataclass
class TerraformScheduledTask:
    deployment: ContainerDeployment
    container_definitions_file: ContainerDefinitionsFile
    schedule_expression: str = "rate(1 hours)"

    task = Template(
        """
        module "scheduled_task" {
          # source  = "./modules/scheduled_task"
          source                = "github.com/halfdanrump/terraform_modules/aws/scheduled_task"
          version               = "1.2"
          account_id            = "{{ deployment.project.account_id }}"
          name                  = "{{ deployment.project.name }}"
          environment           = "{{ deployment.image.environment }}"
          log_group_name        = "{{ deployment.project.awslogs_group }}"
          network_mode          = "awsvpc"
          assign_public_ip      = true
          launch_type           = "FARGATE"
          container_definitions = "${file("{{ self.container_definitions_file.filename }}")}"
          schedule_expression   = "{{ schedule_expression }}"
          cluster_arn           = "{{ deployment.project.ecs_cluster_arn }}"
          memory                = "{{ deployment.memory }}"
          cpu                   = "{{ deployment.cpu }}"
          subnets               = {{ deployment.subnets }}
          security_groups       = {{ deployment.security_groups }}
        }
        """
    )

    cicd = Template(
        """
module "zendishes_production_cicd" {
  source = "github.com/halfdanrump/terraform_modules/aws/ci_dockerbuild"
  name   = ""
  account_id = "{{ project.account_id }}"
  environment = "production"
  github_webhook_token = "${var.github_webhook_token}"
  git_repo = "batch_scripts_docker"
  git_branch = "zendishes-master"
  unittest_buildspec_path = "buildspec/zendishes/buildspec-unittest-allenvs.yml"
  dockerbuild_timeout = "15"
  dockerbuild_buildspec_path = "buildspec/zendishes/buildspec-dockerbuild-production.yml"
}
        """
    )

    def render(self):
        # TODO in the case of multiple Docker images, iterate over images and
        # render template for each zendishes_image
        return self.task.render(deployment=self.deployment)


"""
module "scheduled_task" {
  # source  = "./modules/scheduled_task"
  source                = "github.com/halfdanrump/terraform_modules/aws/scheduled_task"
  version               = "1.2"
  account_id            = "211367837384"
  name                  = "zendishes"
  environment           = "production"
  log_group_name        = "/aws/ecs/vpc_central/zendishes/production"
  network_mode          = "awsvpc"
  assign_public_ip      = true
  launch_type           = "FARGATE"
  container_definitions = "${file("container_definitions/zendishes_production.json")}"
  # schedule_expression   = "cron(0/10 * * * ? 0)" # see https://crontab.guru/
  schedule_expression   = "rate(5 minutes)" # see https://crontab.guru/
  cluster_arn           = "${local.persistent_cluster_arn}"
  memory                = "512"
  cpu                   = "256"
  subnets               = ["${local.subnet_db_b}",
                           "${local.subnet_db_c}",
                           "${local.subnet_natgw}"]
  security_groups       = ["${local.security_group_db}",
                           "${local.security_group_nat}"]

}

module "zendishes_production_cicd" {
  source = "github.com/halfdanrump/terraform_modules/aws/ci_dockerbuild"
  name   = "zendishes"
  account_id = "211367837384"
  environment = "production"
  github_webhook_token = "${var.github_webhook_token}"
  git_repo = "batch_scripts_docker"
  git_branch = "zendishes-master"
  unittest_buildspec_path = "buildspec/zendishes/buildspec-unittest-allenvs.yml"
  dockerbuild_timeout = "15"
  dockerbuild_buildspec_path = "buildspec/zendishes/buildspec-dockerbuild-production.yml"
}

"""
