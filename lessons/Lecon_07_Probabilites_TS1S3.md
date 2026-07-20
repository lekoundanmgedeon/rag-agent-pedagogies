---
niveau: secondaire
classe: Terminale
serie: S1
serie_alias: [S1, S3]
discipline: Mathématiques
chapitre: Les Probabilités
examen_associe: Baccalauréat
source_document: Lecon_07_Probabilites_TS1S3.md
---

# Leçon — Les Probabilités (Terminale S1/S3)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Les Probabilités |
| **Classe** | Terminale |
| **Série** | S1 / S3 |
| **Chapitre** | Probabilités |
| **Sous-chapitre** | Espace probabilisé, probabilité conditionnelle, indépendance, variables aléatoires, loi binomiale |
| **Prérequis** | Dénombrement (Première), vocabulaire ensembliste |
| **Durée estimée** | 9 heures |
| **Compétences visées** | Utiliser la probabilité d'un événement ou d'une réunion d'événements, la probabilité conditionnelle, la formule des probabilités totales, l'indépendance de deux événements ; déterminer la loi de probabilité d'une variable aléatoire, calculer et interpréter espérance, variance, écart-type, fonction de répartition ; connaître et utiliser la loi binomiale |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) définir un espace probabilisé de façon axiomatique, (2) calculer des probabilités conditionnelles et étudier l'indépendance d'événements, (3) construire et étudier une variable aléatoire (loi, fonction de répartition, espérance, variance), (4) reconnaître et exploiter un schéma de Bernoulli et la loi binomiale |
| **Mots-clés** | espace probabilisé, événement, probabilité conditionnelle, indépendance, variable aléatoire, fonction de répartition, loi binomiale, épreuve de Bernoulli |

---

## 2. Introduction

L'introduction des probabilités en Terminale S1/S3 s'appuie sur l'observation statistique et la stabilité des fréquences, avant d'en donner une **définition axiomatique** rigoureuse. Historiquement, les probabilités sont nées des jeux de hasard étudiés par Pascal et Fermat au XVIIᵉ siècle, avant de devenir un outil scientifique majeur touchant pratiquement tous les secteurs de la vie moderne : assurance, médecine, physique statistique, intelligence artificielle.

Ce chapitre, plus approfondi qu'en série S2/S4, met l'accent sur la rigueur de la définition axiomatique d'une probabilité et sur la maîtrise complète de l'étude d'une variable aléatoire (loi, fonction de répartition, espérance, variance, écart-type), avant d'aborder le schéma de Bernoulli et la loi binomiale.

Au Baccalauréat, ce chapitre est très fréquemment sollicité, souvent en lien avec le dénombrement, sous forme d'exercices combinant calcul de probabilités, étude d'une variable aléatoire et utilisation de la loi binomiale.

**Applications concrètes** : contrôle qualité industriel, génétique, actuariat, sciences expérimentales.

---

## 3. Définitions

**Définition 1 (Espace probabilisé).** On appelle probabilité sur un univers fini \( \Omega \) toute application \( p \) qui à chaque événement (partie de \( \Omega \)) associe un réel de \( [0,1] \), telle que \( p(\Omega)=1 \), \( p(\varnothing)=0 \), et pour tous événements \( A_1,\ldots,A_n \) deux à deux disjoints, \( p(A_1\cup\cdots\cup A_n)=\displaystyle\sum_{i=1}^n p(A_i) \). Le couple \( (\Omega,p) \) est appelé espace probabilisé.

**Définition 2 (Événements élémentaires, incompatibles, contraires).** Un événement élémentaire est un singleton de \( \Omega \). Deux événements \( A,B \) sont incompatibles si \( A\cap B=\varnothing \). L'événement contraire de \( A \), noté \( \bar A \), est \( \Omega\setminus A \).

**Définition 3 (Probabilité conditionnelle).** Pour \( B \) de probabilité non nulle, la probabilité conditionnelle de \( A \) sachant \( B \) est
$$ p_B(A) = \frac{p(A\cap B)}{p(B)}. $$

