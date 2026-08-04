"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

const CLE = "tuteur_theme";

/**
 * Applique le thème **avant** le premier rendu.
 *
 * Sans ce script inline, la page s'afficherait en clair pendant un instant
 * avant de basculer en sombre — le « flash blanc » désagréable, et pénible
 * pour qui révise le soir.
 */
export function ThemeScript() {
  const code = `(function(){try{var t=localStorage.getItem('${CLE}');
if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
document.documentElement.dataset.theme=t;}catch(e){}})();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const actuel = (document.documentElement.dataset.theme as "light" | "dark") ?? "light";
    setTheme(actuel);
  }, []);

  function basculer() {
    const suivant = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = suivant;
    localStorage.setItem(CLE, suivant);
    setTheme(suivant);
  }

  return (
    <button
      onClick={basculer}
      className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
      aria-label={theme === "dark" ? "Passer en thème clair" : "Passer en thème sombre"}
      title={theme === "dark" ? "Thème clair" : "Thème sombre"}
    >
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
