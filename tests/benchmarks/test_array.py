from functools import partial
import random

import fsspec
import pytest
import xarray as xr

import cubed
import cubed as xp
import cubed.random
from cubed.core.optimization import multiple_inputs_optimize_dag, simple_optimize_dag
from cubed.diagnostics.rich import RichProgressBar

from ..utils import run

def test_measure_reserved_mem(runtime):
    spec = runtime

    if spec.executor.name in ("single-threaded", "threads"):
        pytest.skip(f"Don't measure reserved memory on {spec.executor.name}")

    reserved_memory = cubed.measure_reserved_mem(executor=spec.executor, work_dir=spec.work_dir)
    print("reserved memory", reserved_memory)


@pytest.mark.parametrize("optimizer", ["new-optimizer"])
@pytest.mark.parametrize("t_length", [50, 500, 5000])
def test_quadratic_means_xarray(tmp_path, runtime, benchmark_all, optimizer, t_length):
    spec = runtime

    if spec.executor.name in ("single-threaded", "threads") and t_length > 50:
        pytest.skip(f"Don't run large computation on {spec.executor.name}")

    # set the random seed to ensure deterministic results
    random.seed(42)

    # create zarr test data (not timed)
    u = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    v = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    arrays = [u, v]
    paths = [f"{spec.work_dir}/u_{t_length}.zarr", f"{spec.work_dir}/v_{t_length}.zarr"]
    cubed.store(arrays, paths, compute_arrays_in_parallel=True, callbacks=[RichProgressBar()])

    # lazily define computation
    ds = xr.Dataset(
        dict(
            anom_u=(
                ["time", "face", "j", "i"],
                cubed.from_zarr(paths[0], spec=spec),
            ),
            anom_v=(
                ["time", "face", "j", "i"],
                cubed.from_zarr(paths[1], spec=spec),
            ),
        )
    )
    quad = ds**2
    quad["uv"] = ds.anom_u * ds.anom_v
    print(quad)
    result = quad.mean("time", skipna=False, split_every=10)

    if optimizer == "new-optimizer":
        opt_fn = partial(multiple_inputs_optimize_dag, max_total_num_input_blocks=20)
        compute_arrays_in_parallel = True
    else:
        opt_fn = simple_optimize_dag
        compute_arrays_in_parallel = False


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


@pytest.mark.skip(reason="Skipping due to large computation")
def test_rechunk_era5(tmp_path, runtime, benchmark_all):
    spec = runtime

    if spec.executor.name in ("single-threaded", "threads"):
        pytest.skip(f"Don't run large computation on {spec.executor.name}")

    # from https://github.com/pangeo-data/rechunker/pull/89
    shape = (350640, 721, 1440)
    source_chunks = (31, 721, 1440)
    target_chunks = (350640, 10, 10)

    # set the random seed to ensure deterministic results
    random.seed(42)

    # create zarr test data (not timed)
    a = cubed.random.random(shape, dtype=xp.float32, chunks=source_chunks, spec=spec)
    path = f"{spec.work_dir}/a.zarr"
    cubed.store([a], [path], compute_arrays_in_parallel=True, callbacks=[RichProgressBar()])

    a = cubed.from_zarr(path, spec=spec)
    result = a.rechunk(chunks=target_chunks, use_new_impl=True)

    result.visualize(filename=tmp_path / f"rechunk_era5")

    try:
        # time only the computing of the result
        run(
            result,
            executor=spec.executor,
            benchmarks=benchmark_all,
            callbacks=[RichProgressBar()],
            _return_in_memory_array=False,  # don't load result into memory!
        )
    finally:
        # delete zarr intermediate data (not timed)
        try:
            work_dir = spec.work_dir
            fs, _, _ = fsspec.get_fs_token_paths(work_dir)
            fs.rm(work_dir, recursive=True)
        except FileNotFoundError:
            pass