**Définition 4 (Indépendance).** \( A \) et \( B \) sont indépendants si \( p(A\cap B)=p(A)\,p(B) \).

**Définition 5 (Variable aléatoire, loi de probabilité).** Une variable aléatoire \( X \) sur \( \Omega \) est une application de \( \Omega \) dans \( \mathbb{R} \). Sa loi de probabilité est la donnée des valeurs \( x_i \) prises par \( X \) et des probabilités \( p(X=x_i) \) associées.

**Définition 6 (Fonction de répartition).** La fonction de répartition de \( X \) est \( F(x)=p(X\le x) \), définie pour tout réel \( x \).

**Définition 7 (Espérance, variance, écart-type).**
$$ E(X)=\sum_ix_ip(X=x_i),\quad V(X)=\sum_ip(X=x_i)\big(x_i-E(X)\big)^2,\quad \sigma(X)=\sqrt{V(X)}. $$

**Définition 8 (Épreuve et schéma de Bernoulli).** Une épreuve de Bernoulli est une expérience à deux issues, succès (probabilité \( p \)) et échec (probabilité \( 1-p \)). Un schéma de Bernoulli est la répétition de \( n \) épreuves de Bernoulli identiques et indépendantes.

**Définition 9 (Distribution binomiale).** Le nombre \( X \) de succès dans un schéma de Bernoulli de paramètres \( n \) et \( p \) suit la loi binomiale \( \mathcal B(n,p) \).

---

## 4. Théorèmes

**Théorème 1 (Conséquences directes des axiomes).**
- Énoncé : \( p(\bar A)=1-p(A) \) ; pour tout événement \( A \), \( p(A) \) est la somme des probabilités des événements élémentaires qui le composent ; si \( A\subset B \), \( p(A)\le p(B) \).

