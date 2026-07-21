#!/usr/bin/env bash
# Ingeste les leçons de `lessons/` dans la stack déployée, via l'API publique.
#
# Les leçons portent leur propre frontmatter YAML (niveau/classe/serie/
# discipline/chapitre) — fusionné automatiquement par `ingestion/pipeline.py`.
# On n'envoie donc AUCUNE métadonnée de formulaire : la renseigner à la main
# risquerait d'écraser le frontmatter avec une série hors taxonomie, ce qui
# casse silencieusement le filtrage RAG (cf. docs/STATUS.md, piège n°4).
#
# Usage :
#   ./scripts/seed-lessons.sh https://tuteur.exemple.sn [tenant]
#   ./scripts/seed-lessons.sh https://tuteur.exemple.sn default --insecure
set -euo pipefail
cd "$(dirname "$0")/.."

API_URL="${1:?Usage: $0 <url-api> [tenant] [--insecure]}"
TENANT="${2:-default}"
CURL_OPTS=()
[ "${3:-}" = "--insecure" ] && CURL_OPTS+=(--insecure)  # certificat auto-signé

LESSONS_DIR="../lessons"
[ -d "$LESSONS_DIR" ] || { echo "Erreur : $LESSONS_DIR introuvable." >&2; exit 1; }

shopt -s nullglob
files=("$LESSONS_DIR"/*.md)
shopt -u nullglob
[ ${#files[@]} -gt 0 ] || { echo "Erreur : aucune leçon .md dans $LESSONS_DIR." >&2; exit 1; }

echo "Upload de ${#files[@]} leçon(s) vers $API_URL (tenant: $TENANT)..."

# Un seul appel multipart pour tous les fichiers : évite de consommer le
# rate limit à l'upload, et couvre le chemin multi-fichiers corrigé dans
# documents.py (ré-application du contexte RLS après chaque commit).
args=()
for f in "${files[@]}"; do args+=(-F "files=@${f}"); done

response=$(curl -sS -f "${CURL_OPTS[@]}" -X POST "$API_URL/api/documents" \
    -H "X-Tenant-Id: $TENANT" "${args[@]}")
echo "$response"

echo
echo "Ingestion asynchrone lancée. Suivi des statuts (Ctrl+C pour arrêter) :"
for _ in $(seq 1 60); do
    listing=$(curl -sS -f "${CURL_OPTS[@]}" "$API_URL/api/documents" -H "X-Tenant-Id: $TENANT")
    pending=$(printf '%s' "$listing" | grep -o '"status":"pending"' | wc -l)
    indexed=$(printf '%s' "$listing" | grep -o '"status":"indexed"' | wc -l)
    failed=$(printf '%s' "$listing" | grep -o '"status":"failed"' | wc -l)
    echo "  indexed=$indexed  pending=$pending  failed=$failed"
    [ "$pending" -eq 0 ] && break
    sleep 5
done

echo
if [ "${failed:-0}" -gt 0 ]; then
    echo "⚠️  $failed document(s) en échec — détail : GET $API_URL/api/documents (champ 'error')."
    exit 1
fi
echo "✅ Corpus prêt : $indexed leçon(s) indexée(s)."
