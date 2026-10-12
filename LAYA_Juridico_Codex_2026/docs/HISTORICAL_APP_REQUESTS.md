# Historical requests for LAYA Juridico

This is a record of the user's requests and confirmed product decisions visible in the conversation, ordered by topic and sequence. It is a requirements history, not a claim that every item is implemented.

## Original project and implementation

1. Use the `LAYA_Juridico_Codex_2026` folder and create the plan and files needed to build and verify the application. FastAPI, LangChain/LangGraph, and LAYA are mandatory tools.
2. Create a plan and verification package first. Require both LangChain and LangGraph, preserve the no-generative-LLM rule, plan national Spanish jurisdiction scope, and self-host the database/private storage.
3. Require verified coverage for every jurisdiction at first release: current law plus history available from approved official sources; block launch for any missing jurisdiction. Integrate LAYA in shadow mode first, use fallback on outage, require measured checks plus professional legal review, and retain uploaded documents until the tenant deletes them.
4. Confirmed the design package and then asked: **"Please, fill the database and do the code."** The database work was to use Docker Desktop for local development, not to modify an externally hosted database.
5. Asked what to enter on the local sign-in screen after visiting `localhost:3000`, explaining that no scripts had been run. The requested help concerned the workspace identifier/session-token form and what was needed to make the application complete.
6. Asked to **"Do the remaining tasks"** after receiving a status list. The outstanding topics named then were normal user login and automatic startup; remaining BOE/regional/provincial/municipal/island/foral ingestion; vector indexing; nationwide coverage/history verification; 200 professionally reviewed queries; production operations; and human documentation and diagrams.
7. Clarified that professional legal review could be done by the user, a lawyer, or an employee of a lawyer. The system is local initially, but repository users should be able to configure a domain for their own servers.

## Document viewing, query quality, library and monitoring

8. Requested that the app show the real BOE document and documents uploaded by users.
9. Requested that every search result always explain why it appeared and improve legal query understanding beyond literal word matching. Asked whether LAYA training or a light local LLM might help, and invited a grill-me interview if requirements were unclear.
10. Decided to keep **no generative LLM**, add semantic search and optional clarification questions, and only consider training after evaluation.
11. Asked for **Documentos** to work like Drive plus a notebook: shared folders, uploaded-document organization, manual notes and document-linked work.
12. Asked for search to attach new documents or existing uploaded documents, similar to ChatGPT's attachment flow.
13. Asked for an on-demand script to check processing and a daily script to check Spanish State official publications.
14. Expanded the source scope to include individual administrative notices and other official bulletin content. Confirmed separate **Normativa** and **Todas las publicaciones** search scopes, while labeling individual notices so they are not presented as generally applicable legal rules.
15. Chose official PDF display where available, alongside clearly labelled exact consolidated/historical result text. Uploaded PDFs should preview in-app; DOCX should show extracted text and allow the original download.
16. Chose search attachments to support both finding related official law and searching within selected private documents, with explicit modes and visible passage evidence.
17. Chose shared workspace folders, case notebooks, searchable library, original previews, manually written notes anchored to document/page selections, and saved references, following existing workspace roles.
18. Chose a Windows-style **Papelera**: trash is recoverable until a person empties it or permanently deletes an item. Permanent deletion revokes access immediately, purges live copies within 24 hours, and expires encrypted backups within 30 days; restores must reapply deletion records. General notebook notes remain separate from deleted-document notes.
19. Chose optional **Refinar consulta**, with direct search always available. The refinement may ask the legal issue, objective, territory and relevant date; users may say unknown and inspect/edit the structured interpretation. The app must not silently infer facts.
20. Confirmed official-bulletin scope should include publicly accessible bulletin items/attachments in approved catalogues, including notices, tenders, appointments, grants and judicial notices where those bulletins publish them. BOE and BORME require ingestion paths. Keep normative and all-publication search separate, reconcile available history, and block completion for missing sources.
21. Confirmed implementation of the design and plan at `docs/superpowers/plans/2026-10-12-document-research.md`, with honest coverage/quality claims and no fabricated approval.
22. Later said **continue** to resume the implementation work.
23. Current request: identify what still needs fixing and which requested/confirmed features are already done or incomplete; save that status in one Markdown file, and save the historical app requests in another Markdown file.

## Standing decisions carried through the requests

- Mandatory local stack: FastAPI, LangChain Core, LangGraph, LAYA, and local BGE-M3; no generative LLM.
- Spanish user interface; evaluate Spanish, Catalan, Galician and Basque search.
- Self-hosted/private data by default. Domain and HTTPS should be configurable for repository adopters.
- User-facing legal results require literal source evidence, distinct publication/version/effective dates, and clear uncertainty. Search signals are not legal advice or a claim of applicability.
- First-release nationwide completeness requires audited official sources for all required State, autonomous-community/city, provincial, municipal, island and foral levels, including available history and the expanded bulletin scope.
- Professional quality review, source completeness, licensing and production-readiness require real human/source evidence; code or a populated database cannot stand in for that evidence.
