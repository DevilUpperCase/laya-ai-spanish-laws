"""Tenant-scoped folders, manually saved notes and recoverable document trash."""
from uuid import UUID
from .errors import DomainError


def writable(context):
    if context.role=='reader':raise DomainError('WRITE_FORBIDDEN',403)


def name(value):
    value=value.strip()
    if not value or len(value)>200 or any(ord(c)<32 for c in value):raise DomainError('NAME_INVALID',422)
    return value


class LibraryService:
    def __init__(self,db,settings):self.db,self.settings=db,settings

    async def list_documents(self,context,*,folder_id=None,query='',trash=False,cursor=None,limit=50):
        limit=min(100,max(1,limit))
        async with self.db.tenant_transaction(context) as conn:
            rows=await (await conn.execute('''SELECT id,filename,mime_type,parse_status,failure_code,created_at,folder_id,trashed_at
              FROM private.documents WHERE deleted_at IS NULL AND (trashed_at IS NOT NULL)=%s
              AND (%s::uuid IS NULL OR folder_id=%s::uuid) AND filename ILIKE %s
              AND (%s::uuid IS NULL OR id>%s::uuid) ORDER BY id LIMIT %s''',
              (trash,folder_id,folder_id,'%'+query[:200]+'%',cursor,cursor,limit+1))).fetchall()
        return {'items':rows[:limit],'next_cursor':str(rows[limit-1]['id']) if len(rows)>limit else None}

    async def create_folder(self,context,title,parent_id):
        writable(context)
        async with self.db.tenant_transaction(context) as conn:
            if parent_id:await self._exists(conn,'folders',parent_id)
            return await (await conn.execute('INSERT INTO private.folders(tenant_id,name,parent_id) VALUES(%s,%s,%s) RETURNING *',(context.tenant_id,name(title),parent_id))).fetchone()

    async def move_folder(self,context,folder_id,parent_id):
        writable(context)
        async with self.db.tenant_transaction(context) as conn:
            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('folders:'+str(context.tenant_id),))
            await self._exists(conn,'folders',folder_id)
            if parent_id:
                await self._exists(conn,'folders',parent_id)
                cycle=await (await conn.execute('WITH RECURSIVE t AS (SELECT id,parent_id FROM private.folders WHERE id=%s UNION ALL SELECT f.id,f.parent_id FROM private.folders f JOIN t ON f.id=t.parent_id) SELECT id FROM t WHERE id=%s',(parent_id,folder_id))).fetchone()
                if cycle:raise DomainError('FOLDER_CYCLE',409)
            await conn.execute('UPDATE private.folders SET parent_id=%s WHERE id=%s',(parent_id,folder_id))

    @staticmethod
    async def _exists(conn,table,key):
        # table is a hard-coded internal name, never client input.
        row=await (await conn.execute(f'SELECT * FROM private.{table} WHERE id=%s',(key,))).fetchone()
        if not row:raise DomainError('ITEM_NOT_FOUND',404)
        return row

    async def folders(self,context):
        async with self.db.tenant_transaction(context) as conn:return await (await conn.execute('SELECT * FROM private.folders ORDER BY name LIMIT 1000')).fetchall()

    async def notebooks(self,context):
        async with self.db.tenant_transaction(context) as conn:return await (await conn.execute('SELECT * FROM private.notebooks ORDER BY title LIMIT 1000')).fetchall()

    async def create_notebook(self,context,title,folder_id=None):
        writable(context)
        async with self.db.tenant_transaction(context) as conn:
            if folder_id:await self._exists(conn,'folders',folder_id)
            return await (await conn.execute('INSERT INTO private.notebooks(tenant_id,title,folder_id) VALUES(%s,%s,%s) RETURNING *',(context.tenant_id,name(title),folder_id))).fetchone()

    async def get_notebook(self,context,key,*,trash=False):
        async with self.db.tenant_transaction(context) as conn:
            notebook=await self._exists(conn,'notebooks',key)
            notes=await (await conn.execute('''SELECT n.* FROM private.notes n LEFT JOIN private.documents d ON d.id=n.document_id
             WHERE n.notebook_id=%s AND (n.document_id IS NULL OR (d.deleted_at IS NULL AND (d.trashed_at IS NOT NULL)=%s)) ORDER BY n.updated_at LIMIT 1000''',(key,trash))).fetchall()
            refs=await (await conn.execute('''SELECT r.* FROM private.saved_references r LEFT JOIN private.documents d ON d.id=r.document_id
             WHERE r.notebook_id=%s AND (r.document_id IS NULL OR (d.deleted_at IS NULL AND (d.trashed_at IS NOT NULL)=%s)) LIMIT 1000''',(key,trash))).fetchall()
            return {**notebook,'notes':notes,'references':refs}

    async def save_note(self,context,data,note_id=None):
        writable(context)
        body=data.get('body','')
        if len(body)>50000:raise DomainError('NOTE_LIMIT',422)
        async with self.db.tenant_transaction(context) as conn:
            if note_id:
                existing=await self._exists(conn,'notes',note_id)
                if existing['document_id']:
                    document=await self._exists(conn,'documents',existing['document_id'])
                    if document['trashed_at'] or document['deleted_at']:raise DomainError('DOCUMENT_NOT_FOUND',404)
                row=await (await conn.execute('UPDATE private.notes SET body=%s,revision=revision+1,updated_at=now() WHERE id=%s AND revision=%s RETURNING *',(body,note_id,data.get('revision')))).fetchone()
                if not row:raise DomainError('REVISION_CONFLICT',409)
                return row
            notebook=await self._exists(conn,'notebooks',data['notebook_id'])
            document_id=data.get('document_id')
            if document_id:
                doc=await self._exists(conn,'documents',document_id)
                if doc['deleted_at'] or doc['trashed_at']:raise DomainError('DOCUMENT_NOT_FOUND',404)
                if data.get('page_number') is not None:
                    chunk=await (await conn.execute('SELECT text FROM private.chunks WHERE document_id=%s AND page_number=%s',(document_id,data['page_number']))).fetchone()
                    if not chunk or not 0<=data.get('start_offset',-1)<data.get('end_offset',-1)<=len(chunk['text']):raise DomainError('SELECTION_INVALID',422)
            return await (await conn.execute('''INSERT INTO private.notes(tenant_id,notebook_id,document_id,page_number,start_offset,end_offset,body)
              VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *''',(context.tenant_id,notebook['id'],document_id,data.get('page_number'),data.get('start_offset'),data.get('end_offset'),body))).fetchone()

    async def save_reference(self,context,notebook_id,version_id):
        writable(context)
        async with self.db.tenant_transaction(context) as conn:
            await self._exists(conn,'notebooks',notebook_id)
            if not await (await conn.execute('SELECT id FROM legal.section_versions WHERE id=%s',(version_id,))).fetchone():raise DomainError('VERSION_NOT_FOUND',404)
            return await (await conn.execute('INSERT INTO private.saved_references(tenant_id,notebook_id,section_version_id) VALUES(%s,%s,%s) RETURNING *',(context.tenant_id,notebook_id,version_id))).fetchone()

    async def update_document(self,context,key,*,filename=None,folder_id=None,move=False,trash=None):
        writable(context)
        async with self.db.tenant_transaction(context) as conn:
            row=await (await conn.execute('SELECT * FROM private.documents WHERE id=%s AND deleted_at IS NULL FOR UPDATE',(key,))).fetchone()
            if not row:raise DomainError('DOCUMENT_NOT_FOUND',404)
            if move and folder_id:await self._exists(conn,'folders',folder_id)
            if filename is not None:await conn.execute('UPDATE private.documents SET filename=%s WHERE id=%s',(name(filename),key))
            if move:await conn.execute('UPDATE private.documents SET folder_id=%s WHERE id=%s',(folder_id,key))
            if trash is not None:await conn.execute('UPDATE private.documents SET trashed_at=CASE WHEN %s THEN now() ELSE NULL END WHERE id=%s',(trash,key))
        return {'id':key}

    async def trash_notes(self,context,key):
        async with self.db.tenant_transaction(context) as conn:
            row=await self._exists(conn,'documents',key)
            if row['deleted_at'] or not row['trashed_at']:raise DomainError('DOCUMENT_NOT_FOUND',404)
            return await (await conn.execute('SELECT * FROM private.notes WHERE document_id=%s ORDER BY updated_at',(key,))).fetchall()
