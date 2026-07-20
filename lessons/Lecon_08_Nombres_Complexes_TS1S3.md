---
niveau: secondaire
classe: Terminale
serie: S1
serie_alias: [S1, S3]
discipline: Mathématiques
chapitre: Les Nombres Complexes
examen_associe: Baccalauréat
source_document: Lecon_08_Nombres_Complexes_TS1S3.md
---

# Leçon — Les Nombres Complexes (Terminale S1/S3)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Les Nombres Complexes |
| **Classe** | Terminale |
| **Série** | S1 / S3 |
| **Chapitre** | Algèbre |
| **Sous-chapitre** | Forme algébrique, trigonométrique, exponentielle ; applications de ℂ dans ℂ ; transformation \( p\cos x+q\sin x \) ; résolution d'équations du 3ᵉ degré |
| **Prérequis** | Trigonométrie, résolution d'équations du second degré, notion de fonction, vecteurs et repérage plan |
| **Durée estimée** | 10 heures |
| **Compétences visées** | Déterminer les différentes écritures d'un nombre complexe ; interpréter module et argument dans des problèmes de distance et d'angle ; connaître et utiliser les formules d'Euler, de Moivre et du binôme de Newton ; transformer \( p\cos x+q\sin x \) ; résoudre une équation du 3ᵉ degré connaissant une racine ; utiliser les applications de ℂ dans ℂ en géométrie |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) manipuler les trois formes d'un nombre complexe, (2) utiliser les formules d'Euler et de Moivre pour linéariser ou développer, (3) transformer une expression \( p\cos x+q\sin x \), (4) résoudre une équation du 3ᵉ degré à l'aide d'une racine connue, (5) utiliser les applications complexes \( z\mapsto az+b \), \( z\mapsto e^{i\theta}z \) pour étudier des configurations géométriques |
| **Mots-clés** | nombre complexe, module, argument, formule de Moivre, formule d'Euler, application de ℂ dans ℂ, transformation trigonométrique |

---

## 2. Introduction

Les nombres complexes, déjà étudiés en série S2/S4, sont ici approfondis avec une exigence supplémentaire : la série S1/S3 introduit les **applications de ℂ dans ℂ** (translations, rotations, homothéties complexes vues comme applications \( z\mapsto az+b \)), la **transformation \( p\cos x+q\sin x \)** (très utile en physique des oscillations), et la **résolution d'équations du troisième degré** connaissant une racine.

Ce chapitre reste central pour la préparation aux études supérieures scientifiques : il prépare directement l'étude des similitudes planes (géométrie), et la maîtrise des nombres complexes est indispensable en physique (signaux, électricité) comme en mathématiques supérieures (analyse complexe, algèbre linéaire).

Au Baccalauréat S1/S3, ce chapitre donne lieu à des exercices riches associant calcul algébrique, interprétation géométrique et parfois lien avec les suites (suite géométrique complexe).

**Applications concrètes** : représentation des signaux en physique (transformation \( p\cos x+q\sin x = r\cos(x-\varphi) \)), étude des similitudes planes, résolution de problèmes de géométrie par les affixes.

---

## 3. Définitions

**Définition 1 (Nombre complexe, forme algébrique).** \( z=a+ib \), \( a,b\in\mathbb R \), \( i^2=-1 \). \( a=\mathrm{Re}(z) \), \( b=\mathrm{Im}(z) \).

**Définition 2 (Conjugué, module, argument).** \( \bar z=a-ib \) ; \( |z|=\sqrt{a^2+b^2} \) ; pour \( z\neq0 \), \( \arg(z) \) est une mesure de l'angle \( (\vec u,\overrightarrow{OM}) \), \( M \) image de \( z \), définie modulo \( 2\pi \).

**Définition 3 (Formes trigonométrique et exponentielle).** \( z=r(\cos\theta+i\sin\theta)=re^{i\theta} \), \( r=|z|,\theta=\arg z \).

