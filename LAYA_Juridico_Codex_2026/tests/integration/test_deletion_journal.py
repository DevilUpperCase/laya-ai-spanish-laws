import json
from uuid import uuid4
import pytest
from services.api.app.deletion_journal import record_intent,read_journal


def test_durable_journal_survives_separate_object_restore_and_rejects_tampering(tmp_path):
    tenant,doc=uuid4(),uuid4()
    path=record_intent(tmp_path,tenant,doc,1)
    record=read_journal(tmp_path)[0]
    assert record["tenant_id"]==str(tenant)
    assert record["document_id"]==str(doc)
    assert "text" not in record and "filename" not in record
    path.write_text('{}')
    with pytest.raises(ValueError):read_journal(tmp_path)
