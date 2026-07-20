---
niveau: secondaire
classe: Terminale
serie: S1
serie_alias: [S1, S3]
discipline: Mathématiques
chapitre: L'Arithmétique
examen_associe: Baccalauréat
source_document: Lecon_09_Arithmetique_TS1S3.md
---

# Leçon — L'Arithmétique (Terminale S1/S3)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | L'Arithmétique dans ℤ |
| **Classe** | Terminale |
| **Série** | S1 / S3 |
| **Chapitre** | Algèbre |
| **Sous-chapitre** | Divisibilité, nombres premiers, PGCD, PPCM, théorème de Gauss, identité de Bezout, division euclidienne, systèmes de numération, congruences |
| **Prérequis** | Connaissance pratique des entiers naturels et relatifs (premier cycle), notion de division euclidienne de base |
| **Durée estimée** | 8 heures |
| **Compétences visées** | Décomposer un entier en produit de facteurs premiers ; déterminer le PGCD et le PPCM de plusieurs entiers ; résoudre dans ℤ des équations du type \( ax+by=c \) ; utiliser les congruences pour résoudre des problèmes d'arithmétique |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) déterminer diviseurs et multiples d'un entier, (2) décomposer un entier en facteurs premiers et en déduire PGCD/PPCM, (3) appliquer le théorème de Gauss et l'identité de Bezout, (4) résoudre une équation diophantienne \( ax+by=c \), (5) utiliser les congruences modulo \( n \), y compris le petit théorème de Fermat |
| **Mots-clés** | divisibilité, nombre premier, PGCD, PPCM, théorème de Gauss, identité de Bezout, algorithme d'Euclide, congruence, système de numération |

---

## 2. Introduction

L'arithmétique est la branche des mathématiques qui étudie les propriétés des nombres entiers. Réintroduite dans le programme de Terminale S1/S3, elle prolonge et approfondit les connaissances pratiques acquises au premier cycle, en particulier par l'introduction des **congruences** et l'étude des **systèmes de numération**, dont les applications en informatique sont considérables (codage binaire, hexadécimal, cryptographie).

Ce chapitre développe un raisonnement rigoureux, essentiel pour la suite des études scientifiques : théorème de Gauss, identité de Bezout, résolution d'équations diophantiennes. Ces outils sont à la base de la cryptographie moderne (chiffrement RSA) et de nombreux algorithmes informatiques.

Au Baccalauréat, ce chapitre donne lieu à des exercices combinant PGCD/PPCM, résolution d'équations diophantiennes, et utilisation des congruences pour des problèmes de divisibilité ou de recherche de restes.

**Applications concrètes** : cryptographie (RSA), codage informatique (bases numériques), calendriers et problèmes de périodicité, clés de contrôle (numéro INSEE, ISBN).

---

## 3. Définitions

**Définition 1 (Divisibilité).** Pour \( a,b\in\mathbb Z \), on dit que \( b \) divise \( a \) (ou que \( a \) est un multiple de \( b \)) s'il existe \( k\in\mathbb Z \) tel que \( a=bk \). On note \( b\mid a \).

**Définition 2 (Nombre premier).** Un entier naturel \( p\ge2 \) est premier s'il n'admet que deux diviseurs positifs : 1 et lui-même.

**Définition 3 (PGCD, PPCM).** Le plus grand commun diviseur de plusieurs entiers est le plus grand entier qui divise chacun d'eux. Le plus petit commun multiple est le plus petit entier positif multiple de chacun d'eux.

**Définition 4 (Entiers premiers entre eux).** Deux entiers sont premiers entre eux si leur PGCD vaut 1.

**Définition 5 (Division euclidienne).** Pour \( a\in\mathbb Z,\ b\in\mathbb N^* \), il existe un unique couple \( (q,r) \) d'entiers tels que \( a=bq+r \) avec \( 0\le r<b \). \( q \) est le quotient, \( r \) le reste.

**Définition 6 (Congruence modulo n).** Pour \( n\in\mathbb N^* \), \( a\equiv b\ [n] \) (« \( a \) congru à \( b \) modulo \( n \) ») signifie que \( n\mid(a-b) \), c'est-à-dire que \( a \) et \( b \) ont le même reste dans la division euclidienne par \( n \).

