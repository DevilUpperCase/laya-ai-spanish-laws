import pytest
from services.api.app.config import Settings
from services.api.app.documents import scan_upload
from services.api.app.errors import DomainError


def test_local_scanner_rejects_standard_eicar_canary_and_accepts_clean_content():
    settings=Settings()
    assert settings.clamav_host
    assert scan_upload(b'clean synthetic document',settings.clamav_host,settings.clamav_port)
    # Harmless industry-standard antivirus test signature, not executable malware.
    eicar=b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'
    with pytest.raises(DomainError) as caught:scan_upload(eicar,settings.clamav_host,settings.clamav_port)
    assert caught.value.code=='MALWARE_DETECTED'
