---
niveau: secondaire
classe: Terminale
serie: S2
serie_alias: [S2, S4]
discipline: Mathématiques
chapitre: Le Calcul Intégral
examen_associe: Baccalauréat
source_document: Lecon_03_Calcul_Integral_TS2S4.md
---

# Leçon — Le Calcul Intégral (Terminale S2/S4)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Le Calcul Intégral |
| **Classe** | Terminale |
| **Série** | S2 / S4 |
| **Chapitre** | Analyse |
| **Sous-chapitre** | Intégrale d'une fonction continue, propriétés, intégration par parties, calcul d'aires et de volumes |
| **Prérequis** | Primitives des fonctions usuelles, dérivation, fonctions continues, notion d'aire |
| **Durée estimée** | 8 heures |
| **Compétences visées** | Calculer une intégrale à l'aide d'une primitive ou d'une intégration par parties ; utiliser les propriétés de l'intégrale ; calculer des aires planes et des volumes |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) calculer une intégrale à partir d'une primitive, (2) utiliser la linéarité, la relation de Chasles et les inégalités sur les intégrales, (3) appliquer l'intégration par parties, (4) calculer une aire plane ou un volume de révolution |
| **Mots-clés** | intégrale, primitive, intégration par parties, relation de Chasles, aire, volume, valeur moyenne |

---

## 2. Introduction