**Définition 7 (Système de numération).** Représentation d'un entier naturel dans une base \( b\ge2 \) donnée, à l'aide de \( b \) chiffres (\( 0 \) à \( b-1 \)), selon l'écriture \( \overline{a_ka_{k-1}\ldots a_1a_0}_{(b)} = \displaystyle\sum_{i=0}^k a_ib^i \).

---

## 4. Théorèmes

**Théorème 1 (Décomposition en facteurs premiers — admis).**
- Énoncé : tout entier naturel \( n\ge2 \) se décompose de façon unique (à l'ordre des facteurs près) en un produit de nombres premiers : \( n=p_1^{\alpha_1}p_2^{\alpha_2}\cdots p_k^{\alpha_k} \).

**Théorème 2 (Théorème de Bezout).**
- Énoncé : deux entiers \( a,b \) sont premiers entre eux si et seulement s'il existe des entiers \( u,v \) tels que \( au+bv=1 \).
- Conséquence : pour \( a,b \) quelconques non tous deux nuls, de PGCD \( d \), il existe \( u,v\in\mathbb Z \) tels que \( au+bv=d \) (identité de Bezout généralisée).

**Théorème 3 (Théorème de Gauss).**
- Énoncé : si \( a\mid bc \) et si \( a \) et \( b \) sont premiers entre eux, alors \( a\mid c \).
- Conséquence usuelle : si \( a\mid c \) et \( b\mid c \) avec \( a,b \) premiers entre eux, alors \( ab\mid c \).

**Théorème 4 (Algorithme d'Euclide).**
- Énoncé : pour calculer \( \mathrm{PGCD}(a,b) \) (\( a>b>0 \)), on effectue des divisions euclidiennes successives : \( a=bq_1+r_1 \), \( b=r_1q_2+r_2 \), etc., jusqu'à obtenir un reste nul ; le PGCD est le dernier reste non nul.

**Théorème 5 (Relation PGCD-PPCM).**
- Énoncé : pour \( a,b \) entiers naturels non nuls, \( \mathrm{PGCD}(a,b)\times\mathrm{PPCM}(a,b) = a\times b \).

**Théorème 6 (Résolution de \( ax+by=c \)).**
- Énoncé : soit \( d=\mathrm{PGCD}(a,b) \). L'équation \( ax+by=c \) (\( a,b,c\in\mathbb Z \)) admet des solutions entières si et seulement si \( d\mid c \). Dans ce cas, si \( (x_0,y_0) \) est une solution particulière, l'ensemble des solutions est \( \left\{\left(x_0+k\dfrac bd,\ y_0-k\dfrac ad\right),\ k\in\mathbb Z\right\} \).

**Théorème 7 (Petit théorème de Fermat).**
- Énoncé : soit \( p \) un nombre premier. Pour tout entier naturel \( x \) non nul, \( x^p\equiv x\ [p] \). Si de plus \( p\nmid x \), alors \( x^{p-1}\equiv1\ [p] \).

---

## 5. Propriétés

1. Si \( a\equiv b\ [n] \) et \( c\equiv d\ [n] \), alors \( a+c\equiv b+d\ [n] \) et \( ac\equiv bd\ [n] \) (compatibilité des congruences avec les opérations).
2. Pour tout \( k\in\mathbb N \), si \( a\equiv b\ [n] \), alors \( a^k\equiv b^k\ [n] \).
3. Tout entier naturel \( n\ge2 \) non premier admet un diviseur premier \( p\le\sqrt n \) (critère pratique pour tester la primalité).
4. Si \( d=\mathrm{PGCD}(a,b) \), alors \( \dfrac ad \) et \( \dfrac bd \) sont premiers entre eux.
5. L'ensemble des multiples communs à \( a \) et \( b \) est exactement l'ensemble des multiples de \( \mathrm{PPCM}(a,b) \).

---

## 6. Démonstrations

**Démonstration du théorème 3 (théorème de Gauss), à partir de Bezout** :
Comme \( a \) et \( b \) sont premiers entre eux, il existe \( u,v\in\mathbb Z \) tels que \( au+bv=1 \) (théorème 2). En multipliant par \( c \) : \( auc+bvc=c \). Or \( a\mid bc \) (hypothèse), donc \( a \) divise \( bvc \) (car il divise \( bc \)), et \( a \) divise trivialement \( auc \). Donc \( a \) divise la somme \( auc+bvc=c \).

**Démonstration de la propriété 1 (compatibilité des congruences avec l'addition)** :
Si \( a\equiv b\ [n] \) et \( c\equiv d\ [n] \), alors \( n\mid(a-b) \) et \( n\mid(c-d) \), donc \( n\mid\big((a-b)+(c-d)\big)=(a+c)-(b+d) \), soit \( a+c\equiv b+d\ [n] \). Pour le produit : \( ac-bd = ac-bc+bc-bd = c(a-b)+b(c-d) \), et \( n \) divise chacun des deux termes, donc \( n\mid(ac-bd) \), soit \( ac\equiv bd\ [n] \).

**Démonstration du théorème 5 (PGCD × PPCM = produit), esquisse** :
En utilisant la décomposition en facteurs premiers de \( a=\prod p_i^{\alpha_i} \) et \( b=\prod p_i^{\beta_i} \), on a \( \mathrm{PGCD}(a,b)=\prod p_i^{\min(\alpha_i,\beta_i)} \) et \( \mathrm{PPCM}(a,b)=\prod p_i^{\max(\alpha_i,\beta_i)} \). Or pour tout couple d'entiers \( (\alpha_i,\beta_i) \), \( \min(\alpha_i,\beta_i)+\max(\alpha_i,\beta_i)=\alpha_i+\beta_i \), donc \( \mathrm{PGCD}(a,b)\times\mathrm{PPCM}(a,b)=\prod p_i^{\alpha_i+\beta_i}=ab \).

---

## 7. Méthodes

**Méthode 1 — Calculer le PGCD par l'algorithme d'Euclide**
1. Effectuer la division euclidienne de \( a \) par \( b \) (\( a>b \)) : \( a=bq+r \).
2. Recommencer avec \( b \) et \( r \), jusqu'à obtenir un reste nul.
3. Le PGCD est le dernier reste non nul.

**Méthode 2 — Résoudre \( ax+by=c \) dans ℤ**
1. Calculer \( d=\mathrm{PGCD}(a,b) \) et vérifier que \( d\mid c \) (sinon pas de solution).
2. Trouver une solution particulière \( (x_0,y_0) \), souvent par remontée de l'algorithme d'Euclide (identité de Bezout) ou par tâtonnement.
3. Écrire la solution générale \( \left(x_0+k\dfrac bd,\ y_0-k\dfrac ad\right) \), \( k\in\mathbb Z \).

**Méthode 3 — Utiliser les congruences pour résoudre un problème**
1. Traduire le problème en termes de congruences modulo un entier bien choisi.
2. Utiliser la compatibilité des congruences avec les opérations pour simplifier.
3. Tester les résidus possibles (souvent en nombre fini) pour conclure.

**Méthode 4 — Écrire un nombre dans une base donnée**
1. Effectuer des divisions euclidiennes successives par la base \( b \).
2. Les restes successifs (lus de bas en haut) donnent les chiffres de l'écriture en base \( b \).

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Calculer \( \mathrm{PGCD}(252,\ 180) \) par l'algorithme d'Euclide.
*Résolution :* \( 252=180\times1+72 \) ; \( 180=72\times2+36 \) ; \( 72=36\times2+0 \).
*Conclusion :* \( \mathrm{PGCD}(252,180)=36 \).

**Exemple 2.**
*Énoncé :* Résoudre dans ℤ² l'équation \( 15x+9y=6 \).
*Résolution :* \( \mathrm{PGCD}(15,9)=3 \), et \( 3\mid6 \) : il y a des solutions. On simplifie par 3 : \( 5x+3y=2 \). Solution particulière : \( x_0=1,y_0=-1 \) (\( 5-3=2 \) ✓). Solution générale : \( \mathrm{PGCD}(5,3)=1 \), donc \( x=1+3k,\ y=-1-5k \), \( k\in\mathbb Z \).
*Conclusion :* \( S=\{(1+3k,\ -1-5k),\ k\in\mathbb Z\} \).

**Exemple 3.**
*Énoncé :* Déterminer le reste de la division de \( 7^{100} \) par 5.
*Résolution :* \( 7\equiv2\ [5] \), donc \( 7^{100}\equiv2^{100}\ [5] \). Or \( 2^4=16\equiv1\ [5] \), donc \( 2^{100}=(2^4)^{25}\equiv1^{25}=1\ [5] \).
*Conclusion :* Le reste de la division de \( 7^{100} \) par 5 est 1.

**Exemple 4.**
*Énoncé :* Écrire \( 45 \) en base 2.
*Résolution :* \( 45=2\times22+1 \) ; \( 22=2\times11+0 \) ; \( 11=2\times5+1 \) ; \( 5=2\times2+1 \) ; \( 2=2\times1+0 \) ; \( 1=2\times0+1 \). En lisant les restes de bas en haut : \( 101101 \).
*Conclusion :* \( 45=(101101)_2 \). Vérification : \( 32+8+4+1=45 \) ✓.

**Exemple 5.**
*Énoncé :* Montrer, en utilisant le petit théorème de Fermat, que pour tout entier \( n \), \( n^7-n \) est divisible par 7.
*Résolution :* 7 est premier. Par le petit théorème de Fermat (théorème 7), pour tout entier naturel \( n \), \( n^7\equiv n\ [7] \), c'est-à-dire \( 7\mid(n^7-n) \). Le résultat s'étend aux entiers relatifs par un raisonnement similaire (parité de la puissance impaire).
*Conclusion :* \( n^7-n \) est toujours divisible par 7.

---

## 9. Erreurs fréquentes

- **Oublier de vérifier la condition \( d\mid c \)** avant de chercher à résoudre \( ax+by=c \) : si cette condition n'est pas remplie, l'équation n'a aucune solution entière.
- **Confondre PGCD et PPCM** dans les formules ou leur utilisation (le PGCD divise, le PPCM est un multiple).
- **Oublier de simplifier par le PGCD** avant de chercher une solution particulière de \( ax+by=c \), ce qui complique inutilement les calculs.
- **Utiliser le petit théorème de Fermat sans vérifier que le modulo est bien un nombre premier**, ou sans vérifier la condition \( p\nmid x \) pour la forme \( x^{p-1}\equiv1\ [p] \).
- **Erreur d'inversion des restes lors de la conversion en base \( b \)** : bien lire les restes de la dernière division vers la première.

---

## 10. Astuces

- **Astuce de calcul** : pour tester si un entier est premier, il suffit de vérifier qu'il n'est divisible par aucun nombre premier inférieur ou égal à sa racine carrée.
- **Astuce de calcul** : pour retrouver une solution particulière de \( au+bv=d \) (Bezout), remonter l'algorithme d'Euclide étape par étape (méthode de la « remontée »).
- **Astuce de rédaction** : toujours présenter clairement chaque étape de l'algorithme d'Euclide (dividende = diviseur × quotient + reste) pour une lecture facile de la remontée.
- **Astuce pour le Bac** : pour un problème de recherche de reste, essayer d'abord les petites puissances (\( a^1,a^2,a^3,\ldots \)) modulo \( n \) pour repérer une périodicité, souvent la clé de la résolution.
- **Astuce de calcul** : pour une conversion en base \( b \), vérifier son résultat en reconvertissant en base 10 par la formule \( \sum a_ib^i \).

---

## 11. Exercices

### Faciles
1. Calculer \( \mathrm{PGCD}(48,18) \) par l'algorithme d'Euclide.
2. Décomposer 360 en produit de facteurs premiers.
3. Déterminer le reste de la division euclidienne de 100 par 7.
4. Vérifier que 97 est un nombre premier.
5. Convertir \( 25 \) en base 2.

### Moyens
6. Calculer \( \mathrm{PPCM}(24,36) \) à l'aide du PGCD.
7. Résoudre dans ℤ² : \( 7x+5y=3 \).
8. Déterminer le reste de la division de \( 2^{50} \) par 7.
9. Montrer que pour tout entier \( n \), \( n^2+n \) est toujours pair (raisonner par congruences modulo 2).
10. Écrire \( 100 \) en base 16.

### Difficiles
11. Montrer que \( \mathrm{PGCD}(2n+1,\ n) = 1 \) pour tout entier naturel \( n \).
12. Résoudre dans ℤ : \( 24x+18y=90 \), et donner la solution générale.
13. Un fermier a des poules et des lapins. En comptant les têtes, il trouve 35 ; en comptant les pattes, il trouve 94. En utilisant une équation diophantienne, retrouver le nombre de poules et de lapins (chaque solution doit être un entier naturel).
14. Déterminer le reste de la division de \( 3^{2024} \) par 13 (13 est premier), en utilisant le petit théorème de Fermat.
15. Montrer, en utilisant les congruences modulo 9, qu'un entier est divisible par 9 si et seulement si la somme de ses chiffres l'est.

---

## 12. Corrigés détaillés

**1.** \( 48=18\times2+12 \) ; \( 18=12\times1+6 \) ; \( 12=6\times2+0 \). \( \mathrm{PGCD}=6 \).

**2.** \( 360=8\times45=2^3\times45=2^3\times9\times5=2^3\times3^2\times5 \).

**3.** \( 100=7\times14+2 \). Reste : 2.

**4.** \( \sqrt{97}\approx9{,}85 \). On teste les nombres premiers \( \le9 \) : 2,3,5,7. 97 n'est divisible par aucun (97 impair, \( 9+7=16 \) non multiple de 3, ne se termine pas par 0 ou 5, \( 97=7\times13+6 \) non divisible par 7). Donc 97 est premier.

**5.** \( 25=2\times12+1 \) ; \( 12=2\times6+0 \) ; \( 6=2\times3+0 \) ; \( 3=2\times1+1 \) ; \( 1=2\times0+1 \). Restes de bas en haut : \( 11001 \). \( 25=(11001)_2 \).

**6.** \( \mathrm{PGCD}(24,36) \) : \( 36=24\times1+12 \) ; \( 24=12\times2+0 \) : PGCD = 12. \( \mathrm{PPCM}=\dfrac{24\times36}{12}=\dfrac{864}{12}=72 \).

**7.** \( \mathrm{PGCD}(7,5)=1 \), donc solutions. Par tâtonnement : \( 7\times4+5\times(-5)=28-25=3 \) ✓, donc \( (x_0,y_0)=(4,-5) \). Solution générale : \( x=4+5k,\ y=-5-7k \), \( k\in\mathbb Z \).

**8.** \( 2^3=8\equiv1\ [7] \), donc \( 2^{50}=2^{48}\times2^2=(2^3)^{16}\times4\equiv1^{16}\times4=4\ [7] \). Reste : 4.

**9.** \( n^2+n=n(n+1) \), produit de deux entiers consécutifs. Modulo 2 : si \( n\equiv0\ [2] \), \( n(n+1)\equiv0\times1=0\ [2] \) ; si \( n\equiv1\ [2] \), \( n(n+1)\equiv1\times0=0\ [2] \) (car \( n+1\equiv0\ [2] \)). Dans les deux cas, \( n^2+n\equiv0\ [2] \) : toujours pair.

**10.** \( 100=16\times6+4 \) ; \( 6=16\times0+6 \). Restes : \( 6,4 \). \( 100=(64)_{16} \). Vérification : \( 6\times16+4=96+4=100 \) ✓.

**11.** Soit \( d=\mathrm{PGCD}(2n+1,n) \). Alors \( d\mid(2n+1) \) et \( d\mid n \), donc \( d\mid2n \), donc \( d\mid\big((2n+1)-2n\big)=1 \). Donc \( d=1 \).

**12.** \( \mathrm{PGCD}(24,18)=6 \), et \( 6\mid90 \) : solutions existent. Simplification : \( 4x+3y=15 \). Solution particulière : \( x_0=0,y_0=5 \) (\( 0+15=15 \) ✓, mais cherchons une forme standard) : en fait \( 4\times0+3\times5=15 \) ✓. \( \mathrm{PGCD}(4,3)=1 \), donc \( x=0+3k,\ y=5-4k \), \( k\in\mathbb Z \). Solution générale de l'équation initiale : \( x=3k,\ y=5-4k \), \( k\in\mathbb Z \).

**13.** Soit \( p \) le nombre de poules (2 pattes) et \( l \) le nombre de lapins (4 pattes). \( p+l=35 \) et \( 2p+4l=94 \), soit \( p+2l=47 \). En soustrayant : \( (p+2l)-(p+l)=47-35\Rightarrow l=12 \), donc \( p=35-12=23 \).

**14.** 13 est premier, \( 3 \) n'est pas multiple de 13, donc par Fermat \( 3^{12}\equiv1\ [13] \). \( 2024=12\times168+8 \), donc \( 3^{2024}=(3^{12})^{168}\times3^8\equiv3^8\ [13] \). \( 3^2=9,\ 3^4=81\equiv81-6\times13=81-78=3\ [13] \), \( 3^8=(3^4)^2\equiv3^2=9\ [13] \). Reste : 9.

**15.** Tout entier \( N \) s'écrit \( N=\sum a_i10^i \). Or \( 10\equiv1\ [9] \), donc \( 10^i\equiv1\ [9] \) pour tout \( i \). Ainsi \( N\equiv\sum a_i\ [9] \), c'est-à-dire que \( N \) et la somme de ses chiffres ont le même reste modulo 9 ; en particulier, \( N \) est divisible par 9 si et seulement si la somme de ses chiffres l'est.

---

## 13. Questions type Bac

1. *(Type Bac)* Résoudre dans ℤ² l'équation \( 13x-8y=1 \), en utilisant la remontée de l'algorithme d'Euclide pour trouver une solution particulière.
2. *(Type Bac)* Un code de sécurité utilise les congruences modulo 26 pour chiffrer des lettres (A=0, B=1, ..., Z=25) selon \( c\equiv3m+5\ [26] \). Déterminer le chiffré de la lettre correspondant à \( m=7 \) (« H »), puis expliquer comment déchiffrer (en utilisant l'inverse de 3 modulo 26, qui vérifie \( 3\times9\equiv1\ [26] \)).
3. *(Type Bac)* Démontrer que pour tout entier naturel \( n \), \( n^5-n \) est divisible par 30 (indication : utiliser la divisibilité par 2, 3 et 5 séparément, avec le petit théorème de Fermat pour 5).

---

## 14. Résumé

L'arithmétique dans ℤ étudie la divisibilité, les nombres premiers (dont tout entier \( \ge2 \) admet une unique décomposition en produit), le PGCD et le PPCM (liés par \( \mathrm{PGCD}\times\mathrm{PPCM}=ab \)), calculables par l'algorithme d'Euclide. Le théorème de Bezout caractérise les entiers premiers entre eux par l'existence de \( u,v \) tels que \( au+bv=1 \) ; le théorème de Gauss (\( a\mid bc \) et \( a,b \) premiers entre eux \( \Rightarrow a\mid c \)) en découle. Ces outils permettent de résoudre les équations diophantiennes \( ax+by=c \), résolubles si et seulement si \( \mathrm{PGCD}(a,b)\mid c \). Les congruences modulo \( n \), compatibles avec les opérations usuelles, permettent de résoudre des problèmes de reste et de divisibilité, notamment via le petit théorème de Fermat (\( x^p\equiv x\ [p] \) pour \( p \) premier). Les systèmes de numération en base \( b \) (2, 5, 16 notamment) généralisent l'écriture décimale usuelle.

---

## 15. Fiche de révision

- \( b\mid a \iff \exists k,\ a=bk \) ; division euclidienne : \( a=bq+r,\ 0\le r<b \)
- Bezout : \( \mathrm{PGCD}(a,b)=1 \iff \exists u,v,\ au+bv=1 \)
- Gauss : \( a\mid bc \) et \( \mathrm{PGCD}(a,b)=1 \Rightarrow a\mid c \)
- \( \mathrm{PGCD}(a,b)\times\mathrm{PPCM}(a,b)=ab \)
- \( ax+by=c \) résoluble \( \iff \mathrm{PGCD}(a,b)\mid c \) ; solution générale : \( x_0+k\frac bd,\ y_0-k\frac ad \)
- Congruences : \( a\equiv b\ [n] \iff n\mid(a-b) \) ; compatibles avec \( + \) et \( \times \)
- Fermat : \( p \) premier \( \Rightarrow x^p\equiv x\ [p] \) ; si \( p\nmid x \), \( x^{p-1}\equiv1\ [p] \)

---

## 16. Glossaire

- **Divisibilité** : relation \( b\mid a \) signifiant que \( a \) est un multiple de \( b \).
- **PGCD/PPCM** : plus grand commun diviseur / plus petit commun multiple.
- **Identité de Bezout** : relation \( au+bv=d \) reliant deux entiers à leur PGCD.
- **Théorème de Gauss** : propriété de divisibilité liée aux entiers premiers entre eux.
- **Congruence** : relation d'égalité des restes dans une division euclidienne.
- **Système de numération** : représentation d'un entier dans une base donnée.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : divisibilité de base et division euclidienne (premier cycle), notion de nombre premier.

**Ce qui sera utilisé ensuite** : cryptographie et sécurité informatique (applications interdisciplinaires), suites numériques (récurrences arithmétiques liées aux congruences), probabilités (dénombrement combiné à des conditions arithmétiques).

---

## 18. Auto-évaluation

### QCM
1. Le PGCD de deux nombres premiers entre eux vaut :
 a) 0 b) 1 c) leur produit d) leur somme

