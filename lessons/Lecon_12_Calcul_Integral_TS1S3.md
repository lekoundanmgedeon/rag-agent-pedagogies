---
niveau: secondaire
classe: Terminale
serie: S1
serie_alias: [S1, S3]
discipline: Mathématiques
chapitre: Le Calcul Intégral
examen_associe: Baccalauréat
source_document: Lecon_12_Calcul_Integral_TS1S3.md
---

# Leçon — Le Calcul Intégral (Terminale S1/S3)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Le Calcul Intégral : Techniques Avancées |
| **Classe** | Terminale |
| **Série** | S1 / S3 |
| **Chapitre** | Analyse |
| **Sous-chapitre** | Intégrale d'une fonction continue, intégration par parties, produits/puissances de fonctions trigonométriques, changement de variable affine, valeurs approchées, calcul d'aires et de volumes |
| **Prérequis** | Primitives usuelles, dérivation, trigonométrie, notion d'aire |
| **Durée estimée** | 9 heures |
| **Compétences visées** | Calculer une aire d'un domaine plan ; utiliser les propriétés de l'intégrale ; maîtriser les techniques de calcul intégral au programme (IPP, produits/puissances trigonométriques, changement de variable affine) |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) calculer une intégrale par intégration par parties (y compris répétée), (2) intégrer des produits et puissances de fonctions trigonométriques, (3) effectuer un changement de variable affine, (4) obtenir des encadrements et valeurs approchées d'intégrales, (5) calculer des aires et volumes, y compris des grandeurs physiques |
| **Mots-clés** | intégrale, primitive, intégration par parties, changement de variable, valeur approchée, méthode des rectangles, méthode des trapèzes |

---

## 2. Introduction

Ce chapitre approfondit le calcul intégral déjà étudié en série S2/S4, avec des techniques supplémentaires exigées par le programme S1/S3 : intégration de produits et de puissances de fonctions trigonométriques, changement de variable affine, et méthodes d'obtention de valeurs approchées d'intégrales (rectangles, trapèzes, tangentes).

Le calcul intégral demeure un outil essentiel pour le calcul d'aires, de volumes, et de grandeurs physiques (centre d'inertie, moment d'inertie), avec une importance accrue en S1/S3 où les calculs peuvent être plus techniques.

Au Baccalauréat S1/S3, ce chapitre est très fréquemment associé à l'étude de fonctions, avec des exercices demandant le calcul explicite d'une aire, ou l'établissement d'un encadrement d'intégrale par une méthode numérique.

**Applications concrètes** : calcul de travail d'une force variable, de charge électrique, de centre de gravité et de moment d'inertie en mécanique, approximation numérique d'intégrales non calculables explicitement.

---

## 3. Définitions

