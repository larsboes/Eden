"""Shared fixtures and configuration for the EDEN test suite."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-skip e2e tests unless explicitly requested with -m e2e or --run-e2e."""
    # If the user explicitly asked for e2e tests, don't skip them
    if config.getoption("-m", default="") and "e2e" in config.getoption("-m", default=""):
        return
    if config.getoption("--run-e2e", default=False):
        return

    skip_e2e = pytest.mark.skip(reason="e2e test — run with: pytest -m e2e or --run-e2e")
    for item in items:
        # Skip anything in tests/e2e/ or tests/test_aws_api.py
        test_path = str(item.fspath)
        if "/e2e/" in test_path or test_path.endswith("test_aws_api.py"):
            item.add_marker(skip_e2e)


def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run e2e tests that hit real AWS services (Bedrock, DynamoDB)",
    )
