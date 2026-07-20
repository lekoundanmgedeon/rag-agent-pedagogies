---
niveau: secondaire
classe: Terminale
serie: S2
serie_alias: [S2, S4]
discipline: Mathématiques
chapitre: Les Équations Différentielles
examen_associe: Baccalauréat
source_document: Lecon_04_Equations_Differentielles_TS2S4.md
---

# Leçon — Les Équations Différentielles (Terminale S2/S4)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Les Équations Différentielles Linéaires |
| **Classe** | Terminale |
| **Série** | S2 / S4 |
| **Chapitre** | Analyse |
| **Sous-chapitre** | Équations différentielles linéaires homogènes et avec second membre, du premier et du second ordre, à coefficients constants |
| **Prérequis** | Fonction exponentielle, dérivation, résolution d'équations du second degré (pour l'équation caractéristique), primitives |
| **Durée estimée** | 6 heures |
| **Compétences visées** | Résoudre une équation différentielle linéaire homogène du premier ou du second ordre à coefficients constants ; résoudre une équation avec second membre ; utiliser une condition initiale pour déterminer la solution particulière |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) reconnaître le type d'équation différentielle, (2) résoudre l'équation homogène associée, (3) trouver une solution particulière avec second membre, (4) déterminer la solution unique vérifiant des conditions initiales données |
| **Mots-clés** | équation différentielle, équation homogène, équation caractéristique, second membre, condition initiale |

---

## 2. Introduction

Une équation différentielle relie une fonction inconnue à ses dérivées. Elle permet de modéliser des phénomènes d'évolution continue : décroissance radioactive, charge/décharge d'un condensateur, oscillations mécaniques, refroidissement d'un corps. En sciences physiques, de nombreuses lois s'expriment naturellement sous forme d'équations différentielles (par exemple \( f'=kf \) pour une croissance ou décroissance exponentielle).

Le programme de Terminale S2/S4 se limite aux équations différentielles **linéaires à coefficients constants**, du premier et du second ordre, sans développer de théorie générale : l'objectif est de savoir résoudre ces équations dans des cas concrets, souvent en lien direct avec les sciences physiques.

Au Baccalauréat, ce chapitre apparaît généralement sous forme d'un exercice indépendant, ou en fin d'un exercice d'analyse portant sur une fonction vérifiant une équation différentielle, avec détermination d'une constante à l'aide d'une condition initiale.

**Applications concrètes** : décharge d'un condensateur (\( RC \dfrac{dq}{dt}+q=0 \)), refroidissement de Newton, circuits électriques oscillants (équation du second ordre).

---

## 3. Définitions

**Définition 1 (Équation différentielle linéaire homogène du premier ordre).** C'est une équation de la forme
$$ y' = ay \quad (a\in\mathbb{R}), $$
d'inconnue une fonction \( y \) dérivable sur \( \mathbb{R} \).

**Définition 2 (Équation différentielle linéaire homogène du second ordre).** C'est une équation de la forme
$$ y'' + py' + qy = 0 \quad (p,q\in\mathbb{R}), $$
d'inconnue une fonction \( y \) deux fois dérivable sur \( \mathbb{R} \).

**Définition 3 (Équation caractéristique).** Pour l'équation \( y''+py'+qy=0 \), on appelle équation caractéristique l'équation du second degré
$$ r^2+pr+q=0 $$
d'inconnue \( r\in\mathbb{C} \).

