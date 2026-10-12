from datetime import date
from dataclasses import replace
from uuid import uuid4
import psycopg
from services.api.app.config import Settings
from services.ingest.ingest.contracts import ParsedPublication,SectionVersion,RawPublication,PublicationRef
from services.ingest.ingest.pipeline import store_publication
from services.ingest.ingest.boe import digest


def test_identical_original_bytes_preserve_distinct_manifest_versions(tmp_path):
    source='TEST_'+uuid4().hex.upper();identifier=source+':instrument';published=date(2026,1,1);text='Synthetic regulation';sha=digest(text)
    original=RawPublication(PublicationRef(source,'1','https://official.example/1',published),b'<article>Synthetic regulation</article>','html')
    version=SectionVersion(identifier+':one','es:document','Document',0,'2026-01-01',published,published,None,text,sha)
    parsed=ParsedPublication('1','Synthetic','Reglamento',published,'1',original.ref.official_url,None,'Reviewed manifest','',None,(version,),is_consolidated=False,instrument_id=identifier)
    with psycopg.connect(Settings().admin_database_url) as conn:
        conn.execute('INSERT INTO legal.sources(id,name,official_url,terms_url) VALUES(%s,\'Synthetic\',\'https://official.example\',\'https://official.example/terms\')',(source,))
        try:
            assert store_publication(conn,parsed,original,tmp_path,'ES')==1
            assert store_publication(conn,parsed,original,tmp_path,'ES')==0
            second=replace(version,id=identifier+':two',version_ref='2026-02-01',consolidation_date=date(2026,2,1))
            assert store_publication(conn,replace(parsed,versions=(second,)),original,tmp_path,'ES')==1
            third=replace(version,id=identifier+':eu',section_key='eu:document',language_code='eu')
            assert store_publication(conn,replace(parsed,versions=(third,)),original,tmp_path,'ES')==1
            assert conn.execute('SELECT count(*) FROM legal.publications WHERE instrument_id=%s',(identifier,)).fetchone()[0]==3
        finally:conn.rollback()  # All synthetic source/instrument rows stay in this test transaction.
