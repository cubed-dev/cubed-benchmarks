# Cubed Benchmarks

Set of Cubed benchmarks to run at scale on various executors.

## Test Locally (for developers)

The `cubed benchmarks` test suite can be run locally with the following steps:

1. Create a conda environment using `ci/environment.yml`
2. Run tests with `python -m pytest tests`.

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

```bash
aws s3 cp s3://cubed-runtime-ci/benchmarks/benchmark.db ./benchmark.db
pytest --benchmark
```

## Acknowledgements

This repository is heavily inspired by [`Coiled Benchmarks`](https://github.com/coiled/benchmarks/), with many sections of code being lifted directly.

## License

[Apache-2.0](LICENSE)
