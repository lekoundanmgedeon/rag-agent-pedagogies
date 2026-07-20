---
niveau: secondaire
classe: Terminale
serie: S1
serie_alias: [S1, S3]
discipline: Mathématiques
chapitre: Les Fonctions Numériques
examen_associe: Baccalauréat
source_document: Lecon_11_Fonctions_Numeriques_TS1S3.md
---

# Leçon — Les Fonctions Numériques (Terminale S1/S3)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Les Fonctions Numériques : Limites, Continuité, Dérivation |
| **Classe** | Terminale |
| **Série** | S1 / S3 |
| **Chapitre** | Analyse |
| **Sous-chapitre** | Continuité, théorème des valeurs intermédiaires, fonction réciproque, dérivation de fonctions composées, théorème des accroissements finis, étude de fonctions usuelles |
| **Prérequis** | Dérivation de base (Première), limites, continuité intuitive, fonctions usuelles (polynômes, rationnelles) |
| **Durée estimée** | 12 heures |
| **Compétences visées** | Utiliser le théorème des valeurs intermédiaires ; justifier l'existence et la continuité d'une fonction réciproque ; dériver une fonction composée ; utiliser le théorème et l'inégalité des accroissements finis ; étudier des fonctions faisant intervenir ln, exp, fonctions puissances |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) déterminer l'image d'un intervalle par une fonction continue, (2) justifier l'existence d'une fonction réciproque et la représenter, (3) dériver des fonctions composées complexes, (4) utiliser le théorème des accroissements finis, (5) étudier complètement une fonction usuelle ou composée |
| **Mots-clés** | continuité, théorème des valeurs intermédiaires, fonction réciproque, dérivée composée, accroissements finis, croissances comparées |

---

## 2. Introduction

L'étude des fonctions numériques constitue le cœur du programme d'analyse de Terminale S1/S3. Ce chapitre consolide et approfondit les notions de continuité et de dérivation vues en Première, avec une exigence de rigueur accrue : théorème des valeurs intermédiaires, existence et continuité d'une fonction réciproque, dérivation de fonctions composées, théorème des accroissements finis.

Ces outils permettent de résoudre des problèmes concrets : encadrement de solutions d'équations non résolubles algébriquement, étude complète de fonctions complexes (composées de logarithme, exponentielle, puissances), et préparent directement le calcul intégral et les équations différentielles.

Au Baccalauréat S1/S3, l'étude de fonctions est **l'exercice le plus systématiquement présent**, généralement le plus long du sujet, combinant limites, dérivation, tableau de variations, tracé de courbe, et parfois lien avec une suite ou une intégrale.

**Applications concrètes** : modélisation de phénomènes physiques continus, recherche de valeurs approchées de solutions (méthode de dichotomie basée sur le théorème des valeurs intermédiaires), optimisation.

---

## 3. Définitions

**Définition 1 (Continuité en un point, sur un intervalle — rappel).** \( f \) est continue en \( x_0 \) si \( f(x_0) \) existe et \( \displaystyle\lim_{x\to x_0}f(x)=f(x_0) \). \( f \) est continue sur un intervalle \( I \) si elle est continue en tout point de \( I \).

**Définition 2 (Prolongement par continuité).** Si \( f \) n'est pas définie en \( x_0 \) mais que \( \displaystyle\lim_{x\to x_0}f(x)=L \) existe (finie), on définit le prolongement par continuité \( \tilde f \) de \( f \) en posant \( \tilde f(x_0)=L \) et \( \tilde f(x)=f(x) \) ailleurs.

**Définition 3 (Fonction réciproque).** Si \( f:I\to J \) est une bijection, sa réciproque \( f^{-1}:J\to I \) est l'unique fonction telle que \( f^{-1}(f(x))=x \) pour \( x\in I \) et \( f(f^{-1}(y))=y \) pour \( y\in J \).

**Définition 4 (Dérivée d'une fonction composée).** Si \( u \) est dérivable en \( x \) et \( v \) dérivable en \( u(x) \), alors \( v\circ u \) est dérivable en \( x \), de dérivée \( (v\circ u)'(x)=u'(x)\times v'(u(x)) \).

