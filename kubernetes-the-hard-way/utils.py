import logging
import os
import subprocess
from logging.config import dictConfig
from pathlib import Path
from contextlib import contextmanager

GCLOUD = "gcloud"

TEMPLATE_DIR = Path(__file__).parent / "templates"


@contextmanager
def template_dir():
    curr_dir = os.getcwd()
    yield os.chdir(TEMPLATE_DIR)
    os.chdir(curr_dir)


def run_command(command, log=True):
    if log:
        logging.info(f"Command to run: '{command}'")
    ps = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    return ps.communicate()[0].decode("utf8").splitlines()


def configure_logger():
    logging_config = dict(
        version=1,
        formatters={"f": {"format": "%(asctime)s %(name)-4s [%(levelname)s] %(message)s"}},
        handlers={
            "h": {"class": "logging.StreamHandler", "formatter": "f", "level": logging.DEBUG}
        },
        root={"handlers": ["h"], "level": logging.DEBUG},
    )

    dictConfig(logging_config)
