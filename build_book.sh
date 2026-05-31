#!/bin/bash

# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelomas@gmail.com>
#
# SPDX-License-Identifier: ISC

uv run jupyter-book clean docs
uv run jupyter-book build docs
