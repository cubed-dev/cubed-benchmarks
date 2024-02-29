import contextlib
import time
import datetime
import os

import pytest
import sqlalchemy
import filelock
import subprocess

import cubed


def run_benchmark(
        result, 
        executor, 
    ):

    # TODO: cubed.compute won't yet work on an xarray object (like dask.compute does)
    cubed.compute(
        result, 
        executor=executor,
    )


RUNTIME_CONFIGS = [
    'local_single-threaded.yaml'
    #'lithops_gcf.yaml'
    #'lithops_aws.yaml'
    #'lithops_aws_1Z.yaml'
    #'coiled.yaml'
]


@pytest.fixture(params=RUNTIME_CONFIGS)
def runtime(config: str):
    spec = cubed.spec.spec_from_config(config)

    executor_name = ...
    executor = cubed.runtime.create.create_executor(executor_name)

    yield spec, executor
