# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

import shutil
import tempfile

import pytest


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(dir=".")
    yield d
    shutil.rmtree(d)
