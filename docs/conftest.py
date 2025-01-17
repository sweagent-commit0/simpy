"""
This module scans all ``*.rst`` files below ``docs/`` for example code.
Example code is discovered by checking for lines containing the ``..
literals include:: `` directives.

An example consists of two consecutive literals include directives. The
first must include a ``*.py`` file and the second a ``*.out`` file. The
``*.py`` file consists of the example code which is executed in
a separate process. The output of this process is compared to the
contents of the ``*.out`` file.

"""
import pathlib
import subprocess
import sys
from typing import ClassVar

import pytest
from _pytest.assertion.util import _diff_text
from py._code.code import TerminalRepr


def pytest_collect_file(path, parent):
    """Checks if the file is a rst file and creates an
    :class:`ExampleFile` instance."""
    if path.ext == '.py' and path.dirname.endswith('code'):
        return ExampleFile.from_parent(parent, path=pathlib.Path(path.strpath))
    else:
        return None


class ExampleFile(pytest.File):
    """Represents an example ``.py`` and its output ``.out``."""

    def collect(self):
        pyfile = self.fspath
        outfile = pyfile.new(ext='.out')

        if outfile.check():
            yield ExampleItem.from_parent(self, pyfile=pyfile, outfile=outfile)


class ExampleItem(pytest.Item):
    """Executes an example found in a rst-file."""

    def __init__(self, pyfile, outfile, parent):
        pytest.Item.__init__(self, str(pyfile), parent)
        self.pyfile = pyfile
        self.outfile = outfile

    def runtest(self):
        # Read expected output.
        with self.outfile.open() as f:
            expected = f.read()

        output = subprocess.check_output(
            [sys.executable, str(self.pyfile)],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

        if output != expected:
            # Hijack the ValueError exception to identify mismatching output.
            raise ValueError(expected, output)

    def repr_failure(self, exc_info):
        if exc_info.errisinstance(ValueError):
            # Output is mismatching. Create a nice diff as failure description.
            expected, output = exc_info.value.args
            message = _diff_text(output, expected)
            return ReprFailExample(self.pyfile, self.outfile, message)

        elif exc_info.errisinstance(subprocess.CalledProcessError):
            # Something went wrong while executing the example.
            return ReprErrorExample(self.pyfile, exc_info)

        else:
            # Something went terribly wrong :(
            return pytest.Item.repr_failure(self, exc_info)

    def reportinfo(self):
        return self.fspath, None, f'{self.pyfile.purebasename} example'


class ReprFailExample(TerminalRepr):
    """Reports output mismatches in a nice and informative representation."""

    Markup: ClassVar = {
        '+': {'green': True},
        '-': {'red': True},
        '?': {'bold': True},
    }
    """Colorization codes for the diff markup."""

    def __init__(self, pyfile, outfile, message):
        self.pyfile = pyfile
        self.outfile = outfile
        self.message = message

    def toterminal(self, tw):
        for line in self.message:
            markup = ReprFailExample.Markup.get(line[0], {})
            tw.line(line, **markup)
        tw.line('')
        tw.line(f'{self.pyfile}: Unexpected output')


class ReprErrorExample(TerminalRepr):
    """Reports failures in the execution of an example."""

    def __init__(self, pyfile, exc_info):
        self.pyfile = pyfile
        self.exc_info = exc_info

    def toterminal(self, tw):
        tw.line(
            'Execution of {self.pyfile.basename} failed. Captured output:',
            red=True,
            bold=True,
        )
        tw.sep('-')
        tw.line(self.exc_info.value.output)
        rc = self.exc_info.value.returncode
        tw.line(f'{self.pyfile}: Example failed (exitcode={rc})')
