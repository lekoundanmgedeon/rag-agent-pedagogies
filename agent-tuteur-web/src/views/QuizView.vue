<template>
  <AppShell>
    <header class="page-header">
      <h2>🎯 Teste tes connaissances</h2>
      <button class="btn btn-sm" :disabled="loading" @click="generer">
        <span v-if="loading" class="spinner" />{{ sujet ? 'Nouvelle question' : 'Commencer' }}
      </button>
    </header>

    <div class="page-scroll">
      <div class="page-inner">

        <section class="card card-pad reglages">
          <div class="field">
            <label for="quiz-chapitre">Chapitre</label>
            <select
              v-if="chapitres.length"
              id="quiz-chapitre"
              v-model="competence"
              class="select"
              :disabled="loading"
            >
              <option v-for="c in chapitres" :key="c" :value="c">{{ c }}</option>
            </select>
            <input
              v-else
              id="quiz-chapitre"
              v-model="competence"
              class="input"
              placeholder="ex. Suites numériques"
              :disabled="loading"
            />
          </div>

          <div class="field">
            <label for="quiz-type">Type de question</label>
            <select id="quiz-type" v-model="type" class="select" :disabled="loading">
              <option value="qcm">Choix multiple</option>
              <option value="vrai_faux">Vrai ou faux</option>
            </select>
          </div>

          <button class="btn btn-primary" :disabled="loading || !competence" @click="generer">
            <span v-if="loading" class="spinner" />{{ sujet ? 'Nouvelle question' : 'Commencer' }}
          </button>
        </section>

        <p v-if="!chapitres.length && !catalogueCharge" class="muted hint">
          Chargement des chapitres disponibles…
        </p>
        <p v-else-if="!chapitres.length" class="muted hint">
          Aucun chapitre n'est indexé pour ton cadre : saisis toi-même la notion à réviser.
        </p>

        <p v-if="erreur" class="badge badge-error erreur">{{ erreur }}</p>

        <!-- Le modèle n'a rien produit d'exploitable : on le dit, on ne remplit
             pas l'écran d'un QCM factice qui donnerait l'illusion d'un exercice. -->
        <section v-if="sujet && !sujet.available" class="card card-pad indispo">
          <p>{{ sujet.instructions || "Je n'ai pas réussi à préparer une question exploitable sur ce chapitre." }}</p>
          <button class="btn btn-sm" @click="generer">Réessayer</button>
        </section>

        <section v-if="sujet?.available" class="card card-pad question">
          <div class="q-head">
            <span class="badge">{{ sujet.competence }}</span>
            <span class="muted q-type">{{ type === 'qcm' ? 'Choix multiple' : 'Vrai ou faux' }}</span>
          </div>

          <div class="markdown-body enonce" v-html="enonceRendu" />

          <fieldset class="propositions" :disabled="Boolean(correction)">
            <legend class="sr-only">Propositions</legend>
            <label
              v-for="prop in sujet.choices"
              :key="prop.id"
              class="proposition"
              :class="classeProposition(prop.id)"
            >
              <input v-model="choix" type="radio" name="proposition" :value="prop.id" />
              <span class="prop-id">{{ prop.id }}.</span>
              <span class="markdown-body prop-texte" v-html="renderMarkdown(prop.text)" />
              <span v-if="correction && correction.correct_answer === prop.id" class="prop-marque">✓</span>
              <span v-else-if="estMonErreur(prop.id)" class="prop-marque erreur-marque">✕</span>
            </label>
          </fieldset>

          <button
            v-if="!correction"
            class="btn btn-primary valider"
            :disabled="!choix || loading"
            @click="repondre"
          >
            <span v-if="loading" class="spinner" />Valider ma réponse
          </button>

          <div v-else class="correction">
            <div class="corr-head">
              <span class="badge" :class="correction.is_correct ? 'badge-success' : 'badge-error'">
                {{ correction.is_correct ? 'Bonne réponse' : 'Réponse incorrecte' }}
              </span>
              <span v-if="correction.mastery" class="muted maitrise">
                {{ correction.mastery.competence }} — maîtrise
                {{ Math.round(correction.mastery.mastery_score * 100) }} %
                · {{ correction.mastery.attempts }} tentative{{ correction.mastery.attempts > 1 ? 's' : '' }}
              </span>
            </div>

            <div class="markdown-body" v-html="renderMarkdown(correction.explanation)" />

            <div v-if="correction.badges?.length" class="badges-gagnes">
              <span class="badge-icone">🏅</span>
              <span class="badges-titre">
                Nouveau badge{{ correction.badges.length > 1 ? 's' : '' }} :
              </span>
              <span v-for="b in correction.badges" :key="b.code" class="badge badge-warning">
                {{ b.label }}
              </span>
            </div>

            <button class="btn btn-sm suivante" @click="generer">Question suivante</button>
          </div>
        </section>

        <p v-if="!sujet && !loading" class="muted hint">
          Choisis un chapitre et lance-toi : une question à la fois, corrigée immédiatement.
        </p>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