2. Le théorème de Gauss énonce que si \( a\mid bc \) et \( \mathrm{PGCD}(a,b)=1 \), alors :
 a) \( a\mid b \) b) \( a\mid c \) c) \( b\mid c \) d) \( a=bc \)

3. L'équation \( ax+by=c \) admet des solutions entières si et seulement si :
 a) \( a \) divise \( c \) b) \( b \) divise \( c \) c) \( \mathrm{PGCD}(a,b) \) divise \( c \) d) toujours

### Vrai/Faux
1. Tout entier naturel supérieur à 1 admet une unique décomposition en facteurs premiers. (Vrai)
2. Deux entiers premiers entre eux ont nécessairement un PGCD égal à leur produit. (Faux — le PGCD vaut 1)
3. Les congruences sont compatibles avec l'addition et la multiplication. (Vrai)

### Questions ouvertes
1. Expliquer la méthode de remontée de l'algorithme d'Euclide pour trouver une solution particulière de l'identité de Bezout.
2. Décrire une application concrète des congruences modulo n (autre que celles vues en cours).

---

## Métadonnées RAG

- **Titre** : L'Arithmétique dans ℤ
- **Chapitre** : Algèbre
- **Sous-chapitre** : Divisibilité, nombres premiers, PGCD, PPCM, théorème de Gauss, identité de Bezout, division euclidienne, systèmes de numération, congruences
- **Compétences** : Décomposer en facteurs premiers ; calculer PGCD/PPCM ; résoudre \( ax+by=c \) ; utiliser les congruences et le petit théorème de Fermat
- **Notions** : divisibilité, nombre premier, Bezout, Gauss, algorithme d'Euclide, congruence, système de numération
- **Mots-clés** : arithmétique, PGCD, PPCM, Bezout, Gauss, congruence, Fermat
- **Pré-requis** : divisibilité de base, division euclidienne
- **Niveau** : Terminale S1/S3
- **Temps estimé** : 8h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS1S3-ALG-ARITHMETIQUE-01
- **Résumé (200 mots max)** : Cette leçon, spécifique à la série S1/S3 (nouveauté du programme par rapport aux classes précédentes), couvre l'arithmétique dans ℤ : divisibilité, nombres premiers et décomposition en facteurs premiers, PGCD et PPCM (calculables par l'algorithme d'Euclide, liés par \( \mathrm{PGCD}\times\mathrm{PPCM}=ab \)), théorèmes de Bezout et de Gauss, résolution d'équations diophantiennes \( ax+by=c \), congruences modulo \( n \) et petit théorème de Fermat, et systèmes de numération en base quelconque. Cinq exemples résolus couvrent chaque grande compétence, y compris une application du petit théorème de Fermat. Quinze exercices progressifs, avec corrigés détaillés, incluent des problèmes concrets (poules et lapins, critère de divisibilité par 9, cryptographie simple). Des questions type Bac, un résumé, une fiche de révision et une auto-évaluation complètent la leçon, en lien avec la cryptographie et l'informatique.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS1S3-ARITHM-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : divisibilité, Bezout, Gauss, Euclide

**Bloc 2 — ID: TS1S3-ARITHM-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : congruence, méthode de résolution, base numérique

**Bloc 3 — ID: TS1S3-ARITHM-B3** — Exemples résolus (section 8) — mots-clés : exemple, PGCD, équation diophantienne, Fermat

**Bloc 4 — ID: TS1S3-ARITHM-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, remontée d'Euclide

**Bloc 5 — ID: TS1S3-ARITHM-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, poules et lapins, divisibilité par 9

**Bloc 6 — ID: TS1S3-ARITHM-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Arithmétique, Terminale S1/S3, page 61 — nouveauté du programme signalée dans l'introduction générale)
✓ Exactitude mathématique vérifiée (corrigés recalculés, notamment Fermat et Bezout)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 7 et 8 (série S1/S3)
