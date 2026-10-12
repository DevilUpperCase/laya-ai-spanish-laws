"""Fail closed on changed local artifacts; no remote loaders or trusted custom code."""
import hashlib
import re


def verify_artifacts(root,entry,revision):
    if not re.fullmatch(r"[0-9a-f]{40}",revision) or entry.get("revision")!=revision:
        raise ValueError("Model revision mismatch")
    files=entry.get("files")
    if not isinstance(files,dict) or not files:raise ValueError("Model artifact manifest missing")
    root=root.resolve()
    for name,digest in files.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not re.fullmatch(r"[0-9a-f]{64}",digest):
            raise ValueError("Unsafe model manifest")
        h=hashlib.sha256()
        with path.open("rb") as stream:
            while block:=stream.read(1024*1024):h.update(block)
        if h.hexdigest()!=digest:raise ValueError("Model artifact hash mismatch")