**Théorème 2 (Probabilité d'une réunion).**
- Énoncé : \( p(A\cup B)=p(A)+p(B)-p(A\cap B) \), et \( p(A\cup B)=p(A)+p(B) \) si \( A,B \) incompatibles.

**Théorème 3 (Formule des probabilités totales).**
- Énoncé : soit \( B_1,\ldots,B_n \) une partition de \( \Omega \) (en événements de probabilité non nulle). Pour tout événement \( A \) :
$$ p(A)=\sum_{i=1}^n p(A\cap B_i) = \sum_{i=1}^n p(B_i)\,p_{B_i}(A). $$

**Théorème 4 (Probabilité d'une intersection — probabilité produit).**
- Énoncé : \( p(A\cap B)=p(A)\,p_A(B)=p(B)\,p_B(A) \) ; si \( A,B \) indépendants, \( p(A\cap B)=p(A)p(B) \).
- Extension : pour une suite d'événements indépendants \( A_1,\ldots,A_n \), \( p(A_1\cap\cdots\cap A_n)=p(A_1)\times\cdots\times p(A_n) \).

**Théorème 5 (Loi binomiale).**
- Énoncé : si \( X\sim\mathcal B(n,p) \), alors pour \( k\in\{0,\ldots,n\} \),
$$ p(X=k)=\binom nk p^k(1-p)^{n-k}, \qquad E(X)=np,\qquad V(X)=np(1-p). $$

---

## 5. Propriétés

1. \( \displaystyle\sum_i p(X=x_i)=1 \) pour toute variable aléatoire.
2. La fonction de répartition \( F \) est croissante, en escalier (dans le cas fini), et vérifie \( \displaystyle\lim_{x\to-\infty}F(x)=0 \), \( \displaystyle\lim_{x\to+\infty}F(x)=1 \).
3. Formule de König-Huygens : \( V(X)=E(X^2)-\big(E(X)\big)^2 \).
4. Si \( X \) et \( Y \) sont deux variables aléatoires, \( E(X+Y)=E(X)+E(Y) \) (linéarité de l'espérance, admise, valable même si \( X,Y \) ne sont pas indépendantes).
5. Si \( A,B \) sont indépendants, alors \( \bar A,B \) le sont aussi, de même que \( A,\bar B \) et \( \bar A,\bar B \).

---

## 6. Démonstrations

**Démonstration du théorème 2** (identique en structure au raisonnement ensembliste) :
On décompose \( A\cup B \) en trois parties disjointes \( A\setminus B \), \( A\cap B \), \( B\setminus A \). Par additivité (axiome de définition 1) :
$$ p(A\cup B) = p(A\setminus B)+p(A\cap B)+p(B\setminus A). $$
Or \( p(A)=p(A\setminus B)+p(A\cap B) \) et \( p(B)=p(B\setminus A)+p(A\cap B) \), donc \( p(A)+p(B)=p(A\setminus B)+p(B\setminus A)+2p(A\cap B) \), ce qui donne, en réinjectant : \( p(A\cup B)=p(A)+p(B)-p(A\cap B) \).

**Démonstration de la propriété 3 (König-Huygens)** :
$$ V(X)=\sum_ip_i(x_i-E(X))^2=\sum_ip_ix_i^2-2E(X)\sum_ip_ix_i+E(X)^2\sum_ip_i = E(X^2)-2E(X)^2+E(X)^2=E(X^2)-E(X)^2. $$

**Démonstration du théorème 5 (loi binomiale)** :
L'événement \( (X=k) \) correspond au choix de \( k \) épreuves parmi \( n \) donnant un succès (les autres donnant un échec). Il y a \( \binom nk \) façons de choisir ces \( k \) épreuves ; par indépendance, chaque configuration a pour probabilité \( p^k(1-p)^{n-k} \) ; ces configurations étant deux à deux incompatibles, on somme leurs probabilités : \( p(X=k)=\binom nk p^k(1-p)^{n-k} \).

---

## 7. Méthodes

**Méthode 1 — Construire un espace probabilisé et calculer une probabilité**
1. Décrire précisément l'univers \( \Omega \) (lister ou dénombrer les issues).
2. Déterminer si l'on est en situation d'équiprobabilité ou non.
3. Calculer \( p(A) \) selon la définition (rapport de cardinaux si équiprobabilité, sinon somme des probabilités élémentaires).

**Méthode 2 — Étudier une variable aléatoire complètement**
1. Déterminer les valeurs prises par \( X \).
2. Calculer la loi \( p(X=x_i) \) pour chaque valeur, en vérifiant que la somme vaut 1.
3. Construire la fonction de répartition \( F \).
4. Calculer \( E(X) \) puis \( V(X) \) (via König-Huygens de préférence) et \( \sigma(X) \).

**Méthode 3 — Reconnaître et exploiter un schéma de Bernoulli**
1. Vérifier la répétition de \( n \) épreuves identiques et indépendantes à deux issues.
2. Identifier \( p \) (probabilité de succès).
3. Appliquer directement les formules de la loi binomiale.

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Une urne contient 4 boules rouges, 3 boules bleues et 3 boules vertes. On tire une boule au hasard. Calculer la probabilité de tirer une boule rouge ou bleue.
*Résolution :* Équiprobabilité, \( \mathrm{Card}(\Omega)=10 \). \( p(\text{rouge ou bleue})=\dfrac{4+3}{10}=\dfrac7{10} \) (événements incompatibles).
*Conclusion :* \( p=\dfrac7{10} \).

**Exemple 2.**
*Énoncé :* On lance deux dés équilibrés. Soit \( A \) : « la somme est 8 », \( B \) : « le premier dé donne 3 ». Calculer \( p_B(A) \).
*Résolution :* \( p(B)=\dfrac6{36}=\dfrac16 \) (6 issues avec premier dé = 3). Parmi ces 6 issues, celle qui donne une somme de 8 est (3,5), soit 1 issue. \( p(A\cap B)=\dfrac1{36} \). \( p_B(A)=\dfrac{1/36}{6/36}=\dfrac16 \).
*Conclusion :* \( p_B(A)=\dfrac16 \).

**Exemple 3.**
*Énoncé :* Soit \( X \) le nombre de « Face » obtenus en 3 lancers d'une pièce équilibrée. Construire la loi de \( X \), sa fonction de répartition, et calculer \( E(X) \), \( V(X) \).
*Résolution :* \( X\sim\mathcal B\left(3,\dfrac12\right) \). \( p(X=0)=\dfrac18,\ p(X=1)=\dfrac38,\ p(X=2)=\dfrac38,\ p(X=3)=\dfrac18 \). Fonction de répartition : \( F(x)=0 \) pour \( x<0 \) ; \( F(x)=\frac18 \) pour \( 0\le x<1 \) ; \( F(x)=\frac48=\frac12 \) pour \( 1\le x<2 \) ; \( F(x)=\frac78 \) pour \( 2\le x<3 \) ; \( F(x)=1 \) pour \( x\ge3 \). \( E(X)=np=3\times0{,}5=1{,}5 \) ; \( V(X)=np(1-p)=3\times0{,}5\times0{,}5=0{,}75 \).
*Conclusion :* La loi, la fonction de répartition, l'espérance et la variance sont entièrement déterminées.

**Exemple 4.**
*Énoncé :* Dans une population, 3 % des individus sont porteurs d'un certain gène. On teste 15 individus indépendamment. Quelle est la probabilité qu'exactement 2 soient porteurs ?
*Résolution :* \( X\sim\mathcal B(15;0{,}03) \). \( p(X=2)=\binom{15}2(0{,}03)^2(0{,}97)^{13}=105\times0{,}0009\times0{,}97^{13} \). \( 0{,}97^{13}\approx0{,}6730 \). \( p(X=2)\approx105\times0{,}0009\times0{,}6730\approx0{,}0636 \).
*Conclusion :* \( p(X=2)\approx0{,}064 \), soit environ 6,4 %.

**Exemple 5.**
*Énoncé :* Montrer que si \( A \) et \( B \) sont indépendants avec \( p(A)=0{,}6 \) et \( p(B)=0{,}5 \), alors \( \bar A \) et \( B \) sont aussi indépendants.
*Résolution :* \( p(\bar A\cap B) = p(B)-p(A\cap B) = p(B)-p(A)p(B) = p(B)(1-p(A)) = p(B)p(\bar A) \). Numériquement : \( p(\bar A)=0{,}4 \), \( p(\bar A\cap B)=0{,}5\times0{,}4=0{,}2 \), et \( p(\bar A)p(B)=0{,}4\times0{,}5=0{,}2 \), donc bien égaux.
*Conclusion :* \( \bar A \) et \( B \) sont indépendants.

---

## 9. Erreurs fréquentes

- **Négliger la vérification de l'équiprobabilité** avant d'appliquer la formule \( p(A)=\dfrac{\mathrm{Card}(A)}{\mathrm{Card}(\Omega)} \) : cette formule n'est valable qu'en situation d'équiprobabilité.
- **Confondre \( p_A(B) \) et \( p_B(A) \)**, qui ne sont égales que dans des cas particuliers.
- **Oublier que la fonction de répartition est en escalier** dans le cas d'une variable aléatoire discrète, et non une fonction continue.
- **Utiliser l'indépendance sans l'avoir démontrée** (ou sans qu'elle soit donnée par le contexte de l'énoncé, comme un tirage avec remise) : l'indépendance ne se suppose pas, elle se vérifie ou se justifie par le protocole expérimental.
- **Erreur de calcul dans les coefficients binomiaux ou dans les puissances** lors de l'application de la formule de la loi binomiale.

---

## 10. Astuces

- **Astuce de calcul** : pour calculer une probabilité conditionnelle rapidement, restreindre mentalement l'univers à l'événement conditionnant \( B \), puis raisonner comme dans un nouvel espace probabilisé.
- **Astuce de rédaction** : toujours vérifier, avant de conclure à l'indépendance, que l'égalité \( p(A\cap B)=p(A)p(B) \) est bien vérifiée numériquement (ne pas se contenter d'une intuition).
- **Astuce pour le Bac** : pour construire la fonction de répartition d'une variable aléatoire discrète, dresser d'abord un tableau des valeurs cumulées de la loi, puis en déduire les paliers de \( F \).
- **Astuce de calcul** : pour la loi binomiale, utiliser directement \( E(X)=np \) et \( V(X)=np(1-p) \) plutôt que de repasser par la définition générale, sauf si l'énoncé demande explicitement la démonstration.

---

## 11. Exercices

### Faciles
1. On tire une carte dans un jeu de 52 cartes. Calculer la probabilité de tirer un cœur.
2. Soient \( A,B \) tels que \( p(A)=0{,}5,\ p(B)=0{,}3,\ p(A\cap B)=0{,}15 \). Calculer \( p(A\cup B) \) et vérifier si \( A,B \) sont indépendants.
3. Une variable aléatoire \( X \) prend les valeurs \( -1,0,2 \) avec probabilités \( 0{,}3;0{,}5;0{,}2 \). Calculer \( E(X) \).
4. Un événement a une probabilité de 0,25. Calculer la probabilité de l'événement contraire.
5. \( X\sim\mathcal B(6;0{,}5) \). Calculer \( E(X) \) et \( V(X) \).

### Moyens
6. Une urne contient 5 boules noires et 5 boules blanches. On tire 3 boules sans remise. Calculer la probabilité d'obtenir exactement 2 boules blanches.
7. Sachant \( p(A)=0{,}4 \), \( p_A(B)=0{,}6 \), \( p_{\bar A}(B)=0{,}2 \), calculer \( p(B) \) par la formule des probabilités totales.
8. En reprenant l'exercice 7, calculer \( p_B(A) \).
9. Un joueur lance un dé équilibré 4 fois. Soit \( X \) le nombre de fois où il obtient un 6. Donner la loi de \( X \) et calculer \( p(X\ge1) \).
10. Construire la fonction de répartition de la variable \( X \) de l'exercice 9 (pour les valeurs 0,1,2,3,4).

### Difficiles
11. Un laboratoire teste un vaccin sur une population où 5 % contractent une maladie sans vaccination. Le vaccin réduit ce risque à 1 %. 70 % de la population est vaccinée. On choisit une personne au hasard. (a) Calculer la probabilité qu'elle contracte la maladie. (b) Sachant qu'elle a contracté la maladie, calculer la probabilité qu'elle soit vaccinée.
12. Montrer, dans le cas général, que \( V(aX+b)=a^2V(X) \) pour des réels \( a,b \), à partir de la définition de la variance.
13. Une chaîne de production fabrique des pièces avec un taux de défaut de 2 %. On prélève un échantillon de 25 pièces (grand stock). Calculer la probabilité qu'il y ait au moins 2 pièces défectueuses (on pourra passer par le complémentaire).
14. Soient \( A_1, A_2, A_3 \) trois événements indépendants de même probabilité \( p \). Exprimer, en fonction de \( p \), la probabilité qu'au moins un des trois événements se réalise.
15. Un système électronique fonctionne si au moins 2 de ses 3 composants indépendants fonctionnent, chacun avec une probabilité de fonctionnement de 0,9. Calculer la probabilité que le système fonctionne.

---

## 12. Corrigés détaillés

**1.** \( p=\dfrac{13}{52}=\dfrac14 \).

**2.** \( p(A\cup B)=0{,}5+0{,}3-0{,}15=0{,}65 \). Test d'indépendance : \( p(A)\times p(B)=0{,}5\times0{,}3=0{,}15=p(A\cap B) \) : les événements sont indépendants.

**3.** \( E(X)=(-1)\times0{,}3+0\times0{,}5+2\times0{,}2=-0{,}3+0+0{,}4=0{,}1 \).

**4.** \( p(\bar A)=1-0{,}25=0{,}75 \).

**5.** \( E(X)=6\times0{,}5=3 \) ; \( V(X)=6\times0{,}5\times0{,}5=1{,}5 \).

**6.** \( p=\dfrac{\binom52\binom51}{\binom{10}3}=\dfrac{10\times5}{120}=\dfrac{50}{120}=\dfrac{5}{12} \).

**7.** \( p(B)=p(A)p_A(B)+p(\bar A)p_{\bar A}(B)=0{,}4\times0{,}6+0{,}6\times0{,}2=0{,}24+0{,}12=0{,}36 \).

**8.** \( p_B(A)=\dfrac{p(A\cap B)}{p(B)}=\dfrac{0{,}4\times0{,}6}{0{,}36}=\dfrac{0{,}24}{0{,}36}=\dfrac23\approx0{,}667 \).

**9.** \( X\sim\mathcal B\left(4,\dfrac16\right) \). \( p(X\ge1)=1-p(X=0)=1-\left(\dfrac56\right)^4=1-\dfrac{625}{1296}=\dfrac{671}{1296}\approx0{,}518 \).

**10.** \( p(X=0)=\left(\frac56\right)^4=\frac{625}{1296}\approx0{,}482 \) ; \( p(X=1)=\binom41\left(\frac16\right)\left(\frac56\right)^3=4\times\frac16\times\frac{125}{216}=\frac{500}{1296}\approx0{,}386 \) ; \( p(X=2)=\binom42\left(\frac16\right)^2\left(\frac56\right)^2=6\times\frac1{36}\times\frac{25}{36}=\frac{150}{1296}\approx0{,}116 \) ; \( p(X=3)\approx0{,}015 \) ; \( p(X=4)\approx0{,}0008 \). Fonction de répartition : \( F(0)\approx0{,}482 \), \( F(1)\approx0{,}868 \), \( F(2)\approx0{,}984 \), \( F(3)\approx0{,}999 \), \( F(4)=1 \).

**11.** Notons \( V \) : vacciné, \( M \) : malade. \( p(V)=0{,}7,\ p_V(M)=0{,}01,\ p_{\bar V}(M)=0{,}05 \). (a) \( p(M)=0{,}7\times0{,}01+0{,}3\times0{,}05=0{,}007+0{,}015=0{,}022 \). (b) \( p_M(V)=\dfrac{0{,}007}{0{,}022}\approx0{,}318 \).

**12.** \( V(aX+b) = E\big((aX+b-E(aX+b))^2\big) = E\big((aX+b-aE(X)-b)^2\big)=E\big(a^2(X-E(X))^2\big)=a^2E\big((X-E(X))^2\big)=a^2V(X) \).

**13.** \( X\sim\mathcal B(25;0{,}02) \). \( p(X\ge2)=1-p(X=0)-p(X=1) \). \( p(X=0)=(0{,}98)^{25}\approx0{,}6035 \) ; \( p(X=1)=\binom{25}1(0{,}02)(0{,}98)^{24}\approx25\times0{,}02\times0{,}6158\approx0{,}3079 \). \( p(X\ge2)\approx1-0{,}6035-0{,}3079=0{,}0886 \).

**14.** \( p(\text{aucun ne se réalise})=(1-p)^3 \) (indépendance). Donc \( p(\text{au moins un})=1-(1-p)^3 \).

**15.** \( X \) : nombre de composants fonctionnels, \( X\sim\mathcal B(3;0{,}9) \). Le système fonctionne si \( X\ge2 \) : \( p(X\ge2)=p(X=2)+p(X=3)=\binom32(0{,}9)^2(0{,}1)+\binom33(0{,}9)^3=3\times0{,}81\times0{,}1+0{,}729=0{,}243+0{,}729=0{,}972 \).

---

## 13. Questions type Bac

1. *(Type Bac)* Une entreprise produit des composants dans deux usines : l'usine A produit 65 % de la production avec un taux de défaut de 3 %, l'usine B produit 35 % avec un taux de défaut de 6 %. On prélève un composant au hasard. (a) Calculer la probabilité qu'il soit défectueux. (b) Sachant qu'il est défectueux, calculer la probabilité qu'il provienne de l'usine B.
2. *(Type Bac)* On considère une expérience aléatoire où l'on répète 8 fois, de façon indépendante, une épreuve de Bernoulli de paramètre \( p=0{,}25 \). Soit \( X \) le nombre de succès. (a) Justifier que \( X\sim\mathcal B(8;0{,}25) \). (b) Calculer \( E(X) \) et \( V(X) \). (c) Calculer \( p(X=3) \).
3. *(Type Bac)* Soit \( X \) une variable aléatoire prenant les valeurs \( -2,1,3 \) avec des probabilités respectives \( a,\ 2a,\ 3a \). (a) Déterminer \( a \) sachant que la somme des probabilités vaut 1. (b) Calculer \( E(X) \) et \( V(X) \).

---

## 14. Résumé

Un espace probabilisé \( (\Omega,p) \) est défini axiomatiquement : \( p(\Omega)=1 \), \( p(\varnothing)=0 \), additivité sur les événements deux à deux disjoints. La probabilité conditionnelle \( p_B(A)=\dfrac{p(A\cap B)}{p(B)} \) permet de réviser une probabilité ; l'indépendance se caractérise par \( p(A\cap B)=p(A)p(B) \) et se vérifie, ne se suppose pas. La formule des probabilités totales décompose le calcul d'une probabilité à partir d'une partition de l'univers. Une variable aléatoire est étudiée par sa loi de probabilité, sa fonction de répartition (en escalier dans le cas discret), son espérance (linéaire), sa variance (calculable via König-Huygens) et son écart-type. Le schéma de Bernoulli, répétition d'épreuves identiques et indépendantes à deux issues, conduit à la loi binomiale \( \mathcal B(n,p) \), de paramètres \( E(X)=np \) et \( V(X)=np(1-p) \).

---

## 15. Fiche de révision

- \( p(\Omega)=1,\ p(\varnothing)=0 \) ; \( p(\bar A)=1-p(A) \) ; \( p(A\cup B)=p(A)+p(B)-p(A\cap B) \)
- \( p_B(A)=\dfrac{p(A\cap B)}{p(B)} \) ; indépendance : \( p(A\cap B)=p(A)p(B) \)
- Probabilités totales : \( p(A)=\sum_i p(B_i)p_{B_i}(A) \)
- \( E(X)=\sum x_ip_i \) ; \( V(X)=E(X^2)-E(X)^2 \) ; \( \sigma(X)=\sqrt{V(X)} \)
- Fonction de répartition : \( F(x)=p(X\le x) \), croissante, en escalier
- Loi binomiale : \( p(X=k)=\binom nk p^k(1-p)^{n-k} \), \( E(X)=np,\ V(X)=np(1-p) \)

---

## 16. Glossaire

- **Espace probabilisé** : couple \( (\Omega,p) \) formé d'un univers et d'une probabilité.
- **Probabilité conditionnelle** : probabilité révisée sachant la réalisation d'un événement.
- **Fonction de répartition** : fonction cumulative \( F(x)=p(X\le x) \).
- **Schéma de Bernoulli** : répétition d'épreuves identiques et indépendantes à deux issues.
- **Loi binomiale** : loi de probabilité du nombre de succès dans un schéma de Bernoulli.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : dénombrement (Première), vocabulaire ensembliste.

**Ce qui sera utilisé ensuite** : arithmétique (probabilités et théorie des nombres dans certains problèmes combinés), suites numériques (schémas répétés et convergence de fréquences), applications interdisciplinaires en sciences physiques et économie.

---

## 18. Auto-évaluation

### QCM
1. Dans un espace probabilisé, \( p(\Omega) \) vaut toujours :
 a) 0 b) 1 c) 0,5 d) indéterminé