**Définition 4 (Application de ℂ dans ℂ).** Une application de ℂ dans ℂ associe à tout nombre complexe \( z \) un nombre complexe \( z' \), souvent noté \( z\mapsto z' \). Le programme retient en particulier : \( z\mapsto z+z_0 \) (translation), \( z\mapsto az \) (homothétie/rotation selon \( a \)), \( z\mapsto e^{i\theta}z \) (rotation d'angle \( \theta \)), \( z\mapsto az+z_0 \) (similitude directe, \( a\in\mathbb C^*,\ z_0\in\mathbb C \)).

**Définition 5 (Racine n-ième d'un nombre complexe).** \( \zeta \) est une racine n-ième de \( z \) si \( \zeta^n=z \).

---

## 4. Théorèmes

**Théorème 1 (Module et argument d'un produit, d'un quotient — rappel).**
- Énoncé : \( |z_1z_2|=|z_1||z_2| \), \( \arg(z_1z_2)=\arg z_1+\arg z_2\ [2\pi] \) ; de même pour un quotient avec soustraction des arguments.

**Théorème 2 (Formule de Moivre).**
- Énoncé : pour tout \( n\in\mathbb Z \) et tout réel \( \theta \), \( (\cos\theta+i\sin\theta)^n=\cos(n\theta)+i\sin(n\theta) \).

**Théorème 3 (Formules d'Euler).**
- Énoncé : \( \cos\theta=\dfrac{e^{i\theta}+e^{-i\theta}}2 \), \( \sin\theta=\dfrac{e^{i\theta}-e^{-i\theta}}{2i} \). Utilisées pour la linéarisation de polynômes trigonométriques (degré \( \le5 \) au programme).

**Théorème 4 (Formule du binôme de Newton).**
- Énoncé : pour tous \( a,b\in\mathbb C \) et \( n\in\mathbb N \), \( (a+b)^n=\displaystyle\sum_{k=0}^n\binom nk a^kb^{n-k} \).

**Théorème 5 (Racines n-ièmes d'un nombre complexe non nul).**
- Énoncé : soit \( z=re^{i\theta}\neq0 \). Les racines n-ièmes de \( z \) sont les \( n \) nombres complexes
$$ \zeta_k = r^{1/n}\,e^{i\left(\frac\theta n+\frac{2k\pi}n\right)}, \qquad k=0,1,\ldots,n-1. $$
- Interprétation géométrique : les images des \( \zeta_k \) sont les sommets d'un polygone régulier à \( n \) côtés, inscrit dans le cercle de centre \( O \) et de rayon \( r^{1/n} \).

**Théorème 6 (Transformation de \( p\cos x+q\sin x \)).**
- Énoncé : pour \( p,q\in\mathbb R \) non tous deux nuls, en posant \( p+iq=re^{i\varphi} \) (\( r=\sqrt{p^2+q^2} \)), on a \( p\cos x+q\sin x = r\cos(x-\varphi) \).
- Application : résolution de \( p\cos x+q\sin x=k \) en se ramenant à \( \cos(x-\varphi)=\dfrac kr \).

**Théorème 7 (Applications de ℂ dans ℂ et configurations géométriques).**
- Énoncé : l'application \( z\mapsto az+z_0 \) (\( a\in\mathbb C^*,\ z_0\in\mathbb C \)) est une similitude directe de rapport \( |a| \) et d'angle \( \arg(a) \) ; si \( |a|=1 \) c'est une rotation (ou l'identité si \( a=1 \)) ; l'application \( z\mapsto z+z_0 \) est une translation de vecteur d'affixe \( z_0 \).

---

## 5. Propriétés

1. \( z\bar z=|z|^2 \) ; \( \overline{z_1+z_2}=\bar z_1+\bar z_2 \) ; \( \overline{z_1z_2}=\bar z_1\bar z_2 \).
2. \( AB=|z_B-z_A| \) ; angle \( (\vec u,\overrightarrow{AB})=\arg(z_B-z_A)\ [2\pi] \).
3. \( \dfrac{z_C-z_A}{z_B-z_A} \) réel \( \iff A,B,C \) alignés ; imaginaire pur \( \iff (AC)\perp(AB) \).
4. Toute équation du 3ᵉ degré à coefficients réels admet au moins une racine réelle ; si elle admet une racine complexe non réelle, sa conjuguée est aussi racine.
5. La somme des racines n-ièmes de l'unité (pour \( n\ge2 \)) est nulle.

---

## 6. Démonstrations

**Démonstration du théorème 2 (Moivre), par récurrence pour \( n\in\mathbb N \)** :
- Initialisation \( n=0 \) : \( (\cos\theta+i\sin\theta)^0=1=\cos0+i\sin0 \).
- Hérédité : si \( (\cos\theta+i\sin\theta)^n=\cos n\theta+i\sin n\theta \), alors en multipliant par \( \cos\theta+i\sin\theta \) et en utilisant les formules d'addition trigonométriques :
$$ (\cos n\theta+i\sin n\theta)(\cos\theta+i\sin\theta) = \cos(n\theta+\theta)+i\sin(n\theta+\theta) = \cos((n+1)\theta)+i\sin((n+1)\theta). $$
- Conclusion par récurrence ; le cas \( n\in\mathbb Z^- \) s'obtient en utilisant \( z^{-n}=1/z^n \).

**Démonstration du théorème 5 (racines n-ièmes)** :
On cherche \( \zeta=\rho e^{i\alpha} \) tel que \( \zeta^n=z \), soit \( \rho^ne^{in\alpha}=re^{i\theta} \). Par égalité des modules et des arguments (modulo \( 2\pi \)) : \( \rho^n=r\Rightarrow\rho=r^{1/n} \), et \( n\alpha=\theta+2k\pi\Rightarrow\alpha=\dfrac\theta n+\dfrac{2k\pi}n \), pour \( k\in\mathbb Z \). Les valeurs de \( \alpha \) distinctes modulo \( 2\pi \) correspondent à \( k=0,1,\ldots,n-1 \) : il y a donc exactement \( n \) racines n-ièmes distinctes.

**Démonstration du théorème 6 (transformation \( p\cos x+q\sin x \))** :
En posant \( p+iq=re^{i\varphi} \) (avec \( r=\sqrt{p^2+q^2} \), donc \( p=r\cos\varphi,\ q=r\sin\varphi \)) :
$$ p\cos x+q\sin x = r\cos\varphi\cos x+r\sin\varphi\sin x = r\cos(x-\varphi) $$
en utilisant la formule d'addition \( \cos(x-\varphi)=\cos x\cos\varphi+\sin x\sin\varphi \).

---

## 7. Méthodes

**Méthode 1 — Résoudre une équation du 3ᵉ degré connaissant une racine**
1. Vérifier que la racine donnée \( z_0 \) annule bien le polynôme.
2. Factoriser le polynôme par \( (z-z_0) \) (division ou identification des coefficients).
3. Résoudre l'équation du second degré restante (dans \( \mathbb C \) si nécessaire).

**Méthode 2 — Transformer et résoudre \( p\cos x+q\sin x=k \)**
1. Calculer \( r=\sqrt{p^2+q^2} \) et déterminer \( \varphi \) tel que \( \cos\varphi=\dfrac pr,\ \sin\varphi=\dfrac qr \).
2. Écrire \( p\cos x+q\sin x = r\cos(x-\varphi) \).
3. Résoudre \( \cos(x-\varphi)=\dfrac kr \) (si \( |k|\le r \)) par les méthodes usuelles de résolution trigonométrique.

**Méthode 3 — Étudier une application \( z\mapsto az+b \) comme similitude**
1. Identifier \( a \) et \( b \) dans l'écriture \( z'=az+b \).
2. Le rapport de la similitude est \( |a| \), l'angle est \( \arg(a) \).
3. Le centre \( \Omega \) (point fixe si \( a\neq1 \)) vérifie \( \omega=a\omega+b \), soit \( \omega=\dfrac{b}{1-a} \).

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Linéariser \( \sin^4\theta \) à l'aide des formules d'Euler.
*Résolution :* \( \sin\theta=\dfrac{e^{i\theta}-e^{-i\theta}}{2i} \), donc \( \sin^4\theta = \dfrac{1}{16}\left(e^{i\theta}-e^{-i\theta}\right)^4 \). En développant par le binôme de Newton :
$$ (e^{i\theta}-e^{-i\theta})^4 = e^{4i\theta}-4e^{2i\theta}+6-4e^{-2i\theta}+e^{-4i\theta}. $$
On regroupe : \( = 2\cos4\theta-8\cos2\theta+6 \). Donc \( \sin^4\theta=\dfrac1{16}(2\cos4\theta-8\cos2\theta+6)=\dfrac18\cos4\theta-\dfrac12\cos2\theta+\dfrac38 \).
*Conclusion :* \( \sin^4\theta = \dfrac18\cos4\theta-\dfrac12\cos2\theta+\dfrac38 \).

**Exemple 2.**
*Énoncé :* Résoudre \( z^3-6z^2+13z-10=0 \), sachant que 2 est une racine.
*Résolution :* On vérifie : \( 8-24+26-10=0 \) ✓. On factorise : \( z^3-6z^2+13z-10=(z-2)(z^2-4z+5) \) (par identification des coefficients). On résout \( z^2-4z+5=0 \) : \( \Delta=16-20=-4 \), racines \( z=\dfrac{4\pm2i}2=2\pm i \).
*Conclusion :* \( S=\{2,\ 2+i,\ 2-i\} \).

**Exemple 3.**
*Énoncé :* Transformer \( \sqrt3\cos x+\sin x \) sous la forme \( r\cos(x-\varphi) \), puis résoudre \( \sqrt3\cos x+\sin x=1 \) sur \( [0,2\pi[ \).
*Résolution :* \( p=\sqrt3,\ q=1 \), \( r=\sqrt{3+1}=2 \). \( \cos\varphi=\dfrac{\sqrt3}2,\ \sin\varphi=\dfrac12\Rightarrow\varphi=\dfrac\pi6 \). Donc \( \sqrt3\cos x+\sin x=2\cos\left(x-\dfrac\pi6\right) \). L'équation devient \( 2\cos\left(x-\dfrac\pi6\right)=1\Rightarrow\cos\left(x-\dfrac\pi6\right)=\dfrac12 \), donc \( x-\dfrac\pi6=\pm\dfrac\pi3\ [2\pi] \), soit \( x=\dfrac\pi2\ [2\pi] \) ou \( x=-\dfrac\pi6\ [2\pi]=\dfrac{11\pi}6\ [2\pi] \).
*Conclusion :* \( S=\left\{\dfrac\pi2,\ \dfrac{11\pi}6\right\} \) sur \( [0,2\pi[ \).

**Exemple 4.**
*Énoncé :* Déterminer les racines cubiques de l'unité, et vérifier que leur somme est nulle.
*Résolution :* \( 1=e^{i0} \). Racines : \( \zeta_k=e^{i\frac{2k\pi}3} \), \( k=0,1,2 \), soit \( \zeta_0=1 \), \( \zeta_1=e^{i2\pi/3}=-\dfrac12+i\dfrac{\sqrt3}2 \), \( \zeta_2=e^{i4\pi/3}=-\dfrac12-i\dfrac{\sqrt3}2 \). Somme : \( 1+\left(-\dfrac12+i\dfrac{\sqrt3}2\right)+\left(-\dfrac12-i\dfrac{\sqrt3}2\right)=1-1+0i=0 \).
*Conclusion :* La somme des racines cubiques de l'unité est bien nulle.

**Exemple 5.**
*Énoncé :* Soit \( f(z)=iz+2-i \). Montrer que \( f \) est une rotation et déterminer son centre et son angle.
*Résolution :* On a \( a=i \), \( b=2-i \). Comme \( |a|=|i|=1 \), \( f \) est une rotation (ou l'identité si \( a=1 \), ce qui n'est pas le cas ici) d'angle \( \arg(i)=\dfrac\pi2 \). Centre \( \omega \) : \( \omega=i\omega+2-i\Rightarrow\omega-i\omega=2-i\Rightarrow\omega(1-i)=2-i\Rightarrow\omega=\dfrac{2-i}{1-i} \). En multipliant par le conjugué : \( \omega=\dfrac{(2-i)(1+i)}{(1-i)(1+i)}=\dfrac{2+2i-i-i^2}{2}=\dfrac{2+i+1}2=\dfrac{3+i}2 \).
*Conclusion :* \( f \) est la rotation de centre \( \Omega\left(\dfrac32,\dfrac12\right) \) et d'angle \( \dfrac\pi2 \).

---

## 9. Erreurs fréquentes

- **Oublier de vérifier que la racine donnée annule bien le polynôme** avant de factoriser une équation du 3ᵉ degré.
- **Erreur de signe dans la transformation \( p\cos x+q\sin x=r\cos(x-\varphi) \)** : bien vérifier que \( \cos\varphi=p/r \) et \( \sin\varphi=q/r \) (et non l'inverse).
- **Confondre le nombre de racines n-ièmes** (toujours exactement \( n \), pour \( z\neq0 \)) avec un nombre plus restreint obtenu en oubliant certaines valeurs de \( k \).
- **Confondre le rapport et l'angle d'une similitude** \( z\mapsto az+b \) : le rapport est \( |a| \) (un réel positif), l'angle est \( \arg(a) \) (modulo \( 2\pi \)).
- **Erreur de développement dans le binôme de Newton** pour la linéarisation (oubli de termes, erreur de signe sur les termes en \( e^{-ik\theta} \)).

---

## 10. Astuces

- **Astuce de calcul** : pour linéariser \( \cos^n\theta \) ou \( \sin^n\theta \), utiliser systématiquement le triangle de Pascal pour développer rapidement \( (e^{i\theta}\pm e^{-i\theta})^n \).
- **Astuce de calcul** : pour factoriser un polynôme du 3ᵉ degré connaissant une racine, utiliser l'identification des coefficients plutôt que la division euclidienne complète, souvent plus rapide.
- **Astuce de rédaction** : toujours préciser le domaine de résolution (\( [0,2\pi[ \), \( \mathbb R \), etc.) lors de la résolution d'une équation trigonométrique après transformation.
- **Astuce pour le Bac** : pour une similitude \( z\mapsto az+b \), retenir la phrase-clé « rapport = module de \( a \), angle = argument de \( a \), centre = point fixe » pour structurer la réponse.
- **Astuce de calcul** : pour les racines n-ièmes de l'unité, les répartir directement sur le cercle trigonométrique aux angles \( \dfrac{2k\pi}n \), ce qui évite les erreurs de calcul.

---

## 11. Exercices

### Faciles
1. Écrire \( z=2-2i\sqrt3 \) sous forme trigonométrique.
2. Calculer \( (1+i)^8 \) à l'aide de la formule de Moivre.
3. Résoudre dans ℂ : \( z^2+2z+5=0 \).
4. Déterminer le module et l'argument de \( i^{2023} \).
5. Transformer \( \cos x+\sin x \) sous la forme \( r\cos(x-\varphi) \).

### Moyens
6. Résoudre \( z^3-3z^2+3z+7=0 \) sachant que \( -1 \) est une racine.
7. Résoudre sur \( \mathbb R \) : \( \cos x-\sqrt3\sin x=\sqrt2 \).
8. Déterminer les racines carrées complexes de \( 5+12i \).
9. Soit \( f(z)=2iz-1+i \). Déterminer la nature de \( f \) et ses éléments caractéristiques.
10. Linéariser \( \cos^2\theta\sin^2\theta \).

### Difficiles
11. Résoudre dans ℂ l'équation \( z^4=-1 \), et représenter les solutions sur le cercle trigonométrique.
12. Résoudre \( z^3+z^2-14z-24=0 \), sachant qu'une racine est un entier négatif à déterminer par tâtonnement (diviseurs de 24).
13. Soit \( \theta \) réel. Montrer, en utilisant les nombres complexes, que \( \cos(5\theta) \) s'exprime comme un polynôme en \( \cos\theta \) (formule de Chebyshev, calcul détaillé non exigé mais méthode à esquisser).
14. Un triangle a pour sommets les affixes des racines cubiques de \( 8i \). Montrer que ce triangle est équilatéral et calculer son aire.
15. Soit \( f(z)=\dfrac{1+i}{\sqrt2}z+3-i \). Déterminer la nature précise de \( f \), son rapport, son angle, et son centre.

---

## 12. Corrigés détaillés

**1.** \( r=\sqrt{4+12}=4 \) ; \( \cos\theta=\dfrac24=\dfrac12,\ \sin\theta=\dfrac{-2\sqrt3}4=-\dfrac{\sqrt3}2\Rightarrow\theta=-\dfrac\pi3 \). \( z=4\left(\cos\left(-\dfrac\pi3\right)+i\sin\left(-\dfrac\pi3\right)\right) \).

**2.** \( 1+i=\sqrt2\,e^{i\pi/4} \), donc \( (1+i)^8=(\sqrt2)^8e^{i8\pi/4}=16\,e^{i2\pi}=16 \).

**3.** \( \Delta=4-20=-16 \) ; \( z=\dfrac{-2\pm4i}2=-1\pm2i \).

**4.** \( i^{2023}=i^{4\times505+3}=i^3=-i \). Module 1, argument \( -\dfrac\pi2\ [2\pi] \).

**5.** \( p=q=1,\ r=\sqrt2 \), \( \cos\varphi=\sin\varphi=\dfrac1{\sqrt2}\Rightarrow\varphi=\dfrac\pi4 \). \( \cos x+\sin x=\sqrt2\cos\left(x-\dfrac\pi4\right) \).

**6.** Vérification : \( -1-3-3+7=0 \) ✓. Factorisation : \( z^3-3z^2+3z+7=(z+1)(z^2-4z+7) \). \( \Delta=16-28=-12 \), racines \( z=\dfrac{4\pm2i\sqrt3}2=2\pm i\sqrt3 \). \( S=\{-1,\ 2+i\sqrt3,\ 2-i\sqrt3\} \).

**7.** \( p=1,q=-\sqrt3,r=2 \), \( \cos\varphi=\frac12,\sin\varphi=-\frac{\sqrt3}2\Rightarrow\varphi=-\frac\pi3 \). \( \cos x-\sqrt3\sin x=2\cos\left(x+\frac\pi3\right) \). Équation : \( 2\cos\left(x+\frac\pi3\right)=\sqrt2\Rightarrow\cos\left(x+\frac\pi3\right)=\frac{\sqrt2}2 \), donc \( x+\frac\pi3=\pm\frac\pi4\ [2\pi] \), soit \( x=-\frac\pi{12}\ [2\pi] \) ou \( x=-\frac{7\pi}{12}\ [2\pi] \).

**8.** \( x^2-y^2=5,\ 2xy=12\Rightarrow xy=6 \), \( x^2+y^2=|5+12i|=13 \). \( x^2=9,y^2=4\Rightarrow x=\pm3,y=\pm2 \) (même signe car \( xy>0 \)) : racines \( 3+2i \) et \( -3-2i \).

**9.** \( a=2i,\ |a|=2\neq1 \) : similitude directe de rapport 2 et d'angle \( \arg(2i)=\frac\pi2 \) (pas une rotation ni une homothétie pure). Centre : \( \omega=2i\omega-1+i\Rightarrow\omega(1-2i)=-1+i\Rightarrow\omega=\dfrac{-1+i}{1-2i}=\dfrac{(-1+i)(1+2i)}{(1-2i)(1+2i)}=\dfrac{-1-2i+i+2i^2}{1+4}=\dfrac{-1-i-2}5=\dfrac{-3-i}5 \).

**10.** \( \cos^2\theta\sin^2\theta=\left(\dfrac{\sin2\theta}2\right)^2=\dfrac{\sin^22\theta}4=\dfrac{1-\cos4\theta}8 \) (en utilisant \( \sin^2u=\frac{1-\cos2u}2 \) avec \( u=2\theta \)).

**11.** \( -1=e^{i\pi} \). Racines 4ᵉ : \( \zeta_k=e^{i\left(\frac\pi4+\frac{k\pi}2\right)} \), \( k=0,1,2,3 \) : \( \zeta_0=e^{i\pi/4},\ \zeta_1=e^{i3\pi/4},\ \zeta_2=e^{i5\pi/4},\ \zeta_3=e^{i7\pi/4} \). Elles forment un carré inscrit dans le cercle unité.

**12.** Test des diviseurs de 24 : pour \( z=-2 \) : \( -8+4+28-24=0 \) ✓. Factorisation : \( z^3+z^2-14z-24=(z+2)(z^2-z-12)=(z+2)(z-4)(z+3) \). \( S=\{-2,4,-3\} \).

**13.** En écrivant \( \cos\theta+i\sin\theta=e^{i\theta} \), on a \( \cos(5\theta)=\mathrm{Re}\big((\cos\theta+i\sin\theta)^5\big) \). En développant par le binôme de Newton et en ne gardant que les termes réels (puissances paires de \( i\sin\theta \)), on obtient un polynôme en \( \cos\theta \) et \( \sin^2\theta=1-\cos^2\theta \), donc finalement uniquement en \( \cos\theta \) : c'est le principe des polynômes de Chebyshev (calcul complet non détaillé ici, méthode exigible).

**14.** \( 8i=8e^{i\pi/2} \). Racines cubiques : \( \zeta_k=2e^{i\left(\frac\pi6+\frac{2k\pi}3\right)} \), \( k=0,1,2 \), toutes de module 2, argument espacés de \( \frac{2\pi}3 \) : elles forment un triangle équilatéral inscrit dans le cercle de rayon 2. Aire d'un triangle équilatéral inscrit dans un cercle de rayon \( R \) : \( \text{Aire}=\dfrac{3\sqrt3}4R^2=\dfrac{3\sqrt3}4\times4=3\sqrt3 \).

**15.** \( a=\dfrac{1+i}{\sqrt2}=e^{i\pi/4} \) (module 1). Donc \( f \) est une **rotation** d'angle \( \dfrac\pi4 \). Centre : \( \omega=e^{i\pi/4}\omega+3-i\Rightarrow\omega(1-e^{i\pi/4})=3-i\Rightarrow\omega=\dfrac{3-i}{1-e^{i\pi/4}} \) (valeur numérique non simplifiée ici, méthode identique aux exemples précédents).

---

## 13. Questions type Bac

1. *(Type Bac)* Résoudre dans ℂ l'équation \( z^3-4z^2+6z-4=0 \), sachant que 2 est une racine, puis représenter les images des solutions dans le plan complexe.
2. *(Type Bac)* Un mobile a pour élongation \( x(t)=3\cos(\omega t)+4\sin(\omega t) \). Écrire \( x(t) \) sous la forme \( r\cos(\omega t-\varphi) \), et déterminer l'amplitude et la phase à l'origine.
3. *(Type Bac)* Soit \( f \) l'application définie par \( f(z)=\left(\dfrac{\sqrt3+i}2\right)z-1 \). Déterminer la nature de \( f \), son rapport, son angle et son centre.

---

## 14. Résumé

Ce chapitre approfondit l'étude des nombres complexes vue en première partie : les formules d'Euler et de Moivre permettent de linéariser des polynômes trigonométriques et de calculer des puissances de nombres complexes. La transformation \( p\cos x+q\sin x=r\cos(x-\varphi) \), obtenue en écrivant \( p+iq=re^{i\varphi} \), est un outil essentiel pour résoudre des équations trigonométriques et modéliser des phénomènes oscillatoires. Les racines n-ièmes d'un nombre complexe non nul, au nombre de \( n \), se répartissent régulièrement sur un cercle. Les applications de ℂ dans ℂ du type \( z\mapsto az+b \) permettent d'étudier les similitudes directes planes : rapport \( |a| \), angle \( \arg(a) \), centre point fixe de l'application. Enfin, la résolution d'une équation du 3ᵉ degré connaissant une racine se ramène, après factorisation, à la résolution d'une équation du second degré, éventuellement dans ℂ.

---

## 15. Fiche de révision

- Moivre : \( (\cos\theta+i\sin\theta)^n=\cos n\theta+i\sin n\theta \)
- Euler : \( \cos\theta=\dfrac{e^{i\theta}+e^{-i\theta}}2,\ \sin\theta=\dfrac{e^{i\theta}-e^{-i\theta}}{2i} \)
- Racines n-ièmes de \( z=re^{i\theta} \) : \( \zeta_k=r^{1/n}e^{i(\theta/n+2k\pi/n)} \), \( k=0,\ldots,n-1 \)
- \( p\cos x+q\sin x=r\cos(x-\varphi) \), \( r=\sqrt{p^2+q^2} \), \( \cos\varphi=p/r,\sin\varphi=q/r \)
- \( z\mapsto az+b \) : similitude de rapport \( |a| \), angle \( \arg(a) \), centre \( \omega=\dfrac{b}{1-a} \) (\( a\neq1 \))
- 3ᵉ degré : factoriser par \( (z-z_0) \) si \( z_0 \) racine connue, puis résoudre le facteur du 2nd degré

---

## 16. Glossaire

- **Formule de Moivre** : expression de \( (\cos\theta+i\sin\theta)^n \).
- **Formule d'Euler** : expression de \( \cos\theta \) et \( \sin\theta \) via l'exponentielle complexe.
- **Racine n-ième** : nombre complexe dont la puissance n-ième redonne un nombre donné.
- **Similitude directe** : application du plan conservant les angles orientés et multipliant les distances par un rapport constant.
- **Équation caractéristique du 3ᵉ degré** : ici, équation polynomiale de degré 3 à résoudre par factorisation.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : trigonométrie, résolution d'équations du second degré, notion de fonction et de composition.

**Ce qui sera utilisé ensuite** : géométrie plane (calcul barycentrique, similitudes planes directes, triangles semblables), courbes planes et coniques (interprétation complexe possible), suites géométriques complexes.

---

## 18. Auto-évaluation

### QCM
1. Le nombre de racines n-ièmes distinctes d'un complexe non nul est :
 a) 1 b) \( n \) c) \( n-1 \) d) infini

2. Dans \( p\cos x+q\sin x=r\cos(x-\varphi) \), on a \( r \) égal à :
 a) \( p+q \) b) \( \sqrt{p^2+q^2} \) c) \( pq \) d) \( p^2+q^2 \)

3. Pour \( z\mapsto az+b \) avec \( |a|=1 \) et \( a\neq1 \), l'application est :
 a) une translation b) une rotation c) une homothétie d) une symétrie

