"""Finite original-item capture; source periods preserve incomplete or failed evidence."""
import hashlib,json,subprocess,sys,os
from pathlib import Path
from .boe_bulletin import parse_summary,parse_item_xml
from .boe_originals import archive_asset
from services.api.app.query_intent import split_passages

def sync_day(conn,client,source,day,settings,max_items=None):
    source_id=source.upper()+'_DAILY';url='https://www.boe.es/datosabiertos/api/'+source+'/sumario/'+day.strftime('%Y%m%d')
    try:
        content=client.get(url).content;summary=parse_summary(content,source)
        if summary['date']!=day:raise ValueError('Wrong publication day')
        archive_asset(conn,source_id,'summary:'+day.isoformat(),url,content,'application/xml',settings.public_storage_path,'daily_summary')
        conn.execute('''INSERT INTO legal.source_periods(source_id,publication_date,expected_count,expected_assets,status,summary_sha256)
         VALUES(%s,%s,%s,%s,'captured',%s) ON CONFLICT(source_id,publication_date) DO UPDATE SET expected_count=EXCLUDED.expected_count,
         expected_assets=EXCLUDED.expected_assets,status='captured',summary_sha256=EXCLUDED.summary_sha256,reconciled_at=now(),failure_code=NULL''',
         (source_id,day,len(summary['items']),sum(1+bool(i['xml_url']) for i in summary['items']),hashlib.sha256(content).hexdigest()))
        for item in summary['items']:
            key=source_id+':'+item['external_id']
            conn.execute('''INSERT INTO legal.bulletin_items(id,source_id,external_id,title,publication_date,jurisdiction_id,category,normative,official_url,pdf_url)
             VALUES(%s,%s,%s,%s,%s,'ES',%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET title=EXCLUDED.title,category=EXCLUDED.category,normative=EXCLUDED.normative''',
             (key,source_id,item['external_id'],item['title'],day,item['category'],item['normative'],item['official_url'],item['pdf_url']))
        conn.commit();processed=0;failures=0
        for item in summary['items']:
            if max_items is not None and processed>=max_items:break
            key=source_id+':'+item['external_id']
            if conn.execute("SELECT 1 FROM legal.bulletin_items WHERE id=%s AND status='complete'",(key,)).fetchone():continue
            processed+=1
            try:
                pdf=client.get(item['pdf_url']).content
                if not pdf.startswith(b'%PDF-'):raise ValueError('Invalid original PDF')
                archive_asset(conn,source_id,item['external_id'],item['pdf_url'],pdf,'application/pdf',settings.public_storage_path)
                text=None
                if item['xml_url']:
                    xml=client.get(item['xml_url']).content
                    archive_asset(conn,source_id,item['external_id'],item['xml_url'],xml,'application/xml',settings.public_storage_path,'original_metadata')
                    text=parse_item_xml(xml,item['external_id'])
                if text is None:
                    # Bounded isolated parser, original archived already; no generated OCR.
                    pdf_path=Path(settings.public_storage_path)/('assets/'+hashlib.sha256(pdf).hexdigest())
                    env=os.environ.copy();env['PYTHONPATH']=str(Path(__file__).resolve().parents[3]);env['PYTHONUTF8']='1'
                    child=subprocess.run([sys.executable,'-m','services.api.app.extract_worker',str(pdf_path),'application/pdf','1000','5000000','0',settings.ocr_language],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=120,creationflags=0x08000000 if os.name=='nt' else 0)
                    if child.returncode:raise ValueError('Original PDF requires parser/OCR review')
                    text='\n'.join(p['text'] for p in json.loads(child.stdout))
                if not text or len(text)>5_000_000:raise ValueError('Item text outside parser budget')
                conn.execute("UPDATE legal.bulletin_items SET text=%s,search_vector=to_tsvector('simple',public.unaccent(%s)),status='complete',failure_code=NULL WHERE id=%s",(text,text,key))
                conn.execute('DELETE FROM legal.bulletin_chunks WHERE item_id=%s',(key,))
                for ordinal,(start,end,passage) in enumerate(split_passages(text)):
                    chunk_id=hashlib.sha256((key+':'+str(start)+':'+passage).encode()).hexdigest()
                    conn.execute("INSERT INTO legal.bulletin_chunks(id,item_id,ordinal,start_offset,end_offset,passage,search_vector) VALUES(%s,%s,%s,%s,%s,%s,to_tsvector('simple',public.unaccent(%s)))",(chunk_id,key,ordinal,start,end,passage,passage))
                conn.commit()
            except Exception as error:
                conn.rollback();failures+=1
                conn.execute("UPDATE legal.bulletin_items SET status='failed',failure_code=%s WHERE id=%s",(type(error).__name__,key));conn.commit()
        complete=conn.execute("SELECT count(*) FROM legal.bulletin_items WHERE source_id=%s AND publication_date=%s AND status='complete'",(source_id,day)).fetchone()[0]
        status='complete' if complete==len(summary['items']) else 'partial'
        conn.execute('UPDATE legal.source_periods SET status=%s,reconciled_at=now() WHERE source_id=%s AND publication_date=%s',(status,source_id,day))
        if status=='complete':conn.execute('UPDATE legal.sources SET last_successful_sync=now(),last_integrated_publication=greatest(last_integrated_publication,%s) WHERE id=%s',(day,source_id))
        conn.commit();return {'source':source,'date':day.isoformat(),'expected':len(summary['items']),'integrated':complete,'status':status,'failures':failures}
    except Exception as error:
        conn.rollback()
        conn.execute('''INSERT INTO legal.source_periods(source_id,publication_date,status,failure_code) VALUES(%s,%s,'unavailable',%s)
          ON CONFLICT(source_id,publication_date) DO UPDATE SET status='unavailable',failure_code=EXCLUDED.failure_code,reconciled_at=now()''',(source_id,day,type(error).__name__))
        conn.commit();return {'source':source,'date':day.isoformat(),'status':'unavailable','error_type':type(error).__name__}
