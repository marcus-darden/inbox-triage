"""Shared helpers: load the extensionless bin/ scripts as modules, and build the shortcuts once."""
import importlib.machinery
import importlib.util
import os
import plistlib
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ["InboxTriage Token", "InboxTriage Engine", "InboxTriage"]


def load_script(name):
    path = os.path.join(REPO, "bin", name)
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def builder():
    return load_script("build-shortcut")


@pytest.fixture(scope="session")
def learn():
    return load_script("learn")


@pytest.fixture(scope="session")
def shortcuts(tmp_path_factory):
    """Build all three shortcuts (unsigned) into a temp folder; return {name: list of actions}."""
    out = tmp_path_factory.mktemp("build")
    env = dict(os.environ, INBOX_TRIAGE_BUILD=str(out))
    subprocess.run([sys.executable, os.path.join(REPO, "bin", "build-shortcut"), "--no-sign"],
                   check=True, env=env, capture_output=True)
    result = {}
    for name in NAMES:
        with open(out / f"{name}.unsigned.shortcut", "rb") as f:
            result[name] = plistlib.load(f)
    return result
