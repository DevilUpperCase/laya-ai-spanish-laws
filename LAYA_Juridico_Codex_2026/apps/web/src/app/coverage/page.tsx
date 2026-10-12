"use client";

import { useEffect, useState } from "react";
import { useSession } from "@/components/workspace";
import { api, Coverage, safeOfficialUrl } from "@/lib/api";

export default function CoverageView() {
  const session = useSession();
  const [report, setReport] = useState<Coverage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (session) {
      api<Coverage>("/v1/coverage", session)
        .then((result) => {
          if (!cancelled) setReport(result);
        })
        .catch((requestError) => {
          if (!cancelled) setError(requestError.message);
        });
    }
    return () => {
      cancelled = true;
    };
  }, [session]);

  return (
    <>
      <p className="eyebrow">Transparencia del corpus</p>
      <h1>
        Qué tenemos.
        <br />
        <em>Qué falta verificar.</em>
      </h1>
      <p className="lead">Importar un inventario territorial no certifica la cobertura de su normativa.</p>
      {error && <p className="error" role="alert">{error}</p>}

      {report ? (
        <>
          <div className="stats">
            {[
              ["Jurisdicciones inventariadas", report.total_jurisdictions],
              ["Normas importadas", report.legal_instruments],
              ["Versiones de secciones", report.section_versions],
              ["Jurisdicciones verificadas", report.verified_jurisdictions],
            ].map(([label, value]) => (
              <div className="panel stat" key={String(label)}>
                <span className="muted">{label}</span>
                <strong>{Number(value).toLocaleString("es-ES")}</strong>
              </div>
            ))}
          </div>

          <div className="warning">
            <strong>Primer lanzamiento bloqueado</strong>
            <p>Falta verificar la cobertura vigente e histórica de todas las jurisdicciones y completar la evaluación profesional.</p>
            {report.limitations.map((limitation, index) => <p key={index}>{limitation}</p>)}
          </div>

          {report.document_processing?.generated_at && (
            <section className="panel">
              <h2>Comprobación diaria de documentos</h2>
              <p>Informe: {new Date(report.document_processing.generated_at).toLocaleString("es-ES")}</p>
              <p>
                Procesamiento: {report.document_processing.snapshot_processing} · Cobertura nacional: {report.document_processing.national_coverage} ·
                Actualidad: {report.document_processing.freshness}
              </p>
              <p>
                Publicaciones integradas del catálogo capturado: {report.document_processing.integrated_items} ·
                Pasajes de boletines pendientes de índice: {report.document_processing.bulletin_index_pending}
              </p>
            </section>
          )}

          <section className="panel">
            <h2>Fuentes registradas</h2>
            <p className="muted" style={{ marginBottom: 20 }}>
              Un enlace de directorio puede estar pendiente de integración y auditoría.
            </p>
            <div className="table-scroll">
              <table className="source-table">
                <thead>
                  <tr>
                    <th>Fuente oficial</th>
                    <th>Estado de auditoría</th>
                    <th>Última sincronización completa</th>
                  </tr>
                </thead>
                <tbody>
                  {report.sources.map((source) => (
                    <tr key={source.id}>
                      <td>
                        <a href={safeOfficialUrl(source.official_url)} target="_blank" rel="noreferrer">{source.name}</a>
                      </td>
                      <td>{source.audit_status === "verified" ? "Verificada" : "Pendiente"}</td>
                      <td>
                        {source.last_successful_sync
                          ? new Date(source.last_successful_sync).toLocaleString("es-ES")
                          : "Sin evidencia completa"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : (
        !error && <p className="loading" role="status">Consultando la cobertura…</p>
      )}
    </>
  );
}
