"use client";

/**
 * Tableau de bord — état réel des services.
 *
 * Chaque chiffre affiché ici vient de l'API. Le frontend NURU affichait des
 * constantes (`rag_vectors_count: 2635`) quand l'appel échouait, si bien que
 * trois valeurs différentes circulaient pour la même métrique. Ici, une panne
 * se voit : elle s'affiche comme une erreur, pas comme un chiffre plausible.
 */

import { useCallback, useEffect, useState } from "react";
import { Activity, Database, FileText, Server } from "lucide-react";
import { Carte, Chargement, Etiquette, EtatErreur } from "@/components/ui";
import { documents, sante, type Document, type Health } from "@/lib/api";

export default function PageTableauDeBord() {
  const [etatSante, setEtatSante] = useState<Health | null>(null);
  const [docs, setDocs] = useState<Document[] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [chargement, setChargement] = useState(true);

  const charger = useCallback(() => {
    setChargement(true);
    setErreur(null);
    Promise.all([sante.lire(), documents.lister()])
      .then(([s, d]) => {
        setEtatSante(s);
        setDocs(d);
      })
      .catch(setErreur)
      .finally(() => setChargement(false));
  }, []);

  useEffect(charger, [charger]);

  if (chargement) return <Chargement />;
  if (erreur) return <EtatErreur erreur={erreur} onReessayer={charger} />;
  if (!etatSante || !docs) return null;

  const indexes = docs.filter((d) => d.status === "indexed").length;
  const echecs = docs.filter((d) => d.status === "failed").length;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Tuile Icone={FileText} libelle="Documents" valeur={String(docs.length)} />
      <Tuile Icone={Database} libelle="Indexés" valeur={String(indexes)} />
      <Tuile
        Icone={Activity}
        libelle="En échec"
        valeur={String(echecs)}
        ton={echecs > 0 ? "rouge" : "vert"}
      />
      <Tuile
        Icone={Server}
        libelle="Base de données"
        valeur={etatSante.db ? "OK" : "Injoignable"}
        ton={etatSante.db ? "vert" : "rouge"}
      />

      <Carte className="sm:col-span-2 lg:col-span-4">
        <p className="mb-3 text-sm font-medium">Services</p>
        <div className="flex flex-wrap gap-2">
          <ServiceEtat nom="Qdrant" valeur={etatSante.qdrant} />
          <ServiceEtat nom="Redis" valeur={etatSante.redis} />
          <span className="text-xs text-slate-500">
            Chaîne LLM : {(etatSante.llm ?? []).join(" → ")}
          </span>
        </div>
      </Carte>
    </div>
  );
}

function Tuile({
  Icone,
  libelle,
  valeur,
  ton = "neutre",
}: {
  Icone: React.ComponentType<{ size?: number; className?: string }>;
  libelle: string;
  valeur: string;
  ton?: "neutre" | "vert" | "rouge";
}) {
  const couleur = { neutre: "text-slate-400", vert: "text-emerald-500", rouge: "text-red-500" }[ton];
  return (
    <Carte className="flex items-center gap-3">
      <Icone size={22} className={couleur} />
      <div>
        <p className="text-xs text-slate-500">{libelle}</p>
        <p className="text-lg font-semibold tabular-nums">{valeur}</p>
      </div>
    </Carte>
  );
}

function ServiceEtat({ nom, valeur }: { nom: string; valeur: string }) {
  const ton = valeur === "ok" ? "vert" : valeur === "not_configured" ? "neutre" : "rouge";
  const libelle = valeur === "not_configured" ? "non configuré" : valeur;
  return (
    <Etiquette ton={ton}>
      {nom} : {libelle}
    </Etiquette>
  );
}
