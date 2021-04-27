#!/bin/sh

set -e

export TOXENV="py$(echo -n TRAVIS_PYTHON_VERSION | sed 's/\.//')"
tox
