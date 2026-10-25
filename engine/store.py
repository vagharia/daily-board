"""The `data` branch holds all generated JSON. Each run rewrites it as a single orphan commit
(no history, so the repository stays small). Two workflows write to it (news + ticker); each
owns its own files and merges the other's latest files before pushing."""
import os
import random
import shutil
import subprocess
import tarfile
import tempfile
import time

from . import config
from .util import iso, log, now

BRANCH = "data"
TICKER_FILES = {"ticker.json", "state/ticker_state.json"}
ENV = {
    "GIT_AUTHOR_NAME": "board-bot", "GIT_AUTHOR_EMAIL": "board-bot@users.noreply.github.com",
    "GIT_COMMITTER_NAME": "board-bot", "GIT_COMMITTER_EMAIL": "board-bot@users.noreply.github.com",
}

_expected = None


def _git(*args, cwd=None, env=None, check=True, capture=True):
    e = dict(os.environ)
    e.update(ENV)
    if env:
        e.update(env)
    r = subprocess.run(["git", *args], cwd=cwd, env=e, capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[:300]}")
    return (r.stdout or "").strip()


def _fetch():
    r = subprocess.run(["git", "fetch", "--depth=1", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return _git("rev-parse", f"refs/remotes/origin/{BRANCH}")


def _extract(rev, dest):
    os.makedirs(dest, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tf:
        tar_path = tf.name
    try:
        _git("archive", "--format=tar", "-o", tar_path, rev)
        with tarfile.open(tar_path) as t:
            t.extractall(dest, filter="data")
    finally:
        os.unlink(tar_path)


def prepare():
    """Check out the current data branch into DATA_DIR (publishing runs only)."""
    global _expected
    d = config.DATA_DIR
    if not config.PUBLISH:
        os.makedirs(d, exist_ok=True)
        return
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    _expected = _fetch()
    if _expected:
        _extract(_expected, d)
        log(f"data branch at {_expected[:8]} extracted")
    else:
        log("no data branch yet, starting fresh")


def _owned_by_ticker(rel):
    return rel in TICKER_FILES


def publish(role):
    """role: 'news' or 'ticker'. Commit DATA_DIR as an orphan commit and force-push with lease."""
    global _expected
    if not config.PUBLISH:
        log("publish disabled (local run)")
        return False
    repo = os.getcwd()
    gitdir = os.path.join(repo, ".git")
    mine = (lambda rel: _owned_by_ticker(rel)) if role == "ticker" else (lambda rel: not _owned_by_ticker(rel))
    for attempt in range(6):
        idx = tempfile.mktemp(prefix="dbidx")
        env = {"GIT_INDEX_FILE": idx}
        try:
            _git(f"--git-dir={gitdir}", "--work-tree=.", "add", "-A", ".", cwd=config.DATA_DIR, env=env)
            tree = _git(f"--git-dir={gitdir}", "write-tree", cwd=config.DATA_DIR, env=env)
        finally:
            if os.path.exists(idx):
                os.unlink(idx)
        commit = _git("commit-tree", tree, "-m", f"data {role} {iso(now())}")
        lease = f"--force-with-lease=refs/heads/{BRANCH}:{_expected or ''}"
        r = subprocess.run(["git", "push", lease, "origin", f"{commit}:refs/heads/{BRANCH}"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            log(f"published data ({role}) {commit[:8]}")
            _expected = commit
            return True
        log(f"push rejected (attempt {attempt + 1}): {r.stderr.strip()[:200]}")
        time.sleep(2 + random.random() * 4)
        new = _fetch()
        if new:
            tmp = tempfile.mkdtemp(prefix="dbmerge")
            try:
                _extract(new, tmp)
                # take the other workflow's files from the new tip
                for root, _, files in os.walk(tmp):
                    for f in files:
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, tmp).replace(os.sep, "/")
                        if not mine(rel):
                            dst = os.path.join(config.DATA_DIR, rel)
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(full, dst)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        _expected = new
    log("publish failed after retries")
    return False


def heartbeat(state):
    """Scheduled workflows in public repos stop after 60 days without activity; commit a tiny
    file to the default branch every ~3 weeks to keep them alive."""
    if not config.PUBLISH:
        return
    last = state.get("heartbeat", 0)
    if now() - last < 20 * 86400:
        return
    try:
        path = os.path.join(".github", "heartbeat.txt")
        with open(path, "w") as f:
            f.write(iso(now()) + "\n")
        _git("add", path)
        _git("commit", "-m", "heartbeat", "--no-verify")
        _git("push", "origin", "HEAD:refs/heads/main")
        state["heartbeat"] = now()
        log("heartbeat committed")
    except Exception as e:  # noqa: BLE001
        log("heartbeat failed:", str(e)[:120])
