import subprocess,sys
import pytest


def test_runtime_lock_rejects_second_owner_and_releases(tmp_path):
    from scripts.runtime_lock import RuntimeLock
    path=tmp_path/'owner.lock'
    code="from pathlib import Path;from scripts.runtime_lock import RuntimeLock;RuntimeLock(Path(__import__('sys').argv[1])).__enter__()"
    with RuntimeLock(path):
        assert subprocess.run([sys.executable,'-c',code,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
    assert subprocess.run([sys.executable,'-c',code,str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
