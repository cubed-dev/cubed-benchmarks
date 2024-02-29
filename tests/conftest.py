import os
import yaml

import pytest

import cubed

from .utils import spec_from_config_file

from typing import Iterator


RUNTIME_CONFIGS = [
    'configs/local_single-threaded.yaml'
    #'configs/lithops_gcf.yaml'
    #'configs/lithops_aws.yaml'
    #'configs/lithops_aws_1Z.yaml'
    #'configs/coiled_aws.yaml'
]


@pytest.fixture(params=RUNTIME_CONFIGS)
def runtime(request) -> Iterator[cubed.Spec]:
    """
    Yields a cubed.Spec for each .yaml file in the /configs/ directory, 
    so any test parametrized with this fixture will run for all executors.
    """
    config_filepath = request.param
    yield spec_from_config_file(config_filepath)
