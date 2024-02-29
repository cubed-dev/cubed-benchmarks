import cubed


def run_benchmark(
        result, 
        executor, 
    ):

    # TODO: cubed.compute won't yet work on an xarray object (like dask.compute does) because xarray has magic dask dunder methods
    cubed.compute(
        result, 
        executor=executor,
    )

    # TODO clean up by deleting intermediate data here?
