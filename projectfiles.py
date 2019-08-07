import abc
import json
import yaml
import os
from dataclasses import dataclass

from jinja2 import Template

from projectdata import (
    EcsTask,
    ProjectConfig,
    ContainerDeployment,
    DockerImage,
    FileType,
)

from templates import dockerfile_template, scheduled_task_template, cicd_template


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
        elif self.filetype == FileType.dockerfile:
            return self.document
        else:
            raise NotImplementedError()
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

    def __init__(self, task: EcsTask, buildspec_version: str = "0.2"):
        """
        Args:
            name: name of the project
            environment: deployment environment, typically `production` or `staging`
        """
        name, environment = task.name, task.environment

        docker_compose_filename = f"docker-compose-{name}-{environment}-fargate.yml"
        imagedefinitions_filename = f"imagedefinitions_{name}-{environment}.json"
        imagedefinitions = [
            {"name": f"{name}", "imageUri": deployment.image.uri}
            for deployment in task.container_deployments
        ]

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
        self.task = task
        self._imagedefinitions = imagedefinitions
        self._phases = phases
        self._document = document

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"buildspec/buildspec-dockerbuild-{self.task.name}-{self.task.environment}.yml"


class ContainerDefinitionsFile(FileBase):

    filetype = FileType.json

    def __init__(self, task: EcsTask):
        """
        Defines a task to be run in ecs in `region`.
        Logs are sent to `awslogs_group` in CloudWatch.
        """
        # TODO add support for custom Docker tags
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
                        "awslogs-region": task.region,
                        "awslogs-stream-prefix": "ecs",
                    },
                }
                ### Not sure if the below three lines are necessary
                # "entryPoint": None,
                # "command": None,
                # "cpu": 0,
            }
            for deployment in task.container_deployments
        ]
        self.task = task
        self._document = tasks

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"terraform/container_definitions/container_definitions-{self.task.name}-{self.task.environment}.json"


class DockerComposeFile(FileBase):
    """
    The compose files are just used in the buildspec. It's possible that
    I won't need this class in the future, but now I'm just modelling my
    current setup.
    """

    filetype = FileType.yaml

    def __init__(
        self,
        task: EcsTask,
        build_context: str = "containers/",  # TODO remove default value. Should be managed be abstraction.
        compose_version: str = "3.2",
    ):
        services = {
            "version": compose_version,
            "services": {
                deployment.image.name: {
                    "build": {
                        "context": build_context,
                        "dockerfile": deployment.image.filename,
                    },
                    "image": deployment.image.uri,
                    "environment": [
                        f"RUNTIME_ENVIRONMENT={deployment.image.environment}"
                    ],
                }
                for deployment in task.container_deployments
            },
        }
        self.task = task
        self._document = services

    @property
    def document(self):
        return self._document

    @property
    def filepath(self):
        return f"docker-compose-{self.task.name}-{self.task.environment}.yml"


@dataclass
class DockerFile(FileBase):
    image: DockerImage
    script_name: str = "main"
    python_version: str = "3.7.4"

    filetype = FileType.dockerfile
    dockerfile = dockerfile_template

    @property
    def document(self):
        return self.dockerfile.render(image=self.image)

    @property
    def filepath(self):
        return f"containers/Dockerfile-{self.image.name}"


@dataclass
class TerraformScheduledTask:
    deployment: ContainerDeployment
    container_definitions_file: ContainerDefinitionsFile
    schedule_expression: str = "rate(1 hours)"

    task = scheduled_task_template

    cicd = cicd_template

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