### Vrai/Faux
1. Une équation du 3ᵉ degré à coefficients réels admet toujours au moins une racine réelle. (Vrai)
2. La formule de Moivre s'applique uniquement pour \( n>0 \). (Faux — elle s'étend à \( n\in\mathbb Z \))
3. Les racines n-ièmes de l'unité ont pour somme 1. (Faux — leur somme est nulle pour \( n\ge2 \))

### Questions ouvertes
1. Expliquer la méthode générale pour résoudre une équation du 3ᵉ degré connaissant une racine.
2. Décrire comment la transformation \( p\cos x+q\sin x=r\cos(x-\varphi) \) facilite la résolution d'une équation trigonométrique.

---

## Métadonnées RAG

- **Titre** : Les Nombres Complexes (approfondissement)
- **Chapitre** : Algèbre
- **Sous-chapitre** : Forme algébrique, trigonométrique, exponentielle ; applications de ℂ dans ℂ ; transformation \( p\cos x+q\sin x \) ; résolution d'équations du 3ᵉ degré
- **Compétences** : Utiliser Moivre, Euler et le binôme de Newton ; transformer \( p\cos x+q\sin x \) ; résoudre une équation du 3ᵉ degré ; étudier des applications de ℂ dans ℂ
- **Notions** : formule de Moivre, formule d'Euler, racines n-ièmes, similitude directe, transformation trigonométrique
- **Mots-clés** : nombre complexe, Moivre, Euler, racine n-ième, similitude, 3ᵉ degré
- **Pré-requis** : trigonométrie, équations du second degré, nombres complexes de base
- **Niveau** : Terminale S1/S3
- **Temps estimé** : 10h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS1S3-ALG-COMPLEXES-02
- **Résumé (200 mots max)** : Cette leçon approfondit l'étude des nombres complexes pour la série S1/S3 : formules de Moivre et d'Euler pour la linéarisation et le calcul de puissances, formule du binôme de Newton, détermination des racines n-ièmes d'un nombre complexe (réparties régulièrement sur un cercle), transformation de \( p\cos x+q\sin x \) en \( r\cos(x-\varphi) \) très utile en résolution d'équations trigonométriques et en physique des oscillations, résolution d'équations du 3ᵉ degré connaissant une racine, et étude des applications de ℂ dans ℂ du type \( z\mapsto az+b \) comme similitudes directes planes (rapport, angle, centre). Cinq exemples résolus couvrent chaque compétence. Quinze exercices progressifs, avec corrigés détaillés, incluent des applications physiques et géométriques. Des questions type Bac, une fiche de révision et une auto-évaluation complètent la leçon, qui prépare directement la géométrie plane et les similitudes.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS1S3-COMPLEXES-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : Moivre, Euler, racines n-ièmes, similitude

**Bloc 2 — ID: TS1S3-COMPLEXES-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : 3ᵉ degré, transformation trigonométrique, méthode

**Bloc 3 — ID: TS1S3-COMPLEXES-B3** — Exemples résolus (section 8) — mots-clés : exemple, linéarisation, rotation, racines cubiques

**Bloc 4 — ID: TS1S3-COMPLEXES-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, binôme de Newton

**Bloc 5 — ID: TS1S3-COMPLEXES-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, racines n-ièmes, similitude

**Bloc 6 — ID: TS1S3-COMPLEXES-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Nombres complexes, Terminale S1/S3, pages 60-61)
✓ Exactitude mathématique vérifiée (corrigés recalculés, notamment racines n-ièmes et similitudes)
✓ Cohérence des notations avec les leçons précédentes (S2/S4 et S1/S3)
✓ Absence de contradictions
✓ Progression logique respectée (approfondissement par rapport à la leçon S2/S4)
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec la leçon 7 (Probabilités S1/S3)
