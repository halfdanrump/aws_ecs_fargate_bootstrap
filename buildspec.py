import json
import yaml
import os


class BuildspecFile:
    """
    Class for creating a single buildspec file
    """

    def __init__(self, name: str, environment: str = "production"):
        docker_compose_filename = f"docker-compose-{name}-{environment}-fargate.yml"
        imagedefinitions_filename = f"imagedefinitions_{name}-{environment}.json"
        imagedefinitions = [
            {
                "name": f"{name}",
                "imageUri": f"211367837384.dkr.ecr.ap-northeast-1.amazonaws.com/{name}_{environment}:latest",
            }
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
            "version": 0.2,
            "phases": phases,
            "artifacts": imagedefinitions_filename,
        }
        self.docker_compose_filename = docker_compose_filename
        self.imagedefinitions = imagedefinitions
        self.phases = phases
        self.document = document

    def render(self, folder: str, filename: str):
        filepath = os.path.join(folder, filename)
        with open(filepath, "rw") as f:
            f.write(yaml.dump(self.document))
