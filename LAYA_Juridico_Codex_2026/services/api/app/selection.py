from .errors import DomainError


def resolve_span(text, selection):
    if selection.end_offset > len(text):
        raise DomainError("SELECTION_INVALID",422)
    selected=text[selection.start_offset:selection.end_offset]
    if selection.selected_text is not None and selection.selected_text != selected:
        raise DomainError("SELECTION_MISMATCH",409)
    return selected


class SelectionService:
    def __init__(self, db):
        self.db=db

    async def resolve(self,context,document_id,selection):
        async with self.db.tenant_transaction(context) as conn:
            row=await (await conn.execute("""SELECT c.text FROM private.chunks c JOIN private.documents d ON d.id=c.document_id
             WHERE d.id=%s AND d.deleted_at IS NULL AND d.trashed_at IS NULL AND d.parse_status='ready' AND c.page_number=%s""",(document_id,selection.page_number))).fetchone()
            if row is None:
                raise DomainError("DOCUMENT_NOT_FOUND_OR_NOT_READY",404)
            return resolve_span(row["text"],selection)

    async def recheck(self,context,document_id):
        async with self.db.tenant_transaction(context) as conn:
            row=await (await conn.execute("SELECT id FROM private.documents WHERE id=%s AND deleted_at IS NULL AND trashed_at IS NULL AND parse_status='ready'",(document_id,))).fetchone()
            if row is None:
                raise DomainError("DOCUMENT_NOT_FOUND",404)
