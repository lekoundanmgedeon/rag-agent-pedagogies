"use client";

/**
 * Journaux de conversation — la trace d'orchestration de chaque réponse.
 *
 * Chaque ligne porte la `trace` du tour : niveau d'indice, sources retenues,
 * outil déclenché, et le détail nœud par nœud. C'est ce qui permet de
 * reconstituer *pourquoi* le tuteur a répondu ainsi, sans relire les logs
 * serveur.
 */

import { useCallback, useEffect, useState } from "react";
import { Bouton, Carte, Chargement, Etiquette, EtatErreur, Info } from "@/components/ui";
import { journaux, type ChatLogEntry } from "@/lib/api";

export default function PageJournaux() {
  const [entrees, setEntrees] = useState<ChatLogEntry[] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [deplie, setDeplie] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    journaux.chat().then(setEntrees).catch(setErreur);
  }, []);

  useEffect(charger, [charger]);

  if (erreur) return <EtatErreur erreur={erreur} onReessayer={charger} />;
  if (entrees === null) return <Chargement />;
  if (entrees.length === 0) return <Info>Aucun échange enregistré pour l&apos;instant.</Info>;

  return (
    <div className="flex flex-col gap-3">
      {entrees.map((e) => {
        const trace = e.trace as Record<string, unknown>;
        const ouvert = deplie === e.message_id;
        return (
          <Carte key={e.message_id} className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Etiquette>{String(trace.hint_label ?? "—")}</Etiquette>
              <span className="text-slate-500">élève {e.student_id}</span>
              <span className="text-slate-400">
                {new Date(e.created_at).toLocaleString("fr-FR")}
              </span>
              {typeof trace.tool_used === "string" && (
                <Etiquette ton="jaune">outil : {trace.tool_used}</Etiquette>
              )}
            </div>

            <Bouton
              variante="secondaire"
              onClick={() => setDeplie(ouvert ? null : e.message_id)}
              className="self-start text-xs"
            >
              {ouvert ? "Masquer la trace" : "Voir la trace"}
            </Bouton>

            {ouvert && (
              <pre className="max-h-96 overflow-auto rounded-lg bg-slate-50 p-3 text-xs dark:bg-slate-900">
                {JSON.stringify(trace, null, 2)}
              </pre>
            )}
          </Carte>
        );
      })}
    </div>
  );
}
