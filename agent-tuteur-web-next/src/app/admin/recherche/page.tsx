"use client";

/**
 * Recherche dans le corpus — outil de diagnostic.
 *
 * Il sert à répondre à « pourquoi le tuteur a-t-il dit ça ? » en montrant ce
 * que la recherche remonte réellement pour une question donnée, avec les
 * scores. C'est aussi ainsi qu'on repère un chapitre mal indexé.
 */

import { useState } from "react";
import { Search } from "lucide-react";
import { Bouton, Carte, Chargement, Etiquette, EtatErreur, Info } from "@/components/ui";
import { recherche, type SearchResult } from "@/lib/api";

export default function PageRecherche() {
  const [question, setQuestion] = useState("");
  const [resultats, setResultats] = useState<SearchResult[] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [enCours, setEnCours] = useState(false);

  async function lancer(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setEnCours(true);
    setErreur(null);
    try {
      setResultats(await recherche.lancer({ query: question, top_k: 5, curriculum_context: {} }));
    } catch (err) {
      setErreur(err);
      setResultats(null);
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={lancer} className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Question d'élève à tester…"
          aria-label="Question à tester"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
        />
        <Bouton type="submit" disabled={enCours || !question.trim()}>
          <Search size={16} /> Chercher
        </Bouton>
      </form>

      {erreur ? <EtatErreur erreur={erreur} /> : null}
      {enCours ? <Chargement libelle="Recherche…" /> : null}
      {resultats?.length === 0 && (
        <Info>
          Aucun extrait trouvé. Le corpus est peut-être vide, ou le filtre
          curriculaire trop restrictif.
        </Info>
      )}

      {resultats?.map((r, i) => (
        <Carte key={i} className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Etiquette ton="vert">score {r.score.toFixed(3)}</Etiquette>
            {r.metadata?.chapitre ? <Etiquette>{String(r.metadata.chapitre)}</Etiquette> : null}
            {r.metadata?.type_chunk ? (
              <Etiquette>{String(r.metadata.type_chunk)}</Etiquette>
            ) : null}
            {r.metadata?.source_document ? (
              <span className="text-slate-500">{String(r.metadata.source_document)}</span>
            ) : null}
          </div>
          <p className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">
            {r.text}
          </p>
        </Carte>
      ))}
    </div>
  );
}