2. La formule de König-Huygens pour la variance est :
 a) \( V(X)=E(X)^2-E(X^2) \) b) \( V(X)=E(X^2)-E(X)^2 \) c) \( V(X)=E(X^2)+E(X)^2 \) d) \( V(X)=E(X) \)

3. Dans un schéma de Bernoulli, les épreuves doivent être :
 a) dépendantes b) identiques et indépendantes c) toutes différentes d) au nombre de 2 exactement

### Vrai/Faux
1. La fonction de répartition d'une variable aléatoire discrète est continue. (Faux — elle est en escalier)
2. L'indépendance de deux événements doit être vérifiée, pas supposée arbitrairement. (Vrai)
3. \( E(X+Y)=E(X)+E(Y) \) même si \( X \) et \( Y \) ne sont pas indépendantes. (Vrai — linéarité de l'espérance)

### Questions ouvertes
1. Expliquer la différence entre la définition axiomatique d'une probabilité et le calcul par équiprobabilité.
2. Décrire, à l'aide d'un exemple, comment la formule des probabilités totales permet de calculer une probabilité globale à partir de sous-populations.

---

## Métadonnées RAG

- **Titre** : Les Probabilités
- **Chapitre** : Probabilités
- **Sous-chapitre** : Espace probabilisé, probabilité conditionnelle, indépendance, variables aléatoires, loi binomiale
- **Compétences** : Calculer des probabilités et probabilités conditionnelles ; étudier l'indépendance ; étudier une variable aléatoire complète ; utiliser la loi binomiale
- **Notions** : espace probabilisé, probabilité conditionnelle, indépendance, fonction de répartition, loi binomiale
- **Mots-clés** : probabilité, espace probabilisé, conditionnelle, indépendance, variable aléatoire, loi binomiale
- **Pré-requis** : dénombrement, ensembles
- **Niveau** : Terminale S1/S3
- **Temps estimé** : 9h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS1S3-PROBA-01
- **Résumé (200 mots max)** : Cette leçon introduit les probabilités en Terminale S1/S3 à partir d'une définition axiomatique de l'espace probabilisé, plus rigoureuse qu'en série S2/S4. Elle couvre la probabilité conditionnelle, l'indépendance d'événements (à vérifier, non à supposer), la formule des probabilités totales, puis l'étude complète d'une variable aléatoire discrète : loi de probabilité, fonction de répartition (en escalier), espérance (linéaire), variance (via König-Huygens) et écart-type. Le schéma de Bernoulli et la loi binomiale, avec ses paramètres \( E(X)=np \) et \( V(X)=np(1-p) \), concluent la leçon. Cinq exemples résolus couvrent tirages, probabilité conditionnelle, construction complète d'une variable aléatoire, et application médicale/génétique. Quinze exercices progressifs sont corrigés en détail, incluant un exercice sur la propriété \( V(aX+b)=a^2V(X) \). Des questions type Bac, une fiche de révision et une auto-évaluation complètent la leçon, première de la série S1/S3.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS1S3-PROBA-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : espace probabilisé, axiome, probabilités totales

**Bloc 2 — ID: TS1S3-PROBA-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : König-Huygens, fonction de répartition, schéma de Bernoulli

**Bloc 3 — ID: TS1S3-PROBA-B3** — Exemples résolus (section 8) — mots-clés : exemple, urne, dé, fonction de répartition

**Bloc 4 — ID: TS1S3-PROBA-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, indépendance

**Bloc 5 — ID: TS1S3-PROBA-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, vaccin, production

**Bloc 6 — ID: TS1S3-PROBA-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Probabilités, Terminale S1/S3, page 59)
✓ Exactitude mathématique vérifiée (corrigés recalculés, notamment probabilités totales et Bayes)
✓ Cohérence des notations avec la série S2/S4 (transposable, notations harmonisées)
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté, légèrement plus axiomatique conformément au programme S1/S3
✓ Première leçon de la série S1/S3 — homogénéité à maintenir pour les leçons suivantes