Le calcul intégral prolonge la recherche de primitives amorcée en Première et donne un sens rigoureux à la notion d'aire sous une courbe. Il permet de résoudre des problèmes très concrets : calcul d'aires de domaines plans complexes, de volumes de solides de révolution, de grandeurs physiques (travail d'une force, quantité d'électricité, centre d'inertie).

Ce chapitre est central dans le programme de Terminale S2/S4 : il réinvestit la dérivation (recherche de primitives), prépare les équations différentielles, et apparaît très fréquemment au Baccalauréat, souvent associé à l'étude de fonctions (calcul d'aire entre une courbe et l'axe des abscisses, ou entre deux courbes).

**Applications concrètes** : calcul de travail en physique, de charge électrique, de centre de gravité, de volumes de pièces mécaniques par la méthode des sections.

---

## 3. Définitions

**Définition 1 (Primitive).** Soit \( f \) une fonction continue sur un intervalle \( I \). Une primitive de \( f \) sur \( I \) est une fonction \( F \) dérivable sur \( I \) telle que, pour tout \( x\in I \), \( F'(x)=f(x) \).

**Définition 2 (Intégrale d'une fonction continue).** Soit \( f \) continue sur \( I \) contenant \( a \) et \( b \), et \( F \) une primitive de \( f \) sur \( I \). L'intégrale de \( f \) entre \( a \) et \( b \) est
$$ \int_a^b f(x)\,dx = F(b)-F(a). $$

**Définition 3 (Interprétation géométrique).** Si \( f \) est continue et positive sur \( [a,b] \), \( \displaystyle\int_a^b f(x)\,dx \) est l'aire, exprimée en unités d'aire, du domaine délimité par la courbe de \( f \), l'axe des abscisses, et les droites \( x=a \) et \( x=b \).

**Définition 4 (Valeur moyenne d'une fonction).** La valeur moyenne de \( f \) sur \( [a,b] \) (\( a\neq b \)) est
$$ \mu = \frac{1}{b-a}\int_a^b f(x)\,dx. $$

---

## 4. Théorèmes

**Théorème 1 (Existence des primitives — admis).**
- Énoncé : toute fonction continue sur un intervalle \( I \) admet des primitives sur \( I \). Deux primitives de \( f \) sur \( I \) diffèrent d'une constante.
- Conséquence : la fonction \( x\mapsto\int_a^x f(t)\,dt \) est l'unique primitive de \( f \) sur \( I \) qui s'annule en \( a \).

**Théorème 2 (Linéarité).**
- Énoncé : pour \( f, g \) continues sur \( [a,b] \) et \( \lambda\in\mathbb{R} \), \( \displaystyle\int_a^b(f+g)(x)\,dx=\int_a^bf(x)\,dx+\int_a^bg(x)\,dx \) et \( \displaystyle\int_a^b\lambda f(x)\,dx=\lambda\int_a^bf(x)\,dx \).

**Théorème 3 (Relation de Chasles).**
- Énoncé : pour \( a,b,c \) dans \( I \), \( \displaystyle\int_a^bf(x)\,dx = \int_a^cf(x)\,dx+\int_c^bf(x)\,dx \).

**Théorème 4 (Positivité et intégration des inégalités).**
- Énoncé : si \( f\ge0 \) sur \( [a,b] \) (\( a\le b \)), alors \( \int_a^bf(x)\,dx\ge0 \). Si \( f\le g \) sur \( [a,b] \), alors \( \int_a^bf(x)\,dx\le\int_a^bg(x)\,dx \).
- Cas particulier (inégalité de la moyenne) : si pour tout \( x\in[a,b] \), \( m\le f(x)\le M \), alors \( m(b-a)\le\int_a^bf(x)\,dx\le M(b-a) \).

**Théorème 5 (Intégration par parties).**
- Énoncé : si \( u \) et \( v \) sont dérivables, à dérivées continues, sur \( [a,b] \), alors
$$ \int_a^b u(x)v'(x)\,dx = \big[u(x)v(x)\big]_a^b - \int_a^b u'(x)v(x)\,dx. $$
- Conditions d'application : choisir \( u \) qui se simplifie par dérivation et \( v' \) facile à primitiver.

---

## 5. Propriétés

1. \( \displaystyle\int_a^a f(x)\,dx = 0 \).
2. \( \displaystyle\int_b^a f(x)\,dx = -\int_a^b f(x)\,dx \).
3. L'aire entre deux courbes \( C_f \) et \( C_g \) (avec \( f\ge g \) sur \( [a,b] \)) vaut \( \displaystyle\int_a^b\big(f(x)-g(x)\big)\,dx \) unités d'aire.
4. Le volume engendré par la rotation autour de l'axe des abscisses d'une portion de courbe \( y=f(x) \) sur \( [a,b] \) est \( V = \pi\displaystyle\int_a^b f(x)^2\,dx \).
5. Si \( S(z) \) désigne l'aire de la section plane d'un solide à la cote \( z\in[a,b] \), le volume du solide vaut \( V=\displaystyle\int_a^b S(z)\,dz \).

---

## 6. Démonstrations

**Démonstration du théorème 2 (linéarité), cas de la somme** :
Soient \( F \) une primitive de \( f \) et \( G \) une primitive de \( g \) sur \( [a,b] \). Alors \( F+G \) est une primitive de \( f+g \) (car \( (F+G)'=F'+G'=f+g \)), donc
$$ \int_a^b(f+g)(x)\,dx = (F+G)(b)-(F+G)(a) = \big(F(b)-F(a)\big)+\big(G(b)-G(a)\big) = \int_a^bf(x)\,dx+\int_a^bg(x)\,dx. $$

**Démonstration de la propriété 3 (aire entre deux courbes), esquisse** :
L'aire entre \( C_f \) et \( C_g \) (avec \( f\ge g\ge0 \) pour simplifier) est la différence entre l'aire sous \( C_f \) et l'aire sous \( C_g \) sur \( [a,b] \), soit \( \int_a^bf(x)\,dx-\int_a^bg(x)\,dx=\int_a^b(f(x)-g(x))\,dx \) par linéarité (théorème 2). Le cas général (sans supposer \( g\ge0 \)) se traite en translatant verticalement les deux fonctions par une même constante, ce qui ne change pas l'aire entre les courbes.

**Démonstration du théorème 5 (intégration par parties)** :
On part de la formule de dérivation d'un produit : \( (uv)' = u'v+uv' \), donc \( uv' = (uv)'-u'v \). En intégrant entre \( a \) et \( b \) (théorème 2, linéarité) :
$$ \int_a^b u(x)v'(x)\,dx = \int_a^b(uv)'(x)\,dx - \int_a^b u'(x)v(x)\,dx = \big[u(x)v(x)\big]_a^b - \int_a^b u'(x)v(x)\,dx. $$

---

## 7. Méthodes

**Méthode 1 — Calculer une intégrale à l'aide d'une primitive**
1. Identifier une primitive \( F \) de \( f \) (fonctions usuelles, ou primitives de \( u'e^u \), \( \frac{u'}{u} \), \( u'u^n \), etc.).
2. Calculer \( F(b)-F(a) \).

**Méthode 2 — Calculer une intégrale par intégration par parties**
1. Choisir \( u \) (qui se simplifie par dérivation, ex. \( x, \ln x \)) et \( v' \) (facile à primitiver, ex. \( e^x, \cos x \)).
2. Calculer \( u' \) et une primitive \( v \) de \( v' \).
3. Appliquer la formule \( \int_a^buv'=[uv]_a^b-\int_a^bu'v \), et calculer la nouvelle intégrale (éventuellement en répétant l'opération).

**Méthode 3 — Calculer une aire plane**
1. Étudier le signe de \( f \) (ou de \( f-g \)) sur l'intervalle considéré.
2. Découper l'intervalle si le signe change, en utilisant la relation de Chasles.
3. Calculer chaque intégrale en prenant la valeur absolue si nécessaire (aire = \( \int|f(x)-g(x)|\,dx \)), puis sommer.

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Calculer \( \displaystyle\int_0^1 (3x^2+2x)\,dx \).
*Résolution :* Une primitive est \( F(x)=x^3+x^2 \). Donc \( \int_0^1(3x^2+2x)\,dx = F(1)-F(0) = (1+1)-0=2 \).
*Conclusion :* L'intégrale vaut 2.

**Exemple 2.**
*Énoncé :* Calculer \( \displaystyle\int_0^{1} x e^x\,dx \) par intégration par parties.
*Résolution :* On pose \( u=x,\ v'=e^x \), donc \( u'=1,\ v=e^x \).
$$ \int_0^1 xe^x\,dx = [xe^x]_0^1-\int_0^1 e^x\,dx = (1\cdot e-0)-[e^x]_0^1 = e-(e-1)=1. $$
*Conclusion :* L'intégrale vaut 1.

**Exemple 3.**
*Énoncé :* Calculer l'aire du domaine délimité par la courbe de \( f(x)=4-x^2 \) et l'axe des abscisses.
*Résolution :* \( f(x)=0 \iff x=\pm2 \), et \( f\ge0 \) sur \( [-2,2] \). Aire \( = \int_{-2}^{2}(4-x^2)\,dx = \left[4x-\frac{x^3}{3}\right]_{-2}^2 = \left(8-\frac83\right)-\left(-8+\frac83\right)=16-\frac{16}{3}=\frac{32}{3} \).
*Conclusion :* L'aire vaut \( \dfrac{32}{3} \) unités d'aire.

**Exemple 4.**
*Énoncé :* Calculer le volume du solide engendré par la rotation autour de l'axe des abscisses de la portion de la courbe \( y=\sqrt{x} \) pour \( x\in[0,4] \).
*Résolution :* \( V=\pi\displaystyle\int_0^4 (\sqrt x)^2\,dx = \pi\int_0^4 x\,dx = \pi\left[\frac{x^2}{2}\right]_0^4 = \pi\times8=8\pi \).
*Conclusion :* Le volume vaut \( 8\pi \) unités de volume.

**Exemple 5.**
*Énoncé :* Calculer la valeur moyenne de \( f(x)=\cos x \) sur \( \left[0,\dfrac{\pi}{2}\right] \).
*Résolution :* \( \mu = \dfrac{1}{\pi/2-0}\displaystyle\int_0^{\pi/2}\cos x\,dx = \dfrac{2}{\pi}\big[\sin x\big]_0^{\pi/2} = \dfrac2\pi(1-0)=\dfrac2\pi \).
*Conclusion :* La valeur moyenne vaut \( \dfrac{2}{\pi} \).

---

## 9. Erreurs fréquentes

- **Oublier la constante d'intégration lors de la recherche d'une primitive générale**, ou au contraire l'ajouter par erreur lors du calcul d'une intégrale définie (l'intégrale définie ne comporte pas de « +C »).
- **Confondre \( \int f(x)\,dx \)** (primitive, fonction de \( x \)) **et \( \int_a^bf(x)\,dx \)** (nombre réel).
- **Calculer l'aire entre deux courbes sans étudier le signe de \( f-g \)** : si le signe change sur l'intervalle, il faut découper et prendre la valeur absolue sur chaque sous-intervalle.
- **Erreur de choix dans l'intégration par parties** : choisir \( u \) qui se complique par dérivation (ex. prendre \( u=e^x \) au lieu de \( u=x \) dans \( \int xe^x\,dx \)) mène à une impasse.
- **Oublier le facteur \( \pi \)** dans le calcul de volume de révolution, ou oublier d'élever \( f(x) \) au carré.

---

## 10. Astuces

- **Astuce de calcul** : pour intégrer un produit \( u'e^u \), reconnaître directement la primitive \( e^u \) sans passer par l'intégration par parties.
- **Astuce de calcul** : pour choisir \( u \) et \( v' \) en intégration par parties, retenir l'ordre de priorité pour \( u \) : logarithme, polynôme, exponentielle, trigonométrique (« LPET »).
- **Astuce de rédaction** : toujours écrire clairement l'étape \( \big[F(x)\big]_a^b = F(b)-F(a) \) avant de faire l'application numérique, pour limiter les erreurs de signe.
- **Astuce pour le Bac** : pour un calcul d'aire, toujours commencer par tracer un rapide croquis (ou l'imaginer) afin d'identifier le signe de la fonction et les bornes pertinentes.
- **Astuce de calcul** : pour une intégrale de fonction paire sur \( [-a,a] \), utiliser \( \int_{-a}^a f = 2\int_0^a f \) ; pour une fonction impaire, l'intégrale sur \( [-a,a] \) est nulle.

---

## 11. Exercices

### Faciles
1. Calculer \( \displaystyle\int_1^2 (2x+1)\,dx \).
2. Calculer \( \displaystyle\int_0^{\pi} \sin x\,dx \).
3. Calculer \( \displaystyle\int_1^e \dfrac{1}{x}\,dx \).
4. Calculer \( \displaystyle\int_0^1 e^x\,dx \).
5. Calculer \( \displaystyle\int_{-1}^{1} x^3\,dx \) (utiliser la parité).

### Moyens
6. Calculer \( \displaystyle\int_0^{1} x^2 e^x\,dx \) par intégration par parties (deux étapes).
7. Calculer l'aire délimitée par les courbes de \( f(x)=x^2 \) et \( g(x)=x+2 \).
8. Calculer \( \displaystyle\int_0^{\pi/2} x\cos x\,dx \).
9. Déterminer la valeur moyenne de \( f(x)=x^2 \) sur \( [0,3] \).
10. Calculer le volume engendré par la rotation autour de l'axe des abscisses de \( y=x \) sur \( [0,2] \) (vérifier avec la formule du cône).

### Difficiles
11. Calculer \( \displaystyle\int_1^e x\ln x\,dx \) par intégration par parties.
12. Calculer l'aire du domaine compris entre la courbe de \( f(x)=x^2-4x+3 \) et l'axe des abscisses, en tenant compte du changement de signe de \( f \).
13. Montrer, en utilisant l'inégalité de la moyenne, que \( 1\le\displaystyle\int_0^1 e^{x^2}\,dx\le e \).
14. Calculer \( \displaystyle\int_0^{1} \dfrac{2x}{x^2+1}\,dx \), puis en déduire \( \displaystyle\int_0^1\dfrac{x}{x^2+1}\,dx \).
15. Un solide est engendré par la rotation, autour de l'axe des abscisses, de la portion de la courbe \( y=\sqrt{4-x^2} \) sur \( [-2,2] \). Calculer son volume et vérifier qu'il correspond au volume d'une sphère de rayon 2.

---

## 12. Corrigés détaillés

**1.** Primitive \( F(x)=x^2+x \) ; \( F(2)-F(1)=(4+2)-(1+1)=6-2=4 \).

**2.** Primitive \( F(x)=-\cos x \) ; \( F(\pi)-F(0)=-\cos\pi-(-\cos0)=1-(-1)=2 \).

**3.** Primitive \( F(x)=\ln x \) ; \( F(e)-F(1)=1-0=1 \).

**4.** Primitive \( F(x)=e^x \) ; \( F(1)-F(0)=e-1 \).

**5.** \( x^3 \) est impaire, donc \( \displaystyle\int_{-1}^1 x^3\,dx=0 \).

**6.** Première IPP : \( u=x^2,\ v'=e^x \Rightarrow u'=2x,\ v=e^x \) : \( \int_0^1x^2e^x\,dx=[x^2e^x]_0^1-2\int_0^1xe^x\,dx = e - 2\times1 = e-2 \) (en réutilisant le résultat de l'exemple 2 : \( \int_0^1xe^x\,dx=1 \)).

**7.** Intersections : \( x^2=x+2\Rightarrow x^2-x-2=0\Rightarrow(x-2)(x+1)=0\Rightarrow x=-1$ ou $x=2 \). Sur \( [-1,2] \), \( g\ge f \) (à vérifier en un point, ex. \( x=0 \) : \( g(0)=2>f(0)=0 \)). Aire \( =\int_{-1}^2(g-f)(x)\,dx=\int_{-1}^2(x+2-x^2)\,dx=\left[\frac{x^2}2+2x-\frac{x^3}3\right]_{-1}^2 \). En \( x=2 \) : \( 2+4-\frac83=6-\frac83=\frac{10}3 \). En \( x=-1 \) : \( \frac12-2+\frac13=-\frac76 \). Aire \( =\frac{10}3-\left(-\frac76\right)=\frac{20}6+\frac76=\frac{27}6=\frac92 \).

**8.** \( u=x,\ v'=\cos x\Rightarrow u'=1,\ v=\sin x \) : \( \int_0^{\pi/2}x\cos x\,dx=[x\sin x]_0^{\pi/2}-\int_0^{\pi/2}\sin x\,dx = \frac{\pi}{2}\times1-0-[-\cos x]_0^{\pi/2}=\frac\pi2-(0-(-1))=\frac\pi2-1 \).

**9.** \( \mu=\dfrac{1}{3}\displaystyle\int_0^3x^2\,dx=\dfrac13\left[\dfrac{x^3}3\right]_0^3=\dfrac13\times9=3 \).

**10.** \( V=\pi\displaystyle\int_0^2 x^2\,dx=\pi\left[\dfrac{x^3}3\right]_0^2=\dfrac{8\pi}3 \), ce qui correspond bien à la formule du volume d'un cône de rayon 2 et de hauteur 2 : \( V=\dfrac13\pi r^2h=\dfrac13\pi\times4\times2=\dfrac{8\pi}3 \). ✓

**11.** \( u=\ln x,\ v'=x\Rightarrow u'=\dfrac1x,\ v=\dfrac{x^2}2 \) : \( \int_1^ex\ln x\,dx=\left[\dfrac{x^2}2\ln x\right]_1^e-\int_1^e\dfrac{x}2\,dx=\left(\dfrac{e^2}2-0\right)-\left[\dfrac{x^2}4\right]_1^e=\dfrac{e^2}2-\left(\dfrac{e^2}4-\dfrac14\right)=\dfrac{e^2}4+\dfrac14 \).

**12.** \( f(x)=x^2-4x+3=(x-1)(x-3) \), racines 1 et 3, \( f\le0 \) sur \( [1,3] \) et \( f\ge0 \) ailleurs. En se limitant à l'intervalle \( [1,3] \) : aire \( = -\int_1^3f(x)\,dx = -\left[\dfrac{x^3}3-2x^2+3x\right]_1^3 \). En \( x=3 \) : \( 9-18+9=0 \). En \( x=1 \) : \( \frac13-2+3=\frac43 \). Donc l'intégrale vaut \( 0-\frac43=-\frac43 \), et l'aire (positive) vaut \( \frac43 \).

**13.** Sur \( [0,1] \), \( x^2\in[0,1] \), donc \( e^{x^2}\in[e^0,e^1]=[1,e] \). Par l'inégalité de la moyenne (théorème 4, cas particulier), \( 1\times(1-0)\le\int_0^1e^{x^2}\,dx\le e\times(1-0) \), soit \( 1\le\int_0^1e^{x^2}\,dx\le e \).

**14.** \( \int_0^1\dfrac{2x}{x^2+1}\,dx=[\ln(x^2+1)]_0^1=\ln2-\ln1=\ln2 \). Comme \( \dfrac{x}{x^2+1}=\dfrac12\cdot\dfrac{2x}{x^2+1} \), on a \( \int_0^1\dfrac{x}{x^2+1}\,dx=\dfrac12\ln2 \).

**15.** \( V=\pi\displaystyle\int_{-2}^2(4-x^2)\,dx=\pi\left[4x-\dfrac{x^3}3\right]_{-2}^2 = \pi\left[\left(8-\dfrac83\right)-\left(-8+\dfrac83\right)\right]=\pi\times\dfrac{32}3=\dfrac{32\pi}3 \). Or le volume d'une sphère de rayon 2 est \( \dfrac43\pi r^3=\dfrac43\pi\times8=\dfrac{32\pi}3 \). ✓ Les deux résultats coïncident.

---

## 13. Questions type Bac

1. *(Type Bac)* Soit \( f(x)=x e^{-x} \) sur \( [0,+\infty[ \). Calculer \( \displaystyle\int_0^1 f(x)\,dx \) par intégration par parties, et interpréter géométriquement le résultat.
2. *(Type Bac)* Calculer l'aire du domaine délimité par la courbe de \( f(x)=\ln x \), l'axe des abscisses, et les droites \( x=1 \) et \( x=e \).
3. *(Type Bac)* Un réservoir a la forme du solide engendré par la rotation, autour de l'axe des abscisses, de la courbe \( y=\sqrt{x} \) sur \( [0,h] \). Exprimer son volume en fonction de \( h \), puis calculer \( h \) pour un volume de \( 50\pi \) (unités adaptées).

---

## 14. Résumé

L'intégrale d'une fonction continue \( f \) entre \( a \) et \( b \) se calcule à l'aide d'une primitive \( F \) : \( \int_a^bf(x)\,dx=F(b)-F(a) \). Elle vérifie la linéarité, la relation de Chasles, et des propriétés d'inégalités (positivité, inégalité de la moyenne) qui permettent d'encadrer une intégrale sans la calculer explicitement. L'intégration par parties, issue de la dérivation d'un produit, permet de calculer des intégrales de produits de fonctions (polynôme × exponentielle, polynôme × logarithme, etc.). Le calcul intégral permet enfin de calculer des aires planes (y compris entre deux courbes, avec attention au signe) et des volumes de solides de révolution via la formule \( V=\pi\int_a^bf(x)^2\,dx \), ou plus généralement \( V=\int_a^bS(z)\,dz \) à partir de l'aire des sections.

---

## 15. Fiche de révision

- \( \int_a^bf(x)\,dx=F(b)-F(a) \), \( F \) primitive de \( f \)
- Linéarité, Chasles : \( \int_a^cf=\int_a^bf+\int_b^cf \)
- \( f\ge0 \) sur \( [a,b] \Rightarrow \int_a^bf\ge0 \) ; inégalité de la moyenne : \( m(b-a)\le\int_a^bf\le M(b-a) \)
- IPP : \( \int_a^buv'=[uv]_a^b-\int_a^bu'v \)
- Aire entre courbes : \( \int_a^b|f-g| \) ; Volume de révolution : \( V=\pi\int_a^bf(x)^2\,dx \)
- Valeur moyenne : \( \mu=\dfrac1{b-a}\int_a^bf(x)\,dx \)

---

## 16. Glossaire

- **Primitive** : fonction dont la dérivée est la fonction donnée.
- **Intégrale définie** : nombre réel \( F(b)-F(a) \), interprété comme une aire algébrique.
- **Relation de Chasles** : additivité de l'intégrale par rapport aux bornes.
- **Intégration par parties** : technique de calcul d'intégrale de produit, dérivée de la dérivation d'un produit.
- **Valeur moyenne** : moyenne « continue » d'une fonction sur un intervalle.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : dérivation, primitives des fonctions usuelles, fonctions logarithme et exponentielle, notion d'aire.

**Ce qui sera utilisé ensuite** : équations différentielles (résolution par primitives), statistiques (calculs de moyenne continue en probabilités continues, hors programme strict mais lié conceptuellement), applications physiques interdisciplinaires.

---

## 18. Auto-évaluation

### QCM
1. \( \displaystyle\int_a^a f(x)\,dx \) vaut :
 a) \( f(a) \) b) 0 c) 1 d) indéterminé

2. Dans l'intégration par parties, on choisit \( u \) de préférence :
 a) qui se complique par dérivation b) qui se simplifie par dérivation c) toujours égal à \( e^x \) d) au hasard

3. Le volume engendré par la rotation de \( y=f(x) \) autour de l'axe des abscisses sur \( [a,b] \) est :
 a) \( \int_a^bf(x)\,dx \) b) \( \pi\int_a^bf(x)^2\,dx \) c) \( 2\pi\int_a^bf(x)\,dx \) d) \( \int_a^bf(x)^2\,dx \)

### Vrai/Faux
1. \( \int_a^b f(x)\,dx = -\int_b^a f(x)\,dx \). (Vrai)
2. Si \( f\le g \) sur \( [a,b] \), alors nécessairement \( \int_a^bf\,dx \le \int_a^b g\,dx \). (Vrai)
3. L'aire entre deux courbes est toujours donnée par \( \int_a^b(f(x)-g(x))\,dx \), même si le signe de \( f-g \) change. (Faux — il faut alors utiliser la valeur absolue et découper)

### Questions ouvertes
1. Expliquer pourquoi il est nécessaire d'étudier le signe de \( f-g \) avant de calculer l'aire entre deux courbes.
2. Justifier, à l'aide de la dérivation d'un produit, la formule de l'intégration par parties.

---

## Métadonnées RAG

- **Titre** : Le Calcul Intégral
- **Chapitre** : Analyse
- **Sous-chapitre** : Intégrale d'une fonction continue, propriétés, intégration par parties, calcul d'aires et de volumes
- **Compétences** : Calculer une intégrale à l'aide d'une primitive ou d'une IPP ; utiliser les propriétés de l'intégrale ; calculer des aires et des volumes
- **Notions** : primitive, intégrale, relation de Chasles, intégration par parties, aire, volume, valeur moyenne
- **Mots-clés** : intégrale, primitive, IPP, aire, volume, valeur moyenne
- **Pré-requis** : dérivation, primitives usuelles, fonctions continues
- **Niveau** : Terminale S2/S4
- **Temps estimé** : 8h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS2S4-ANA-INTEGRALES-01
- **Résumé (200 mots max)** : Cette leçon présente le calcul intégral : définition de l'intégrale d'une fonction continue à partir d'une primitive, propriétés (linéarité, relation de Chasles, positivité, inégalité de la moyenne), et la technique de l'intégration par parties, démontrée à partir de la dérivation d'un produit. Une large place est accordée aux applications géométriques : calcul d'aires planes (y compris entre deux courbes, avec attention au changement de signe) et calcul de volumes de solides de révolution via \( V=\pi\int f^2 \) ou par sections. La leçon comprend cinq exemples résolus couvrant primitives simples, IPP, aires et volumes, quinze exercices progressifs avec corrigés détaillés (incluant une vérification croisée avec les formules géométriques usuelles de cône et de sphère), des questions type Bac, une fiche de révision et une auto-évaluation. Elle prolonge la dérivation et prépare directement les équations différentielles.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS2S4-INTEGRALES-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : primitive, intégrale, Chasles, inégalité de la moyenne

**Bloc 2 — ID: TS2S4-INTEGRALES-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : IPP, aire entre courbes, volume de révolution

**Bloc 3 — ID: TS2S4-INTEGRALES-B3** — Exemples résolus (section 8) — mots-clés : exemple, calcul d'aire, calcul de volume

**Bloc 4 — ID: TS2S4-INTEGRALES-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, LPET

**Bloc 5 — ID: TS2S4-INTEGRALES-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, sphère, cône

**Bloc 6 — ID: TS2S4-INTEGRALES-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Calcul intégral, Terminale S2/S4, pages 76-77)
✓ Exactitude mathématique vérifiée (corrigés recalculés, cohérence cône/sphère validée)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 1 et 2