**Définition 4 (Équation avec second membre).** C'est une équation de la forme \( y'=ay+g(x) \) (premier ordre) ou \( y''+py'+qy=g(x) \) (second ordre), où \( g \) est une fonction donnée, non identiquement nulle.

**Définition 5 (Condition initiale).** Ensemble de valeurs données pour \( y \) (et éventuellement \( y' \)) en un point particulier, permettant de déterminer une solution unique parmi la famille de solutions.

---

## 4. Théorèmes

**Théorème 1 (Solutions de \( y'=ay \) — admis).**
- Énoncé : les solutions sur \( \mathbb{R} \) de \( y'=ay \) sont les fonctions \( x\mapsto Ce^{ax} \), \( C\in\mathbb{R} \) quelconque.
- Existence et unicité : il existe une unique solution vérifiant une condition initiale donnée \( y(x_0)=y_0 \), à savoir \( C=y_0e^{-ax_0} \).

**Théorème 2 (Solutions de \( y''+py'+qy=0 \) selon le signe du discriminant de l'équation caractéristique).**
- Énoncé : soit \( \Delta=p^2-4q \) le discriminant de l'équation caractéristique \( r^2+pr+q=0 \).
 - Si \( \Delta>0 \) : deux racines réelles distinctes \( r_1,r_2 \) ; les solutions sont \( y=Ae^{r_1x}+Be^{r_2x} \), \( A,B\in\mathbb{R} \).
 - Si \( \Delta=0 \) : une racine double \( r_0=-\dfrac p2 \) ; les solutions sont \( y=(Ax+B)e^{r_0x} \), \( A,B\in\mathbb{R} \).
 - Si \( \Delta<0 \) : deux racines complexes conjuguées \( r=\alpha\pm i\beta \) ; les solutions sont \( y=e^{\alpha x}(A\cos\beta x+B\sin\beta x) \), \( A,B\in\mathbb{R} \).
- Existence et unicité (admises) : une unique solution correspond à un couple de conditions initiales \( (y(x_0),y'(x_0)) \).

**Théorème 3 (Structure des solutions avec second membre).**
- Énoncé : la solution générale de \( y'=ay+g(x) \) (ou \( y''+py'+qy=g(x) \)) est la somme d'une solution particulière \( y_p \) de l'équation avec second membre et de la solution générale \( y_h \) de l'équation homogène associée : \( y=y_h+y_p \).

---

## 5. Propriétés

1. Toute combinaison linéaire de solutions de l'équation homogène \( y'=ay \) (resp. \( y''+py'+qy=0 \)) est encore solution de cette équation.
2. Pour un second membre constant \( g(x)=c \) dans \( y'=ay+c \) (\( a\neq0 \)), une solution particulière constante est \( y_p=-\dfrac{c}{a} \).
3. Pour un second membre \( g(x)=A\cos\alpha x+B\sin\alpha x \) dans \( y''+\omega^2y=A\cos\alpha x+B\sin\alpha x \) (avec \( \alpha\neq\omega \)), on cherche une solution particulière de la même forme \( y_p=a\cos\alpha x+b\sin\alpha x \).
4. Le nombre de constantes arbitraires dans la solution générale est égal à l'ordre de l'équation (1 constante pour le premier ordre, 2 pour le second ordre).

---

## 6. Démonstrations

**Démonstration du théorème 1 (cas \( y'=ay \))** :
Soit \( y \) une solution de \( y'=ay \). Considérons \( z(x)=y(x)e^{-ax} \). Alors
$$ z'(x) = y'(x)e^{-ax} - a\,y(x)e^{-ax} = e^{-ax}\big(y'(x)-ay(x)\big) = 0 $$
car \( y'=ay \). Donc \( z \) est constante, \( z(x)=C \), soit \( y(x)=Ce^{ax} \). Réciproquement, on vérifie que toute fonction \( Ce^{ax} \) est bien solution : \( (Ce^{ax})'=aCe^{ax} \). ✓

**Démonstration (esquisse) du théorème 2, cas \( \Delta>0 \)** :
On vérifie d'abord que \( e^{r_1x} \) et \( e^{r_2x} \) sont solutions, en substituant dans l'équation : \( (e^{r_ix})''+p(e^{r_ix})'+q(e^{r_ix}) = e^{r_ix}(r_i^2+pr_i+q)=0 \) car \( r_i \) est racine de l'équation caractéristique. L'existence et l'unicité de la solution générale sous cette forme, ainsi que la preuve qu'il n'y a pas d'autres solutions, sont admises au niveau Terminale.

**Démonstration de la propriété 2** :
On cherche \( y_p \) constante telle que \( y_p'=ay_p+c \), soit \( 0=ay_p+c \), d'où \( y_p=-\dfrac ca \) (pour \( a\neq0 \)).

---

## 7. Méthodes

**Méthode 1 — Résoudre \( y'=ay \) avec condition initiale**
1. Écrire la solution générale \( y=Ce^{ax} \).
2. Utiliser la condition initiale \( y(x_0)=y_0 \) pour déterminer \( C \).

**Méthode 2 — Résoudre \( y''+py'+qy=0 \)**
1. Écrire l'équation caractéristique \( r^2+pr+q=0 \) et calculer \( \Delta \).
2. Selon le signe de \( \Delta \), écrire la forme générale de la solution (théorème 2).
3. Utiliser les conditions initiales \( y(x_0) \) et \( y'(x_0) \) pour déterminer les deux constantes.

**Méthode 3 — Résoudre une équation avec second membre**
1. Résoudre l'équation homogène associée (\( y_h \)).
2. Chercher une solution particulière \( y_p \) de même forme que le second membre \( g(x) \) (constante si \( g \) constant, polynôme de même degré si \( g \) polynomial, etc.).
3. La solution générale est \( y=y_h+y_p \).
4. Utiliser les conditions initiales pour déterminer les constantes restantes.

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Résoudre \( y'=3y \) avec \( y(0)=2 \).
*Résolution :* Solution générale : \( y=Ce^{3x} \). Condition initiale : \( y(0)=C=2 \).
*Conclusion :* \( y(x)=2e^{3x} \).

**Exemple 2.**
*Énoncé :* Résoudre \( y''-3y'+2y=0 \).
*Résolution :* Équation caractéristique : \( r^2-3r+2=0 \), \( \Delta=9-8=1>0 \), racines \( r_1=1,\ r_2=2 \).
*Conclusion :* \( y(x)=Ae^x+Be^{2x} \), \( A,B\in\mathbb{R} \).

**Exemple 3.**
*Énoncé :* Résoudre \( y''-4y'+4y=0 \), avec \( y(0)=1 \) et \( y'(0)=0 \).
*Résolution :* Équation caractéristique \( r^2-4r+4=0 \), \( \Delta=16-16=0 \), racine double \( r_0=2 \). Solution générale : \( y=(Ax+B)e^{2x} \). \( y'(x)=Ae^{2x}+2(Ax+B)e^{2x} \). Conditions : \( y(0)=B=1 \) ; \( y'(0)=A+2B=0\Rightarrow A=-2 \).
*Conclusion :* \( y(x)=(-2x+1)e^{2x} \).

**Exemple 4.**
*Énoncé :* Résoudre \( y''+y=0 \), avec \( y(0)=1 \) et \( y'(0)=1 \).
*Résolution :* Équation caractéristique \( r^2+1=0 \), \( \Delta=-4<0 \), racines \( r=\pm i \) (\( \alpha=0,\ \beta=1 \)). Solution générale : \( y=A\cos x+B\sin x \). \( y(0)=A=1 \) ; \( y'(x)=-A\sin x+B\cos x \), \( y'(0)=B=1 \).
*Conclusion :* \( y(x)=\cos x+\sin x \).

**Exemple 5.**
*Énoncé :* Résoudre \( y'=2y+6 \) avec \( y(0)=1 \).
*Résolution :* Solution particulière constante : \( y_p=-\dfrac{6}{2}=-3 \). Solution homogène : \( y_h=Ce^{2x} \). Solution générale : \( y=Ce^{2x}-3 \). Condition initiale : \( y(0)=C-3=1\Rightarrow C=4 \).
*Conclusion :* \( y(x)=4e^{2x}-3 \).

---

## 9. Erreurs fréquentes

- **Oublier de vérifier le signe de \( \Delta \)** avant d'écrire la forme de la solution de \( y''+py'+qy=0 \) : les trois cas donnent des formes très différentes.
- **Confondre l'équation caractéristique** \( r^2+pr+q=0 \) **avec l'équation différentielle elle-même**.
- **Utiliser une seule condition initiale pour une équation du second ordre** : il en faut deux (\( y(x_0) \) et \( y'(x_0) \)) pour déterminer les deux constantes.
- **Chercher une solution particulière de mauvaise forme** : par exemple, chercher une solution particulière constante alors que le second membre est un polynôme non constant, ou l'inverse.
- **Erreur de signe dans le calcul de la solution particulière constante** \( y_p=-\dfrac ca \) : bien vérifier le signe en réinjectant dans l'équation.

---

## 10. Astuces

- **Astuce de calcul** : pour résoudre l'équation caractéristique, utiliser les mêmes techniques que pour une équation du second degré classique (calcul du discriminant, formules des racines).
- **Astuce de rédaction** : toujours écrire explicitement l'équation caractéristique associée avant de donner la solution, même si le résultat semble évident.
- **Astuce pour le Bac** : en cas de second membre trigonométrique dans une équation du second ordre du type oscillateur (\( y''+\omega^2y=\ldots \)), chercher une solution particulière de la forme \( a\cos(\alpha x)+b\sin(\alpha x) \) et substituer directement pour identifier \( a \) et \( b \) par identification des coefficients.
- **Astuce de vérification** : après avoir trouvé une solution, toujours vérifier en substituant dans l'équation différentielle initiale (calcul de \( y' \), \( y'' \) et report), c'est le moyen le plus sûr de détecter une erreur.

---

## 11. Exercices

### Faciles
1. Résoudre \( y'=5y \).
2. Résoudre \( y'=-2y \) avec \( y(0)=3 \).
3. Résoudre \( y''-y=0 \).
4. Résoudre \( y''+4y=0 \).
5. Résoudre \( y''+2y'+y=0 \).

### Moyens
6. Résoudre \( y''-5y'+6y=0 \) avec \( y(0)=2 \) et \( y'(0)=3 \).
7. Résoudre \( y'=4y-8 \) avec \( y(0)=0 \).
8. Résoudre \( y''+9y=0 \) avec \( y(0)=0 \) et \( y'(0)=3 \).
9. Résoudre \( y''-2y'+y=0 \) avec \( y(0)=1 \) et \( y'(0)=0 \).
10. Une substance radioactive se désintègre selon \( N'(t)=-\lambda N(t) \), avec \( N(0)=N_0 \). Exprimer \( N(t) \) et la demi-vie \( T \) en fonction de \( \lambda \).

### Difficiles
11. Résoudre \( y'=3y+2x \) (chercher une solution particulière affine \( y_p=ax+b \)).
12. Résoudre \( y''-y'-2y=0 \) avec \( y(0)=1 \) et \( y'(0)=-1 \), puis étudier la limite de \( y(x) \) quand \( x\to+\infty \).
13. Un circuit RLC vérifie \( q''+\dfrac{R}{L}q'+\dfrac{1}{LC}q=0 \). Discuter, selon le signe de \( \Delta=\left(\dfrac RL\right)^2-\dfrac{4}{LC} \), la nature du régime (apériodique, critique, oscillant).
14. Résoudre \( y''+4y=\cos x \) (second membre non résonant, chercher \( y_p=a\cos x \)).
15. Résoudre \( y'' + y' - 6y = 0 \) avec \( y(0) = 0,\ y'(0) = 5 \), puis déterminer le signe de \( y(x) \) pour \( x > 0 \).

---

## 12. Corrigés détaillés

**1.** \( y=Ce^{5x} \), \( C\in\mathbb{R} \).

**2.** \( y=Ce^{-2x} \), \( y(0)=C=3 \), donc \( y=3e^{-2x} \).

**3.** \( r^2-1=0\Rightarrow r=\pm1 \) ; \( y=Ae^x+Be^{-x} \).

**4.** \( r^2+4=0\Rightarrow r=\pm2i \) (\( \alpha=0,\beta=2 \)) ; \( y=A\cos2x+B\sin2x \).

**5.** \( r^2+2r+1=(r+1)^2=0\Rightarrow r_0=-1 \) (racine double) ; \( y=(Ax+B)e^{-x} \).

**6.** \( r^2-5r+6=0\Rightarrow(r-2)(r-3)=0\Rightarrow r_1=2,r_2=3 \). \( y=Ae^{2x}+Be^{3x} \). \( y(0)=A+B=2 \) ; \( y'(x)=2Ae^{2x}+3Be^{3x} \), \( y'(0)=2A+3B=3 \). En résolvant : \( A+B=2\Rightarrow A=2-B \) ; \( 2(2-B)+3B=3\Rightarrow4+B=3\Rightarrow B=-1,\ A=3 \). Donc \( y(x)=3e^{2x}-e^{3x} \).

**7.** \( y_p=-\dfrac{-8}4=2 \) ; \( y_h=Ce^{4x} \) ; \( y=Ce^{4x}+2 \) ; \( y(0)=C+2=0\Rightarrow C=-2 \) ; \( y(x)=-2e^{4x}+2 \).

**8.** \( r^2+9=0\Rightarrow r=\pm3i \) ; \( y=A\cos3x+B\sin3x \) ; \( y(0)=A=0 \) ; \( y'(x)=-3A\sin3x+3B\cos3x \), \( y'(0)=3B=3\Rightarrow B=1 \) ; \( y(x)=\sin3x \).

**9.** \( r^2-2r+1=(r-1)^2=0\Rightarrow r_0=1 \) ; \( y=(Ax+B)e^x \) ; \( y(0)=B=1 \) ; \( y'(x)=Ae^x+(Ax+B)e^x \), \( y'(0)=A+B=0\Rightarrow A=-1 \) ; \( y(x)=(1-x)e^x \).

**10.** \( N(t)=N_0e^{-\lambda t} \). Demi-vie : \( N(T)=\dfrac{N_0}2\Rightarrow e^{-\lambda T}=\dfrac12\Rightarrow T=\dfrac{\ln2}{\lambda} \).

**11.** On cherche \( y_p=ax+b \) : \( y_p'=a \) ; l'équation devient \( a=3(ax+b)+2x=3ax+3b+2x \), donc par identification : coefficient de \( x \) : \( 0=3a+2\Rightarrow a=-\frac23 \) ; terme constant : \( a=3b\Rightarrow b=\frac a3=-\frac29 \). Solution générale : \( y=Ce^{3x}-\dfrac23x-\dfrac29 \).

**12.** \( r^2-r-2=0\Rightarrow(r-2)(r+1)=0\Rightarrow r_1=2,r_2=-1 \). \( y=Ae^{2x}+Be^{-x} \). \( y(0)=A+B=1 \) ; \( y'(x)=2Ae^{2x}-Be^{-x} \), \( y'(0)=2A-B=-1 \). En résolvant : \( A+B=1,\ 2A-B=-1\Rightarrow 3A=0\Rightarrow A=0,B=1 \). Donc \( y(x)=e^{-x} \), et \( \lim_{x\to+\infty}y(x)=0 \).

**13.** Si \( \Delta>0 \) : régime apériodique (deux exponentielles réelles décroissantes, pas d'oscillation). Si \( \Delta=0 \) : régime critique (retour le plus rapide sans oscillation). Si \( \Delta<0 \) : régime oscillant amorti (produit d'une exponentielle décroissante par une fonction sinusoïdale, car la partie réelle des racines complexes est négative si \( R,L,C>0 \)).

**14.** \( r^2+4=0\Rightarrow y_h=A\cos2x+B\sin2x \). Second membre \( \cos x \), non résonant (car \( 1\neq2 \)) : on cherche \( y_p=a\cos x \) (par symétrie, pas de terme en \( \sin x \) car le second membre n'en comporte pas et l'équation est paire en \( x\to-x \)) : \( y_p''=-a\cos x \), donc \( -a\cos x+4a\cos x=\cos x\Rightarrow3a=1\Rightarrow a=\frac13 \). Solution générale : \( y=A\cos2x+B\sin2x+\dfrac13\cos x \).

**15.** \( r^2+r-6=0\Rightarrow(r-2)(r+3)=0\Rightarrow r_1=2,r_2=-3 \). \( y=Ae^{2x}+Be^{-3x} \). \( y(0)=A+B=0\Rightarrow B=-A \). \( y'(x)=2Ae^{2x}-3Be^{-3x} \), \( y'(0)=2A-3B=5\Rightarrow2A+3A=5\Rightarrow A=1,B=-1 \). Donc \( y(x)=e^{2x}-e^{-3x} \). Pour \( x>0 \), \( e^{2x}>1>e^{-3x} \), donc \( y(x)>0 \).

---

## 13. Questions type Bac

1. *(Type Bac)* La température \( \theta(t) \) d'un corps plongé dans un milieu à température constante \( \theta_0=20 \) vérifie la loi de Newton \( \theta'(t)=-k(\theta(t)-\theta_0) \). Montrer que \( \theta(t)-\theta_0 \) vérifie une équation homogène, en déduire \( \theta(t) \), puis déterminer \( k \) sachant que \( \theta(0)=100 \) et \( \theta(10)=60 \).
2. *(Type Bac)* Résoudre \( y''+2y'+5y=0 \), et donner l'allure de la courbe représentative d'une solution particulière (amortissement, oscillation).
3. *(Type Bac)* On considère l'équation différentielle \( y'-2y=4x-3 \). Vérifier qu'une solution particulière est de la forme \( y_p=ax+b \), la déterminer, puis donner la solution générale.

---

## 14. Résumé

Une équation différentielle linéaire homogène du premier ordre \( y'=ay \) a pour solutions \( y=Ce^{ax} \). Une équation homogène du second ordre \( y''+py'+qy=0 \) se résout via son équation caractéristique \( r^2+pr+q=0 \) : la forme des solutions dépend du signe du discriminant (exponentielles réelles si \( \Delta>0 \), exponentielle × polynôme si \( \Delta=0 \), exponentielle × sinusoïde si \( \Delta<0 \)). Pour une équation avec second membre, la solution générale est la somme de la solution de l'équation homogène et d'une solution particulière de même forme que le second membre. Les constantes d'intégration (une pour le premier ordre, deux pour le second ordre) se déterminent à l'aide de conditions initiales sur \( y \) (et \( y' \) pour le second ordre).

---

## 15. Fiche de révision

- \( y'=ay \Rightarrow y=Ce^{ax} \)
- \( y''+py'+qy=0 \), équation caractéristique \( r^2+pr+q=0 \), \( \Delta=p^2-4q \) :
 - \( \Delta>0 \) : \( y=Ae^{r_1x}+Be^{r_2x} \)
 - \( \Delta=0 \) : \( y=(Ax+B)e^{r_0x} \)
 - \( \Delta<0 \), \( r=\alpha\pm i\beta \) : \( y=e^{\alpha x}(A\cos\beta x+B\sin\beta x) \)
- Second membre : \( y=y_h+y_p \), \( y_p \) de même forme que \( g(x) \)
- 1 condition initiale (1er ordre) ou 2 (2nd ordre : \( y(x_0), y'(x_0) \))

---

## 16. Glossaire

- **Équation caractéristique** : équation du second degré associée à une équation différentielle du second ordre.
- **Équation homogène** : équation différentielle sans second membre (membre de droite nul).
- **Second membre** : terme non nul ajouté à droite de l'équation différentielle.
- **Solution particulière** : une solution spécifique de l'équation avec second membre.
- **Condition initiale** : valeur(s) imposée(s) à la solution (et sa dérivée) en un point donné.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : fonction exponentielle, dérivation, résolution d'équations du second degré, fonctions trigonométriques.

**Ce qui sera utilisé ensuite** : applications en sciences physiques (circuits électriques, mécanique), modélisation de phénomènes continus, lien conceptuel avec les suites récurrentes (discrétisation).

---

## 18. Auto-évaluation

### QCM
1. La solution générale de \( y'=ay \) est :
 a) \( y=a e^x \) b) \( y=Ce^{ax} \) c) \( y=C+ax \) d) \( y=ax+C \)

2. Si \( \Delta=0 \) pour \( y''+py'+qy=0 \), la solution générale est :
 a) \( Ae^{r_1x}+Be^{r_2x} \) b) \( (Ax+B)e^{r_0x} \) c) \( A\cos(r_0x)+B\sin(r_0x) \) d) \( Ce^{r_0x} \)

3. Pour déterminer les deux constantes d'une équation du second ordre, il faut :
 a) une condition initiale b) deux conditions initiales (\( y \) et \( y' \)) c) trois conditions d) aucune

### Vrai/Faux
1. La solution générale d'une équation avec second membre est la somme de la solution homogène et d'une solution particulière. (Vrai)
2. L'équation caractéristique de \( y''+py'+qy=0 \) est \( y^2+py+q=0 \). (Faux — c'est \( r^2+pr+q=0 \), en \( r \), pas en \( y \))
3. Si \( \Delta<0 \), les solutions de \( y''+py'+qy=0 \) font intervenir des fonctions trigonométriques. (Vrai)

### Questions ouvertes
1. Expliquer pourquoi la solution générale d'une équation différentielle linéaire du second ordre comporte exactement deux constantes arbitraires.
2. Décrire, en une phrase pour chaque cas, l'allure des solutions de \( y''+py'+qy=0 \) selon le signe de \( \Delta \).

---

## Métadonnées RAG

- **Titre** : Les Équations Différentielles Linéaires
- **Chapitre** : Analyse
- **Sous-chapitre** : Équations différentielles linéaires homogènes et avec second membre, du premier et du second ordre, à coefficients constants
- **Compétences** : Résoudre une équation homogène (1er ou 2nd ordre) ; résoudre une équation avec second membre ; utiliser des conditions initiales
- **Notions** : équation caractéristique, discriminant, solution homogène, solution particulière
- **Mots-clés** : équation différentielle, équation caractéristique, second membre, condition initiale
- **Pré-requis** : exponentielle, dérivation, équations du second degré
- **Niveau** : Terminale S2/S4
- **Temps estimé** : 6h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS2S4-ANA-EQDIFF-01
- **Résumé (200 mots max)** : Cette leçon présente la résolution des équations différentielles linéaires à coefficients constants, du premier ordre (\( y'=ay \), solutions \( Ce^{ax} \)) et du second ordre (\( y''+py'+qy=0 \), résolue via l'équation caractéristique \( r^2+pr+q=0 \) dont le signe du discriminant détermine la forme des solutions : exponentielles réelles, exponentielle-polynôme, ou exponentielle-sinusoïde). La leçon traite également les équations avec second membre, résolues en sommant la solution homogène et une solution particulière de même forme que le second membre. Cinq exemples résolus illustrent chaque cas, notamment avec conditions initiales. Quinze exercices progressifs incluent des applications physiques (radioactivité, circuits RLC, loi de refroidissement de Newton). Des questions type Bac, un résumé, une fiche de révision et une auto-évaluation complètent la leçon, qui prolonge l'étude de l'exponentielle et prépare les applications interdisciplinaires en sciences physiques.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS2S4-EQDIFF-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : équation caractéristique, discriminant, ordre

**Bloc 2 — ID: TS2S4-EQDIFF-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : solution particulière, second membre, méthode de résolution

**Bloc 3 — ID: TS2S4-EQDIFF-B3** — Exemples résolus (section 8) — mots-clés : exemple, condition initiale, oscillateur

**Bloc 4 — ID: TS2S4-EQDIFF-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, vérification

**Bloc 5 — ID: TS2S4-EQDIFF-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, radioactivité, circuit RLC

**Bloc 6 — ID: TS2S4-EQDIFF-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Équations différentielles linéaires, Terminale S2/S4, page 77)
✓ Exactitude mathématique vérifiée (corrigés recalculés, y compris identification de solutions particulières)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 1, 2 et 3
