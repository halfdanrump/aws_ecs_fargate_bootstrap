import os
from os import environ
from pprint import pprint

import yaml

RUNTIME_ENVIRONMENT = environ.get("RUNTIME_ENVIRONMENT")
assert RUNTIME_ENVIRONMENT, "RUNTIME_ENVIRONMENT must be set!"
print("*" * 100)
print("RUNTIME ENVIRONMENT")
print(RUNTIME_ENVIRONMENT)
print("*" * 100)

# Make sure that RUNTIME_ENVIRONMENT has a valid value
assert RUNTIME_ENVIRONMENT in ["localhost", "docker_localhost", "staging", "production"]


def load_config(folder_name: str) -> None:
    """
    Inits the config read from the config.yml file in the folder specified by `folder_name`
    """
    # path = path.join(path.dirname(__file__), "config.yml")
    # config_path = path.join("../", "zendishes", "config.yml")

    config_path = os.path.join(
        "/".join(os.path.abspath(__file__).split("/")[:-2]),  # pretty nasty
        folder_name,
        "config.yml",
    )

    with open(config_path) as f:
        all_config = yaml.load(f)
        shared_config = all_config["shared"]
        config = all_config[RUNTIME_ENVIRONMENT]

        # make it possible to retrieve env name through config dict
        config["env_name"] = RUNTIME_ENVIRONMENT

        # update keys that also have values in shared config
        for key, value in shared_config.items():
            if key in config:
                config[key].update(value)
            else:
                config[key] = value

        # set release: conglomerate of version + environment
        # release is used by sentry
        config.update({"release": f"{config['version']}-{RUNTIME_ENVIRONMENT}"})
    pprint(config)
    return config
