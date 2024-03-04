import cubed
import cubed.random
import cubed.array_api as xp


from ..utils import run


def test_quad_means(runtime, benchmark_all):
    # from cubed.tests.test_core.test_plan_quad_means

    spec = runtime

    # TODO parametrize the scale through this parameter?
    t_length = 50

    # TODO write initial data out to bucket first to read from later
    u = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    v = cubed.random.random((t_length, 1, 987, 1920), chunks=(10, 1, -1, -1), spec=spec)
    
    # lazily define computation
    uv = u * v
    result = xp.mean(uv, axis=0, split_every=10, use_new_impl=True)

    # time only the computing of the result
    computed_result = run(result, executor=spec.executor, benchmarks=benchmark_all)

    # TODO check result is correct here
