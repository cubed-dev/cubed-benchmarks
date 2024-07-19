# Cubed Benchmarks

Set of Cubed benchmarks to run at scale on various executors.

## Test Locally (for developers)

The `cubed benchmarks` test suite can be run locally with the following steps:

1. Create a conda environment using `mamba env create -n test-env -f ci/environment.yml`
2. Activate the environment with `conda activate test-env`
3. Add test packages with `mamba env update -f ci/environment-test.yml`
4. Run tests with `CUBED_CONFIG=tests/configs/local_single-threaded.yaml pytest`

## Benchmarking

The `cubed-benchmarks` test suite contains a series of pytest fixtures which enable
benchmarking metrics to be collected and stored for historical and regression analysis.
By default, these metrics are not collected and stored, but they can be enabled
by including the `--benchmark` flag in your pytest invocation.

From a high level, here is how the benchmarking works:

* Data from individual test runs are collected and stored in a local sqlite database.
  The schema for this database is stored in `benchmark_schema.py`
* The local sqlite databases are appended to a global historical record, stored in S3.
* The historical data can be analyzed using any of a number of tools.

### Running the benchmarks locally

You can collect benchmarking data by running pytest with the `--benchmark` flag.
This will create a local `benchmark.db` sqlite file in the root of the repository.
If you run a test suite multiple times with benchmarking,
the data will be appended to the database.

You can compare with historical data by downloading the global database from S3 first:

```shell
aws s3 cp s3://cubed-runtime-ci/benchmarks/benchmark.db ./benchmark.db
export CUBED_CONFIG=...
pytest --benchmark
```

### Running the benchmarks locally using the `processes` executor

The `processes` executor uses all the cores on the local machine to run. These
benchmarks can be run locally on a machine with multiple cores (they are not
run in CI since CI hosts typically don't have many cores).

```shell
export CUBED_CONFIG=tests/configs/local_processes.yaml
pytest --benchmark
```

### Inspecting the benchmarks database

There are many ways of doing this, but here is a simple one using DuckDB:

```
> duckdb benchmark.db
select name, call_outcome, start, duration, name_prefix from test_run;
```


## Acknowledgements

This repository is heavily inspired by [`Coiled Benchmarks`](https://github.com/coiled/benchmarks/), with many sections of code being lifted directly.

## License

[Apache-2.0](LICENSE)
