import os
import yaml

import cubed
from cubed.extensions.history import HistoryCallback
from cubed.spec import spec_from_config
from cubed import config


def spec_from_config_file(filepath: str) -> cubed.Spec:
    # from https://donfig.readthedocs.io/en/latest/configuration.html#downstream-libraries
    # TODO shouldn't there be a way to do this in cubed? i.e. a classmethod on the Spec object?

    fn = os.path.join(os.path.dirname(__file__), filepath)

    with open(fn) as f:
        defaults = yaml.safe_load(f)

    config.update_defaults(defaults)

    return spec_from_config(config)


def get_directory_size(work_dir: str) -> float:
    """Get the size of any data written to the given directory (local or remote)."""

    import fsspec

    total_size = 0

    if work_dir.startswith('s3://'):
        fs = fsspec.filesystem('s3')
    else:
        fs = fsspec.filesystem('file')

    # List all files and subdirectories in the directory
    contents = fs.glob(f'{work_dir}/**', detail=True)

    for item in contents:
        if item['type'] == 'file':
            # If it's a file, add its size to the total
            total_size += item['size']

    return total_size


def run(
        result, 
        executor,
        spec,
        benchmarks,
        **kwargs
    ):

    # add the history callback to any other callback already passed
    history = HistoryCallback()
    callbacks = kwargs.get('callbacks', [])
    callbacks.append(history)
    kwargs['callbacks'] = callbacks

    with benchmarks(history, spec.work_dir):

        computed_result = result.compute(
            executor=executor,
            **kwargs,
        )

    # TODO clean up by deleting intermediate data here?

    return computed_result
