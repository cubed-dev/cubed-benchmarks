from functools import partial
import random

import fsspec
import pytest
import xarray as xr

import cubed
import cubed.random
from cubed.core.optimization import multiple_inputs_optimize_dag, simple_optimize_dag
from cubed.extensions.rich import RichProgressBar
from cubed.runtime.executors.python import PythonDagExecutor 
from cubed.runtime.executors.python_async import AsyncPythonDagExecutor

from ..utils import run


@pytest.mark.parametrize(
    "t_length, optimizer, compute_arrays_in_parallel",
    [
        # (50, "old-optimizer", False),
        # (50, "new-optimizer", True),
        # (500, "old-optimizer", False),
        # (500, "new-optimizer", True),
        # (5000, "old-optimizer", False),
        # (5000, "new-optimizer", True),
        (50000, "old-optimizer", False),
        (50000, "new-optimizer", False),
        (50000, "new-optimizer", True),
    ],
)
def test_quadratic_means_xarray(tmp_path, runtime, benchmark_all, t_length, optimizer, compute_arrays_in_parallel):
    spec = runtime

    if isinstance(spec.executor, (PythonDagExecutor, AsyncPythonDagExecutor)) and t_length > 50:
        pytest.skip(f"Don't run large computation on {type(spec.executor)}")

    # set the random seed to ensure deterministic results
    random.seed(42)

    # create zarr test data (not timed)
    u = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    v = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    arrays = [u, v]
    paths = [f"{spec.work_dir}/u_{t_length}.zarr", f"{spec.work_dir}/v_{t_length}.zarr"]
    cubed.store(arrays, paths, compute_arrays_in_parallel=True, callbacks=[RichProgressBar()])

    # lazily define computation
    u = cubed.from_zarr(paths[0], spec=spec)
    v = cubed.from_zarr(paths[1], spec=spec)
    ds = xr.Dataset(
        dict(
            anom_u=(["time", "face", "j", "i"], u),
            anom_v=(["time", "face", "j", "i"], v),
        )
    )
    quad = ds**2
    quad["uv"] = ds.anom_u * ds.anom_v
    print(quad)
    result = quad.mean(
        "time", skipna=False, use_new_impl=True, split_every=10
    )

    if optimizer == "new-optimizer":
        opt_fn = partial(multiple_inputs_optimize_dag, max_total_num_input_blocks=20)
    else:
        opt_fn = simple_optimize_dag


    cubed.visualize(
        *(result[var].data for var in ("anom_u", "anom_v", "uv")),
        filename=tmp_path / f"quadratic_means_xarray_{t_length}-unoptimized",
        optimize_graph=False,
        show_hidden=True,
    )
    cubed.visualize(
        *(result[var].data for var in ("anom_u", "anom_v", "uv")),
        filename=tmp_path / f"quadratic_means_xarray_{t_length}",
        optimize_function=opt_fn,
        show_hidden=True,
    )

    # time only the computing of the result
    computed_result = run(
        result,
        executor=spec.executor,
        benchmarks=benchmark_all,
        optimize_function=opt_fn,
        compute_arrays_in_parallel=compute_arrays_in_parallel,
        callbacks=[RichProgressBar()],
    )

    # TODO check result is correct here
    assert computed_result is not None

    # delete zarr test data (not timed)
    for path in paths:
        try:
            fs, _, _ = fsspec.get_fs_token_paths(path)
            fs.rm(path, recursive=True)
        except FileNotFoundError:
            pass
