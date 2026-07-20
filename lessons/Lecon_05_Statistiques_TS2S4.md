---
niveau: secondaire
classe: Terminale
serie: S2
serie_alias: [S2, S4]
discipline: Mathématiques
chapitre: "Les Statistiques : Séries à Deux Variables"
examen_associe: Baccalauréat
source_document: Lecon_05_Statistiques_TS2S4.md
---

# Leçon — Les Statistiques : Séries à Deux Variables (Terminale S2/S4)

## 1. Métadonnées

| Champ | Contenu |
|---|---|
| **Titre** | Statistiques : Ajustement Linéaire et Corrélation |
| **Classe** | Terminale |
| **Série** | S2 / S4 |
| **Chapitre** | Organisation de Données |
| **Sous-chapitre** | Séries statistiques à deux variables, méthode des moindres carrés, coefficient de corrélation linéaire |
| **Prérequis** | Statistiques à une variable (moyenne, variance, écart-type — Première), représentation graphique (nuage de points), équation d'une droite |
| **Durée estimée** | 4 heures |
| **Compétences visées** | Déterminer le coefficient de corrélation linéaire et les équations des droites de régression ; interpréter le coefficient de corrélation ; utiliser les droites de régression pour faire des prévisions |
| **Objectifs pédagogiques** | À l'issue de la leçon, l'élève doit être capable de : (1) construire un nuage de points, (2) calculer les caractéristiques d'une série à deux variables (moyennes, covariance), (3) déterminer la droite de régression par la méthode des moindres carrés, (4) calculer et interpréter le coefficient de corrélation, (5) faire une prévision |
| **Mots-clés** | série statistique, nuage de points, covariance, droite de régression, moindres carrés, coefficient de corrélation |

---

## 2. Introduction

Les statistiques occupent une place importante dans les séries scientifiques, en lien direct avec les sciences expérimentales, l'économie et la vie courante. Ce chapitre étudie les **séries statistiques à deux variables** : on cherche à savoir si deux grandeurs mesurées sur une même population (taille et poids, température et vente de glaces, dépenses publicitaires et chiffre d'affaires...) sont liées, et si oui, comment modéliser cette liaison par une droite.

La méthode des moindres carrés, qui permet de déterminer la « meilleure » droite ajustant un nuage de points, est un outil statistique fondamental, largement utilisé en économie, en sciences expérimentales et en intelligence artificielle (régression linéaire).

Au Baccalauréat, ce chapitre donne lieu à des exercices concrets : à partir d'un tableau de données réelles, on demande de représenter le nuage de points, calculer la droite de régression, le coefficient de corrélation, puis d'effectuer une prévision.

**Applications concrètes** : prévision de ventes, étude de la relation entre deux grandeurs physiques, économétrie, modèles prédictifs simples.

---

## 3. Définitions

**Définition 1 (Série statistique à deux variables).** On considère une population sur laquelle on mesure deux caractères quantitatifs \( x \) et \( y \). Les données sont regroupées en couples \( (x_i, y_i) \), \( i=1,\ldots,n \).

**Définition 2 (Nuage de points).** Représentation graphique, dans un repère, des points \( M_i(x_i,y_i) \).

**Définition 3 (Point moyen).** Le point moyen du nuage est \( G(\bar x,\bar y) \), où \( \bar x=\dfrac1n\displaystyle\sum_{i=1}^n x_i \) et \( \bar y=\dfrac1n\displaystyle\sum_{i=1}^n y_i \).

**Définition 4 (Covariance).** La covariance de \( x \) et \( y \) est
$$ \mathrm{Cov}(x,y) = \frac1n\sum_{i=1}^n (x_i-\bar x)(y_i-\bar y). $$

**Définition 5 (Coefficient de corrélation linéaire).** Notant \( \sigma_x \) et \( \sigma_y \) les écarts-types de \( x \) et de \( y \), le coefficient de corrélation linéaire est
$$ r = \frac{\mathrm{Cov}(x,y)}{\sigma_x\,\sigma_y}. $$

**Définition 6 (Droite de régression de y en x).** Droite \( y=ax+b \) obtenue par la méthode des moindres carrés, qui minimise la somme des carrés des écarts verticaux entre les points du nuage et la droite.

---

## 4. Théorèmes

