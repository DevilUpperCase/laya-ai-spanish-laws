"""Generate a human-oriented inventory of all owned source files and Python interfaces."""
import ast,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
API={
'main':'Assemble FastAPI, lifespan, routes, middleware, dependencies and operational/release health.',
'config':'Validate local/private service boundaries, secrets, model pins and runtime limits.',
'contracts':'Typed request, result, candidate, tenant, document and classifier data contracts.',
'browser_auth':'Verify passwords with local Auth; create, resolve, revoke and expire hashed opaque browser sessions.',
'auth':'Verify RS256 automation identity or browser session, then resolve live tenant membership.',
'database':'Manage async restricted-role pools and trusted transaction-local user/tenant context.',
'body_limit':'Bound incoming request bodies before framework multipart parsing.',
'coverage':'Read actual inventory/import/index counts without implying audited nationwide coverage.',
'documents':'Validate and scan uploads, authorize stored pages/downloads, guard paths and revoke access on deletion.',
'jobs':'Lease durable extraction/purge work, check deletion epochs and recover exhausted jobs.',
'extract_worker':'Run bounded native document/OCR extraction in an isolated subprocess.',
'deletion_journal':'Fsync independent deletion intents and validate replay records.',
'selection':'Resolve authorized stored text offsets/hashes rather than trusting browser-selected text.',
'search':'Resolve request/selection context, execute the transient graph and attach coverage/degradation warnings.',
'search_graph':'Compile the sequential ephemeral LangGraph with shadow classification and literal explanations.',
'retrieval':'Retrieve filtered reference/FTS/trigram/vector candidates, use current-version cache and fuse rankings.',
'fusion':'Combine independent candidate rank lists using reciprocal rank fusion.',
'embeddings':'Load verified local BGE-M3 offline and produce bounded normalized 1024-dimensional vectors.',
'model_integrity':'Verify model/OCR artifacts against immutable revision and file hashes before use.',
'laya_client':'Invoke authenticated bounded local LAYA batches with circuit breaking and strict non-generation envelopes.',
'laya_policy':'Apply safe relevance policy and keep classification separate from legal applicability/ranking approval.',
'explanations':'Construct literal evidence-based match reasons without generated legal text.',
'errors':'Represent domain failures using stable safe codes rather than secret-bearing exception bodies.'}
INGEST={'boe':'Parse and discover real BOE catalogue/XML versions; preserve originals and correlated date evidence.', 'dogc':'Discover Catalan open-data norms and parse actual Spanish/Catalan Akoma Ntoso XML originals.', 'dog':'Conservatively capture Galicia general-disposition RSS/HTML with explicit history/freshness limits.', 'manifest':'Validate reviewed enumerated publication manifests and parse bounded HTML/PDF originals.', 'pipeline':'Archive original bytes and atomically commit instrument/publication/version/chunk records and current cache.', 'contracts':'Define publisher discovery, original, version and reconciliation interfaces.', 'official_http':'Fetch bounded official public bodies with exact host/redirect and verified TLS constraints.', 'source_registry':'Parse official publisher directory and resolve implemented concrete adapters.', 'inventory':'Load captured official INE geographic hierarchy and record inventory reconciliation limits.', 'jurisdiction_resolver':'Resolve publisher issuer identities to exact official geographic IDs.'}
UI={'workspace':'Own password login, restored cookie session, workspace selection, password change and logout.', 'results':'Render literal results with source links, date metadata and understandable warnings.', 'api':'Define browser API contracts, fixed same-origin calls and Spanish domain/error messages.', 'utils':'Merge conditional utility classes for reusable controls.', 'layout':'Declare Spanish document metadata and shared authenticated workspace shell.', 'page':'Render the route-specific search, document or coverage workflow.', 'route':'Stream an allowlisted API path to a fixed private upstream, forwarding only required headers.'}


def purpose(path,content):
    if path.name=='__init__.py':return 'Package boundary for imports; no application workflow.'
    if path.parts[0]=='tests':return 'Regression/fixture verification for '+str(path.parent).replace('tests/','')+'; synthetic inputs do not imply professional release approval.'
    if str(path).replace('\\','/').startswith('services/api/app/'):return API.get(path.stem,'API support module; see its interfaces below.')
    if str(path).replace('\\','/').startswith('services/ingest/ingest/'):return INGEST.get(path.stem,'Publisher-ingestion support module.')
    if path.suffix=='.py':
        tree=ast.parse(content);return ast.get_docstring(tree) or 'CLI/support module for '+path.stem.replace('_',' ')+'. Inspect listed interfaces and the operator guide before maintenance use.'
    if path.parts[0]=='apps':return UI.get(path.stem,'Reusable '+path.stem.replace('-',' ')+' UI component/configuration for the Spanish application.')
    if path.suffix=='.sql':return 'Checksum-tracked schema, permissions, indexes or recovery migration. Applied migrations are immutable; add a successor migration.'
    if path.suffix=='.ps1':return 'Register/remove only the named limited current-user scheduled task or local operation described in the operator guide.'
    if path.parts[0]=='infra':return 'Pinned local deployment/service configuration. Production templates require explicit hosting/TLS review.'
    return 'Owned build/configuration/verification support; separate from third-party dependencies and private runtime data.'


def interfaces(content):
    tree=ast.parse(content);rows=[]
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            if isinstance(node,ast.ClassDef):
                rows.append(f'`class {node.name}`')
                for member in node.body:
                    if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        signature=ast.unparse(member.args);rows.append(f'`{node.name}.{member.name}({signature})`')
            else:rows.append(f'`{node.name}({ast.unparse(node.args)})`')
    return rows


def main():
    roots=['services','scripts','evaluation','db','infra','apps/web/src','tests']
    extensions={'.py','.ts','.tsx','.sql','.ps1','.cjs','.yaml','.css'}
    paths=sorted({p for folder in roots for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in extensions and not any(part in {'__pycache__','fixtures','node_modules','.next'} for part in p.parts)})
    paths+= [p for p in [ROOT/'pyproject.toml',ROOT/'apps/web/package.json',ROOT/'apps/web/next.config.ts',ROOT/'apps/web/tsconfig.json',ROOT/'.env.example'] if p.is_file()]
    text=['# Owned code reference','','Generated by `scripts/document_code.py`. Read the developer/operator guides for workflows and trust boundaries. This inventory covers owned code, tests, SQL, infrastructure and configuration; it excludes third-party dependencies, generated caches, private files, public snapshots and model weights. Function signatures describe interfaces, not proof of safety or release acceptance.','',f'Total owned files: **{len(paths)}**.','']
    for path in paths:
        relative=path.relative_to(ROOT);content=path.read_text(encoding='utf-8-sig')
        text.extend([f'## `{relative.as_posix()}`','',purpose(relative,content),''])
        if path.suffix=='.py':
            rows=interfaces(content)
            if rows:text.extend(['Interfaces:','',*['- '+row for row in rows],''])
        elif path.suffix in {'.ts','.tsx','.cjs'}:
            exported=re.findall(r'export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|type|interface)\s+(\w+)',content)
            if exported:text.extend(['Exports: '+', '.join('`'+name+'`' for name in exported)+'.',''])
    (ROOT/'docs/CODE_REFERENCE.md').write_text('\n'.join(text),encoding='utf-8');print(f'Documented {len(paths)} owned files.')


if __name__=='__main__':main()
