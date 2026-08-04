"use client";

/**
 * Gestion du corpus — téléversement, état d'ingestion, réindexation.
 *
 * L'ingestion est asynchrone : un document part en `pending` puis passe à
 * `indexed` ou `failed`. On rafraîchit donc la liste tant qu'il reste un
 * document en cours, plutôt que de laisser l'administrateur recharger la page
 * à la main.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw, Trash2, Upload } from "lucide-react";
import { Bouton, Carte, Chargement, Etiquette, EtatErreur, Info } from "@/components/ui";
import { documents, type Document } from "@/lib/api";

const INTERVALLE_SONDAGE_MS = 2000;

export default function PageDocuments() {
  const [liste, setListe] = useState<Document[] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);
  const champFichier = useRef<HTMLInputElement>(null);

  const charger = useCallback(async () => {
    try {
      setListe(await documents.lister());
      setErreur(null);
    } catch (err) {
      setErreur(err);
    }
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  // Sondage tant qu'une ingestion est en cours — et seulement dans ce cas.
  const enAttente = (liste ?? []).some((d) => d.status === "pending");
  useEffect(() => {
    if (!enAttente) return;
    const id = setInterval(charger, INTERVALLE_SONDAGE_MS);
    return () => clearInterval(id);
  }, [enAttente, charger]);

  async function televerser(e: React.ChangeEvent<HTMLInputElement>) {
    const fichier = e.target.files?.[0];
    if (!fichier) return;
    setEnvoi(true);
    setErreur(null);
    try {
      await documents.televerser(fichier, {});
      await charger();
    } catch (err) {
      setErreur(err);
    } finally {
      setEnvoi(false);
      if (champFichier.current) champFichier.current.value = "";
    }
  }

  async function agir(action: () => Promise<unknown>) {
    setErreur(null);
    try {
      await action();
      await charger();
    } catch (err) {
      setErreur(err);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Carte className="flex flex-wrap items-center gap-3">
        <input
          ref={champFichier}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={televerser}
          disabled={envoi}
          className="hidden"
          id="fichier"
        />
        <label htmlFor="fichier">
          <span className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700">
            <Upload size={16} />
            {envoi ? "Envoi…" : "Téléverser un document"}
          </span>
        </label>
        <span className="text-xs text-slate-500">PDF, DOCX, TXT ou Markdown.</span>
      </Carte>

      {erreur ? <EtatErreur erreur={erreur} onReessayer={charger} /> : null}

      {liste === null && !erreur ? <Chargement /> : null}

      {liste?.length === 0 && (
        <Info>Aucun document dans le corpus. Téléversez-en un pour commencer.</Info>
      )}

      {liste && liste.length > 0 && (
        <Carte className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-left text-xs uppercase text-slate-500 dark:border-slate-700">
              <tr>
                <th className="px-4 py-2">Fichier</th>
                <th className="px-4 py-2">Type</th>
                <th className="px-4 py-2">État</th>
                <th className="px-4 py-2">Ajouté</th>
                <th className="px-4 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {liste.map((doc) => (
                <tr key={doc.id} className="border-b border-slate-100 last:border-0 dark:border-slate-700">
                  <td className="px-4 py-2">
                    <div className="font-medium">{doc.filename}</div>
                    {doc.error && <div className="text-xs text-red-500">{doc.error}</div>}
                  </td>
                  <td className="px-4 py-2 uppercase text-slate-500">{doc.doc_type}</td>
                  <td className="px-4 py-2">
                    <EtatDocument statut={doc.status} />
                  </td>
                  <td className="px-4 py-2 text-slate-500">
                    {new Date(doc.created_at).toLocaleDateString("fr-FR")}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => agir(() => documents.reindexer(doc.id))}
                        title="Réindexer"
                        aria-label={`Réindexer ${doc.filename}`}
                        className="rounded p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                      >
                        <RefreshCw size={15} />
                      </button>
                      <button
                        onClick={() => agir(() => documents.supprimer(doc.id))}
                        title="Supprimer"
                        aria-label={`Supprimer ${doc.filename}`}
                        className="rounded p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Carte>
      )}
    </div>
  );
}

function EtatDocument({ statut }: { statut: string }) {
  if (statut === "indexed") return <Etiquette ton="vert">Indexé</Etiquette>;
  if (statut === "failed") return <Etiquette ton="rouge">Échec</Etiquette>;
  return <Etiquette ton="jaune">En cours…</Etiquette>;
}
