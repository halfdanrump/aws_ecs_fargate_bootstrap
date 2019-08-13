from jinja2 import Template

dockerfile_template = Template(
    """
FROM python:{{ image.python_version }}

RUN apt-get update

RUN mkdir -p /workdir
WORKDIR /workdir

RUN mkdir -p data/

# upgrade pip and install python requirements
RUN pip install --upgrade pip
RUN pip install --upgrade pipenv

COPY {{ image.name }}/Pipfile /workdir/
COPY {{ image.name }}/Pipfile.lock /workdir/

RUN pipenv install --ignore-pipfile --deploy --system

RUN mkdir -p services/{{ image.name }}

# VOLUME /workdir/{{ volume_name }}

# copy app files
COPY {{ image.name }}/*.py services/{{ image.name }}/
COPY modules services/modules

LABEL maintainer = "Halfdan Rump <halfdan.rump@vuzz.com>"
LABEL org.label-schema.description = "{{ image.description }}"
LABEL org.label-schema.name = "{{ image.name }}"

#CMD python -c 'while True: pass'
#ENTRYPOINT ["python", "-m"]
CMD python -m services.{{ image.name }}.{{ image.script_name }}
"""
)

pipfile_template = Template(
    """
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
PyYAML = "==3.13"
sentry-sdk = "==0.7.14"
slack_logger = "==0.3.1"
progressbar2 = "==3.42.0"

[requires]
python_version = "{{ python_version }}"
"""
)

python_batch_script = Template(
    """
from sentry_sdk import capture_exception
from sentry_sdk import init as init_sentry

from ..modules.config import load_config
from ..modules.logger import Logger, LoggerName


def main():
    raise NotImplementedError("You must implement this.")

if __name__ == "__main__":
    config = load_config(folder_name={{ image.name }})
    init_sentry(config["sentry_dsn"])
    try:
        logger = Logger(config=config["logging"], default_loggers=[LoggerName.stdout])
        logger.info("running {{ image.name }} ")
        main()
        logger.info("done")
    except Exception as e:
        # send error to sentry
        capture_exception(e)

        # send error to slack
        logger.error(e, LoggerName.slack)
"""
)

makefile_template = Template(
    """
lock_dependencies:
{%- for task in tasks %}
{%- for deployment in task.container_deployments %}
\t\tcd containers/{{ deployment.image.name }} && pipenv install
{% endfor -%}
{% endfor -%}

build_docker:
{%- for task in tasks %}
\t\tdocker-compose -f docker-compose-{{ task.name }}-{{ task.environment }}.yml build
{% endfor -%}


tfinit:
\t\tcd terraform && terraform init

tfapply:
\t\tcd terraform && terraform apply
"""
)

scheduled_task_template = Template(
    """
variable "log_groups" {
  description = "Map from service name to log group name"
  default     = {
    {% for deployment in task.container_deployments -%}
    "{{ deployment.image.name }}" = "{{ deployment.awslogs_group }}"
    {% endfor -%}
  }
}



module "fargate-scheduled-task-multicontainer" {
    source  = "halfdanrump/fargate-scheduled-task-multicontainer/aws"
    version = "12.6.1"
    account_id            = "{{ project_config.account_id }}"
    name                  = "{{ task.name }}"
    environment           = "{{ task.environment }}"
    log_groups            = var.log_groups
    network_mode          = "awsvpc"
    assign_public_ip      = true
    launch_type           = "FARGATE"
    container_definitions = "${file("{{ container_definitions_filename }}")}"
    schedule_expression   = "{{ schedule_expression }}"
    cluster_arn           = "{{ project_config.ecs_cluster_arn }}"
    memory                = "{{ task.memory }}"
    cpu                   = "{{ task.cpu }}"
    subnets               = {{ subnets }}
    security_groups       = {{ security_groups }}
}

### aws codepipeline CICD

module "{{ task.name }}_production_cicd" {
  source = "github.com/halfdanrump/terraform_modules/aws/ci_dockerbuild"
  name   = "{{ task.name }}"
  account_id = "{{ project_config.account_id }}"
  environment = "{{ task.name }}"
  github_webhook_token = "${var.github_webhook_token}"
  git_repo = "{{ project_config.git_repo_name}}"
  git_branch = "{{ project_config.git_repo_branch }}"
  unittest_buildspec_path = "buildspec/buildspec-unittest-{{ task.name }}-allenvs.yml"
  dockerbuild_timeout = "15"
  dockerbuild_buildspec_path = "buildspec/buildspec-dockerbuild-{{ task.name }}-{{ task.environment }}.yml"
}

"""
)

cicd_template = Template(
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
