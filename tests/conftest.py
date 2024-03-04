import contextlib
import time
import datetime
import os
import pathlib
import sys

from typing import Iterator

import pytest
import sqlalchemy
from sqlalchemy.orm import Session
import filelock
import subprocess

import cubed
import xarray
import cubed_xarray
import lithops

from .utils import spec_from_config_file

from benchmark_schema import TestRun


RUNTIME_CONFIGS = [
    'configs/local_single-threaded.yaml',
    #'configs/local_async.yaml',
    #'configs/lithops_gcf.yaml',
    #'configs/lithops_aws.yaml',
    #'configs/lithops_aws_1Z.yaml',
    #'configs/coiled_aws.yaml',
]


TEST_DIR = pathlib.Path("./tests").absolute()


def pytest_addoption(parser):
    parser.addoption(
        "--benchmark", action="store_true", help="Collect benchmarking data for tests"
    )


# ############################################### #
#            BENCHMARKING RELATED                 #
# ############################################### #

DB_NAME = os.environ.get("DB_NAME", "benchmark.db")


if os.environ.get("GITHUB_SERVER_URL"):
    WORKFLOW_URL = "/".join(
        [
            os.environ.get("GITHUB_SERVER_URL", ""),
            os.environ.get("GITHUB_REPOSITORY", ""),
            "actions",
            "runs",
            os.environ.get("GITHUB_RUN_ID", ""),
        ]
    )
else:
    WORKFLOW_URL = None


@pytest.fixture(scope="session")
def benchmark_db_engine(pytestconfig, tmp_path_factory):
    """Session-scoped fixture for the SQLAlchemy engine for the benchmark sqlite database.

    You can control the database name with the environment variable ``DB_NAME``,
    which defaults to ``benchmark.db``. Most tests shouldn't need to include this
    fixture directly.

    Yields
    ------
    The SQLAlchemy engine if the ``--benchmark`` option is set, None otherwise.
    """

    if not pytestconfig.getoption("--benchmark"):
        yield
    else:
        engine = sqlalchemy.create_engine(f"sqlite:///{DB_NAME}")

        # get the temp directory shared by all workers
        root_tmp_dir = tmp_path_factory.getbasetemp().parent
        lock = root_tmp_dir / (DB_NAME + ".lock")

        # Create the db if it does not exist already.
        with filelock.FileLock(lock):
            if not os.path.exists(DB_NAME):
                with engine.connect() as conn:
                    conn.execute(sqlalchemy.text("VACUUM"))

        # TODO use alembic for database migration like Coiled Benchmarks does

        yield engine


@pytest.fixture(scope="function")
def benchmark_db_session(benchmark_db_engine):
    """SQLAlchemy session for a given test.

    Most tests shouldn't need to include this fixture directly.

    Yields
    ------
    SQLAlchemy session for the benchmark database engine if run as part of a benchmark,
    None otherwise.
    """
    if not benchmark_db_engine:
        yield
    else:
        with Session(benchmark_db_engine, future=True) as session, session.begin():
            
            # This will create the test_run table if it doesn't exist
            TestRun.__table__.create(bind=benchmark_db_engine, checkfirst=True)
            
            yield session


@pytest.fixture(scope="function")
def test_run_benchmark(benchmark_db_session, request, testrun_uid):
    """SQLAlchemy ORM object representing a given test run.

    By including this fixture in a test (or another fixture that includes it)
    you trigger the test being written to the benchmark database. This fixture
    includes data common to all tests, including python version, test name,
    and the test outcome.

    Yields
    ------
    SQLAlchemy ORM object representing a given test run if run as part of a benchmark,
    None otherwise.
    """
    if not benchmark_db_session:
        yield
    else:
        run = TestRun(
            session_id=testrun_uid,
            name=request.node.name,
            originalname=request.node.originalname,
            path=str(request.node.path.relative_to(TEST_DIR)),
            cubed_version=cubed.__version__,
            cubed_xarray_version=cubed_xarray.__version__,
            xarray_version=xarray.__version__,
            lithops_version=lithops.__version__, 
            python_version=".".join(map(str, sys.version_info)),
            platform=sys.platform,
            ci_run_url=WORKFLOW_URL,
        )
        yield run

        rep = getattr(request.node, "rep_setup", None)
        if rep:
            run.setup_outcome = rep.outcome
        rep = getattr(request.node, "rep_call", None)
        if rep:
            run.call_outcome = rep.outcome
        rep = getattr(request.node, "rep_teardown", None)
        if rep:
            run.teardown_outcome = rep.outcome

        benchmark_db_session.add(run)
        benchmark_db_session.commit()


