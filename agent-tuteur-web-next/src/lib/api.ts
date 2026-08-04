/**
 * Client d'API — **entièrement typé depuis le schéma OpenAPI du backend**.
 *
 * Les types viennent de `src/types/api.d.ts`, généré par `npm run gen:api`.
 * Rien n'est écrit à la main ici : renommer un champ côté API casse la
 * compilation du frontend, au lieu de produire un `undefined` silencieux une
 * fois en production. C'est le mécanisme qui empêche les deux moitiés du
 * projet de re-diverger — voir ADR 0010.
 *
 * ## Règle absolue : aucune donnée inventée
 *
 * Une requête qui échoue lève une {@link ApiError}. On ne renvoie **jamais**
 * de valeur de repli fabriquée. Le frontend NURU faisait l'inverse :
 *
 * ```ts
 * // lib/api.ts (NURU) — à ne surtout pas reproduire
 * try { … } catch { return { total_users: 0, rag_vectors_count: 2635, … } }
 * ```
 *
 * Une panne de l'API s'affichait alors comme des statistiques plausibles mais
 * fausses, impossibles à distinguer de vraies données. Ici, l'appelant reçoit
 * une erreur et affiche un état d'erreur.
 */

import type { components } from "@/types/api";

type S = components["schemas"];

// Types du contrat, réexportés pour que les écrans n'importent qu'un module.
export type Token = S["TokenOut"];
export type User = S["UserOut"];
export type ChatRequest = S["ChatRequest"];
export type Conversation = S["ConversationOut"];
export type Message = S["MessageOut"];
export type Progression = S["ProgressionOut"];
export type Quiz = S["QuizOut"];
export type QuizCorrection = S["QuizCorrectionOut"];
export type QuizAnswerRequest = S["QuizAnswerRequest"];
export type Mastery = S["MasteryOut"];
export type MasteryEntry = S["MasteryEntryOut"];
export type Badge = S["BadgeOut"];
export type EvaluationHistory = S["EvaluationHistoryOut"];
export type Document = S["DocumentOut"];
export type SearchResult = S["SearchResultOut"];
export type ChatLogEntry = S["ChatLogEntry"];
export type Health = S["HealthOut"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const CLE_JETON = "tuteur_token";

export function lireJeton(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CLE_JETON);
}

export function ecrireJeton(jeton: string): void {
  window.localStorage.setItem(CLE_JETON, jeton);
  // Le middleware de Next s'exécute côté serveur et ne voit pas localStorage :
  // le jeton est donc aussi déposé en cookie, pour la garde de route.
  // `SameSite=Strict` empêche qu'il parte vers un autre site.
  document.cookie = `${CLE_JETON}=${jeton}; path=/; SameSite=Strict; max-age=604800`;
}

export function effacerJeton(): void {
  window.localStorage.removeItem(CLE_JETON);
  document.cookie = `${CLE_JETON}=; path=/; SameSite=Strict; max-age=0`;
}

/** Transforme une réponse HTTP en échec en `ApiError` lisible. */
async function versApiError(resp: Response): Promise<ApiError> {
  let detail = `Erreur ${resp.status}`;
  try {
    const corps = await resp.json();
    if (typeof corps?.detail === "string") detail = corps.detail;
  } catch {
    /* corps non-JSON : on garde le message par défaut */
  }
  return new ApiError(detail, resp.status);
}

