---
niveau: secondaire
classe: Terminale
serie: T1
discipline: Mathématiques
examen_associe: Baccalauréat
source_document: maths_t1_statistiques.md
---

## Compétence : Calculer les paramètres d'une série statistique

En série technique T1 (nouvelle nomenclature STIDD1), l'élève sait calculer la
moyenne, la variance et l'écart-type d'une série statistique et interpréter ces
paramètres de dispersion.

La moyenne d'une série de valeurs $x_i$ affectées des effectifs $n_i$ est :

$$ \bar{x} = \frac{1}{N} \sum_{i} n_i x_i \qquad \text{avec } N = \sum_i n_i $$

La variance mesure la dispersion autour de la moyenne :

$$ V = \frac{1}{N} \sum_i n_i (x_i - \bar{x})^2 = \frac{1}{N}\sum_i n_i x_i^2 - \bar{x}^2 $$

et l'écart-type est $\sigma = \sqrt{V}$.

### Exercice : Moyenne et écart-type

**Énoncé.** Une machine produit des pièces dont la longueur (en mm) relevée sur un
échantillon donne : $10$ (effectif $2$), $12$ (effectif $5$), $14$ (effectif $3$).
Calculer la moyenne et l'écart-type.

**Indice.** Calcule d'abord $N$, puis $\bar{x} = \frac{1}{N}\sum n_i x_i$. Utilise
ensuite $V = \frac{1}{N}\sum n_i x_i^2 - \bar{x}^2$.

**Solution.** $N = 2 + 5 + 3 = 10$.

$$ \bar{x} = \frac{2\times 10 + 5\times 12 + 3\times 14}{10} = \frac{20 + 60 + 42}{10} = 12{,}2\ \text{mm} $$

$$ V = \frac{2\times 100 + 5\times 144 + 3\times 196}{10} - 12{,}2^2 = \frac{200 + 720 + 588}{10} - 148{,}84 = 150{,}8 - 148{,}84 = 1{,}96 $$

Donc $\sigma = \sqrt{1{,}96} = 1{,}4\ \text{mm}$.
