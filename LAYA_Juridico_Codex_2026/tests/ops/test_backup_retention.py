from datetime import datetime,timedelta,timezone
from io import BytesIO
import hashlib,hmac,json
from scripts import backup_local as backup


def test_incomplete_or_foreign_snapshots_do_not_block_valid_expiry(tmp_path,monkeypatch):
    root=tmp_path/'backups';root.mkdir();key=b'k'*32;key_path=tmp_path/'key';key_path.write_bytes(key)
    monkeypatch.setattr(backup,'BACKUPS',root);monkeypatch.setattr(backup,'KEY',key_path);monkeypatch.setattr(backup,'ROOT',tmp_path)
    (tmp_path/'verification/reports').mkdir(parents=True)
    incomplete=root/'20200101T000000Z-0000000000000000';incomplete.mkdir();(incomplete/'app.pg.enc').write_bytes(b'partial')
    valid=root/'20200102T000000Z-0000000000000001';valid.mkdir();artifact=valid/'app.pg.enc';backup.encrypt_stream(BytesIO(b'synthetic'),artifact,key)
    payload={'files':{'app.pg.enc':backup.digest(artifact)},'expires_at':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}
    def sign(folder):
        (folder/'manifest.json').write_text(json.dumps({'payload':payload,'hmac_sha256':hmac.new(key,backup.canonical(payload),hashlib.sha256).hexdigest()}))
    sign(valid)
    foreign=root/'20200103T000000Z-0000000000000002';foreign.mkdir();(foreign/'app.pg.enc').write_bytes(artifact.read_bytes());sign(foreign);(foreign/'operator-note.txt').write_text('Preserve me')
    assert backup.expire()==1
    assert not valid.exists() and (incomplete/'app.pg.enc').exists() and (foreign/'operator-note.txt').exists()
    report=json.loads((tmp_path/'verification/reports/backup-retention.json').read_text());assert len(report['requires_operator_review'])==2