async function requete<T>(
  chemin: string,
  options: RequestInit & { params?: Record<string, string | undefined> } = {},
): Promise<T> {
  const { params, ...init } = options;
  const url = new URL(chemin, window.location.origin);
  for (const [cle, valeur] of Object.entries(params ?? {})) {
    if (valeur) url.searchParams.set(cle, valeur);
  }

  const entetes = new Headers(init.headers);
  entetes.set("Content-Type", "application/json");
  const jeton = lireJeton();
  if (jeton) entetes.set("Authorization", `Bearer ${jeton}`);

  const resp = await fetch(url, { ...init, headers: entetes });

  if (resp.status === 401) {
    // Jeton expiré ou révoqué : on nettoie et on renvoie au login. Sans cela,
    // l'écran resterait bloqué sur une erreur incompréhensible.
    effacerJeton();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
    throw new ApiError("Session expirée, reconnectez-vous.", 401);
  }
  if (!resp.ok) throw await versApiError(resp);
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

const get = <T,>(chemin: string, params?: Record<string, string | undefined>) =>
  requete<T>(chemin, { method: "GET", params });

const post = <T,>(chemin: string, corps?: unknown) =>
  requete<T>(chemin, { method: "POST", body: corps ? JSON.stringify(corps) : undefined });

const supprimer = <T,>(chemin: string) => requete<T>(chemin, { method: "DELETE" });

// ── Authentification ────────────────────────────────────────────────────────

export const auth = {
  connexion: (email: string, motDePasse: string) =>
    post<Token>("/api/auth/login", { email, password: motDePasse }),
  moi: () => get<User>("/api/auth/me"),
  listerComptes: () => get<User[]>("/api/auth/users"),
  creerCompte: (payload: S["CreateUserRequest"]) => post<User>("/api/auth/users", payload),
};

// ── Chat (streaming) ────────────────────────────────────────────────────────

/** Un événement du flux SSE de `/api/chat`. */
export type EvenementChat =
  | { meta: NonNullable<unknown> }
  | { token: string }
  | { done: { message_id: string; conversation_id: string } }
  | { error: string };

/**
 * Ouvre le flux SSE de `/api/chat` et restitue les événements au fur et à mesure.
 *
 * On utilise `fetch` et non `EventSource` : `EventSource` ne permet pas de
 * porter l'en-tête `Authorization`, or toutes nos routes exigent un jeton.
 * (Même raison que dans le frontend Vue, d'où ce code est porté.)
 */
export async function* streamerChat(
  corps: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<EvenementChat> {
  const entetes = new Headers({
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  });
  const jeton = lireJeton();
  if (jeton) entetes.set("Authorization", `Bearer ${jeton}`);

  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: entetes,
    body: JSON.stringify(corps),
    signal,
  });

  if (!resp.ok || !resp.body) throw await versApiError(resp);

  const lecteur = resp.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  try {
    for (;;) {
      const { done, value } = await lecteur.read();
      if (done) break;
      tampon += decodeur.decode(value, { stream: true });
      const lignes = tampon.split(/\r?\n/);
      // La dernière ligne peut être un fragment incomplet : on la garde pour
      // le tour suivant plutôt que d'essayer de la décoder.
      tampon = lignes.pop() ?? "";
      for (const ligne of lignes) {
        if (!ligne.startsWith("data:")) continue;
        const charge = ligne.slice(5).trim();
        if (!charge) continue;
        try {
          yield JSON.parse(charge) as EvenementChat;
        } catch {
          /* fragment JSON incomplet : ignoré */
        }
      }
    }
  } finally {
    lecteur.releaseLock();
  }
}

// ── Conversations ───────────────────────────────────────────────────────────

export const conversations = {
  lister: (studentId?: string) =>
    get<Conversation[]>("/api/conversations", { student_id: studentId }),
  messages: (id: string) => get<Message[]>(`/api/conversations/${id}/messages`),
  supprimer: (id: string) => supprimer<void>(`/api/conversations/${id}`),
};

export const feedback = {
  envoyer: (messageId: string, valeur: -1 | 1) =>
    post<S["FeedbackOut"]>(`/api/messages/${messageId}/feedback`, { value: valeur }),
};

// ── Domaine pédagogique ─────────────────────────────────────────────────────

export const quiz = {
  generer: (payload: S["QuizRequest"]) => post<Quiz>("/api/quiz", payload),
  repondre: (payload: QuizAnswerRequest) => post<QuizCorrection>("/api/quiz/answer", payload),
};

export const progression = {
  lire: (studentId: string) => get<Progression>(`/api/progression/${studentId}`),
};

export const maitrise = {
  lire: (studentId: string) => get<Mastery>(`/api/mastery/${studentId}`),
};

export const evaluation = {
  historique: (studentId: string) => get<EvaluationHistory>(`/api/evaluation/${studentId}`),
};

// ── Espace administration ───────────────────────────────────────────────────

export const documents = {
  lister: () => get<Document[]>("/api/documents"),
  lire: (id: string) => get<Document>(`/api/documents/${id}`),
  supprimer: (id: string) => supprimer<void>(`/api/documents/${id}`),
  reindexer: (id: string) => post<Document>(`/api/documents/${id}/reindex`),

  /** Téléversement — multipart, donc en dehors du helper JSON. */
  async televerser(fichier: File, metadonnees: Record<string, string>): Promise<S["UploadedDocumentOut"]> {
    const formulaire = new FormData();
    formulaire.append("file", fichier);
    for (const [cle, valeur] of Object.entries(metadonnees)) {
      if (valeur) formulaire.append(cle, valeur);
    }
    const entetes = new Headers();
    const jeton = lireJeton();
    if (jeton) entetes.set("Authorization", `Bearer ${jeton}`);

    const resp = await fetch("/api/documents", {
      method: "POST",
      headers: entetes, // pas de Content-Type : le navigateur pose la frontière multipart
      body: formulaire,
    });
    if (!resp.ok) throw await versApiError(resp);
    return (await resp.json()) as S["UploadedDocumentOut"];
  },
};

export const recherche = {
  lancer: (payload: S["SearchRequest"]) => post<SearchResult[]>("/api/search", payload),
};

export const journaux = {
  chat: () => get<ChatLogEntry[]>("/api/logs/chat"),
};

export const sante = {
  lire: () => get<Health>("/health"),
};
