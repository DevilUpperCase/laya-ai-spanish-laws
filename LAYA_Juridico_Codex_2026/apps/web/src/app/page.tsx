"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import { AttachmentPicker } from "@/components/attachment-picker";
import { Button } from "@/components/ui/button";
import { useSession } from "@/components/workspace";
import { Results } from "@/components/results";
import { api, DocumentRecord, message, SearchResponse } from "@/lib/api";

type Jurisdiction = { id: string; name: string; level: string };
type SearchScope = "normative" | "all_publications" | "attachments";

export default function Page() {
  const session = useSession();
  const [guided, setGuided] = useState(false);
  const [issue, setIssue] = useState("");
  const [objective, setObjective] = useState("");
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [scope, setScope] = useState<SearchScope>("normative");
  const [query, setQuery] = useState("");
  const [territory, setTerritory] = useState("");
  const [date, setDate] = useState("");
  const [history, setHistory] = useState(false);
  const [verified, setVerified] = useState(false);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (session) {
      api<Jurisdiction[]>("/v1/jurisdictions", session)
        .then((rows) => {
          if (!cancelled) setJurisdictions(rows);
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
    };
  }, [session]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!session || (scope === "attachments" && !docs.length)) return;
    setBusy(true);
    setError("");
    setResponse(null);
    try {
      setResponse(
        await api<SearchResponse>("/v1/search", session, {
          method: "POST",
          body: JSON.stringify({
            query,
            intent: guided ? { issue, objective } : null,
            attachment_ids: docs.map((doc) => doc.id),
            scope,
            territory_codes: territory ? [territory] : [],
            as_of: date || null,
            include_historical: history,
            verified_only: verified,
          }),
        }),
      );
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Error de búsqueda");
    } finally {
      setBusy(false);
    }
  }

  const attachmentsReady = docs.length > 0 && docs.every((doc) => doc.parse_status === "ready");

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Investigación jurídica</p>
          <h1>
            Encuentra la norma.
            <br />
            <em>Comprueba la fuente.</em>
          </h1>
          <p className="lead">Busca por concepto, referencia o cuestión jurídica.</p>
        </div>
        <BookOpen size={62} strokeWidth={1} className="heading-icon" />
      </div>

      <div className="search-layout">
        <aside className="panel filters">
          <h2>Ámbito de consulta</h2>
          <label>
            Territorio
            <select value={territory} onChange={(event) => setTerritory(event.target.value)}>
              <option value="">Todos los territorios importados</option>
              {jurisdictions.map((jurisdiction) => (
                <option key={jurisdiction.id} value={jurisdiction.id}>
                  {jurisdiction.name} · {jurisdiction.id}
                </option>
              ))}
            </select>
          </label>
          <label>
            Fecha de consulta
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </label>
          <p className="muted">Las fechas de publicación y vigencia se muestran por separado.</p>
          <label className="checkbox">
            <input type="checkbox" checked={history} onChange={(event) => setHistory(event.target.checked)} />
            Incluir versiones históricas
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={verified} onChange={(event) => setVerified(event.target.checked)} />
            Solo intervalos de vigencia verificados
          </label>
          <div className="filter-note">
            La normativa provincial y municipal requiere auditorías adicionales. Los filtros no garantizan cobertura
            completa.
          </div>
        </aside>

        <section>
          <Button variant="outline" onClick={() => setGuided(!guided)}>
            Refinar consulta
          </Button>
          {guided && (
            <div className="panel refinement">
              <h2>Comprender tu cuestión</h2>
              <label>
                Problema jurídico (puedes dejarlo vacío si lo desconoces)
                <textarea value={issue} onChange={(event) => setIssue(event.target.value)} maxLength={1000} rows={3} />
              </label>
              <label>
                Objetivo de la consulta
                <textarea value={objective} onChange={(event) => setObjective(event.target.value)} maxLength={1000} rows={3} />
              </label>
              <p>
                Interpretación: {issue || "problema no especificado"} · Objetivo: {objective || "no especificado"} ·
                Fecha: {date || "versiones actuales"}. Revisa el territorio y la fecha. No se supondrán hechos.
              </p>
            </div>
          )}

          <fieldset className="scope-options" aria-label="Ámbito de búsqueda">
            <legend>Buscar en</legend>
            <label>
              <input
                type="radio"
                name="search-scope"
                value="normative"
                checked={scope === "normative"}
                onChange={() => setScope("normative")}
              />
              Normativa
            </label>
            <label>
              <input
                type="radio"
                name="search-scope"
                value="all_publications"
                checked={scope === "all_publications"}
                onChange={() => setScope("all_publications")}
              />
              Todas las publicaciones
            </label>
            <label>
              <input
                type="radio"
                name="search-scope"
                value="attachments"
                checked={scope === "attachments"}
                disabled={!attachmentsReady}
                onChange={() => setScope("attachments")}
              />
              Documentos adjuntos
            </label>
          </fieldset>

          <AttachmentPicker selected={docs} onChange={setDocs} />

          <form onSubmit={submit} className="search-form">
            <label htmlFor="query" className="sr-only">
              Consulta jurídica
            </label>
            <Search size={21} />
            <input
              id="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Escribe tu consulta o una referencia BOE…"
              required
              maxLength={3000}
            />
            <Button disabled={busy || docs.some((doc) => doc.parse_status !== "ready") || (scope === "attachments" && !attachmentsReady)}>
              {busy ? "Buscando…" : "Buscar"}
              <ArrowRight size={17} />
            </Button>
          </form>
          <div className="search-hint">Referencias exactas · Extractos literales · Fuente oficial</div>
          {busy && <p className="loading" role="status">Consultando el corpus oficial…</p>}
          {error && <p className="error" role="alert">{error}</p>}

          {response ? (
            <>
              <div className="results-heading">
                <h2>{response.results.length + (response.private_results?.length ?? 0)} extractos encontrados</h2>
                <span className="badge">Clasificación en observación</span>
              </div>
              <div className="warning" role="status">
                {response.warnings.map((code) => <p key={code}>{message(code)}</p>)}
              </div>
              {!!response.context_evidence?.length && (
                <section className="panel">
                  <h2>Contexto utilizado de tus adjuntos</h2>
                  {response.context_evidence.map((passage, index) => (
                    <article key={index}>
                      <Link href={`/documents/${passage.document_id}?page=${passage.page_number}`}>
                        {passage.filename} · página {passage.page_number}
                      </Link>
                      <p className="passage">{passage.passage}</p>
                    </article>
                  ))}
                </section>
              )}
              {response.private_results?.map((passage, index) => (
                <article className="result-card" key={index}>
                  <h2>{passage.filename} · página {passage.page_number}</h2>
                  <p className="passage">{passage.passage}</p>
                  <div className="reason-box">
                    {passage.retrieval_evidence.map((signal, signalIndex) => (
                      <p key={signalIndex}>
                        {signal.engine === "private_semantic" ? "Similitud semántica de la consulta" : "Recuperación textual"}
                        · posición {signal.rank}
                      </p>
                    ))}
                  </div>
                  {passage.ocr_uncertain && <p className="warning">Texto obtenido mediante OCR; verifica el original.</p>}
                  <Link href={`/documents/${passage.document_id}?page=${passage.page_number}`}>Ver documento original</Link>
                </article>
              ))}
              {response.results.length ? (
                <Results results={response.results} />
              ) : response.private_results?.length ? null : (
                <div className="empty">
                  <Search size={32} />
                  <h2>No se encontraron extractos</h2>
                  <p>Prueba una referencia o una consulta más breve. También puede faltar normativa en el corpus.</p>
                </div>
              )}
            </>
          ) : !busy ? (
            <div className="empty">
              <BookOpen size={36} strokeWidth={1.2} />
              <h2>La evidencia empieza por una pregunta</h2>
              <p>Los resultados incluirán extractos originales, referencias y avisos sobre su vigencia.</p>
            </div>
          ) : null}
        </section>
      </div>
    </>
  );
}
