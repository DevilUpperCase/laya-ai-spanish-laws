from io import BytesIO
import pytest
from cryptography.exceptions import InvalidTag


def test_encrypted_backup_roundtrip_and_tamper_rejection(tmp_path):
    from scripts.backup_local import encrypt_stream,verified_plaintext
    key=bytes(range(32));path=tmp_path/'snapshot.enc';private=b'synthetic private canary'*10000
    encrypt_stream(BytesIO(private),path,key)
    assert private[:40] not in path.read_bytes()
    assert b''.join(verified_plaintext(path,key))==private
    data=bytearray(path.read_bytes());data[40]^=1;path.write_bytes(data)
    with pytest.raises(InvalidTag):next(verified_plaintext(path,key))


def test_wrong_key_cannot_release_any_plaintext(tmp_path):
    from scripts.backup_local import encrypt_stream,verified_plaintext
    path=tmp_path/'snapshot.enc';encrypt_stream(BytesIO(b'canary'),path,b'a'*32)
    with pytest.raises(InvalidTag):next(verified_plaintext(path,b'b'*32))


@pytest.mark.parametrize('suffix',[b'',b'extra'])
def test_authenticated_end_marker_required_before_any_content(tmp_path,suffix):
    from scripts.backup_local import encrypt_stream,verified_plaintext
    path=tmp_path/'snapshot.enc';encrypt_stream(BytesIO(b'canary'),path,b'a'*32)
    data=path.read_bytes();path.write_bytes(data[:-20] if suffix==b'' else data+suffix)
    with pytest.raises(ValueError):next(verified_plaintext(path,b'a'*32))
