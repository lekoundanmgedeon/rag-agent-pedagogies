---
niveau: secondaire
classe: Terminale
serie: S1
discipline: Mathématiques
examen_associe: Baccalauréat
source_document: maths_ts1_derivees.md
---

## Compétence : Dériver une fonction et étudier ses variations

L'élève sait calculer la dérivée d'une fonction usuelle, appliquer les règles de
dérivation (somme, produit, quotient, composée) et exploiter le signe de la
dérivée pour dresser le tableau de variations.

Rappels des dérivées de référence :

- $(x^n)' = n\,x^{n-1}$ pour $n \in \mathbb{Z}$
- $(\sqrt{x})' = \dfrac{1}{2\sqrt{x}}$ pour $x > 0$
- $(\ln x)' = \dfrac{1}{x}$ pour $x > 0$
- $(e^x)' = e^x$

Règles de dérivation :

$$ (uv)' = u'v + uv' \qquad \left(\frac{u}{v}\right)' = \frac{u'v - uv'}{v^2} \qquad (v \circ u)' = u' \times (v' \circ u) $$

Le sens de variation se lit sur le signe de $f'$ : si $f'(x) > 0$ sur un
intervalle, alors $f$ y est strictement croissante.

## Chapitre : Fonction dérivée et équation de la tangente

L'équation de la tangente à la courbe de $f$ au point d'abscisse $a$ est :

$$ y = f'(a)\,(x - a) + f(a) $$

Le nombre dérivé $f'(a)$ est le coefficient directeur de cette tangente. Il
correspond à la limite du taux d'accroissement :

$$ f'(a) = \lim_{h \to 0} \frac{f(a+h) - f(a)}{h} $$

### Exercice 1 : Dérivée d'un quotient

**Énoncé.** Soit $f(x) = \dfrac{2x + 1}{x - 3}$ définie sur $\mathbb{R} \setminus \{3\}$.
Calculer $f'(x)$ et étudier son signe.

**Indice.** Pose $u = 2x + 1$ et $v = x - 3$, puis applique la formule du quotient
$\left(\frac{u}{v}\right)' = \dfrac{u'v - uv'}{v^2}$.

**Solution.** On a $u' = 2$ et $v' = 1$, donc :

$$ f'(x) = \frac{2(x-3) - (2x+1)\times 1}{(x-3)^2} = \frac{2x - 6 - 2x - 1}{(x-3)^2} = \frac{-7}{(x-3)^2} $$

Comme $(x-3)^2 > 0$ partout où $f$ est définie, $f'(x) < 0$ : la fonction $f$ est
strictement décroissante sur $]-\infty, 3[$ et sur $]3, +\infty[$.

### Exercice 2 : Tangente et étude de variations

**Énoncé.** Soit $g(x) = x^3 - 3x + 2$. Déterminer l'équation de la tangente à la
courbe de $g$ au point d'abscisse $a = 1$, puis dresser le tableau de variations.

**Indice.** Calcule d'abord $g'(x)$, puis $g'(1)$ et $g(1)$ pour la tangente.
Résous ensuite $g'(x) = 0$ pour le tableau de variations.

**Solution.** $g'(x) = 3x^2 - 3 = 3(x-1)(x+1)$. Au point $a = 1$ : $g'(1) = 0$ et
$g(1) = 0$, donc la tangente a pour équation $y = 0$ (axe des abscisses).

$g'(x) = 0$ pour $x = -1$ ou $x = 1$. Le signe de $g'$ est positif sur
$]-\infty, -1[$, négatif sur $]-1, 1[$ et positif sur $]1, +\infty[$ : $g$ admet un
maximum local en $x = -1$ ($g(-1) = 4$) et un minimum local en $x = 1$ ($g(1) = 0$).
