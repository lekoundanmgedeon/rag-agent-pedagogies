/**
 * Garde de route — remplace le `beforeEach` de vue-router.
 *
 * Le fichier s'appelle `proxy.ts` (et non `middleware.ts`) : depuis Next 16,
 * c'est la convention, l'ancien nom étant déprécié.
 *
 * Elle évite d'afficher un écran vide à quelqu'un qui n'est pas connecté, et
 * renvoie vers le login en mémorisant la page demandée.
 *
 * ## Ce que cette garde ne fait PAS
 *
 * Elle ne **protège** rien. La seule autorité en matière de droits est l'API :
 * `Depends(get_current_user)`, `require_admin` et `ensure_can_access_student`.
 * Un utilisateur peut contourner ce fichier en une seconde (il tourne dans son
 * navigateur) ; il ne peut rien obtenir de l'API pour autant.
 *
 * C'est une garde de **confort**, pas de sécurité. Confondre les deux est
 * exactement l'erreur qu'avait faite le frontend NURU, dont l'`AuthContext`
 * déduisait le rôle de l'adresse e-mail quand le backend était injoignable :
 *
 * ```ts
 * if (email.includes('admin')) fallbackRole = 'admin';   // NURU — supprimé
 * ```
 *
 * Couper le réseau et se connecter avec `admin@n-importe-quoi.fr` ouvrait
 * l'interface d'administration. Rien de tel ici : sans réponse de l'API, il
 * n'y a pas de connexion.
 */

import { NextResponse, type NextRequest } from "next/server";

const PUBLIQUES = ["/login"];
const RESERVEES_ADMIN = ["/admin"];
const CLE_JETON = "tuteur_token";

/**
 * Lit le rôle inscrit dans le jeton, **sans vérifier la signature**.
 *
 * Vérifier la signature demanderait le secret du serveur, qui n'a rien à faire
 * ici. C'est acceptable précisément parce que cette garde est cosmétique : un
 * jeton falsifié permettrait d'afficher l'écran d'administration, dont tous les
 * appels seraient refusés par l'API.
 */
function roleDuJeton(jeton: string): string | null {
  try {
    const charge = jeton.split(".")[1];
    if (!charge) return null;
    const json = atob(charge.replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json) as { role?: string };
    return claims.role ?? null;
  } catch {
    return null;
  }
}

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (PUBLIQUES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const jeton = req.cookies.get(CLE_JETON)?.value;
  if (!jeton) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }

  if (RESERVEES_ADMIN.some((p) => pathname.startsWith(p)) && roleDuJeton(jeton) !== "admin") {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
}

export const config = {
  // Tout sauf les ressources internes de Next, les fichiers statiques, et les
  // chemins redirigés vers l'API (`/api/*` et `/health`), qui portent leur
  // propre authentification par en-tête.
  //
  // `health` doit impérativement figurer ici : sans lui, la garde interceptait
  // l'appel du tableau de bord et le redirigeait vers le login — l'écran
  // d'administration s'affichait alors en erreur.
  matcher: ["/((?!api|health|_next/static|_next/image|favicon.ico|.*\\.svg).*)"],
};
