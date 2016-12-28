# NOTE WELL: No side-effects are allowed in __init__ files. This means you!
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from re import compile as Regex
from re import MULTILINE

from py._path.local import LocalPath as Path

TOP = Path(__file__) / '../../..'
COVERAGE_REQS = TOP.join('requirements.d/coverage.txt')


def requirements(reqs, path='requirements.txt'):
    """Write a requirements.txt file to the current working directory."""
    Path(path).write(reqs)


def run(*cmd, **env):
    if env:
        from os import environ
        tmp = env
        env = environ.copy()
        env.update(tmp)
    else:
        env = None

    from .capture_subprocess import capture_subprocess
    from venv_update import info, colorize
    info('\nTEST> ' + colorize(cmd))
    out, err = capture_subprocess(cmd, env=env)
    err = strip_coverage_warnings(err)
    return out, err


def venv_update(*args, **env):
    # we get coverage for free via the (patched) pytest-cov plugin
    return run(
        'venv-update',
        *args,
        **env
    )


def venv_update_symlink_pwd():
    # I wish I didn't need this =/
    # surely there's a better way -.-
    # NOTE: `pip install TOP` causes an infinite copyfiles loop, under tox >.<
    from venv_update import __file__ as venv_update_path, dotpy

    # symlink so that we get coverage, where possible
    venv_update_path = Path(dotpy(venv_update_path))
    local_vu = Path(venv_update_path.basename)
    local_vu.mksymlinkto(venv_update_path)


# coverage.py adds some helpful warnings to stderr, with no way to quiet them.
coverage_warnings_regex = Regex(
    r'^Coverage.py warning: (%s)\n' % '|'.join((
        r'Module .* was never imported\.',
        r'No data was collected\.',
        r'Module venv_update was previously imported, but not measured\.',
    )),
    flags=MULTILINE,
)


def strip_coverage_warnings(stderr):
    return coverage_warnings_regex.sub('', stderr)


# pip adds some helpful warnings to stderr, with no way to quiet them.
pip_warnings_regex = Regex(
    '|'.join((
        (
            r'^DEPRECATION: Python 2\.6 is no longer supported by the Python core team, please upgrade your Python\. '
            r'A future version of pip will drop support for Python 2\.6\n'
        ),
        r"^  Url '[^']*/\.cache/pip-faster/wheelhouse' is ignored: it is neither a file nor a directory\.\n",
        r'^You are using pip version [0-9.]+, however version [0-9.]+ is available\.\n',
        r"^You should consider upgrading via the 'pip install --upgrade pip' command\.\n",
    )),
    flags=MULTILINE,
)


def strip_pip_warnings(stderr):
    return pip_warnings_regex.sub('', stderr)


def uncolor(text):
    # the colored_tty, uncolored_pipe tests cover this pretty well.
    from re import sub
    text = sub('\033\\[[^A-z]*[A-z]', '', text)
    return sub('[^\n\r]*\r', '', text)


def pip_freeze(venv='venv'):
    from os.path import join
    out, err = run(join(venv, 'bin', 'pip'), 'freeze', '--local')

    # Most python distributions which have argparse in the stdlib fail to
    # expose it to setuptools as an installed package (it seems all but ubuntu
    # do this). This results in argparse sometimes being installed locally,
    # sometimes not, even for a specific version of python.
    # We normalize by never looking at argparse =/
    import re
    out = re.sub(r'argparse==[\d.]+\n', '', out, count=1)

    # We don't pin the coverage package.
    out = re.sub(r'coverage==[\d.]+\n', 'coverage==X.Y\n', out, count=1)

    err = strip_pip_warnings(err)
    assert err == ''
    return out


def install_coverage(venv='venv'):
    venv = Path(venv)
    if not venv.exists():
        run('virtualenv', str(venv))
    run(str(venv.join('bin/python')), '-m', 'pip.__main__', 'install', '-r', str(COVERAGE_REQS))


def enable_coverage():
    from venv_update import Scratch
    install_coverage(Scratch().venv)


class OtherPython(object):
    """represents a python interpreter that doesn't match the "current" interpreter's version"""

    def __init__(self):
        import sys
        if sys.version_info[0] <= 2:
            self.interpreter = 'python3.4'
            self.version_prefix = '3.4.'
        else:
            self.interpreter = 'python2.7'
            self.version_prefix = '2.7.'