@pytest.fixture(scope="function")
def benchmark_time(test_run_benchmark):
    """
    Benchmark the wall clock time of executing some code.

    Yields
    ------
    Context manager that records the wall clock time duration of executing
    the ``with`` statement if run as part of a benchmark, or does nothing otherwise.

    Example
    -------
    .. code-block:: python

        def test_something(benchmark_time):
            with benchmark_time:
                do_something()
    """

    @contextlib.contextmanager
    def _benchmark_time():
        if not test_run_benchmark:
            yield
        else:
            start = time.time()
            yield
            end = time.time()
            test_run_benchmark.duration = end - start
            test_run_benchmark.start = datetime.datetime.utcfromtimestamp(start)
            test_run_benchmark.end = datetime.datetime.utcfromtimestamp(end)

    return _benchmark_time()


@pytest.fixture(scope="function")
def benchmark_memory(test_run_benchmark):
    """Benchmark the memory usage of executing some code.

    Yields
    ------
    Context manager factory function which takes an instantiated cubed HistoryCallback object
    as input. The context manager records peak and average memory usage of
    executing the ``with`` statement if run as part of a benchmark,
    or does nothing otherwise.

    Example
    -------
    .. code-block:: python

        def test_something(benchmark_memory):
            history = cubed.extensions.history.HistoryCallback()
            with benchmark_memory(history):
                cubed.compute(*arrs, callbacks=[history])
    """

    @contextlib.contextmanager
    def _benchmark_memory(history):
        if not test_run_benchmark:
            yield
        else:
            yield

            import pandas as pd

            # read off the memory values and write them into the database
            plan_df = pd.DataFrame(history.plan)
            events_df = pd.DataFrame(history.events)

            plan_df["projected_mem_mb"] = plan_df["projected_mem"] / 1_000_000
            events_df["peak_measured_mem_end_mb"] = (
                events_df["peak_measured_mem_end"] / 1_000_000
            )

            test_run_benchmark.projected_memory = float(plan_df["projected_mem_mb"].max())
            test_run_benchmark.peak_memory = float(events_df["peak_measured_mem_end_mb"].max())
            test_run_benchmark.average_memory = float(events_df["peak_measured_mem_end_mb"].mean())
            
    yield _benchmark_memory



@pytest.fixture(scope="function")
def benchmark_tasks(test_run_benchmark):
    """Benchmark the number and cumulative duration of tasks run.

    Yields
    ------
    Context manager factory function which takes an instantiated cubed HistoryCallback object
    as input. The context manager records number and cumulative duration of
    tasks run while executing the ``with`` statement if run as part of a benchmark,
    or does nothing otherwise.

    Example
    -------
    .. code-block:: python

        def test_something(benchmark_memory):
            history = cubed.extensions.history.HistoryCallback()
            with benchmark_tasks(history):
                cubed.compute(*arrs, callbacks=[history])
    """

    @contextlib.contextmanager
    def _benchmark_tasks(history):
        if not test_run_benchmark:
            yield
        else:
            yield

            import pandas as pd

            # read off the memory values and write them into the database
            plan_df = pd.DataFrame(history.plan)
            events_df = pd.DataFrame(history.events)

            test_run_benchmark.number_of_tasks_run = int(plan_df["num_tasks"].sum())
            
            function_durations = events_df['function_end_tstamp'] - events_df['function_start_tstamp']
            test_run_benchmark.container_seconds = float(function_durations.sum())

    yield _benchmark_tasks


@pytest.fixture(scope="function")
def benchmark_all(
    benchmark_memory,
    benchmark_tasks,
    benchmark_time,
):
    """Benchmark all available metrics

    Yields
    ------
    Context manager factory function which takes an instantiated cubed HistoryCallback object
    as input. The context manager records peak and average memory usage, overall duration, 
    number and cumulative duration of tasks run when executing the ``with`` statement if run as part of a benchmark,
    or does nothing otherwise.

    Example
    -------
    .. code-block:: python

        def test_something(benchmark_all):
            history = cubed.extensions.history.HistoryCallback()
            with benchmark_all(history):
                cubed.compute(*arrs, callbacks=[history])
    
    See Also
    --------
    benchmark_memory
    benchmark_tasks
    benchmark_time
    """

    @contextlib.contextmanager
    def _benchmark_all(history):
        with (
            benchmark_memory(history),
            benchmark_tasks(history),
            benchmark_time,
        ):
            yield

    yield _benchmark_all


@pytest.fixture(params=RUNTIME_CONFIGS)
def runtime(request) -> Iterator[cubed.Spec]:
    """
    Yields a cubed.Spec for each .yaml file in the /configs/ directory, 
    so any test parametrized with this fixture will run for all executors.
    """
    config_filepath = request.param
    yield spec_from_config_file(config_filepath)
