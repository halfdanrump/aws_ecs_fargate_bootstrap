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

COPY {{ container_name }}/Pipfile /workdir/
COPY {{ container_name }}/Pipfile.lock /workdir/

RUN pipenv install --ignore-pipfile --deploy --system

RUN mkdir -p services/{{ image.name }}

# VOLUME /workdir/{{ volume_name }}

# copy app files
COPY {{ image.name }}/annoy_async.py services/{{ image.name }}/
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

[requires]
python_version = "{{ python_version }}"
"""
)

scheduled_task_template = Template(
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
