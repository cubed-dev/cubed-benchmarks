import cubed
import cubed.random
import cubed.array_api as xp


from ..utils_test import run_benchmark


def test_quad_means(runtime):
    # from cubed.tests.test_core.test_plan_quad_means

    spec, executor = runtime

    # TODO parametrize the scale through this parameter?
    t_length = 50

    # write initial data out first to read from later
    u_initial = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    v_initial = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    u_initial.to_zarr(spec.work_dir)
    v_initial.to_zarr(spec.work_dir)

    # lazily set up loading and computation
    u = cubed.from_zarr(spec.work_dir, path='u')
    v = cubed.from_zarr(spec.work_dir, path='v')
    uv = u * v
    result = xp.mean(uv, axis=0, split_every=10, use_new_impl=True)

    # time only the computing of the result
    run_benchmark(result, executor)
