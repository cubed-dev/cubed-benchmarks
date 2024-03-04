import os
import yaml

import cubed
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


def run(
        result, 
        executor,
        benchmarks,
        **kwargs
    ):

    with benchmarks:

        computed_result = result.compute(
            executor=executor,
            **kwargs
        )

    # TODO clean up by deleting intermediate data here?
        
    return computed_result