/**
 * Écran de quiz — générer une question, y répondre, voir la correction.
 *
 * Porté du frontend Next.js supprimé le 2026-08-27, avec les deux principes qui
 * venaient du backend et qui font tout l'intérêt de cet écran :
 *
 * 1. **Jamais de questionnaire factice.** Quand l'API répond `available: false`,
 *    le modèle n'a rien produit d'exploitable : on l'annonce et on propose de
 *    réessayer. Afficher un QCM aux propositions « Option 1 / Option 2 » donnerait
 *    l'illusion d'un exercice.
 * 2. **La bonne réponse n'est pas ici.** Elle voyage scellée dans `quiz_token`,
 *    qu'on renvoie tel quel à la correction sans jamais chercher à le lire —
 *    sinon elle serait lisible dans les outils de développement du navigateur.
 *
 * Une différence assumée avec l'écran d'origine : la liste des chapitres n'est
 * plus écrite en dur (« Dérivation, Limites, Probabilités… »). Elle vient de
 * `GET /api/catalogue`, donc du corpus réellement indexé. C'était exactement le
 * défaut du cas QA #28 — proposer à l'élève un sujet que l'agent refusera
 * ensuite, faute de leçon.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { apiErrorMessage, catalogueApi, quizApi } from '@/services/api.js'
import { renderMarkdown } from '@/composables/useMarkdown.js'
import { useChatStore } from '@/stores/chat.js'
import AppShell from '@/components/layout/AppShell.vue'

const chat = useChatStore()

const chapitres = ref([])
const catalogueCharge = ref(false)
const competence = ref('')
const type = ref('qcm')

const loading = ref(false)
const erreur = ref('')
const sujet = ref(null)
const choix = ref(null)
const correction = ref(null)

const enonceRendu = computed(() => (sujet.value?.question ? renderMarkdown(sujet.value.question) : ''))

function classeProposition(id) {
  if (!correction.value) return { choisie: choix.value === id }
  if (correction.value.correct_answer === id) return { bonne: true }
  return { fausse: estMonErreur(id) }
}

/** Vrai pour la proposition que l'élève a cochée, quand elle n'était pas la bonne. */
function estMonErreur(id) {
  return Boolean(correction.value) && choix.value === id && !correction.value.is_correct
}

async function chargerLesChapitres() {
  try {
    const { data } = await catalogueApi.list(chat.curriculumContext())
    chapitres.value = data.chapitres || []
    if (chapitres.value.length && !chapitres.value.includes(competence.value)) {
      competence.value = chapitres.value[0]
    }
  } catch {
    // Catalogue injoignable : on retombe sur la saisie libre plutôt que sur une
    // liste écrite en dur, qui proposerait des chapitres peut-être absents.
    chapitres.value = []
  } finally {
    catalogueCharge.value = true
  }
}

async function generer() {
  if (!competence.value) return
  loading.value = true
  erreur.value = ''
  sujet.value = null
  choix.value = null
  correction.value = null
  try {
    const { data } = await quizApi.generer(competence.value, type.value, chat.curriculumContext())
    sujet.value = data
  } catch (e) {
    erreur.value = apiErrorMessage(e, "La question n'a pas pu être préparée.")
  } finally {
    loading.value = false
  }
}

async function repondre() {
  if (!sujet.value || !choix.value) return
  loading.value = true
  erreur.value = ''
  try {
    // Le jeton est opaque : on le retransmet sans l'interpréter.
    const { data } = await quizApi.repondre(sujet.value.quiz_token, choix.value)
    correction.value = data
  } catch (e) {
    erreur.value = apiErrorMessage(e, "La réponse n'a pas pu être corrigée.")
  } finally {
    loading.value = false
  }
}

onMounted(chargerLesChapitres)
// Le cadre curriculaire filtre le catalogue : en changer doit changer les
// chapitres proposés, sinon on interrogerait l'élève sur une autre série.
watch(() => chat.curriculumContext(), chargerLesChapitres, { deep: true })
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-surface); }
.page-header h2 { font-size: 17px; }
.page-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.page-inner { max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }

.reglages { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 14px; }
.field { display: flex; flex-direction: column; gap: 5px; min-width: 200px; flex: 1; }
.field label { font-size: 12.5px; font-weight: 550; }

.hint { font-size: 13.5px; }
.erreur { align-self: flex-start; }

.indispo { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }

.question { display: flex; flex-direction: column; gap: 16px; }
.q-head { display: flex; align-items: center; gap: 10px; }
.q-type { font-size: 12.5px; }
.enonce { font-size: 15px; }

.propositions { display: flex; flex-direction: column; gap: 8px; border: 0; }
.proposition {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 12px 14px; border: 1px solid var(--border); border-radius: 10px;
  cursor: pointer; transition: border-color .15s var(--ease), background .15s var(--ease);
}
.proposition:hover { border-color: var(--accent); }
.propositions[disabled] .proposition { cursor: default; }
.proposition.choisie { border-color: var(--accent); }
/* Après correction : la bonne réponse est toujours mise en évidence, même quand
   l'élève ne l'a pas choisie — c'est elle qu'il doit retenir. */
.proposition.bonne { border-color: var(--success, #16a34a); background: color-mix(in srgb, var(--success, #16a34a) 10%, transparent); }
.proposition.fausse { border-color: var(--error, #dc2626); background: color-mix(in srgb, var(--error, #dc2626) 10%, transparent); }
.prop-id { font-weight: 600; min-width: 1.2em; }
.prop-texte { flex: 1; }
.prop-marque { font-weight: 700; color: var(--success, #16a34a); }
.prop-marque.erreur-marque { color: var(--error, #dc2626); }

.valider { align-self: flex-start; }
.correction { display: flex; flex-direction: column; gap: 12px; border-top: 1px solid var(--border); padding-top: 16px; }
.corr-head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.maitrise { font-size: 12.5px; }
.badges-gagnes {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding: 12px 14px; border-radius: 10px;
  background: color-mix(in srgb, var(--warning, #d97706) 12%, transparent);
}
.badges-titre { font-size: 13.5px; font-weight: 550; }
.badge-icone { font-size: 17px; }
.suivante { align-self: flex-start; }

.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
</style>
