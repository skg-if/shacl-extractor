# SPDX-FileCopyrightText: 2025-2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

import shutil
import tempfile
import unittest


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(dir=".")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
