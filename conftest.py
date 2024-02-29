import os
import yaml

import pytest

import cubed
from cubed import config
from cubed.spec import spec_from_config

from typing import Iterator


RUNTIME_CONFIGS = [
    'configs/local_single-threaded.yaml'
    #'configs/lithops_gcf.yaml'
    #'configs/lithops_aws.yaml'
    #'configs/lithops_aws_1Z.yaml'
    #'configs/coiled_aws.yaml'
]


def run_benchmark(
        result, 
        executor, 
    ):

    # TODO: cubed.compute won't yet work on an xarray object (like dask.compute does) because xarray has magic dask dunder methods
    cubed.compute(
        result, 
        executor=executor,
    )


def spec_from_config_file(filepath: str) -> cubed.Spec:
    # from https://donfig.readthedocs.io/en/latest/configuration.html#downstream-libraries
    # TODO shouldn't there be a way to do this in cubed? i.e. a classmethod on the Spec object?

    fn = os.path.join(os.path.dirname(__file__), filepath)

    with open(fn) as f:
        defaults = yaml.safe_load(f)

    config.update_defaults(defaults)

    return spec_from_config(config)


@pytest.fixture(params=RUNTIME_CONFIGS)
def runtime(request) -> Iterator[cubed.Spec]:
    """
    Yields a cubed.Spec for each .yaml file in the /configs/ directory, 
    so any test parametrized with this fixture will run for all executors.
    """
    config_filepath = request.param
    yield spec_from_config_file(config_filepath)