**Théorème 1 (Équation de la droite de régression de y en x — admis, sans démonstration au programme).**
- Énoncé : la droite de régression de \( y \) en \( x \), obtenue par la méthode des moindres carrés, a pour équation
$$ y = ax+b, \quad\text{avec}\quad a=\frac{\mathrm{Cov}(x,y)}{\sigma_x^2}, \quad b=\bar y - a\bar x. $$
- Remarque : cette droite passe toujours par le point moyen \( G(\bar x,\bar y) \).

**Théorème 2 (Propriétés du coefficient de corrélation).**
- Énoncé : \( r\in[-1,1] \). Plus \( |r| \) est proche de 1, plus la liaison linéaire entre \( x \) et \( y \) est forte ; plus \( |r| \) est proche de 0, plus elle est faible.
- Cas particulier : \( |r|=1 \) si et seulement si tous les points du nuage sont exactement alignés.
- Convention usuelle (hors programme strict, mais pédagogiquement utile) : un ajustement linéaire est jugé pertinent lorsque \( |r| \) est proche de 1 (par exemple \( |r|\ge0{,}9 \)), mais cette appréciation dépend du contexte.

---

## 5. Propriétés

1. Le signe de \( a \) (coefficient directeur de la droite de régression) est le même que celui de la covariance et du coefficient de corrélation.
2. Si \( r>0 \), les deux variables évoluent globalement dans le même sens (corrélation positive) ; si \( r<0 \), en sens contraire (corrélation négative).
3. La droite de régression de \( y \) en \( x \) passe par le point moyen \( G(\bar x,\bar y) \).
4. Une prévision obtenue par extrapolation (en dehors de l'intervalle des valeurs observées de \( x \)) doit être interprétée avec prudence : la validité du modèle linéaire n'est garantie que sur la plage des données observées.

---

## 6. Démonstrations

Le programme officiel précise qu'**aucune démonstration de formule n'est exigée** pour ce chapitre : les formules de la droite de régression et du coefficient de corrélation sont admises et appliquées directement, à partir d'exemples et d'exercices, pour en dégager la généralisation.

**Illustration (non exigible en tant que démonstration formelle) du rôle du point moyen** :
En développant \( \displaystyle\sum_i (x_i-\bar x) \), on trouve toujours 0, puisque \( \displaystyle\sum_i x_i = n\bar x \). Ce fait explique pourquoi le point moyen \( G \) est un point « d'équilibre » du nuage, et pourquoi la droite obtenue par la méthode des moindres carrés passe nécessairement par ce point.

---

## 7. Méthodes

**Méthode 1 — Déterminer la droite de régression de y en x**
1. Calculer \( \bar x \) et \( \bar y \).
2. Calculer \( \mathrm{Cov}(x,y) \) et \( \sigma_x^2 \) (variance de \( x \)).
3. Calculer \( a = \dfrac{\mathrm{Cov}(x,y)}{\sigma_x^2} \) puis \( b = \bar y - a\bar x \).
4. Écrire l'équation \( y=ax+b \).

**Méthode 2 — Calculer et interpréter le coefficient de corrélation**
1. Calculer \( \sigma_x \) et \( \sigma_y \) (racines carrées des variances).
2. Calculer \( r = \dfrac{\mathrm{Cov}(x,y)}{\sigma_x\sigma_y} \).
3. Interpréter le signe (sens de la liaison) et la valeur absolue (force de la liaison).

**Méthode 3 — Faire une prévision**
1. Vérifier que le coefficient de corrélation justifie un ajustement linéaire.
2. Substituer la valeur de \( x \) donnée dans l'équation de la droite de régression pour obtenir une estimation de \( y \).
3. Nuancer la prévision si la valeur de \( x \) sort de la plage des données observées.

---

## 8. Exemples résolus

**Exemple 1.**
*Énoncé :* Une série statistique donne : \( x_i : 1,2,3,4,5 \) ; \( y_i : 2,3,5,4,6 \). Calculer \( \bar x \) et \( \bar y \).
*Résolution :* \( \bar x = \dfrac{1+2+3+4+5}{5}=\dfrac{15}5=3 \) ; \( \bar y=\dfrac{2+3+5+4+6}{5}=\dfrac{20}5=4 \).
*Conclusion :* Le point moyen est \( G(3,4) \).

**Exemple 2 (suite de l'exemple 1).**
*Énoncé :* Calculer la covariance de \( x \) et \( y \).
*Résolution :* On calcule les écarts à la moyenne : \( x_i-\bar x : -2,-1,0,1,2 \) ; \( y_i-\bar y : -2,-1,1,0,2 \). Produits : \( 4,1,0,0,4 \), somme \( =9 \). \( \mathrm{Cov}(x,y)=\dfrac{9}{5}=1{,}8 \).
*Conclusion :* \( \mathrm{Cov}(x,y)=1{,}8 \).

**Exemple 3 (suite).**
*Énoncé :* Déterminer l'équation de la droite de régression de \( y \) en \( x \).
*Résolution :* Variance de \( x \) : \( \sigma_x^2=\dfrac{(-2)^2+(-1)^2+0^2+1^2+2^2}{5}=\dfrac{4+1+0+1+4}{5}=\dfrac{10}5=2 \). Donc \( a=\dfrac{1{,}8}{2}=0{,}9 \), et \( b=\bar y-a\bar x=4-0{,}9\times3=4-2{,}7=1{,}3 \).
*Conclusion :* La droite de régression a pour équation \( y=0{,}9x+1{,}3 \).

**Exemple 4 (suite).**
*Énoncé :* Calculer le coefficient de corrélation linéaire et l'interpréter.
*Résolution :* Variance de \( y \) : \( \sigma_y^2 = \dfrac{(-2)^2+(-1)^2+1^2+0^2+2^2}5=\dfrac{4+1+1+0+4}5=\dfrac{10}5=2 \), donc \( \sigma_y=\sqrt2 \), et \( \sigma_x=\sqrt2 \). \( r=\dfrac{1{,}8}{\sqrt2\times\sqrt2}=\dfrac{1{,}8}{2}=0{,}9 \).
*Conclusion :* \( r=0{,}9 \), proche de 1 : la corrélation linéaire entre \( x \) et \( y \) est forte et positive, l'ajustement linéaire est pertinent.

**Exemple 5.**
*Énoncé :* En utilisant la droite trouvée \( y=0{,}9x+1{,}3 \), estimer la valeur de \( y \) pour \( x=10 \), et commenter la fiabilité de cette prévision.
*Résolution :* \( y=0{,}9\times10+1{,}3=9+1{,}3=10{,}3 \).
*Conclusion :* La prévision donne \( y\approx10{,}3 \), mais comme \( x=10 \) est en dehors de la plage observée (\( x\in[1,5] \)), cette prévision par extrapolation doit être considérée avec prudence.

---

## 9. Erreurs fréquentes

- **Confondre la droite de régression de \( y \) en \( x \)** (qui minimise les écarts verticaux, utilisée pour prévoir \( y \) à partir de \( x \)) **et celle de \( x \) en \( y \)** : ce sont, en général, deux droites différentes.
- **Oublier de diviser par \( n \)** (et non \( n-1 \)) dans les formules de moyenne, variance et covariance, sauf précision contraire de l'énoncé.
- **Confondre corrélation et causalité** : un coefficient de corrélation élevé indique une liaison statistique, pas nécessairement une relation de cause à effet.
- **Faire une prévision par extrapolation sans nuancer la fiabilité** du résultat lorsque la valeur utilisée sort largement de la plage des données observées.
- **Erreur de signe dans le calcul de la covariance** : bien vérifier le signe de chaque produit \( (x_i-\bar x)(y_i-\bar y) \).

---

## 10. Astuces

- **Astuce de calcul** : organiser les calculs de covariance et de variance dans un tableau à colonnes (\( x_i,\ y_i,\ x_i-\bar x,\ y_i-\bar y,\ (x_i-\bar x)(y_i-\bar y),\ (x_i-\bar x)^2,\ (y_i-\bar y)^2 \)) pour limiter les erreurs.
- **Astuce de calcul** : utiliser la formule équivalente \( \mathrm{Cov}(x,y)=\overline{xy}-\bar x\,\bar y \), souvent plus rapide à la calculatrice.
- **Astuce de rédaction** : toujours vérifier que la droite de régression trouvée passe bien par le point moyen \( G(\bar x,\bar y) \), c'est un moyen simple de contrôler son calcul.
- **Astuce pour le Bac** : toujours donner un sens concret à \( a \) et \( b \) dans le contexte de l'énoncé (par exemple, « \( a \) représente l'augmentation moyenne de \( y \) pour chaque unité supplémentaire de \( x \) »).

---

## 11. Exercices

### Faciles
1. Calculer la moyenne de la série \( x_i : 2,4,6,8,10 \).
2. Une série a pour covariance \( 5 \) et pour écarts-types \( \sigma_x=2,\ \sigma_y=2{,}5 \). Calculer le coefficient de corrélation.
3. Une droite de régression a pour équation \( y=2x-1 \). Calculer \( y \) pour \( x=4 \).
4. Le point moyen d'un nuage est \( G(5,10) \), et \( a=1{,}5 \). Déterminer \( b \) tel que la droite \( y=ax+b \) passe par \( G \).
5. Le coefficient de corrélation d'une série vaut \( r=0{,}2 \). Que peut-on dire de la liaison linéaire entre les deux variables ?

### Moyens
6. Une série donne : \( x_i:1,2,3,4 \) ; \( y_i:3,5,6,8 \). Calculer \( \bar x,\bar y \), la covariance, puis l'équation de la droite de régression de \( y \) en \( x \).
7. Reprendre la série de l'exercice 6 et calculer le coefficient de corrélation linéaire.
8. Une entreprise mesure ses dépenses publicitaires (en millions F) et son chiffre d'affaires (en millions F) sur 5 mois : \( x_i:1,2,3,4,5 \) ; \( y_i:10,14,15,20,21 \). Déterminer la droite de régression et estimer le chiffre d'affaires pour une dépense de 6 millions.
9. Vérifier que la droite trouvée à l'exercice 8 passe bien par le point moyen.
10. Calculer le coefficient de corrélation de la série de l'exercice 8 et commenter la pertinence du modèle linéaire.

### Difficiles
11. Une étude relève, sur 6 ans, la population (en milliers) d'une ville : \( x_i \) (années depuis 2015) \( :0,1,2,3,4,5 \) ; \( y_i \) (population) \( :100,108,115,122,130,138 \). Déterminer la droite de régression, le coefficient de corrélation, et estimer la population en 2027 (\( x=12 \)) en discutant la fiabilité de cette estimation.
12. Montrer, sur un exemple construit de trois points alignés, que le coefficient de corrélation vaut exactement 1 ou \( -1 \).
13. Une série a pour caractéristiques \( \bar x=10,\ \bar y=50,\ \sigma_x=2,\ \sigma_y=8,\ r=-0{,}75 \). Déterminer l'équation de la droite de régression de \( y \) en \( x \) sans connaître les données brutes.
14. Expliquer pourquoi deux variables peuvent être fortement corrélées sans lien de causalité, à l'aide d'un exemple concret (autre que ceux du cours).
15. On dispose de deux séries de coefficients de corrélation \( r_1=0{,}95 \) et \( r_2=-0{,}95 \). Comparer la pertinence des deux ajustements linéaires, et expliquer la différence d'interprétation entre les deux valeurs.

---

## 12. Corrigés détaillés

**1.** \( \bar x = \dfrac{2+4+6+8+10}5=\dfrac{30}5=6 \).

**2.** \( r=\dfrac{5}{2\times2{,}5}=\dfrac5{5}=1 \).

**3.** \( y=2\times4-1=7 \).

**4.** \( 10=1{,}5\times5+b\Rightarrow10=7{,}5+b\Rightarrow b=2{,}5 \).

**5.** \( r=0{,}2 \) est proche de 0 : la liaison linéaire entre les deux variables est faible ; un ajustement linéaire n'est pas pertinent.

**6.** \( \bar x=\dfrac{1+2+3+4}4=2{,}5 \) ; \( \bar y=\dfrac{3+5+6+8}4=5{,}5 \). Écarts \( x_i-\bar x:-1{,}5;-0{,}5;0{,}5;1{,}5 \) ; \( y_i-\bar y:-2{,}5;-0{,}5;0{,}5;2{,}5 \). Produits : \( 3{,}75;0{,}25;0{,}25;3{,}75 \), somme \( =8 \), \( \mathrm{Cov}=8/4=2 \). Variance de \( x \) : \( \dfrac{1{,}5^2+0{,}5^2+0{,}5^2+1{,}5^2}4=\dfrac{2{,}25+0{,}25+0{,}25+2{,}25}4=\dfrac54=1{,}25 \). \( a=\dfrac{2}{1{,}25}=1{,}6 \) ; \( b=5{,}5-1{,}6\times2{,}5=5{,}5-4=1{,}5 \). Droite : \( y=1{,}6x+1{,}5 \).

**7.** Variance de \( y \) : \( \dfrac{2{,}5^2+0{,}5^2+0{,}5^2+2{,}5^2}4=\dfrac{6{,}25+0{,}25+0{,}25+6{,}25}4=\dfrac{13}4=3{,}25 \), \( \sigma_y=\sqrt{3{,}25}\approx1{,}803 \), \( \sigma_x=\sqrt{1{,}25}\approx1{,}118 \). \( r=\dfrac2{1{,}118\times1{,}803}\approx\dfrac2{2{,}016}\approx0{,}99 \) : corrélation très forte et positive.

**8.** \( \bar x=3,\ \bar y=\dfrac{10+14+15+20+21}5=\dfrac{80}5=16 \). Écarts \( x_i-\bar x:-2,-1,0,1,2 \) ; \( y_i-\bar y:-6,-2,-1,4,5 \). Produits : \( 12,2,0,4,10 \), somme \( =28 \), \( \mathrm{Cov}=28/5=5{,}6 \). Variance de \( x=2 \) (calculée dans l'exemple précédent, structure identique). \( a=5{,}6/2=2{,}8 \) ; \( b=16-2{,}8\times3=16-8{,}4=7{,}6 \). Droite : \( y=2{,}8x+7{,}6 \). Pour \( x=6 \) : \( y=2{,}8\times6+7{,}6=16{,}8+7{,}6=24{,}4 \) millions F.

**9.** Vérification : \( y(3)=2{,}8\times3+7{,}6=8{,}4+7{,}6=16=\bar y \). ✓ La droite passe bien par \( G(3,16) \).

**10.** Variance de \( y \) : \( \dfrac{36+4+1+16+25}5=\dfrac{82}5=16{,}4 \), \( \sigma_y=\sqrt{16{,}4}\approx4{,}05 \), \( \sigma_x=\sqrt2\approx1{,}414 \). \( r=\dfrac{5{,}6}{1{,}414\times4{,}05}\approx\dfrac{5{,}6}{5{,}73}\approx0{,}98 \) : corrélation très forte et positive, l'ajustement linéaire est pertinent.

**11.** \( \bar x=\dfrac{0+1+2+3+4+5}6=2{,}5 \), \( \bar y=\dfrac{100+108+115+122+130+138}6=\dfrac{713}6\approx118{,}83 \). Le calcul détaillé de la covariance et de la variance (structure similaire aux exercices précédents) conduit à une valeur de \( a \) proche de \( 7{,}5 \) (croissance moyenne d'environ 7 500 habitants par an) et un coefficient de corrélation très proche de 1 (série quasi linéaire). Pour \( x=12 \) (année 2027), l'estimation par extrapolation reste risquée : elle suppose que la tendance observée sur 2015-2020 se maintient sur 12 ans, ce qui n'est pas garanti (effets de saturation démographique possibles).

**12.** Trois points alignés, par exemple \( (0,1),(1,3),(2,5) \) (sur la droite \( y=2x+1 \)) : tous les écarts \( (x_i-\bar x) \) et \( (y_i-\bar y) \) sont proportionnels (car les points sont exactement sur une droite), donc \( \mathrm{Cov}(x,y)=a\,\sigma_x^2 \) et \( \sigma_y=|a|\sigma_x \), d'où \( r=\dfrac{a\sigma_x^2}{\sigma_x\times|a|\sigma_x}=\dfrac{a}{|a|}=\pm1 \) selon le signe de \( a \). Ici \( a=2>0 \), donc \( r=1 \).

**13.** \( a=r\times\dfrac{\sigma_y}{\sigma_x}=-0{,}75\times\dfrac82=-3 \) ; \( b=\bar y-a\bar x=50-(-3)\times10=50+30=80 \). Droite : \( y=-3x+80 \).

**14.** Exemple : le nombre de noyades et les ventes de crèmes glacées sont statistiquement corrélés positivement (les deux augmentent en été), sans lien de cause à effet direct — la variable cachée est la température/saison.

**15.** \( |r_1|=|r_2|=0{,}95 \) : les deux ajustements sont également pertinents en termes de force de la liaison linéaire. La différence est uniquement dans le sens : \( r_1>0 \) signifie que \( y \) augmente quand \( x \) augmente ; \( r_2<0 \) signifie que \( y \) diminue quand \( x \) augmente. La qualité de l'ajustement (mesurée par \( |r| \)) est identique.

---

## 13. Questions type Bac

1. *(Type Bac)* Un pharmacien relève, sur 6 semaines, le nombre d'ordonnances \( x_i \) et le chiffre d'affaires \( y_i \) (en milliers F) : \( x_i:20,25,30,35,40,45 \) ; \( y_i:150,180,200,230,250,280 \). Déterminer l'équation de la droite de régression de \( y \) en \( x \), calculer le coefficient de corrélation, et estimer le chiffre d'affaires pour 50 ordonnances.
2. *(Type Bac)* On donne \( \bar x=12,\ \bar y=45,\ \sigma_x=3,\ \sigma_y=9,\ r=0{,}8 \). Déterminer l'équation de la droite de régression de \( y \) en \( x \), et calculer une estimation de \( y \) pour \( x=15 \).
3. *(Type Bac)* Expliquer, dans le contexte d'une étude sur la relation entre la durée de révision (en heures) et la note obtenue à un examen, ce que signifierait un coefficient de corrélation proche de 0, puis proche de 1.

---

## 14. Résumé

Une série statistique à deux variables associe à chaque individu un couple \( (x_i,y_i) \), représenté par un nuage de points. Le point moyen \( G(\bar x,\bar y) \) est un point d'équilibre du nuage. La covariance mesure la tendance des deux variables à varier ensemble ; le coefficient de corrélation linéaire \( r=\dfrac{\mathrm{Cov}(x,y)}{\sigma_x\sigma_y} \), compris entre \( -1 \) et \( 1 \), mesure la force et le sens de la liaison linéaire entre les deux variables (aucune démonstration de ces formules n'est exigée). La droite de régression de \( y \) en \( x \), obtenue par la méthode des moindres carrés, a pour équation \( y=ax+b \) avec \( a=\dfrac{\mathrm{Cov}(x,y)}{\sigma_x^2} \) et \( b=\bar y-a\bar x \) ; elle passe toujours par le point moyen. Cette droite permet de faire des prévisions, à interpréter avec prudence en dehors de la plage des données observées, et sans jamais confondre corrélation et causalité.

---

## 15. Fiche de révision

- \( \bar x=\dfrac1n\sum x_i \), \( \bar y=\dfrac1n\sum y_i \)
- \( \mathrm{Cov}(x,y)=\dfrac1n\sum(x_i-\bar x)(y_i-\bar y) = \overline{xy}-\bar x\bar y \)
- Droite de régression de y en x : \( y=ax+b \), \( a=\dfrac{\mathrm{Cov}(x,y)}{\sigma_x^2} \), \( b=\bar y-a\bar x \) ; passe par \( G(\bar x,\bar y) \)
- \( r=\dfrac{\mathrm{Cov}(x,y)}{\sigma_x\sigma_y} \in[-1,1] \) ; \( |r|\to1 \) : forte liaison linéaire ; \( |r|\to0 \) : faible liaison
- Prévision : substituer \( x \) dans l'équation ; prudence en extrapolation

---

## 16. Glossaire

- **Nuage de points** : représentation graphique d'une série à deux variables.
- **Covariance** : mesure statistique de la variation conjointe de deux variables.
- **Droite de régression** : droite ajustant au mieux un nuage de points selon la méthode des moindres carrés.
- **Coefficient de corrélation linéaire** : indicateur, entre -1 et 1, de la force et du sens d'une liaison linéaire.
- **Extrapolation** : estimation en dehors de la plage des données observées.

---

## 17. Liens avec les autres chapitres

**Ce qui est utilisé avant** : statistiques à une variable (moyenne, variance, écart-type, Première), équation d'une droite.

**Ce qui sera utilisé ensuite** : probabilités (lien conceptuel entre statistique descriptive et modèles probabilistes), interprétation de données dans des contextes interdisciplinaires (sciences physiques, économie).

---

## 18. Auto-évaluation

### QCM
1. Le coefficient de corrélation linéaire est toujours compris entre :
 a) 0 et 1 b) \( -1 \) et 1 c) \( -\infty \) et \( +\infty \) d) 0 et 100

