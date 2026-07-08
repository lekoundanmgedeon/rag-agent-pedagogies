---
niveau: secondaire
classe: Terminale
serie: S1
discipline: Mathématiques
examen_associe: Baccalauréat
chapitre: Suites numériques
source_document: annale_bac_s1_2019_maths.md
---

## Chapitre : Suites numériques — annale Baccalauréat S1 2019

Ce document regroupe un exercice d'annale corrigé sur les suites. L'énoncé,
l'indication et la solution forment un tout indivisible pour la révision.

### Exercice : Suite définie par récurrence (Bac S1 2019)

**Énoncé.** On considère la suite $(u_n)$ définie par $u_0 = 1$ et, pour tout
entier naturel $n$, $u_{n+1} = \dfrac{1}{2} u_n + 3$.

1. Calculer $u_1$ et $u_2$.
2. On pose $v_n = u_n - 6$. Montrer que $(v_n)$ est géométrique.
3. En déduire l'expression de $u_n$ en fonction de $n$, puis la limite de $(u_n)$.

**Indice.** Pour la question 2, exprime $v_{n+1} = u_{n+1} - 6$ en fonction de
$v_n$ ; tu dois retrouver une raison constante. Pour la limite, souviens-toi
qu'une suite géométrique de raison $q$ avec $|q| < 1$ tend vers $0$.

**Solution.**

1. $u_1 = \frac{1}{2}\times 1 + 3 = 3{,}5$ et $u_2 = \frac{1}{2}\times 3{,}5 + 3 = 4{,}75$.

2. $v_{n+1} = u_{n+1} - 6 = \frac{1}{2}u_n + 3 - 6 = \frac{1}{2}u_n - 3 = \frac{1}{2}(u_n - 6) = \frac{1}{2}v_n$.
   Donc $(v_n)$ est géométrique de raison $q = \frac{1}{2}$ et de premier terme
   $v_0 = u_0 - 6 = -5$.

3. On a $v_n = v_0\, q^n = -5 \left(\frac{1}{2}\right)^n$, d'où
   $u_n = v_n + 6 = 6 - 5\left(\frac{1}{2}\right)^n$.
   Comme $\left|\frac{1}{2}\right| < 1$, $\left(\frac{1}{2}\right)^n \to 0$, donc
   $\lim_{n \to +\infty} u_n = 6$.