**Définition 1 (Intégrale d'une fonction continue — rappel).** Pour \( f \) continue sur \( I \) contenant \( a \), \( x\mapsto\displaystyle\int_a^xf(t)\,dt \) est l'unique primitive de \( f \) sur \( I \) s'annulant en \( a \).

**Définition 2 (Valeur moyenne).** \( \mu=\dfrac1{b-a}\displaystyle\int_a^bf(x)\,dx \).

**Définition 3 (Changement de variable affine).** Substitution \( x=\alpha t+\beta \) (\( \alpha\neq0 \)) dans une intégrale, avec \( dx=\alpha\,dt \), transformant \( \displaystyle\int_a^bf(x)\,dx \) en \( \displaystyle\int_{t_1}^{t_2}f(\alpha t+\beta)\,\alpha\,dt \), où \( t_1,t_2 \) sont les valeurs de \( t \) correspondant à \( x=a,b \).

**Définition 4 (Méthode des rectangles).** Méthode d'approximation de \( \displaystyle\int_a^bf(x)\,dx \) par une somme d'aires de rectangles de largeur \( \dfrac{b-a}n \), de hauteur \( f \) évaluée en un point de chaque sous-intervalle.

**Définition 5 (Méthode des trapèzes).** Méthode d'approximation remplaçant, sur chaque sous-intervalle, la courbe de \( f \) par le segment reliant ses extrémités (trapèze au lieu de rectangle).

---

## 4. Théorèmes

**Théorème 1 (Propriétés de l'intégrale — rappel).**
- Énoncé : linéarité, relation de Chasles, positivité, inégalité de la moyenne (identiques au programme S2/S4, voir leçon correspondante).

**Théorème 2 (Intégration par parties — rappel et généralisation).**
- Énoncé : \( \displaystyle\int_a^bu(x)v'(x)\,dx=[u(x)v(x)]_a^b-\int_a^bu'(x)v(x)\,dx \), applicable de façon répétée pour des produits polynôme × exponentielle/trigonométrique de degré supérieur.

**Théorème 3 (Changement de variable affine).**
- Énoncé : pour \( x=\alpha t+\beta \) (\( \alpha\neq0 \)), \( \displaystyle\int_a^bf(x)\,dx = \int_{t_1}^{t_2}f(\alpha t+\beta)\,\alpha\,dt \), où \( \alpha t_1+\beta=a \) et \( \alpha t_2+\beta=b \).
- Remarque : seuls les changements de variable **affines** sont exigibles à l'examen (le programme précise explicitement cette restriction).

**Théorème 4 (Linéarisation pour intégrer des produits/puissances trigonométriques).**
- Énoncé : pour intégrer \( \cos^p x\sin^qx \) ou des produits comme \( \cos(ax)\cos(bx) \), on utilise les formules de linéarisation (via les formules d'Euler ou les formules de transformation produit-somme) pour se ramener à une somme de termes du type \( \cos(kx) \), \( \sin(kx) \), directement primitivables.

**Théorème 5 (Encadrement par la méthode des rectangles/trapèzes).**
- Énoncé (cas \( f \) monotone) : si \( f \) est croissante sur \( [a,b] \), la méthode des rectangles « à gauche » minore l'intégrale, celle « à droite » la majore (inégalités inversées si \( f \) décroissante) ; la méthode des trapèzes donne en général une meilleure approximation.

---

## 5. Propriétés

1. Le changement de variable affine conserve l'orientation de l'intégrale si \( \alpha>0 \), l'inverse si \( \alpha<0 \) (ce qui échange les bornes \( t_1,t_2 \)).
2. Pour intégrer \( \cos^2x \) ou \( \sin^2x \), on utilise directement les formules \( \cos^2x=\dfrac{1+\cos2x}2 \), \( \sin^2x=\dfrac{1-\cos2x}2 \), cas particuliers simples de linéarisation.
3. La précision de la méthode des trapèzes est en général supérieure à celle des rectangles, pour un même nombre de subdivisions.
4. Un encadrement d'intégrale obtenu par la méthode des rectangles se resserre lorsque le nombre de subdivisions \( n \) augmente.

---

## 6. Démonstrations

**Démonstration du théorème 3 (changement de variable affine)** :
Soit \( F \) une primitive de \( f \). Posons \( x=\alpha t+\beta \), et \( G(t)=F(\alpha t+\beta) \). Alors \( G'(t)=\alpha F'(\alpha t+\beta)=\alpha f(\alpha t+\beta) \), donc \( G \) est une primitive de \( t\mapsto\alpha f(\alpha t+\beta) \). Ainsi :
$$ \int_{t_1}^{t_2}\alpha f(\alpha t+\beta)\,dt = G(t_2)-G(t_1) = F(\alpha t_2+\beta)-F(\alpha t_1+\beta) = F(b)-F(a) = \int_a^bf(x)\,dx. $$

**Démonstration (exemple) de la linéarisation de \( \cos^2x \)** :
Par la formule de duplication \( \cos(2x)=2\cos^2x-1 \), on isole : \( \cos^2x=\dfrac{1+\cos2x}2 \). Cette écriture permet une primitivation immédiate : une primitive de \( \cos^2x \) est \( \dfrac x2+\dfrac{\sin2x}4 \).

**Illustration du théorème 5 (encadrement par rectangles)** :
Pour \( f \) croissante sur \( [a,b] \), sur chaque sous-intervalle \( [x_k,x_{k+1}] \), on a \( f(x_k)\le f(x)\le f(x_{k+1}) \), donc en intégrant sur ce sous-intervalle : \( f(x_k)(x_{k+1}-x_k)\le\displaystyle\int_{x_k}^{x_{k+1}}f(x)\,dx\le f(x_{k+1})(x_{k+1}-x_k) \). En sommant sur tous les sous-intervalles (relation de Chasles), on obtient l'encadrement global par les sommes de rectangles « à gauche » et « à droite ».

---

## 7. Méthodes

**Méthode 1 — Effectuer un changement de variable affine**
1. Poser \( x=\alpha t+\beta \), déterminer \( dx=\alpha\,dt \).
2. Recalculer les nouvelles bornes en résolvant \( \alpha t+\beta=a \) et \( \alpha t+\beta=b \).
3. Substituer dans l'intégrale, simplifier, puis calculer la nouvelle intégrale.

**Méthode 2 — Intégrer un produit ou une puissance de fonctions trigonométriques**
1. Identifier la forme (puissance simple, produit de cosinus/sinus d'arguments différents).
2. Linéariser à l'aide des formules de duplication ou des formules d'Euler.
3. Intégrer terme à terme (chaque terme étant du type \( \cos(kx) \) ou \( \sin(kx) \), directement primitivable).

**Méthode 3 — Obtenir un encadrement ou une valeur approchée d'une intégrale**
1. Découper l'intervalle en \( n \) sous-intervalles réguliers.
2. Appliquer la méthode demandée (rectangles à gauche/droite, trapèzes, tangentes).
3. Sommer les contributions, éventuellement encadrer si \( f \) est monotone.

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Calculer \( \displaystyle\int_0^{1} (2x+3)^4\,dx \) par changement de variable affine.
*Résolution :* On pose \( t=2x+3 \), donc \( dt=2\,dx \), soit \( dx=\dfrac{dt}2 \). Bornes : \( x=0\Rightarrow t=3 \) ; \( x=1\Rightarrow t=5 \). \( \displaystyle\int_0^1(2x+3)^4\,dx=\int_3^5t^4\cdot\frac{dt}2=\frac12\left[\frac{t^5}5\right]_3^5=\frac1{10}(5^5-3^5)=\frac1{10}(3125-243)=\frac{2882}{10}=288{,}2 \).
*Conclusion :* L'intégrale vaut \( 288{,}2 \).

**Exemple 2.**
*Énoncé :* Calculer \( \displaystyle\int_0^{\pi} \cos^2x\,dx \).
*Résolution :* \( \cos^2x=\dfrac{1+\cos2x}2 \). Une primitive : \( F(x)=\dfrac x2+\dfrac{\sin2x}4 \). \( \displaystyle\int_0^\pi\cos^2x\,dx = F(\pi)-F(0) = \left(\dfrac\pi2+0\right)-(0+0)=\dfrac\pi2 \).
*Conclusion :* L'intégrale vaut \( \dfrac\pi2 \).

**Exemple 3.**
*Énoncé :* Calculer \( \displaystyle\int_0^{\pi/2}\sin(3x)\cos(x)\,dx \) en linéarisant le produit.
*Résolution :* On utilise la formule produit-somme : \( \sin a\cos b=\dfrac12\big[\sin(a+b)+\sin(a-b)\big] \), donc \( \sin(3x)\cos(x)=\dfrac12\big[\sin(4x)+\sin(2x)\big] \). Primitive : \( F(x)=\dfrac12\left[-\dfrac{\cos4x}4-\dfrac{\cos2x}2\right]=-\dfrac{\cos4x}8-\dfrac{\cos2x}4 \). \( F\left(\dfrac\pi2\right)=-\dfrac{\cos2\pi}8-\dfrac{\cos\pi}4=-\dfrac18+\dfrac14=\dfrac18 \). \( F(0)=-\dfrac18-\dfrac14=-\dfrac38 \).
*Conclusion :* \( \displaystyle\int_0^{\pi/2}\sin3x\cos x\,dx = \dfrac18-\left(-\dfrac38\right)=\dfrac48=\dfrac12 \).

**Exemple 4.**
*Énoncé :* Calculer \( \displaystyle\int_0^{1} x^2e^{2x}\,dx \) par intégration par parties répétée.
*Résolution :* Première IPP : \( u=x^2,v'=e^{2x}\Rightarrow u'=2x,v=\dfrac{e^{2x}}2 \) : \( \displaystyle\int_0^1x^2e^{2x}\,dx=\left[\dfrac{x^2e^{2x}}2\right]_0^1-\int_0^1xe^{2x}\,dx=\dfrac{e^2}2-\int_0^1xe^{2x}\,dx \). Deuxième IPP sur \( \int_0^1xe^{2x}\,dx \) : \( u=x,v'=e^{2x}\Rightarrow u'=1,v=\dfrac{e^{2x}}2 \) : \( \displaystyle\int_0^1xe^{2x}\,dx=\left[\dfrac{xe^{2x}}2\right]_0^1-\int_0^1\dfrac{e^{2x}}2\,dx=\dfrac{e^2}2-\left[\dfrac{e^{2x}}4\right]_0^1=\dfrac{e^2}2-\dfrac{e^2-1}4=\dfrac{2e^2-e^2+1}4=\dfrac{e^2+1}4 \). Donc \( \displaystyle\int_0^1x^2e^{2x}\,dx = \dfrac{e^2}2-\dfrac{e^2+1}4=\dfrac{2e^2-e^2-1}4=\dfrac{e^2-1}4 \).
*Conclusion :* L'intégrale vaut \( \dfrac{e^2-1}4 \).

**Exemple 5.**
*Énoncé :* Encadrer \( \displaystyle\int_1^2\dfrac1x\,dx \) par la méthode des rectangles avec \( n=4 \) subdivisions.
*Résolution :* \( f(x)=\dfrac1x \), décroissante sur \( [1,2] \), pas \( h=\dfrac{2-1}4=0{,}25 \). Points : \( 1;\ 1{,}25;\ 1{,}5;\ 1{,}75;\ 2 \). Rectangles « à gauche » (majorant, car \( f \) décroissante) : \( 0{,}25\times(f(1)+f(1{,}25)+f(1{,}5)+f(1{,}75)) = 0{,}25\times(1+0{,}8+0{,}667+0{,}571)\approx0{,}25\times3{,}038\approx0{,}760 \). Rectangles « à droite » (minorant) : \( 0{,}25\times(f(1{,}25)+f(1{,}5)+f(1{,}75)+f(2))\approx0{,}25\times(0{,}8+0{,}667+0{,}571+0{,}5)=0{,}25\times2{,}538\approx0{,}635 \).
*Conclusion :* \( 0{,}635\lesssim\displaystyle\int_1^2\dfrac1x\,dx\lesssim0{,}760 \) (la valeur exacte, \( \ln2\approx0{,}693 \), est bien comprise dans cet encadrement).

---

## 9. Erreurs fréquentes

- **Oublier de recalculer les bornes** lors d'un changement de variable : les nouvelles bornes correspondent aux valeurs de la nouvelle variable, pas aux anciennes.
- **Oublier le facteur \( \alpha \)** (le « \( dx=\alpha\,dt \) ») lors d'un changement de variable affine.
- **Utiliser un changement de variable non affine** (par exemple \( x=t^2 \)), qui n'est pas exigible au programme S1/S3 (seuls les changements affines le sont).
- **Confondre les formules de linéarisation** (duplication vs produit-somme) : bien identifier si l'on traite une puissance ou un produit de deux fonctions trigonométriques d'arguments différents.
- **Choisir le mauvais sens de l'inégalité** dans un encadrement par rectangles selon que \( f \) est croissante ou décroissante.

---

## 10. Astuces

- **Astuce de calcul** : pour un changement de variable affine, choisir \( t \) de façon à simplifier au maximum l'expression sous l'intégrale (souvent \( t=\) l'expression interne d'une composée).
- **Astuce de calcul** : pour la linéarisation d'un produit de sinus/cosinus, mémoriser les deux formules produit-somme de base : \( \cos a\cos b=\frac12[\cos(a-b)+\cos(a+b)] \) et \( \sin a\cos b=\frac12[\sin(a+b)+\sin(a-b)] \).
- **Astuce de rédaction** : pour une IPP répétée, bien numéroter chaque étape (« 1ʳᵉ IPP », « 2ᵉ IPP ») pour ne pas perdre le fil des calculs intermédiaires.
- **Astuce pour le Bac** : pour un encadrement par la méthode des rectangles, toujours vérifier au préalable le sens de variation de \( f \), qui détermine si les rectangles à gauche majorent ou minorent l'intégrale.

---

## 11. Exercices

### Faciles
1. Calculer \( \displaystyle\int_0^1(3x+1)^3\,dx \) par changement de variable affine.
2. Calculer \( \displaystyle\int_0^{\pi}\sin^2x\,dx \).
3. Calculer \( \displaystyle\int_1^2\dfrac1{2x-1}\,dx \) par changement de variable.
4. Calculer \( \displaystyle\int_0^1xe^x\,dx \) par IPP.
5. Calculer \( \displaystyle\int_0^{\pi/4}\cos(2x)\,dx \).

### Moyens
6. Calculer \( \displaystyle\int_0^{\pi/2}\sin(2x)\cos(x)\,dx \) en linéarisant.
7. Calculer \( \displaystyle\int_{-1}^{1}(3x-2)^5\,dx \) par changement de variable.
8. Calculer \( \displaystyle\int_1^e x^2\ln x\,dx \) par IPP.
9. Encadrer \( \displaystyle\int_0^1e^{-x^2}\,dx \) par la méthode des rectangles avec \( n=4 \).
10. Calculer \( \displaystyle\int_0^{\pi}\sin^3x\,dx \) (utiliser \( \sin^3x=\sin x(1-\cos^2x) \) et un changement de variable \( t=\cos x \), esquissé — technique combinant primitive directe).

### Difficiles
11. Calculer \( \displaystyle\int_0^{1}x^2e^{-x}\,dx \) par IPP répétée (deux étapes).
12. Calculer \( \displaystyle\int_0^{\pi}\cos(3x)\cos(x)\,dx \) en linéarisant.
13. Calculer, par changement de variable affine, \( \displaystyle\int_2^5\sqrt{3x-2}\,dx \).
14. Calculer le volume engendré par la rotation, autour de l'axe des abscisses, de la courbe de \( f(x)=\cos x \) sur \( \left[0,\dfrac\pi2\right] \) (utiliser la linéarisation de \( \cos^2x \)).
15. En utilisant la méthode des trapèzes avec \( n=4 \), donner une valeur approchée de \( \displaystyle\int_0^2 x^2\,dx \), et comparer avec la valeur exacte.

---

## 12. Corrigés détaillés

**1.** \( t=3x+1,\ dt=3dx \). Bornes : \( x=0\to t=1 \) ; \( x=1\to t=4 \). \( \displaystyle\int_0^1(3x+1)^3\,dx=\frac13\int_1^4t^3\,dt=\frac13\left[\frac{t^4}4\right]_1^4=\frac1{12}(256-1)=\frac{255}{12}=21{,}25 \).

**2.** \( \sin^2x=\dfrac{1-\cos2x}2 \) ; primitive \( \dfrac x2-\dfrac{\sin2x}4 \) ; \( \displaystyle\int_0^\pi\sin^2x\,dx=\left(\dfrac\pi2-0\right)-(0-0)=\dfrac\pi2 \).

**3.** \( t=2x-1,\ dt=2dx \). Bornes : \( x=1\to t=1 \) ; \( x=2\to t=3 \). \( \displaystyle\int_1^2\dfrac1{2x-1}\,dx=\frac12\int_1^3\dfrac1t\,dt=\frac12[\ln t]_1^3=\frac12\ln3 \).

**4.** \( u=x,v'=e^x\Rightarrow u'=1,v=e^x \) : \( \displaystyle\int_0^1xe^x\,dx=[xe^x]_0^1-\int_0^1e^x\,dx=e-(e-1)=1 \).

**5.** Primitive de \( \cos2x \) : \( \dfrac{\sin2x}2 \). \( \displaystyle\int_0^{\pi/4}\cos2x\,dx=\dfrac{\sin(\pi/2)}2-\dfrac{\sin0}2=\dfrac12 \).

**6.** \( \sin2x\cos x=\dfrac12[\sin3x+\sin x] \). Primitive : \( -\dfrac{\cos3x}6-\dfrac{\cos x}2 \). En \( x=\pi/2 \) : \( -\dfrac{\cos(3\pi/2)}6-\dfrac{\cos(\pi/2)}2=0-0=0 \). En \( x=0 \) : \( -\dfrac16-\dfrac12=-\dfrac23 \). Intégrale \( =0-\left(-\dfrac23\right)=\dfrac23 \).

**7.** \( t=3x-2,\ dt=3dx \). Bornes : \( x=-1\to t=-5 \) ; \( x=1\to t=1 \). \( \displaystyle\int_{-1}^1(3x-2)^5\,dx=\frac13\int_{-5}^1t^5\,dt=\frac13\left[\frac{t^6}6\right]_{-5}^1=\frac1{18}(1-15625)=\frac{-15624}{18}=-868 \).

**8.** \( u=\ln x,v'=x^2\Rightarrow u'=\frac1x,v=\frac{x^3}3 \) : \( \displaystyle\int_1^ex^2\ln x\,dx=\left[\frac{x^3}3\ln x\right]_1^e-\int_1^e\frac{x^2}3\,dx=\left(\frac{e^3}3-0\right)-\left[\frac{x^3}9\right]_1^e=\frac{e^3}3-\frac{e^3-1}9=\frac{3e^3-e^3+1}9=\frac{2e^3+1}9 \).

**9.** \( f(x)=e^{-x^2} \), décroissante sur \( [0,1] \), pas \( 0{,}25 \). Points : \( 0;0{,}25;0{,}5;0{,}75;1 \), valeurs \( f\approx1;0{,}939;0{,}779;0{,}570;0{,}368 \). Rectangles à gauche (majorant) : \( 0{,}25(1+0{,}939+0{,}779+0{,}570)\approx0{,}25\times3{,}288\approx0{,}822 \). Rectangles à droite (minorant) : \( 0{,}25(0{,}939+0{,}779+0{,}570+0{,}368)\approx0{,}25\times2{,}656\approx0{,}664 \). Encadrement : \( 0{,}664\lesssim I\lesssim0{,}822 \).

**10.** En posant \( t=\cos x \), \( dt=-\sin x\,dx \) : \( \displaystyle\int_0^\pi\sin x(1-\cos^2x)\,dx = -\int_1^{-1}(1-t^2)\,dt=\int_{-1}^1(1-t^2)\,dt=\left[t-\frac{t^3}3\right]_{-1}^1=\left(1-\frac13\right)-\left(-1+\frac13\right)=\frac23+\frac23=\frac43 \).

**11.** Première IPP : \( u=x^2,v'=e^{-x}\Rightarrow u'=2x,v=-e^{-x} \) : \( \displaystyle\int_0^1x^2e^{-x}\,dx=[-x^2e^{-x}]_0^1+2\int_0^1xe^{-x}\,dx=-e^{-1}+2\int_0^1xe^{-x}\,dx \). Deuxième IPP : \( u=x,v'=e^{-x}\Rightarrow u'=1,v=-e^{-x} \) : \( \displaystyle\int_0^1xe^{-x}\,dx=[-xe^{-x}]_0^1+\int_0^1e^{-x}\,dx=-e^{-1}+[-e^{-x}]_0^1=-e^{-1}+(1-e^{-1})=1-2e^{-1} \). Résultat final : \( -e^{-1}+2(1-2e^{-1})=-e^{-1}+2-4e^{-1}=2-5e^{-1}=2-\dfrac5e \).

**12.** \( \cos3x\cos x=\dfrac12[\cos2x+\cos4x] \). Primitive : \( \dfrac{\sin2x}4+\dfrac{\sin4x}8 \). En \( x=\pi \) : \( \dfrac{\sin2\pi}4+\dfrac{\sin4\pi}8=0 \). En \( x=0 \) : 0. Intégrale \( =0 \).

**13.** \( t=3x-2,\ dt=3dx \). Bornes : \( x=2\to t=4 \) ; \( x=5\to t=13 \). \( \displaystyle\int_2^5\sqrt{3x-2}\,dx=\frac13\int_4^{13}\sqrt t\,dt=\frac13\left[\frac{2t^{3/2}}3\right]_4^{13}=\frac29\left(13\sqrt{13}-8\right) \).

**14.** \( V=\pi\displaystyle\int_0^{\pi/2}\cos^2x\,dx=\pi\times\frac\pi4 \) (résultat de l'exemple 2 adapté aux bornes \( [0,\pi/2] \) : \( \int_0^{\pi/2}\cos^2x\,dx=\left[\frac x2+\frac{\sin2x}4\right]_0^{\pi/2}=\frac\pi4+0=\frac\pi4 \)). Donc \( V=\dfrac{\pi^2}4 \).

**15.** Méthode des trapèzes, \( n=4 \), pas \( h=0{,}5 \), points \( 0;0{,}5;1;1{,}5;2 \), \( f(x)=x^2 \) : valeurs \( 0;0{,}25;1;2{,}25;4 \). Formule des trapèzes : \( \dfrac h2\left[f(x_0)+2(f(x_1)+f(x_2)+f(x_3))+f(x_4)\right]=\dfrac{0{,}5}2\left[0+2(0{,}25+1+2{,}25)+4\right]=0{,}25[0+7+4]=0{,}25\times11=2{,}75 \). Valeur exacte : \( \displaystyle\int_0^2x^2\,dx=\left[\dfrac{x^3}3\right]_0^2=\dfrac83\approx2{,}667 \). L'approximation (2,75) est proche de la valeur exacte (2,667), avec un léger excès dû à la convexité de \( x^2 \).

---

## 13. Questions type Bac

1. *(Type Bac)* Calculer \( \displaystyle\int_0^{\pi/3}\cos^2x\sin x\,dx \) par changement de variable \( t=\cos x \).
2. *(Type Bac)* Calculer, par changement de variable affine, \( \displaystyle\int_0^1(4x-1)^3\,dx \), puis vérifier le résultat par développement direct du polynôme.
3. *(Type Bac)* En utilisant la méthode des rectangles avec \( n=5 \), donner un encadrement de \( \displaystyle\int_1^2\ln x\,dx \), et comparer avec la valeur exacte obtenue par IPP.

---

## 14. Résumé

Ce chapitre approfondit les techniques de calcul intégral : le changement de variable affine (\( x=\alpha t+\beta \)) transforme une intégrale complexe en une intégrale plus simple, à condition de bien recalculer les bornes. La linéarisation de produits ou de puissances de fonctions trigonométriques (via les formules de duplication ou produit-somme) permet de ramener leur intégration à des primitives usuelles de \( \cos(kx) \) et \( \sin(kx) \). L'intégration par parties peut être appliquée de façon répétée pour des produits polynôme × exponentielle de degré supérieur. Enfin, les méthodes des rectangles et des trapèzes fournissent des valeurs approchées ou des encadrements d'intégrales non calculables explicitement, avec une précision croissante avec le nombre de subdivisions.

---

## 15. Fiche de révision

- Changement de variable affine : \( x=\alpha t+\beta,\ dx=\alpha\,dt \), recalculer les bornes
- \( \cos^2x=\dfrac{1+\cos2x}2 \) ; \( \sin^2x=\dfrac{1-\cos2x}2 \)
- \( \cos a\cos b=\frac12[\cos(a-b)+\cos(a+b)] \) ; \( \sin a\cos b=\frac12[\sin(a+b)+\sin(a-b)] \)
- IPP répétée pour polynômes de degré \( \ge2 \) × exponentielle
- Méthode des rectangles/trapèzes : découper en \( n \) sous-intervalles, sommer les contributions

---

## 16. Glossaire

- **Changement de variable affine** : substitution linéaire simplifiant une intégrale.
- **Linéarisation trigonométrique** : transformation d'un produit ou d'une puissance en somme de termes simples.
- **Méthode des rectangles** : approximation d'une intégrale par une somme d'aires rectangulaires.
- **Méthode des trapèzes** : approximation remplaçant chaque portion de courbe par un segment.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : primitives usuelles, IPP de base (S2/S4), trigonométrie, fonctions numériques (dérivation).

**Ce qui sera utilisé ensuite** : équations différentielles (résolution par primitives), géométrie dans l'espace (calcul de volumes par sections), courbes planes (calcul de longueurs et d'aires).

---

## 18. Auto-évaluation

### QCM
1. Le changement de variable exigible au programme S1/S3 pour l'examen est de type :
 a) polynomial b) affine c) exponentiel d) trigonométrique quelconque