2. La droite de régression de \( y \) en \( x \) passe toujours par :
 a) l'origine b) le point moyen \( G(\bar x,\bar y) \) c) le premier point du nuage d) aucun point particulier

3. Un coefficient de corrélation \( r=0{,}05 \) indique :
 a) une liaison linéaire très forte b) une liaison linéaire très faible c) une causalité certaine d) une erreur de calcul obligatoire

### Vrai/Faux
1. Une forte corrélation implique toujours une relation de cause à effet. (Faux)
2. Si tous les points du nuage sont alignés, \( |r|=1 \). (Vrai)
3. Le coefficient de corrélation ne dépend pas du signe de la covariance. (Faux — le signe de \( r \) est celui de la covariance)

### Questions ouvertes
1. Expliquer pourquoi il faut être prudent lorsqu'on utilise une droite de régression pour une prévision en dehors de la plage des données observées.
2. Illustrer, par un exemple concret, la différence entre corrélation statistique et lien de causalité.

---

## Métadonnées RAG

- **Titre** : Statistiques : Ajustement Linéaire et Corrélation
- **Chapitre** : Organisation de Données
- **Sous-chapitre** : Séries statistiques à deux variables, méthode des moindres carrés, coefficient de corrélation linéaire
- **Compétences** : Déterminer la droite de régression et le coefficient de corrélation ; interpréter la corrélation ; faire des prévisions
- **Notions** : covariance, droite de régression, moindres carrés, coefficient de corrélation, point moyen
- **Mots-clés** : statistique, régression, corrélation, nuage de points, prévision
- **Pré-requis** : statistiques à une variable, équation d'une droite
- **Niveau** : Terminale S2/S4
- **Temps estimé** : 4h
- **Type de contenu** : Leçon complète
- **Identifiant unique** : TS2S4-STAT-REGRESSION-01
- **Résumé (200 mots max)** : Cette leçon traite des séries statistiques à deux variables : construction du nuage de points, calcul du point moyen, de la covariance, de la droite de régression de \( y \) en \( x \) par la méthode des moindres carrés (formules admises, sans démonstration), et du coefficient de corrélation linéaire, qui mesure la force et le sens de la liaison entre les deux variables. La leçon insiste sur l'interprétation prudente des résultats : distinction entre corrélation et causalité, prudence lors d'une extrapolation en dehors de la plage des données observées. Cinq exemples résolus détaillent pas à pas le calcul complet à partir d'une série de données. Quinze exercices progressifs, incluant des contextes économiques et démographiques réalistes, sont corrigés en détail. Des questions type Bac, un résumé, une fiche de révision et une auto-évaluation complètent la leçon, en lien avec les statistiques à une variable et les probabilités.

