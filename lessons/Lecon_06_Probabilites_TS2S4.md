---
niveau: secondaire
classe: Terminale
serie: S2
serie_alias: [S2, S4]
discipline: Mathématiques
chapitre: Les Probabilités
examen_associe: Baccalauréat
source_document: Lecon_06_Probabilites_TS2S4.md
---

# Leçon — Les Probabilités (Terminale S2/S4)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Les Probabilités |
| **Classe** | Terminale |
| **Série** | S2 / S4 |
| **Chapitre** | Organisation de Données |
| **Sous-chapitre** | Probabilité d'un événement, probabilité conditionnelle, indépendance, variables aléatoires, loi binomiale |
| **Prérequis** | Dénombrement (Première), vocabulaire ensembliste (union, intersection, complémentaire) |
| **Durée estimée** | 8 heures |
| **Compétences visées** | Calculer la probabilité d'un événement ou d'une réunion d'événements ; calculer une probabilité conditionnelle ; montrer l'indépendance de deux événements ; déterminer la loi de probabilité d'une variable aléatoire, son espérance, sa variance, son écart-type ; utiliser la loi binomiale |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) calculer des probabilités dans des situations concrètes, (2) utiliser la formule des probabilités totales, (3) construire la loi de probabilité d'une variable aléatoire et calculer ses paramètres, (4) reconnaître et utiliser un schéma de Bernoulli et la loi binomiale |
| **Mots-clés** | probabilité, événement, probabilité conditionnelle, indépendance, variable aléatoire, espérance, variance, loi binomiale |

---

## 2. Introduction

Les probabilités permettent de quantifier l'incertitude et d'analyser des situations où le hasard intervient. Elles trouvent des applications considérables en médecine (fiabilité des tests de dépistage), en économie, en assurance, en génétique, et dans la vie courante (jeux, sondages, contrôle qualité industriel).