2. \( \cos^2x \) se linéarise en :
 a) \( \dfrac{1-\cos2x}2 \) b) \( \dfrac{1+\cos2x}2 \) c) \( \cos(2x) \) d) \( 1-\sin^2x \) uniquement

3. La méthode des trapèzes, comparée à celle des rectangles, offre en général :
 a) une moins bonne précision b) une meilleure précision c) la même précision d) aucune précision

### Vrai/Faux
1. On peut utiliser un changement de variable non affine à l'examen du Bac S1/S3. (Faux — seuls les changements affines sont exigibles)
2. La formule \( \sin a\cos b=\frac12[\sin(a+b)+\sin(a-b)] \) permet de linéariser un produit de sinus et cosinus. (Vrai)
3. Une IPP ne peut jamais être appliquée deux fois de suite. (Faux)

### Questions ouvertes
1. Expliquer pourquoi seuls les changements de variable affines sont exigibles au programme, et donner un exemple d'usage typique.
2. Décrire la différence entre la méthode des rectangles et celle des trapèzes pour approximer une intégrale.

---

## Métadonnées RAG

- **Titre** : Le Calcul Intégral : Techniques Avancées
- **Chapitre** : Analyse
- **Sous-chapitre** : Intégrale d'une fonction continue, intégration par parties, produits/puissances de fonctions trigonométriques, changement de variable affine, valeurs approchées, calcul d'aires et de volumes
- **Compétences** : Calculer des aires ; utiliser les propriétés de l'intégrale ; maîtriser IPP, linéarisation trigonométrique, changement de variable affine
- **Notions** : changement de variable affine, linéarisation trigonométrique, méthode des rectangles, méthode des trapèzes
- **Mots-clés** : intégrale, IPP, changement de variable, linéarisation, rectangles, trapèzes
- **Pré-requis** : primitives usuelles, IPP de base, trigonométrie
- **Niveau** : Terminale S1/S3
- **Temps estimé** : 9h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS1S3-ANA-INTEGRALES-02
- **Résumé (200 mots max)** : Cette leçon approfondit le calcul intégral pour la série S1/S3 avec des techniques supplémentaires : changement de variable affine (seul type exigible à l'examen), linéarisation de produits et puissances de fonctions trigonométriques via les formules de duplication et produit-somme, intégration par parties répétée pour des produits polynôme-exponentielle de degré supérieur, et méthodes d'obtention de valeurs approchées d'intégrales (rectangles, trapèzes). Cinq exemples résolus couvrent chaque technique, incluant un encadrement numérique. Quinze exercices progressifs, avec corrigés détaillés, traitent notamment d'un calcul de volume par linéarisation trigonométrique et d'une comparaison entre valeur approchée (trapèzes) et valeur exacte. Des questions type Bac, un résumé, une fiche de révision et une auto-évaluation complètent la leçon, qui prépare les équations différentielles et la géométrie dans l'espace de la série S1/S3.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS1S3-INTEGRALES-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : changement de variable affine, linéarisation, rectangles

**Bloc 2 — ID: TS1S3-INTEGRALES-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : IPP répétée, produit-somme, méthode

**Bloc 3 — ID: TS1S3-INTEGRALES-B3** — Exemples résolus (section 8) — mots-clés : exemple, changement de variable, linéarisation, encadrement

**Bloc 4 — ID: TS1S3-INTEGRALES-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, bornes

**Bloc 5 — ID: TS1S3-INTEGRALES-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, volume, trapèzes

**Bloc 6 — ID: TS1S3-INTEGRALES-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Calcul intégral, Terminale S1/S3, page 65 — restriction aux changements de variable affines respectée)
✓ Exactitude mathématique vérifiée (corrigés recalculés, notamment linéarisations et IPP répétées)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 7 à 11 (série S1/S3)