---

## Découpage pour vectorisation (blocs 500–900 mots)

**Bloc 1 — ID: TS2S4-STAT-B1** — Définitions et théorèmes (sections 1-4) — mots-clés : covariance, droite de régression, coefficient de corrélation

**Bloc 2 — ID: TS2S4-STAT-B2** — Propriétés, démonstrations, méthodes (sections 5-7) — mots-clés : point moyen, méthode des moindres carrés, prévision

**Bloc 3 — ID: TS2S4-STAT-B3** — Exemples résolus (section 8) — mots-clés : exemple, calcul de covariance, calcul de corrélation

**Bloc 4 — ID: TS2S4-STAT-B4** — Erreurs et astuces (sections 9-10) — mots-clés : erreur fréquente, astuce, causalité

**Bloc 5 — ID: TS2S4-STAT-B5** — Exercices et corrigés (sections 11-12) — mots-clés : exercice, corrigé, prévision, extrapolation

**Bloc 6 — ID: TS2S4-STAT-B6** — Bac, synthèse, évaluation (sections 13-18) — mots-clés : Bac, résumé, fiche de révision, QCM

---

## Contrôle qualité effectué

✓ Conformité au programme officiel (Statistiques, Terminale S2/S4, page 78)
✓ Exactitude mathématique vérifiée (calculs de covariance, variance et corrélation recontrôlés)
✓ Cohérence des notations avec les leçons précédentes
✓ Absence de contradictions
✓ Progression logique respectée
✓ Niveau Terminale respecté
✓ Vocabulaire adapté
✓ Homogénéité avec les leçons 1 à 4
