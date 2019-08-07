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
