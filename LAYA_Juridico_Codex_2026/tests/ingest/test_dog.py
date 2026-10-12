from pathlib import Path
from datetime import date
from services.ingest.ingest.dog import discover_feed,parse_html


def test_dog_general_dispositions_excludes_issue_summary_and_preserves_language():
    folder=Path(__file__).parents[2]/'sources/snapshots'
    rows=discover_feed((folder/'dog-section1-es.rss').read_bytes())
    assert len(rows)==1 and rows[0]['publication_date']==date(2026,10,2)
    versions=parse_html((folder/'dog-sample-es.html').read_bytes(),rows[0],'es')
    assert versions and 'Registro Gallego' in versions[0].text
    assert versions[0].effective_from is None and not versions[0].effectiveness_verified
    assert versions[0].official_url==rows[0]['url']
