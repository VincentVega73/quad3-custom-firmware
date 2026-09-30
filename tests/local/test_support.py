"""Shared guards and environment information for local firmware execution tests."""

from pathlib import Path
import platform


def protect_inputs(output: Path, *inputs: Path) -> None:
    """A JSON report must never replace either input or an alias of it."""
    for source in inputs:
        if output.resolve() == source.resolve():
            raise ValueError('Report path must differ from each input image')
        if output.exists() and source.exists() and output.samefile(source):
            raise ValueError('Report path aliases an input image')


def runtime_versions() -> dict[str, str]:
    import capstone
    import keystone
    import unicorn

    return {
        'python': platform.python_version(),
        'capstone_binding': capstone.__version__,
        'keystone_binding': keystone.__version__,
        'unicorn_binding': unicorn.__version__,
    }