En série S2/S4, ce chapitre consolide les acquis de dénombrement de Première et introduit les notions fondamentales de probabilité conditionnelle, d'indépendance, et de variable aléatoire, avec pour point d'orgue la loi binomiale, modèle probabiliste de très nombreuses situations réelles (répétition d'épreuves identiques et indépendantes).

Au Baccalauréat, ce chapitre est quasi systématiquement présent, souvent sous forme d'un exercice combinant dénombrement, arbre de probabilité, calcul de probabilité conditionnelle, et étude d'une variable aléatoire (loi, espérance, variance).

**Applications concrètes** : interprétation d'un test médical (sensibilité, spécificité, valeur prédictive), contrôle qualité en usine, modèles actuariels en assurance.

---

## 3. Définitions

**Définition 1 (Vocabulaire probabiliste).** Une expérience aléatoire est une expérience dont le résultat ne peut être prédit avec certitude. L'ensemble de tous les résultats possibles est l'**univers**, noté \( \Omega \) (fini dans ce programme). Un **événement** est une partie de \( \Omega \) ; un **événement élémentaire** est un singleton \( \{\omega\} \).

**Définition 2 (Probabilité d'un événement).** Une probabilité sur \( \Omega \) est une application qui à chaque événement \( A \) associe un réel \( p(A)\in[0,1] \), telle que \( p(\Omega)=1 \), \( p(\varnothing)=0 \), et pour des événements deux à deux incompatibles \( A_1,\ldots,A_n \), \( p(A_1\cup\cdots\cup A_n)=p(A_1)+\cdots+p(A_n) \).

**Définition 3 (Équiprobabilité).** Il y a équiprobabilité lorsque tous les événements élémentaires ont la même probabilité. Dans ce cas, pour tout événement \( A \), \( p(A)=\dfrac{\mathrm{Card}(A)}{\mathrm{Card}(\Omega)} \).

**Définition 4 (Probabilité conditionnelle).** Pour \( B \) événement de probabilité non nulle, la probabilité conditionnelle de \( A \) sachant \( B \) est
$$ p_B(A) = \frac{p(A\cap B)}{p(B)}. $$

**Définition 5 (Événements indépendants).** \( A \) et \( B \) sont indépendants si \( p(A\cap B) = p(A)\times p(B) \).

**Définition 6 (Variable aléatoire).** Une variable aléatoire \( X \) est une fonction qui à chaque issue \( \omega\in\Omega \) associe un nombre réel \( X(\omega) \). La loi de probabilité de \( X \) associe à chaque valeur \( x \) prise par \( X \) la probabilité \( p(X=x) \).

**Définition 7 (Fonction de répartition).** \( F(x)=p(X\le x) \).

**Définition 8 (Espérance, variance, écart-type).** Si \( X \) prend les valeurs \( x_1,\ldots,x_n \) avec les probabilités \( p_1,\ldots,p_n \) :
$$ E(X)=\sum_i x_ip_i,\qquad V(X)=\sum_i p_i(x_i-E(X))^2,\qquad \sigma(X)=\sqrt{V(X)}. $$

**Définition 9 (Épreuve de Bernoulli, loi binomiale).** Une épreuve de Bernoulli est une expérience à deux issues (« succès » de probabilité \( p \), « échec » de probabilité \( 1-p \)). En répétant \( n \) fois, de façon indépendante, une même épreuve de Bernoulli, le nombre \( X \) de succès suit la **loi binomiale** de paramètres \( n \) et \( p \), notée \( \mathcal{B}(n,p) \).

---

## 4. Théorèmes

**Théorème 1 (Probabilité de l'événement contraire).**
- Énoncé : \( p(\bar A) = 1-p(A) \).

**Théorème 2 (Probabilité d'une réunion).**
- Énoncé : \( p(A\cup B) = p(A)+p(B)-p(A\cap B) \). Si \( A\cap B=\varnothing \) (événements incompatibles), \( p(A\cup B)=p(A)+p(B) \).

**Théorème 3 (Formule des probabilités totales).**
- Énoncé : soit \( B_1,\ldots,B_n \) une partition de \( \Omega \) (événements deux à deux disjoints, de réunion \( \Omega \), tous de probabilité non nulle). Pour tout événement \( A \) :
$$ p(A) = \sum_{i=1}^n p(B_i)\,p_{B_i}(A). $$

**Théorème 4 (Probabilité d'une intersection).**
- Énoncé : \( p(A\cap B) = p(B)\times p_B(A) = p(A)\times p_A(B) \) (lorsque ces probabilités conditionnelles sont définies).
- Cas particulier (indépendance) : si \( A,B \) indépendants, \( p(A\cap B)=p(A)p(B) \).

**Théorème 5 (Loi binomiale).**
- Énoncé : si \( X\sim\mathcal{B}(n,p) \), alors pour tout \( k\in\{0,1,\ldots,n\} \),
$$ p(X=k) = \binom nk p^k(1-p)^{n-k}. $$
- Propriétés : \( E(X)=np \) ; \( V(X)=np(1-p) \) ; \( \sigma(X)=\sqrt{np(1-p)} \).

---

## 5. Propriétés

1. \( 0\le p(A)\le1 \) pour tout événement \( A \).
2. Si \( A\subset B \), alors \( p(A)\le p(B) \).
3. \( p_B(A)+p_B(\bar A)=1 \) (la probabilité conditionnelle sachant \( B \) définit bien une probabilité sur \( \Omega \)).
4. \( \displaystyle\sum_i p(X=x_i) = 1 \) pour toute variable aléatoire \( X \).
5. Formule de König-Huygens : \( V(X) = E(X^2)-\big(E(X)\big)^2 \), souvent plus rapide pour le calcul de la variance.
6. Si \( A \) et \( B \) sont indépendants, alors \( A \) et \( \bar B \) le sont aussi (de même que \( \bar A \) et \( B \), et \( \bar A \) et \( \bar B \)).

---

## 6. Démonstrations

**Démonstration du théorème 1** :
Comme \( A \) et \( \bar A \) sont incompatibles et \( A\cup\bar A=\Omega \), on a \( p(A)+p(\bar A)=p(\Omega)=1 \), donc \( p(\bar A)=1-p(A) \).

**Démonstration du théorème 2** :
\( A\cup B \) se décompose en trois parties disjointes : \( A\setminus B \), \( B\setminus A \), \( A\cap B \). On a \( p(A)=p(A\setminus B)+p(A\cap B) \) et \( p(B)=p(B\setminus A)+p(A\cap B) \). En sommant : \( p(A)+p(B)=p(A\setminus B)+p(B\setminus A)+2p(A\cap B) \). Or \( p(A\cup B)=p(A\setminus B)+p(B\setminus A)+p(A\cap B) \), donc \( p(A)+p(B)-p(A\cap B)=p(A\cup B) \).

**Démonstration de la propriété 5 (König-Huygens)** :
$$ V(X)=\sum_ip_i(x_i-E(X))^2 = \sum_ip_i\big(x_i^2-2x_iE(X)+E(X)^2\big) = \sum_ip_ix_i^2 - 2E(X)\sum_ip_ix_i + E(X)^2\sum_ip_i. $$
Or \( \sum_ip_ix_i^2=E(X^2) \), \( \sum_ip_ix_i=E(X) \), et \( \sum_ip_i=1 \). Donc \( V(X)=E(X^2)-2E(X)^2+E(X)^2=E(X^2)-E(X)^2 \).

**Démonstration du théorème 5 (loi binomiale), esquisse** :
L'événement « \( X=k \) » correspond à exactement \( k \) succès parmi les \( n \) épreuves. Le nombre de façons de choisir les \( k \) épreuves qui donnent un succès est \( \binom nk \) ; par indépendance des épreuves, chacune de ces configurations a pour probabilité \( p^k(1-p)^{n-k} \). En sommant sur toutes les configurations (événements incompatibles) : \( p(X=k)=\binom nk p^k(1-p)^{n-k} \).

---

## 7. Méthodes

**Méthode 1 — Calculer une probabilité conditionnelle à l'aide d'un arbre pondéré**
1. Construire l'arbre représentant les différentes étapes de l'expérience, avec les probabilités sur chaque branche.
2. Pour une probabilité d'intersection, multiplier les probabilités le long du chemin.
3. Pour une probabilité totale, sommer les probabilités des chemins menant à l'événement recherché.

**Méthode 2 — Étudier une variable aléatoire**
1. Déterminer les valeurs possibles de \( X \).
2. Calculer \( p(X=x_i) \) pour chaque valeur.
3. Vérifier que la somme des probabilités vaut 1.
4. Calculer \( E(X) \), puis \( V(X) \) (directement ou via König-Huygens) et \( \sigma(X) \).

**Méthode 3 — Reconnaître et utiliser une loi binomiale**
1. Vérifier les conditions : répétition de \( n \) épreuves identiques et indépendantes, à deux issues (succès/échec).
2. Identifier \( n \) et \( p \) (probabilité de succès à chaque épreuve).
3. Utiliser \( p(X=k)=\binom nk p^k(1-p)^{n-k} \), et éventuellement \( E(X)=np \), \( V(X)=np(1-p) \).

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* On tire une carte au hasard dans un jeu de 32 cartes. Quelle est la probabilité de tirer un roi ou un cœur ?
*Résolution :* \( p(\text{roi})=\dfrac4{32} \), \( p(\text{cœur})=\dfrac8{32} \), \( p(\text{roi}\cap\text{cœur})=\dfrac1{32} \) (le roi de cœur). \( p(\text{roi ou cœur})=\dfrac4{32}+\dfrac8{32}-\dfrac1{32}=\dfrac{11}{32} \).
*Conclusion :* La probabilité vaut \( \dfrac{11}{32} \).

**Exemple 2.**
*Énoncé :* Un test de dépistage d'une maladie touchant 2 % de la population a une sensibilité de 95 % (probabilité d'être positif sachant qu'on est malade) et une spécificité de 90 % (probabilité d'être négatif sachant qu'on n'est pas malade). Calculer la probabilité qu'une personne testée positive soit réellement malade.
*Résolution :* Notons \( M \) : « être malade », \( T \) : « test positif ». \( p(M)=0{,}02 \), \( p_M(T)=0{,}95 \), \( p_{\bar M}(T)=1-0{,}90=0{,}10 \). Par la formule des probabilités totales : \( p(T)=p(M)p_M(T)+p(\bar M)p_{\bar M}(T)=0{,}02\times0{,}95+0{,}98\times0{,}10=0{,}019+0{,}098=0{,}117 \). Par la formule de Bayes (théorème 4) : \( p_T(M)=\dfrac{p(M\cap T)}{p(T)}=\dfrac{0{,}019}{0{,}117}\approx0{,}162 \).
*Conclusion :* Seulement environ 16,2 % des personnes testées positives sont réellement malades — un résultat contre-intuitif dû à la faible prévalence de la maladie.

**Exemple 3.**
*Énoncé :* On lance deux dés équilibrés. Soit \( X \) la somme des points obtenus. Déterminer la loi de \( X \) restreinte aux valeurs 2, 7 et 12, et calculer \( p(X=7) \).
*Résolution :* \( \Omega \) a 36 issues équiprobables. \( X=2 \) : une seule issue (1,1), \( p=\dfrac1{36} \). \( X=12 \) : une seule issue (6,6), \( p=\dfrac1{36} \). \( X=7 \) : issues (1,6),(2,5),(3,4),(4,3),(5,2),(6,1), soit 6 issues, \( p=\dfrac6{36}=\dfrac16 \).
*Conclusion :* \( p(X=7)=\dfrac16 \), la valeur la plus probable pour la somme de deux dés.

**Exemple 4.**
*Énoncé :* Une urne contient 5 boules rouges et 3 boules noires. On tire une boule, on note sa couleur, on la remet, puis on recommence 4 fois. Soit \( X \) le nombre de boules rouges obtenues. Déterminer la loi de \( X \), et calculer \( E(X) \) et \( V(X) \).
*Résolution :* Les tirages sont indépendants (remise), probabilité de succès (rouge) \( p=\dfrac58 \), \( n=4 \) : \( X\sim\mathcal B\left(4,\dfrac58\right)\). \( p(X=k)=\binom4k\left(\dfrac58\right)^k\left(\dfrac38\right)^{4-k} \). \( E(X)=np=4\times\dfrac58=\dfrac{20}8=2{,}5 \). \( V(X)=np(1-p)=4\times\dfrac58\times\dfrac38=\dfrac{60}{64}=0{,}9375 \).
*Conclusion :* \( E(X)=2{,}5 \), \( V(X)=0{,}9375 \), \( \sigma(X)=\sqrt{0{,}9375}\approx0{,}968 \).

**Exemple 5.**
*Énoncé :* Montrer que, dans l'exemple 4, les événements \( A \)=« obtenir rouge au premier tirage » et \( B \)=« obtenir rouge au deuxième tirage » sont indépendants.
*Résolution :* \( p(A)=\dfrac58 \), \( p(B)=\dfrac58 \) (tirage avec remise, la composition de l'urne ne change pas). \( p(A\cap B)=\dfrac58\times\dfrac58=\dfrac{25}{64} \) (car les tirages successifs avec remise sont indépendants par construction).
*Conclusion :* \( p(A)\times p(B)=\dfrac58\times\dfrac58=\dfrac{25}{64}=p(A\cap B) \) : les événements sont bien indépendants.

---

## 9. Erreurs fréquentes

- **Confondre \( p_B(A) \) (probabilité de \( A \) sachant \( B \)) avec \( p_A(B) \)** (probabilité de \( B \) sachant \( A \)) : ce sont deux quantités différentes en général (cf. exemple 2, où \( p_M(T)=0{,}95 \) est très différent de \( p_T(M)\approx0{,}162 \)).
- **Confondre événements incompatibles et événements indépendants** : deux événements incompatibles non impossibles ne peuvent pas être indépendants (sauf cas trivial), et réciproquement.
- **Oublier de vérifier les conditions d'application de la loi binomiale** (répétitions identiques et indépendantes) avant de l'utiliser directement.
- **Erreur de calcul dans les coefficients binomiaux** \( \binom nk \) : bien vérifier la formule \( \binom nk=\dfrac{n!}{k!(n-k)!} \).
- **Additionner directement des probabilités sans vérifier l'incompatibilité des événements** : la formule \( p(A\cup B)=p(A)+p(B) \) n'est valable que si \( A\cap B=\varnothing \).

---

## 10. Astuces

- **Astuce de calcul** : pour un arbre pondéré, la somme des probabilités sur les branches partant d'un même nœud doit toujours valoir 1 — c'est un moyen rapide de vérifier ses calculs.
- **Astuce de calcul** : pour la variance, préférer la formule de König-Huygens \( V(X)=E(X^2)-E(X)^2 \), souvent plus rapide que le calcul direct par écarts à la moyenne.
- **Astuce de rédaction** : toujours définir clairement les événements par une lettre et une phrase (« Soit \( M \) l'événement... ») avant tout calcul de probabilité conditionnelle.
- **Astuce pour le Bac** : pour reconnaître une loi binomiale, chercher les mots-clés « on répète \( n \) fois de manière indépendante » et « succès/échec » (ou une situation qui s'y ramène, comme un tirage avec remise).
- **Astuce de calcul** : pour la loi binomiale, retenir directement \( E(X)=np \) et \( V(X)=np(1-p) \) sans repasser par la définition générale de l'espérance à chaque exercice.

---

## 11. Exercices

### Faciles
1. On lance un dé équilibré à 6 faces. Calculer la probabilité d'obtenir un nombre pair.
2. Dans un jeu de 52 cartes, calculer la probabilité de tirer un as.
3. Soient \( A,B \) tels que \( p(A)=0{,}4,\ p(B)=0{,}3,\ p(A\cap B)=0{,}1 \). Calculer \( p(A\cup B) \).
4. Une variable aléatoire \( X \) prend les valeurs \( 1,2,3 \) avec probabilités \( 0{,}2;0{,}5;0{,}3 \). Calculer \( E(X) \).
5. Un événement a une probabilité \( p=0{,}3 \). Calculer la probabilité de l'événement contraire.

### Moyens
6. Une urne contient 4 boules blanches et 6 boules noires. On tire 2 boules sans remise. Calculer la probabilité que les deux boules soient blanches.
7. Sachant que \( p(A)=0{,}5,\ p(B)=0{,}4 \) et que \( A,B \) sont indépendants, calculer \( p(A\cap B) \) et \( p(A\cup B) \).
8. Un tireur atteint sa cible avec une probabilité de 0,8 à chaque tir, les tirs étant indépendants. Il tire 5 fois. Soit \( X \) le nombre de fois où il atteint la cible. Donner la loi de \( X \) et calculer \( p(X=5) \).
9. Calculer \( E(X) \) et \( V(X) \) pour la variable de l'exercice 8.
10. Un sac contient 3 boules rouges et 2 boules vertes. On tire successivement, sans remise, 2 boules. Construire l'arbre de probabilité, et calculer la probabilité que les deux boules soient de couleurs différentes.

### Difficiles
11. Une usine produit des pièces dont 5 % sont défectueuses. On prélève un échantillon de 10 pièces au hasard (grand stock, tirages assimilés à des tirages indépendants). Calculer la probabilité qu'au plus une pièce soit défectueuse.
12. Deux machines A et B produisent respectivement 60 % et 40 % des pièces d'une usine. La machine A produit 2 % de pièces défectueuses, la machine B en produit 5 %. On prélève une pièce au hasard. (a) Calculer la probabilité qu'elle soit défectueuse. (b) Sachant qu'elle est défectueuse, calculer la probabilité qu'elle provienne de la machine B.
13. On lance 3 fois une pièce équilibrée. Soit \( X \) le nombre de « Pile » obtenus. Déterminer la loi de \( X \), calculer \( E(X) \) et \( V(X) \), et vérifier la cohérence avec les formules de la loi binomiale.
14. Montrer que si \( A \) et \( B \) sont indépendants, alors \( \bar A \) et \( \bar B \) le sont aussi.
15. Un questionnaire à choix multiples comporte 10 questions, chacune avec 4 réponses possibles dont une seule est correcte. Un candidat répond au hasard à toutes les questions. Calculer la probabilité qu'il obtienne au moins 3 bonnes réponses (on admettra la possibilité d'utiliser une approximation ou de laisser le résultat sous forme de somme).

---

## 12. Corrigés détaillés

**1.** Issues favorables : 2,4,6, soit 3 sur 6. \( p=\dfrac36=\dfrac12 \).

**2.** \( p=\dfrac4{52}=\dfrac1{13} \).

**3.** \( p(A\cup B)=0{,}4+0{,}3-0{,}1=0{,}6 \).

**4.** \( E(X)=1\times0{,}2+2\times0{,}5+3\times0{,}3=0{,}2+1+0{,}9=2{,}1 \).

**5.** \( p(\bar A)=1-0{,}3=0{,}7 \).

**6.** \( p=\dfrac4{10}\times\dfrac39=\dfrac{12}{90}=\dfrac2{15} \) (tirage successif sans remise, ou directement par combinaisons : \( \dfrac{\binom42}{\binom{10}2}=\dfrac6{45}=\dfrac2{15} \)).

**7.** \( p(A\cap B)=0{,}5\times0{,}4=0{,}2 \) ; \( p(A\cup B)=0{,}5+0{,}4-0{,}2=0{,}7 \).

**8.** \( X\sim\mathcal B(5;0{,}8) \). \( p(X=5)=\binom55(0{,}8)^5(0{,}2)^0=0{,}8^5\approx0{,}328 \).

**9.** \( E(X)=5\times0{,}8=4 \) ; \( V(X)=5\times0{,}8\times0{,}2=0{,}8 \).

**10.** L'arbre a pour première étape : \( p(\text{Rouge})=\dfrac35 \), \( p(\text{Vert})=\dfrac25 \). Ensuite (sans remise) : sachant Rouge au 1er tirage, \( p(\text{Vert au 2e})=\dfrac24 \) ; sachant Vert au 1er, \( p(\text{Rouge au 2e})=\dfrac34 \). \( p(\text{couleurs différentes})=\dfrac35\times\dfrac24+\dfrac25\times\dfrac34=\dfrac{6}{20}+\dfrac6{20}=\dfrac{12}{20}=\dfrac35 \).

**11.** \( X\sim\mathcal B(10;0{,}05) \). \( p(X\le1)=p(X=0)+p(X=1)=(0{,}95)^{10}+\binom{10}1(0{,}05)(0{,}95)^9\approx0{,}5987+0{,}3151\approx0{,}9138 \).

**12.** (a) \( p(D)=p(A)p_A(D)+p(B)p_B(D)=0{,}6\times0{,}02+0{,}4\times0{,}05=0{,}012+0{,}02=0{,}032 \). (b) \( p_D(B)=\dfrac{p(B)p_B(D)}{p(D)}=\dfrac{0{,}02}{0{,}032}=0{,}625 \).

**13.** \( X\sim\mathcal B\left(3;\dfrac12\right) \). \( p(X=0)=\dfrac18,\ p(X=1)=\dfrac38,\ p(X=2)=\dfrac38,\ p(X=3)=\dfrac18 \). \( E(X)=0\times\frac18+1\times\frac38+2\times\frac38+3\times\frac18=\frac{0+3+6+3}8=\frac{12}8=1{,}5 \), cohérent avec \( np=3\times0{,}5=1{,}5 \). \( V(X)=np(1-p)=3\times0{,}5\times0{,}5=0{,}75 \).

**14.** \( p(\bar A\cap\bar B)=1-p(A\cup B)=1-(p(A)+p(B)-p(A)p(B))=1-p(A)-p(B)+p(A)p(B)=(1-p(A))(1-p(B))=p(\bar A)p(\bar B) \), en utilisant l'indépendance de \( A,B \) à l'avant-dernière étape. Donc \( \bar A,\bar B \) sont indépendants.

**15.** \( X\sim\mathcal B(10;0{,}25) \). \( p(X\ge3)=1-p(X=0)-p(X=1)-p(X=2) \). \( p(X=0)=(0{,}75)^{10}\approx0{,}0563 \) ; \( p(X=1)=\binom{10}1(0{,}25)(0{,}75)^9\approx0{,}1877 \) ; \( p(X=2)=\binom{10}2(0{,}25)^2(0{,}75)^8\approx0{,}2816 \). Somme \( \approx0{,}5256 \), donc \( p(X\ge3)\approx1-0{,}5256=0{,}4744 \).

---

## 13. Questions type Bac

1. *(Type Bac)* Dans une population, 60 % des personnes sont vaccinées contre une maladie. Parmi les personnes vaccinées, 1 % développent la maladie ; parmi les non-vaccinées, 8 % la développent. On choisit une personne au hasard. (a) Calculer la probabilité qu'elle développe la maladie. (b) Sachant qu'elle a développé la maladie, calculer la probabilité qu'elle soit vaccinée.
2. *(Type Bac)* Une entreprise fabrique des composants électroniques dont 3 % sont défectueux. On prélève un lot de 20 composants (grand stock). Soit \( X \) le nombre de composants défectueux. (a) Justifier que \( X \) suit une loi binomiale et préciser ses paramètres. (b) Calculer \( E(X) \) et \( V(X) \).
3. *(Type Bac)* On lance un dé truqué tel que \( p(6)=\dfrac13 \) et les autres faces sont équiprobables. Soit \( X \) le gain (en F) : on gagne 300 F si on obtient 6, on perd 60 F sinon. Déterminer la loi de \( X \), calculer \( E(X) \), et interpréter le résultat (jeu favorable ou défavorable au joueur).

---

## 14. Résumé

Une probabilité associe à chaque événement un réel entre 0 et 1, avec \( p(\Omega)=1 \) et additivité sur les événements incompatibles. La probabilité conditionnelle \( p_B(A)=\dfrac{p(A\cap B)}{p(B)} \) permet de réviser une probabilité en tenant compte d'une information supplémentaire ; deux événements sont indépendants si \( p(A\cap B)=p(A)p(B) \). La formule des probabilités totales permet de calculer la probabilité d'un événement à partir d'une partition de l'univers. Une variable aléatoire associe un réel à chaque issue ; sa loi de probabilité, son espérance \( E(X) \), sa variance \( V(X) \) (calculable via König-Huygens) et son écart-type \( \sigma(X) \) résument son comportement. Le schéma de Bernoulli répété \( n \) fois de façon indépendante conduit à la loi binomiale \( \mathcal B(n,p) \), de formule \( p(X=k)=\binom nk p^k(1-p)^{n-k} \), d'espérance \( np \) et de variance \( np(1-p) \).

---

## 15. Fiche de révision

- \( p(\bar A)=1-p(A) \) ; \( p(A\cup B)=p(A)+p(B)-p(A\cap B) \)
- \( p_B(A)=\dfrac{p(A\cap B)}{p(B)} \) ; indépendance : \( p(A\cap B)=p(A)p(B) \)
- Probabilités totales : \( p(A)=\sum_ip(B_i)p_{B_i}(A) \) (partition \( B_i \))
- \( E(X)=\sum x_ip_i \) ; \( V(X)=E(X^2)-E(X)^2 \) ; \( \sigma(X)=\sqrt{V(X)} \)
- Loi binomiale \( \mathcal B(n,p) \) : \( p(X=k)=\binom nk p^k(1-p)^{n-k} \) ; \( E(X)=np \) ; \( V(X)=np(1-p) \)

---

## 16. Glossaire

- **Univers** : ensemble de toutes les issues possibles d'une expérience aléatoire.
- **Probabilité conditionnelle** : probabilité révisée compte tenu d'une information supplémentaire.
- **Indépendance** : absence d'influence mutuelle entre deux événements.
- **Variable aléatoire** : fonction associant un réel à chaque issue.
- **Loi binomiale** : loi du nombre de succès dans une répétition d'épreuves de Bernoulli indépendantes.
- **Espérance** : moyenne pondérée des valeurs d'une variable aléatoire.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : dénombrement (combinaisons, Première), statistiques (moyenne, variance — analogie directe avec espérance et variance d'une variable aléatoire).

**Ce qui sera utilisé ensuite** : applications interdisciplinaires (génétique, contrôle qualité, actuariat), lien conceptuel avec les statistiques inférentielles (hors programme de Terminale).

---

## 18. Auto-évaluation

### QCM
1. Si \( A \) et \( B \) sont incompatibles, alors \( p(A\cup B) \) vaut :
 a) \( p(A)\times p(B) \) b) \( p(A)+p(B) \) c) \( p(A)-p(B) \) d) 1

2. Pour une loi binomiale \( \mathcal B(n,p) \), l'espérance vaut :
 a) \( n \) b) \( p \) c) \( np \) d) \( np(1-p) \)

