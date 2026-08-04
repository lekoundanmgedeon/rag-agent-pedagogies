"use client";

/**
 * Rendu du markdown mathématique produit par le tuteur.
 *
 * `remark-math` + `rehype-katex` transforment `$…$` et `$$…$$` en formules
 * lisibles. Sans eux, l'élève verrait du LaTeX brut — inexploitable.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="cours-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
