"""bin/deploy keeps rules approved on the phone: it pulls a phone change into local/ and never overwrites it."""
import os
import subprocess

import pytest
from conftest import REPO

DEPLOY = os.path.join(REPO, "bin", "deploy")


@pytest.fixture
def dirs(tmp_path):
    local, dest = tmp_path / "local", tmp_path / "icloud"
    local.mkdir()
    dest.mkdir()
    subprocess.run(["git", "init", "-q", str(local)], check=True)
    for k, v in [("user.name", "t"), ("user.email", "t@example.com")]:
        subprocess.run(["git", "-C", str(local), "config", k, v], check=True)
    (local / "rules.json").write_text('{"rules": [], "content": []}\n')
    env = dict(os.environ, INBOX_TRIAGE_LOCAL=str(local), INBOX_TRIAGE_DEST=str(dest))
    return local, dest, env


def deploy(env, *args):
    return subprocess.run([DEPLOY, *args], env=env, capture_output=True, text=True)


def test_first_deploy_then_phone_change_is_pulled_and_committed(dirs):
    local, dest, env = dirs
    assert deploy(env).returncode == 0
    assert (dest / "rules.json").read_text() == (local / "rules.json").read_text()
    phone = '{"rules": [{"from": "a@example.com"}], "content": []}\n'
    (dest / "rules.json").write_text(phone)
    r = deploy(env, "--pull-rules")
    assert r.returncode == 0 and "Pulled" in r.stdout
    assert (local / "rules.json").read_text() == phone
    log = subprocess.run(["git", "-C", str(local), "log", "--oneline"], capture_output=True, text=True).stdout
    assert "approved on the phone" in log


def test_local_change_is_deployed(dirs):
    local, dest, env = dirs
    deploy(env)
    mine = '{"rules": [{"from": "b@example.com"}], "content": []}\n'
    (local / "rules.json").write_text(mine)
    assert deploy(env).returncode == 0
    assert (dest / "rules.json").read_text() == mine


def test_both_changed_stops_without_overwriting(dirs):
    local, dest, env = dirs
    deploy(env)
    (dest / "rules.json").write_text('{"rules": [{"from": "phone@example.com"}], "content": []}\n')
    (local / "rules.json").write_text('{"rules": [{"from": "mac@example.com"}], "content": []}\n')
    r = deploy(env)
    assert r.returncode == 1 and "differs" in r.stderr
    assert "phone@" in (dest / "rules.json").read_text() and "mac@" in (local / "rules.json").read_text()