3. La probabilité conditionnelle \( p_B(A) \) est définie par :
 a) \( \dfrac{p(A)}{p(B)} \) b) \( \dfrac{p(A\cap B)}{p(B)} \) c) \( p(A)\times p(B) \) d) \( p(A)-p(B) \)

### Vrai/Faux
1. Deux événements incompatibles sont toujours indépendants. (Faux, sauf cas trivial où l'un des deux est de probabilité nulle)
2. La variance peut se calculer par \( V(X)=E(X^2)-E(X)^2 \). (Vrai)
3. Dans un schéma de Bernoulli répété, les épreuves doivent être indépendantes. (Vrai)

### Questions ouvertes
1. Expliquer, à l'aide de l'exemple du test médical, pourquoi \( p_M(T) \) et \( p_T(M) \) peuvent être très différentes.
2. Décrire les trois conditions nécessaires pour qu'une variable aléatoire suive une loi binomiale.

---

## Métadonnées RAG

- **Titre** : Les Probabilités
- **Chapitre** : Organisation de Données
- **Sous-chapitre** : Probabilité d'un événement, probabilité conditionnelle, indépendance, variables aléatoires, loi binomiale
- **Compétences** : Calculer des probabilités et des probabilités conditionnelles ; montrer l'indépendance ; étudier une variable aléatoire ; utiliser la loi binomiale
- **Notions** : probabilité conditionnelle, indépendance, probabilités totales, variable aléatoire, espérance, variance, loi binomiale
- **Mots-clés** : probabilité, conditionnelle, indépendance, variable aléatoire, loi binomiale, espérance, variance
- **Pré-requis** : dénombrement, statistiques descriptives
- **Niveau** : Terminale S2/S4
- **Temps estimé** : 8h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS2S4-PROBA-01
- **Résumé (200 mots max)** : Cette leçon couvre les probabilités en Terminale S2/S4 : vocabulaire probabiliste, calcul de probabilités d'événements et de réunions, probabilité conditionnelle et indépendance, formule des probabilités totales, puis étude des variables aléatoires (loi de probabilité, espérance, variance via König-Huygens, écart-type), et enfin la loi binomiale issue d'un schéma de Bernoulli répété. Les exemples résolus incluent un cas classique et contre-intuitif de test médical illustrant la différence entre \( p_B(A) \) et \( p_A(B) \). Quinze exercices progressifs couvrent des situations variées (urnes, tests, production industrielle, QCM). Des questions type Bac, un résumé, une fiche de révision et une auto-évaluation complètent la leçon. Ce chapitre clôt la série de leçons S2/S4 et s'articule avec les statistiques descriptives déjà étudiées, ainsi qu'avec le dénombrement vu en Première.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS2S4-PROBA-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : probabilité, conditionnelle, indépendance, probabilités totales

**Bloc 2 — ID: TS2S4-PROBA-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : König-Huygens, arbre pondéré, loi binomiale

**Bloc 3 — ID: TS2S4-PROBA-B3** — Exemples résolus (section 8) — mots-clés : exemple, test médical, urne, dés

**Bloc 4 — ID: TS2S4-PROBA-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, arbre pondéré

**Bloc 5 — ID: TS2S4-PROBA-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, usine, QCM

**Bloc 6 — ID: TS2S4-PROBA-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Probabilités, Terminale S2/S4, pages 78-79)
✓ Exactitude mathématique vérifiée (corrigés recalculés, notamment Bayes et loi binomiale)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 1 à 5 — **série S2/S4 complète (6 leçons)**