**Définition 5 (Point d'inflexion).** La courbe de \( f \) admet un point d'inflexion d'abscisse \( x_0 \) si elle traverse sa tangente en ce point.

---

## 4. Théorèmes

**Théorème 1 (Théorème des valeurs intermédiaires — admis).**
- Énoncé : si \( f \) est continue sur \( [a,b] \), alors pour tout réel \( k \) compris entre \( f(a) \) et \( f(b) \), il existe au moins un \( c\in[a,b] \) tel que \( f(c)=k \).
- Cas particulier (recherche de zéro) : si \( f(a) \) et \( f(b) \) sont de signes contraires, il existe \( c\in]a,b[ \) tel que \( f(c)=0 \).
- Corollaire : si de plus \( f \) est strictement monotone sur \( [a,b] \), ce \( c \) est unique.

**Théorème 2 (Fonction réciproque d'une fonction continue strictement monotone — admis).**
- Énoncé : si \( f \) est continue et strictement monotone sur un intervalle \( I \), alors \( f \) réalise une bijection de \( I \) sur \( f(I) \), et sa réciproque \( f^{-1} \) est continue et de même sens de variation que \( f \).
- Représentation graphique : la courbe de \( f^{-1} \) est symétrique de celle de \( f \) par rapport à la droite \( y=x \).

**Théorème 3 (Dérivée de la fonction réciproque).**
- Énoncé : si \( f \) est dérivable et strictement monotone sur \( I \), de dérivée ne s'annulant pas, alors \( f^{-1} \) est dérivable sur \( f(I) \) et
$$ (f^{-1})'(y) = \frac1{f'(f^{-1}(y))}. $$

**Théorème 4 (Limite d'une fonction composée).**
- Énoncé : soient \( a,b,\ell \) (finis ou infinis). Si \( \displaystyle\lim_{x\to a}f(x)=b \) et \( \displaystyle\lim_{y\to b}g(y)=\ell \), alors \( \displaystyle\lim_{x\to a}g(f(x))=\ell \).

**Théorème 5 (Théorème des accroissements finis — admis).**
- Énoncé : si \( f \) est continue sur \( [a,b] \) et dérivable sur \( ]a,b[ \), il existe \( c\in]a,b[ \) tel que
$$ f'(c) = \frac{f(b)-f(a)}{b-a}. $$

**Théorème 6 (Inégalité des accroissements finis).**
- Énoncé : si \( f \) est dérivable sur \( I \) et si \( m\le f'(x)\le M \) pour tout \( x\in I \), alors pour tous \( a,b\in I \) avec \( a<b \) :
$$ m(b-a) \le f(b)-f(a) \le M(b-a). $$
- Cas particulier : si \( |f'(x)|\le M \) sur \( I \), alors \( |f(b)-f(a)|\le M|b-a| \).

**Théorème 7 (Théorème du prolongement de la dérivée).**
- Énoncé : si \( f \) est continue sur \( [a,b] \) et dérivable sur \( ]a,b[ \), et si \( \displaystyle\lim_{x\to a}f'(x)=\ell \) (finie), alors \( f \) est dérivable à droite en \( a \) et \( f'_d(a)=\ell \).

**Théorème 8 (Point d'inflexion).**
- Énoncé : si \( f \) est deux fois dérivable sur un intervalle ouvert \( I \) contenant \( x_0 \), et si \( f'' \) s'annule en changeant de signe en \( x_0 \), alors le point d'abscisse \( x_0 \) de la courbe de \( f \) est un point d'inflexion.

**Théorème 9 (Limites usuelles de croissances comparées).**
- Énoncé : pour \( \alpha \) rationnel strictement positif :
$$ \lim_{x\to+\infty}\frac{e^x}{x^\alpha}=+\infty,\quad \lim_{x\to+\infty}x^\alpha e^{-x}=0,\quad \lim_{x\to+\infty}\frac{\ln x}{x^\alpha}=0,\quad \lim_{x\to0^+}x^\alpha\ln x=0. $$

---

## 5. Propriétés

1. L'image d'un intervalle fermé borné (segment) par une fonction continue est un intervalle fermé borné.
2. Si \( f \) est continue sur \( [a,b] \) et si \( f(a)\times f(b)<0 \), alors l'équation \( f(x)=0 \) admet au moins une solution dans \( ]a,b[ \) (cas particulier direct du TVI).
3. La composée de deux fonctions continues est continue.
4. Pour les fonctions du type \( f^a \) avec \( a\in\mathbb Q \), les règles de dérivation habituelles s'appliquent : \( (u^a)'=au'u^{a-1} \) (sous réserve de définition).

---

## 6. Démonstrations

**Démonstration (esquisse) du théorème 3 (dérivée de la fonction réciproque)** :
En posant \( y=f(x) \), donc \( x=f^{-1}(y) \), et en dérivant l'identité \( f(f^{-1}(y))=y \) par rapport à \( y \) (via la formule de dérivation d'une composée) :
$$ (f^{-1})'(y)\times f'(f^{-1}(y)) = 1 \quad\Longrightarrow\quad (f^{-1})'(y)=\frac1{f'(f^{-1}(y))}, $$
sous réserve que \( f'(f^{-1}(y))\neq0 \).

**Démonstration (esquisse) du théorème 6, à partir du théorème 5 (accroissements finis)** :
Par le théorème 5, il existe \( c\in]a,b[ \) tel que \( f'(c)=\dfrac{f(b)-f(a)}{b-a} \). Comme \( m\le f'(c)\le M \) par hypothèse, on obtient directement \( m\le\dfrac{f(b)-f(a)}{b-a}\le M \), soit, en multipliant par \( (b-a)>0 \) : \( m(b-a)\le f(b)-f(a)\le M(b-a) \).

**Illustration du théorème 8 (point d'inflexion)** :
Pour \( f(x)=x^3 \), \( f''(x)=6x \), qui s'annule en changeant de signe en \( x=0 \) (négatif pour \( x<0 \), positif pour \( x>0 \)) : le point \( (0,0) \) est donc un point d'inflexion de la courbe de \( f \), ce que l'on peut vérifier visuellement (la courbe traverse sa tangente horizontale en ce point).

---

## 7. Méthodes

**Méthode 1 — Encadrer une solution d'équation par le TVI**
1. Vérifier la continuité de \( f \) sur l'intervalle considéré.
2. Calculer \( f(a) \) et \( f(b) \), vérifier qu'ils sont de signes contraires (ou encadrent \( k \)).
3. Conclure à l'existence d'une solution ; pour l'unicité, ajouter la stricte monotonie.
4. Affiner l'encadrement par dichotomie si demandé.

**Méthode 2 — Dériver une fonction composée complexe**
1. Décomposer la fonction en fonctions élémentaires successives.
2. Appliquer la formule \( (v\circ u)'=u'\times(v'\circ u) \) en partant de l'extérieur.
3. Simplifier l'expression obtenue.

**Méthode 3 — Étudier une fonction faisant intervenir ln, exp, ou puissance**
1. Déterminer l'ensemble de définition.
2. Calculer les limites aux bornes (utiliser les croissances comparées si nécessaire).
3. Calculer la dérivée, étudier son signe, dresser le tableau de variations.
4. Étudier les branches infinies (asymptotes) et, si demandé, les points d'inflexion.
5. Tracer la courbe.

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Montrer que l'équation \( x^3-3x+1=0 \) admet une solution dans \( ]0,1[ \).
*Résolution :* \( f(x)=x^3-3x+1 \) est continue sur \( \mathbb R \) (fonction polynôme). \( f(0)=1>0 \) ; \( f(1)=1-3+1=-1<0 \). Comme \( f(0) \) et \( f(1) \) sont de signes contraires, le théorème des valeurs intermédiaires garantit l'existence d'un \( c\in]0,1[ \) tel que \( f(c)=0 \).
*Conclusion :* L'équation admet bien une solution dans \( ]0,1[ \).

**Exemple 2.**
*Énoncé :* Calculer la dérivée de \( f(x)=\sqrt{\ln(x^2+1)} \).
*Résolution :* On décompose : \( f=w\circ v\circ u \) avec \( u(x)=x^2+1 \), \( v(t)=\ln t \), \( w(s)=\sqrt s \). \( u'(x)=2x \) ; \( (v\circ u)'(x)=\dfrac{2x}{x^2+1} \) ; \( f'(x)=\dfrac{(v\circ u)'(x)}{2\sqrt{(v\circ u)(x)}}=\dfrac{2x/(x^2+1)}{2\sqrt{\ln(x^2+1)}}=\dfrac{x}{(x^2+1)\sqrt{\ln(x^2+1)}} \).
*Conclusion :* \( f'(x)=\dfrac{x}{(x^2+1)\sqrt{\ln(x^2+1)}} \), définie pour \( x^2+1>1 \), soit \( x\neq0 \).

**Exemple 3.**
*Énoncé :* Soit \( f(x)=x-\ln x \) sur \( ]0,+\infty[ \). Montrer que \( f \) réalise une bijection de \( ]0,1] \) sur un intervalle à préciser, et étudier sa réciproque.
*Résolution :* \( f'(x)=1-\dfrac1x \), négative sur \( ]0,1[ \) (car \( \frac1x>1 \)), nulle en \( x=1 \) : \( f \) est strictement décroissante sur \( ]0,1] \). \( \displaystyle\lim_{x\to0^+}f(x)=+\infty \) (car \( -\ln x\to+\infty \)), \( f(1)=1 \). Donc \( f \) réalise une bijection de \( ]0,1] \) sur \( [1,+\infty[ \).
*Conclusion :* \( f^{-1} \) existe, est continue et strictement décroissante sur \( [1,+\infty[ \), à valeurs dans \( ]0,1] \), et sa courbe est symétrique de celle de \( f \) par rapport à la droite \( y=x \).

**Exemple 4.**
*Énoncé :* Calculer \( \displaystyle\lim_{x\to+\infty}\big(x^2e^{-x}\big) \) et \( \displaystyle\lim_{x\to0^+}\big(x\ln x\big) \).
*Résolution :* Par le théorème 9 (croissances comparées) : \( \displaystyle\lim_{x\to+\infty}x^2e^{-x}=0 \) directement. Pour la seconde : \( \displaystyle\lim_{x\to0^+}x\ln x=0 \) (cas \( \alpha=1 \) de \( \displaystyle\lim_{x\to0^+}x^\alpha\ln x=0 \)).
*Conclusion :* Les deux limites valent 0.

**Exemple 5.**
*Énoncé :* Appliquer le théorème des accroissements finis à \( f(x)=\sqrt x \) sur \( [1,4] \), et interpréter géométriquement.
*Résolution :* \( f \) est continue sur \( [1,4] \), dérivable sur \( ]1,4[ \), \( f'(x)=\dfrac1{2\sqrt x} \). Par le théorème 5, il existe \( c\in]1,4[ \) tel que \( f'(c)=\dfrac{f(4)-f(1)}{4-1}=\dfrac{2-1}3=\dfrac13 \). On résout : \( \dfrac1{2\sqrt c}=\dfrac13\Rightarrow\sqrt c=\dfrac32\Rightarrow c=\dfrac94 \).
*Conclusion :* \( c=\dfrac94\in]1,4[ \) ✓. Géométriquement, la tangente en \( c \) est parallèle à la corde reliant les points d'abscisses 1 et 4 sur la courbe de \( f \).

---

## 9. Erreurs fréquentes

- **Oublier de vérifier la continuité ET la stricte monotonie** avant d'affirmer l'unicité de la solution donnée par le TVI (la continuité seule ne donne que l'existence).
- **Erreur dans la dérivation d'une fonction composée à plusieurs étages** : oublier un facteur en « oubliant » une des fonctions intermédiaires dans la chaîne de composition.
- **Confondre le TAF (théorème des accroissements finis, donnant l'existence d'un \( c \) précis)** avec l'inégalité des accroissements finis (donnant un encadrement sans identifier \( c \)) : ce sont deux outils différents, à ne pas confondre dans la rédaction.
- **Utiliser les croissances comparées sans vérifier la forme exacte** de la limite demandée (bien identifier si c'est \( x\to+\infty \) ou \( x\to0^+ \), le signe de l'exposant, etc.).
- **Oublier de préciser l'ensemble de départ et d'arrivée** lors de la construction d'une fonction réciproque.

---

## 10. Astuces

- **Astuce de calcul** : pour dériver une composée à plusieurs étages, travailler « de l'extérieur vers l'intérieur » et écrire chaque étape intermédiaire au brouillon avant de combiner.
- **Astuce de rédaction** : pour utiliser le TVI, toujours présenter les trois éléments dans l'ordre : continuité, valeurs aux bornes de signes contraires (ou encadrant \( k \)), conclusion sur l'existence (et la stricte monotonie pour l'unicité).
- **Astuce pour le Bac** : pour une limite de la forme \( x^\alpha e^{-x} \) ou \( \dfrac{\ln x}{x^\alpha} \), toujours essayer de se ramener directement à une des quatre limites usuelles du théorème 9 par un simple changement d'écriture, plutôt que de refaire un calcul complet.
- **Astuce de calcul** : pour la fonction réciproque, retenir que sa courbe s'obtient par symétrie par rapport à la droite \( y=x \) — un excellent moyen de vérifier un tracé.

---

## 11. Exercices

### Faciles
1. Montrer que \( f(x)=x^3-2x-5 \) s'annule dans \( ]2,3[ \).
2. Calculer \( \displaystyle\lim_{x\to+\infty}\frac{e^x}{x^3} \).
3. Calculer \( \displaystyle\lim_{x\to0^+}x^2\ln x \).
4. Dériver \( f(x)=(3x^2+1)^5 \).
5. Dériver \( f(x)=\sqrt{2x+1} \).

### Moyens
6. Montrer que \( f(x)=x^5+x-1 \) réalise une bijection de \( \mathbb R \) sur \( \mathbb R \) et encadrer d'amplitude \( 0{,}1 \) la solution de \( f(x)=0 \).
7. Dériver \( f(x)=\ln\left(\dfrac{x+1}{x-1}\right) \).
8. Soit \( f(x)=e^x-x-1 \). Étudier son sens de variation et en déduire le signe de \( f \) sur \( \mathbb R \).
9. Appliquer le théorème des accroissements finis à \( f(x)=x^2 \) sur \( [0,2] \) et déterminer la valeur exacte de \( c \).
10. Calculer \( \displaystyle\lim_{x\to+\infty}\dfrac{\ln(x^2+1)}{x} \).

### Difficiles
11. Soit \( f(x)=x-\sin x \). Montrer que \( f \) est croissante sur \( \mathbb R \) et en déduire le signe de \( x-\sin x \) selon le signe de \( x \).
12. En utilisant l'inégalité des accroissements finis appliquée à \( f(x)=\ln x \) sur \( [n,n+1] \), montrer que \( \dfrac1{n+1}\le\ln(n+1)-\ln n\le\dfrac1n \) pour tout entier \( n\ge1 \).
13. Soit \( f(x)=\dfrac{\ln x}x \) sur \( ]0,+\infty[ \). Étudier ses variations, montrer qu'elle admet un maximum, et déterminer son point d'inflexion.
14. Montrer que l'équation \( \ln x=x-2 \) admet exactement deux solutions sur \( ]0,+\infty[ \) (étudier \( f(x)=\ln x-x+2 \)).
15. Soit \( f(x)=x^2e^{-x} \) sur \( \mathbb R \). Étudier complètement \( f \) (limites, dérivée, tableau de variations, points d'inflexion), en utilisant les croissances comparées pour les limites en \( +\infty \).

---

## 12. Corrigés détaillés

**1.** \( f(2)=8-4-5=-1<0 \) ; \( f(3)=27-6-5=16>0 \). Signes contraires, \( f \) continue : par le TVI, \( f \) s'annule dans \( ]2,3[ \).

**2.** Par croissances comparées, \( \dfrac{e^x}{x^3}\to+\infty \).

**3.** Par croissances comparées (\( \alpha=2 \)), \( x^2\ln x=x\times(x\ln x)\to0\times0=0 \) (ou directement via le cas \( \alpha=2 \) de la limite usuelle).

**4.** \( f'(x)=5\times6x\times(3x^2+1)^4=30x(3x^2+1)^4 \).

**5.** \( f'(x)=\dfrac2{2\sqrt{2x+1}}=\dfrac1{\sqrt{2x+1}} \).

**6.** \( f'(x)=5x^4+1>0 \) pour tout \( x \) : \( f \) strictement croissante sur \( \mathbb R \), continue, avec \( \lim_{-\infty}f=-\infty \) et \( \lim_{+\infty}f=+\infty \) : bijection de \( \mathbb R \) sur \( \mathbb R \). \( f(0)=-1<0 \), \( f(1)=1>0 \) : solution dans \( ]0,1[ \). \( f(0{,}7)\approx0{,7^5+0{,}7-1}\approx0{,}168+0{,}7-1=-0{,}132<0 \) ; \( f(0{,}8)\approx0{,}328+0{,}8-1=0{,}128>0 \) : solution dans \( ]0{,}7;\ 0{,}8[ \), encadrement d'amplitude 0,1.

**7.** \( f(x)=\ln(x+1)-\ln(x-1) \) ; \( f'(x)=\dfrac1{x+1}-\dfrac1{x-1}=\dfrac{(x-1)-(x+1)}{(x+1)(x-1)}=\dfrac{-2}{x^2-1} \).

**8.** \( f'(x)=e^x-1 \), négative pour \( x<0 \), positive pour \( x>0 \), nulle en \( x=0 \) : \( f \) décroît puis croît, minimum en \( x=0 \) avec \( f(0)=1-0-1=0 \). Donc \( f(x)\ge0 \) pour tout \( x \), c'est-à-dire \( e^x\ge x+1 \) pour tout réel \( x \).

**9.** \( f'(x)=2x \) ; \( \dfrac{f(2)-f(0)}{2-0}=\dfrac{4-0}2=2 \) ; \( 2c=2\Rightarrow c=1\in]0,2[ \) ✓.

**10.** \( \dfrac{\ln(x^2+1)}x \sim \dfrac{\ln(x^2)}x=\dfrac{2\ln x}x\to0 \) par croissances comparées.

**11.** \( f'(x)=1-\cos x\ge0 \) pour tout \( x \) (car \( \cos x\le1 \)), avec égalité seulement en des points isolés : \( f \) est croissante sur \( \mathbb R \). Comme \( f(0)=0 \), pour \( x>0 \), \( f(x)\ge f(0)=0 \), soit \( x\ge\sin x \) ; pour \( x<0 \), \( f(x)\le f(0)=0 \), soit \( x\le\sin x \).

**12.** \( f(x)=\ln x \), \( f'(x)=\dfrac1x \), décroissante. Sur \( [n,n+1] \), \( f'(x)\in\left[\dfrac1{n+1},\dfrac1n\right] \) (car \( f' \) décroissante). Par l'inégalité des accroissements finis : \( \dfrac1{n+1}\times1\le f(n+1)-f(n)\le\dfrac1n\times1 \), soit \( \dfrac1{n+1}\le\ln(n+1)-\ln n\le\dfrac1n \).

**13.** \( f'(x)=\dfrac{1-\ln x}{x^2} \), positive pour \( x<e \), négative pour \( x>e \), nulle en \( x=e \) : maximum en \( x=e \), \( f(e)=\dfrac1e \). \( f''(x) \) (calcul) change de signe en \( x=e^{3/2} \) (point où \( 2\ln x-3=0 \)), qui est le point d'inflexion.

**14.** \( f(x)=\ln x-x+2 \) ; \( f'(x)=\dfrac1x-1 \), positive sur \( ]0,1[ \), négative sur \( ]1,+\infty[ \) : maximum en \( x=1 \), \( f(1)=0-1+2=1>0 \). \( \lim_{x\to0^+}f(x)=-\infty \) ; \( \lim_{x\to+\infty}f(x)=-\infty \) (car \( -x \) l'emporte sur \( \ln x \)). Comme \( f \) croît de \( -\infty \) à \( 1>0 \) sur \( ]0,1] \), puis décroît de \( 1 \) à \( -\infty \) sur \( [1,+\infty[ \), par le TVI appliqué sur chaque intervalle de monotonie, il existe exactement une solution sur \( ]0,1[ \) et une sur \( ]1,+\infty[ \) : deux solutions au total.

**15.** \( \mathrm{Df}=\mathbb R \). \( \lim_{-\infty}f=+\infty \) (car \( x^2\to+\infty \) et \( e^{-x}\to+\infty \)) ; \( \lim_{+\infty}f=0 \) (croissances comparées, théorème 9). \( f'(x)=2xe^{-x}-x^2e^{-x}=xe^{-x}(2-x) \), du signe de \( x(2-x) \) : négative sur \( ]-\infty,0[ \), positive sur \( ]0,2[ \), négative sur \( ]2,+\infty[ \). Minimum local en \( x=0 \) (\( f(0)=0 \)), maximum local en \( x=2 \) (\( f(2)=4e^{-2} \)). L'axe des abscisses (\( y=0 \)) est asymptote horizontale en \( +\infty \). Points d'inflexion : étude de \( f'' \) (calcul supplémentaire, hors détail ici) donnant deux points d'inflexion de part et d'autre du maximum.

---

## 13. Questions type Bac

1. *(Type Bac)* Soit \( f(x)=xe^{-x}+1 \) sur \( \mathbb R \). (a) Étudier les limites de \( f \) en \( -\infty \) et \( +\infty \). (b) Étudier les variations de \( f \) et dresser son tableau de variations. (c) Montrer que l'équation \( f(x)=0 \) admet une unique solution sur \( \mathbb R \) et donner un encadrement d'amplitude \( 0{,}1 \).
2. *(Type Bac)* Soit \( f(x)=\ln(x^2-1) \). (a) Déterminer l'ensemble de définition de \( f \). (b) Calculer \( f'(x) \). (c) Étudier les branches infinies de \( f \).
3. *(Type Bac)* Soit \( f:x\mapsto2x^3-3x^2-12x+5 \) sur \( \mathbb R \). Montrer que \( f \) admet exactly trois zéros distincts en utilisant le théorème des valeurs intermédiaires sur des intervalles bien choisis.

---

## 14. Résumé

Le théorème des valeurs intermédiaires garantit l'existence (et, avec monotonie stricte, l'unicité) d'une solution à \( f(x)=k \) sur un intervalle où \( f \) est continue et prend des valeurs de part et d'autre de \( k \). Une fonction continue et strictement monotone sur un intervalle réalise une bijection, dont la réciproque est continue, de même monotonie, et représentée par symétrie par rapport à \( y=x \) ; sa dérivée se calcule par \( (f^{-1})'(y)=\dfrac1{f'(f^{-1}(y))} \). La dérivation de fonctions composées à plusieurs étages se fait « de l'extérieur vers l'intérieur ». Le théorème des accroissements finis garantit l'existence d'un point où la tangente est parallèle à une corde ; son corollaire, l'inégalité des accroissements finis, permet d'encadrer des variations de fonctions sans identifier ce point précisément. Enfin, les limites usuelles de croissances comparées (exponentielle contre puissance, logarithme contre puissance) permettent de lever de nombreuses formes indéterminées dans l'étude de fonctions faisant intervenir \( \ln \) et \( \exp \).

---

## 15. Fiche de révision

- TVI : \( f \) continue sur \( [a,b] \), \( f(a) \) et \( f(b) \) de signes contraires \( \Rightarrow \exists c,\ f(c)=0 \) (unique si \( f \) strictement monotone)
- \( f \) continue et strictement monotone sur \( I \) \( \Rightarrow \) bijective de \( I \) sur \( f(I) \), \( f^{-1} \) continue, même monotonie
- \( (f^{-1})'(y)=\dfrac1{f'(f^{-1}(y))} \)
- \( (v\circ u)'=u'\times(v'\circ u) \)
- TAF : \( \exists c\in]a,b[,\ f'(c)=\dfrac{f(b)-f(a)}{b-a} \)
- Inégalité des AF : \( m\le f'\le M \) sur \( I\Rightarrow m(b-a)\le f(b)-f(a)\le M(b-a) \)
- Croissances comparées : \( \dfrac{e^x}{x^\alpha}\to+\infty \) ; \( x^\alpha e^{-x}\to0 \) ; \( \dfrac{\ln x}{x^\alpha}\to0 \) ; \( x^\alpha\ln x\to0\ (x\to0^+) \)

---

## 16. Glossaire

- **Théorème des valeurs intermédiaires (TVI)** : garantit l'existence d'un antécédent d'une valeur intermédiaire par une fonction continue.
- **Fonction réciproque** : fonction inverse d'une bijection.
- **Théorème des accroissements finis (TAF)** : garantit l'existence d'un point où la tangente est parallèle à une corde.
- **Inégalité des accroissements finis** : encadrement des variations d'une fonction à partir d'un encadrement de sa dérivée.
- **Croissances comparées** : hiérarchie des vitesses de croissance entre exponentielle, puissance et logarithme.
- **Point d'inflexion** : point où la courbe traverse sa tangente.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : dérivation de base (Première), limites et continuité intuitives, fonctions logarithme et exponentielle (introduites en parallèle).

**Ce qui sera utilisé ensuite** : calcul intégral (primitives liées aux fonctions étudiées), équations différentielles, géométrie plane et courbes paramétrées (étude de fonctions vectorielles).

---

## 18. Auto-évaluation

### QCM
1. Le théorème des valeurs intermédiaires nécessite que la fonction soit :
 a) dérivable b) continue c) bijective d) croissante uniquement

2. La dérivée de la fonction réciproque \( f^{-1} \) en \( y \) est :
 a) \( f'(y) \) b) \( \dfrac1{f'(y)} \) c) \( \dfrac1{f'(f^{-1}(y))} \) d) \( f(f^{-1}(y)) \)

3. \( \displaystyle\lim_{x\to+\infty}x^2e^{-x} \) vaut :
 a) \( +\infty \) b) 0 c) 1 d) indéterminé

### Vrai/Faux
1. Le TVI garantit toujours l'unicité de la solution. (Faux — il faut la stricte monotonie en plus)
2. La courbe de \( f^{-1} \) est symétrique de celle de \( f \) par rapport à la droite \( y=x \). (Vrai)
3. Le théorème des accroissements finis identifie précisément la valeur de \( c \) dans tous les cas. (Faux — il garantit seulement son existence, sauf calcul explicite possible)

### Questions ouvertes
1. Expliquer la différence entre le théorème des accroissements finis et son inégalité associée, et donner un exemple d'usage de chacun.
2. Décrire la méthode pour dériver une fonction composée de trois fonctions élémentaires.

---

## Métadonnées RAG

- **Titre** : Les Fonctions Numériques : Limites, Continuité, Dérivation
- **Chapitre** : Analyse
- **Sous-chapitre** : Continuité, théorème des valeurs intermédiaires, fonction réciproque, dérivation de fonctions composées, théorème des accroissements finis, étude de fonctions usuelles
- **Compétences** : Utiliser le TVI ; construire une fonction réciproque ; dériver des fonctions composées ; utiliser les accroissements finis ; étudier des fonctions complexes
- **Notions** : continuité, TVI, fonction réciproque, dérivée composée, TAF, croissances comparées
- **Mots-clés** : continuité, valeurs intermédiaires, fonction réciproque, accroissements finis, croissances comparées
- **Pré-requis** : dérivation de base, limites, fonctions usuelles
- **Niveau** : Terminale S1/S3
- **Temps estimé** : 12h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS1S3-ANA-FONCTIONS-01
- **Résumé (200 mots max)** : Cette leçon, la plus dense du programme d'analyse S1/S3, couvre le théorème des valeurs intermédiaires (existence et unicité de solutions), l'existence et l'étude de la fonction réciproque d'une bijection continue (continuité, monotonie, dérivée, symétrie graphique), la dérivation de fonctions composées à plusieurs étages, le théorème des accroissements finis et son inégalité associée, le théorème de prolongement de la dérivée, la notion de point d'inflexion, et les limites usuelles de croissances comparées entre exponentielle, puissance et logarithme. Cinq exemples résolus couvrent chaque grande compétence. Quinze exercices progressifs, avec corrigés détaillés, incluent des démonstrations d'inégalités classiques (\( e^x\ge x+1 \), encadrement de \( \ln(n+1)-\ln n \)) et l'étude complète de fonctions faisant intervenir exponentielle et logarithme. Des questions type Bac, un résumé, une fiche de révision et une auto-évaluation complètent la leçon, qui prépare directement le calcul intégral et les équations différentielles.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS1S3-FONCTIONS-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : TVI, fonction réciproque, dérivée composée

**Bloc 2 — ID: TS1S3-FONCTIONS-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : TAF, inégalité des accroissements finis, méthode

**Bloc 3 — ID: TS1S3-FONCTIONS-B3** — Exemples résolus (section 8) — mots-clés : exemple, bijection, dérivée composée, croissances comparées

**Bloc 4 — ID: TS1S3-FONCTIONS-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, rédaction TVI

**Bloc 5 — ID: TS1S3-FONCTIONS-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, inégalité, encadrement

**Bloc 6 — ID: TS1S3-FONCTIONS-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Fonctions numériques, Terminale S1/S3, pages 63-65)
✓ Exactitude mathématique vérifiée (corrigés recalculés, notamment TAF, inégalités et croissances comparées)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 7 à 10 (série S1/S3)
