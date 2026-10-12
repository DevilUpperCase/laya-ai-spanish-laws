"""Durable deletion intents kept independently of private object/database backups."""
import hashlib
import json
import os
from datetime import datetime,timezone
from uuid import UUID,uuid4


def encoded(record):return json.dumps(record,sort_keys=True,separators=(",",":")).encode()


def record_intent(root,tenant,document,epoch):
    root.mkdir(parents=True,exist_ok=True)
    record={"tenant_id":str(tenant),"document_id":str(document),"epoch":epoch,
            "deleted_at":datetime.now(timezone.utc).isoformat()}
    envelope={"record":record,"sha256":hashlib.sha256(encoded(record)).hexdigest()}
    target=root/(str(document)+".json")
    temporary=root/(str(uuid4())+".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded(envelope));stream.flush();os.fsync(stream.fileno())
        temporary.replace(target)
        if os.name!="nt":
            descriptor=os.open(root,os.O_RDONLY)
            try:os.fsync(descriptor)
            finally:os.close(descriptor)
    finally:temporary.unlink(missing_ok=True)
    return target


def read_journal(root):
    if not root.is_dir():raise ValueError("Independent deletion journal missing; restore access must remain closed")
    records=[]
    for path in root.glob("*.json"):
        envelope=json.loads(path.read_text())
        record=envelope.get("record",{})
        if hashlib.sha256(encoded(record)).hexdigest()!=envelope.get("sha256"):raise ValueError("Deletion journal integrity failure")
        if set(record)!={"tenant_id","document_id","epoch","deleted_at"}:raise ValueError("Invalid deletion record")
        UUID(record["tenant_id"]);UUID(record["document_id"])
        if type(record["epoch"]) is not int or record["epoch"]<1:raise ValueError("Invalid deletion epoch")
        if datetime.fromisoformat(record["deleted_at"]).tzinfo is None:raise ValueError("Timezone required")
        records.append(record)
    return records
