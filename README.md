# Neural_Terra-i

## Analyse d'anomalies dans la forêt primaire à partir d'images satellite radar



Dans le cadre d'un projet de collaboration avec Alliance of Bioversity International and CIAT, on développe des outils exploitant des algorithmes de Machine Learning pour traiter des informations fournies par des capteurs de télédétection (e.g. par des satellites), avec l'objectif de détecter la déforestation et surveiller les changements dans l'utilisation des sols.
Dans le cadre de ce projet, nous avons l'objectif de traiter des images fournies par les satellites Sentinel-1 de l'Agence Spatial Européenne (ESA). Ces satellites transportent un instrument radar qui permet de recueillir des données par tous les temps, de jour comme de nuit. Or, l'utilisation de ces données reste pas évident pour les non-experts du domaine et nécessite d'un pré-traitement lourd et chronophage.

Ce projet se déroule sur deux phases. Dans une première phase, nous allons étudier la faisabilité de créer des modèles capables de réaliser les différentes étapes de pré-traitement des images radar, liées à l'elimination du bruit, la calibration, et le filtrage des speckles à l'aide de réseaux de neurones profonds. Dans la deuxième phase, nous allons étudier une région de forêt tropicale afin de detecter des anomalies dans le patron de croissance naturelle de la forêt.

## Travail demandé:

1. Acquérir, pré-traiter et analyser des images satellite radar (Sentinel-1).

2. Développer des modèles à base de réseaux de neurones profonds capables de réaliser le débruitage des images radar équivalent au pré-traitement "classique" des images (https://github.com/wajuqi/Sentinel-1-preprocessing-using-Snappy). Pour entraîner ces modèles par un approche supervisé, on vise utiliser les images brutes en entrée et les images pré-traitées comme sortie désirée du système.

3. Evaluer la qualité des modèles d'élimination de bruit des images radar à base de réseaux de neurones profonds ainsi que le temps de calcul nécessaire pour appliquer un modèle pré-entraîné sur une collection d'images.

4. Acquérir et pré-traiter des images satellite radar (Sentinel-1) pour étudier l'évolution de la végétation en utilisant plusieurs images d'une même zone mais correspondantes à des temps différents.

5. Développer des outils de visualisation de cartes d'anomalies facilitant l'exploration des résultats obtenus à partir de l'application des modèles.
