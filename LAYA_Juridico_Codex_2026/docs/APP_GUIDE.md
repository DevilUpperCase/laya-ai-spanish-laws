# Using LAYA Jurídico

LAYA Jurídico searches imported official Spanish legislation and the historical text versions supplied by those publishers. It returns literal passages with publication/version dates, geographic identity and links to the official source. You can also upload a private PDF or DOCX and select text to search for related legislation.

The interface is Spanish. Search evaluation is planned for Spanish, Catalan, Galician and Basque. The current local corpus is mainly BOE, with small DOGC and DOG imports. **Nationwide coverage is incomplete.** A successful search does not establish that every relevant local ordinance has been imported, that a provision is currently effective, or that it applies to your facts.

## Sign in

1. Open http://127.0.0.1:3000 or http://localhost:3000.
2. Enter **Correo electrónico** and **Contraseña**. Your generated local account is in `private-data/login-credentials.json`; copy the values without quotation marks. Keep this file private. The former tenant-ID/token form has been replaced.
3. Click **Entrar al espacio**. If your account belongs to multiple workspaces, select the appropriate one. Membership is checked on the server.
4. Change your generated password using the account controls. After changing it, sign in again. The original credentials file is a bootstrap record; it is not automatically rewritten with your new password.

Refreshing the page restores an unexpired login through a protected cookie. The default browser session expires after one hour. **Cerrar sesión** revokes it. Password changes revoke all browser sessions for that user. Access to another workspace requires membership; knowing its identifier is insufficient.

The local stack starts after you sign in to Windows. Docker Desktop must be installed, and this account must remain signed in for background tasks. A restart may take several minutes while databases, malware signatures and local models load. If the page cannot connect, use the operator guide's status command.

## Search official texts

Enter a concrete query in **Consulta jurídica**, such as `arrendamiento vivienda`, or an exact reference such as `BOE-A-1994-26003`. Choose territory, document type and date options when relevant, then click **Buscar**. Geographic filters use official identifiers, avoiding ambiguity between municipalities with the same name. A broader territory includes its descendants.

Results are passages, so several results can belong to one instrument. Each card shows the source reference, territory, language, literal text, publication date, version date and evidence-based explanation. Open **Fuente oficial** to verify the full text, surrounding provisions and publisher notices. No generated legal opinion is produced.

Publication date, version/consolidation date and legal effectiveness are distinct. **Vigencia por verificar** means effectiveness has not been independently established. An original publication date is not an assumed commencement date. Selecting a historical date limits the published versions considered; it does not automatically prove the law's effectiveness on that date. A verified-only search excludes versions without verified effectiveness evidence and can therefore return no results.

| Notice | What it means and what to do |
|---|---|
| National coverage pending | A required publisher, period or jurisdiction can be missing. Check additional official sources. |
| Semantic index in progress | Text search includes imported passages; semantic retrieval only includes indexed passages. |
| LAYA unavailable/incomplete | Baseline ordering is retained. LAYA runs in shadow mode and cannot change rankings yet. |
| Text retrieval degraded | At least one retrieval engine exceeded its budget. Results can be incomplete; narrow the query and check sources. |
| History/annexes not reconciled | The import does not prove all versions or annexes are present. Read the complete official publication. |
| Informational consolidated text | The consolidated presentation does not itself certify legal applicability. |

A first search after startup may be slow while local weights load. Empty results mean no match was returned from the available corpus and filters; they do not prove that no applicable legislation exists.

## Work with a private document

1. Open **Documentos** and choose a PDF or DOCX under **Archivo PDF o DOCX**.
2. Click **Cargar y procesar**. The server validates the format and size, scans it for malware, stores it privately and queues extraction.
3. Wait for processing. PDFs retain page boundaries; DOCX paragraphs and tables have logical sections rather than original page geometry. Image-only PDFs use pinned local OCR and are marked uncertain. Check OCR before relying on it.
4. Select the relevant text in **Texto del documento**, then click **Buscar normativa relacionada**. The server verifies the document, text hash, page and offsets against the stored text. It uses the selected passage to search the public legal corpus.
5. Use the authorized download control when needed. Downloads require current workspace access.

Uploads are limited to 20 MiB, 300 PDF pages and two million extracted characters. Encrypted PDFs, unsafe DOCX relationships/macros, excessive archives and unsupported files are rejected. Extraction failures are visible rather than silently presented as empty documents. A reader can view authorized documents but cannot upload or delete them.

Private documents, text and selections remain on this self-hosted system. Search workflows do not persist private graph state or send document text to external inference/tracing services. Documents are kept until the tenant deletes them.

## Delete a document

Click **Eliminar documento**, then **Confirmar eliminación**. Access is revoked immediately, including previously known document/download URLs. A background worker removes live originals and extracted content; the required deadline is 24 hours. Encrypted backups have a maximum 30-day retention contract. A restore must replay the latest deletion records before permitting access, so an old snapshot cannot make a deleted document accessible again.

The local synthetic restore rehearsal passed. Off-host deletion-journal replication, independent key custody and proof of elapsed backup expiry are still production requirements. Do not interpret a local rehearsal as completion of those obligations.

## Inspect coverage and get help

**Cobertura** shows observed source/corpus counts and the outstanding national-release blocker. A registered source or a high instrument count is not an audited coverage claim. All state, autonomous-community/city, provincial, municipal, island and foral requirements remain mandatory for release.

For connection/processing problems, give the operator the time, operation and visible error code. Do not send passwords, session cookies, tokens or private document text in a diagnostic report. Operators should use [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md). Developers should use [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).
