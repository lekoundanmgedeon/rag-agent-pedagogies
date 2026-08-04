"use client";

/**
 * Écran du tuteur — chat **streamé** de bout en bout.
 *
 * Le streaming est l'acquis principal du frontend Vue, absent du frontend NURU :
 * l'élève voit la réponse s'écrire au lieu d'attendre plusieurs secondes devant
 * un écran figé. Le premier événement (`meta`) arrive **avant** le premier mot
 * et porte le niveau d'indice et les sources : on peut donc les afficher
 * immédiatement.
 */

import { useEffect, useRef, useState } from "react";
import { Send, Square } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Markdown } from "@/components/Markdown";
import { Bouton, Carte, Etiquette, EtatErreur } from "@/components/ui";
import { streamerChat, type EvenementChat } from "@/lib/api";

type Meta = {
  hint_level?: number | null;
  hint_label?: string | null;
  sources?: { source_document?: string | null; chapitre?: string | null }[];
};

type Tour = {
  question: string;
  reponse: string;
  meta: Meta | null;
  enCours: boolean;
};

export default function PageTuteur() {
  const [tours, setTours] = useState<Tour[]>([]);
  const [question, setQuestion] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const controleur = useRef<AbortController | null>(null);
  const finDeListe = useRef<HTMLDivElement>(null);

  const enCours = tours.some((t) => t.enCours);

  useEffect(() => {
    finDeListe.current?.scrollIntoView({ behavior: "smooth" });
  }, [tours]);

  async function envoyer(e: React.FormEvent) {
    e.preventDefault();
    const texte = question.trim();
    if (!texte || enCours) return;

    setErreur(null);
    setQuestion("");
    setTours((t) => [...t, { question: texte, reponse: "", meta: null, enCours: true }]);

    const ctrl = new AbortController();
    controleur.current = ctrl;

    const majDernier = (maj: (t: Tour) => Tour) =>
      setTours((tours) => tours.map((t, i) => (i === tours.length - 1 ? maj(t) : t)));

    try {
      for await (const ev of streamerChat(
        { question: texte, conversation_id: conversationId, curriculum_context: {} },
        ctrl.signal,
      )) {
        appliquer(ev, majDernier, setConversationId);
      }
    } catch (err) {
      // Une interruption volontaire n'est pas une erreur à afficher.
      if (!(err instanceof DOMException && err.name === "AbortError")) setErreur(err);
    } finally {
      majDernier((t) => ({ ...t, enCours: false }));
      controleur.current = null;
    }
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-4">
        {tours.length === 0 && (
          <Carte className="text-sm text-slate-600 dark:text-slate-300">
            <p className="mb-2 font-medium text-slate-800 dark:text-slate-100">
              Pose ta question de mathématiques.
            </p>
            <p>
              Le tuteur te guide par indices progressifs plutôt que de donner la
              réponse. Tu peux aussi demander <em>« explique-moi les dérivées »</em>{" "}
              pour un cours, ou <em>« teste-moi »</em> pour un quiz.
            </p>
          </Carte>
        )}

        {tours.map((tour, i) => (
          <div key={i} className="flex flex-col gap-2">
            <div className="self-end rounded-2xl rounded-br-sm bg-emerald-600 px-4 py-2 text-sm text-white">
              {tour.question}
            </div>

            <Carte>
              {tour.meta && <BandeauMeta meta={tour.meta} />}
              {tour.reponse ? (
                <Markdown>{tour.reponse}</Markdown>
              ) : (
                <p className="text-sm text-slate-400">
                  <span className="curseur-frappe">Le tuteur réfléchit</span>
                </p>
              )}
            </Carte>
          </div>
        ))}

        {erreur ? <EtatErreur erreur={erreur} /> : null}
        <div ref={finDeListe} />

        <form onSubmit={envoyer} className="sticky bottom-4 flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ta question…"
            aria-label="Ta question"
            className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:border-emerald-500 dark:border-slate-600 dark:bg-slate-800"
          />
          {enCours ? (
            <Bouton
              type="button"
              variante="secondaire"
              onClick={() => controleur.current?.abort()}
              title="Arrêter la génération"
            >
              <Square size={16} />
            </Bouton>
          ) : (
            <Bouton type="submit" disabled={!question.trim()}>
              <Send size={16} />
            </Bouton>
          )}
        </form>
      </div>
    </AppShell>
  );
}

function appliquer(
  ev: EvenementChat,
  majDernier: (maj: (t: Tour) => Tour) => void,
  setConversationId: (id: string) => void,
) {
  if ("meta" in ev) {
    majDernier((t) => ({ ...t, meta: ev.meta as Meta }));
  } else if ("token" in ev) {
    majDernier((t) => ({ ...t, reponse: t.reponse + ev.token }));
  } else if ("done" in ev) {
    setConversationId(ev.done.conversation_id);
    majDernier((t) => ({ ...t, enCours: false }));
  } else if ("error" in ev) {
    majDernier((t) => ({ ...t, reponse: t.reponse || ev.error, enCours: false }));
  }
}

function BandeauMeta({ meta }: { meta: Meta }) {
  const sources = meta.sources ?? [];
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 border-b border-slate-100 pb-3 dark:border-slate-700">
      {meta.hint_label && <Etiquette ton="vert">{meta.hint_label}</Etiquette>}
      {sources.length > 0 && (
        <span className="text-xs text-slate-500">
          {sources.length} source{sources.length > 1 ? "s" : ""} :{" "}
          {sources
            .slice(0, 3)
            .map((s) => s.chapitre || s.source_document)
            .filter(Boolean)
            .join(" · ")}
        </span>
      )}
    </div>
  );
}
