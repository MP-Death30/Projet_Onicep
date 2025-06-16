# 🎓 Scraper de Formations Onisep avec Recherche par Localisation

Un outil Python automatisé pour rechercher et extraire des informations détaillées sur les formations disponibles sur [Onisep.fr](https://www.onisep.fr), avec la possibilité de filtrer par localisation géographique.

## ✨ Fonctionnalités

- **🔍 Recherche avancée** : Recherche par mot-clé avec filtrage par niveau d'études
- **📍 Filtrage géographique** : Recherche par ville, code postal, département ou région
- **📊 Extraction complète** : Récupération des informations détaillées (durée, nature, type, établissements)
- **📈 Pagination automatique** : Parcours automatique de plusieurs pages de résultats
- **💾 Export CSV** : Sauvegarde des résultats dans un fichier CSV structuré
- **🤖 Mode headless** : Exécution en arrière-plan sans interface graphique

## 🛠️ Prérequis

### Logiciels requis
- Python 3.7+
- Google Chrome (dernière version)

### Dépendances Python
```bash
pip install selenium webdriver-manager
```

## 📦 Installation

1. **Cloner ou télécharger le projet**
```bash
git clone [url-du-repo]
cd onisep-scraper
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Vérifier l'installation de Chrome**
Le script utilise Chrome en mode headless. Assurez-vous que Google Chrome est installé sur votre système.

## 🚀 Utilisation

### Lancement du programme
```bash
python scraper_onisep.py
```

### Interface interactive

Le programme vous guidera à travers plusieurs étapes :

#### 1. 🔍 Mot-clé de recherche
```
Mot-clé de recherche (ex: mathématiques) : informatique
```

#### 2. 🎯 Niveau d'études
```
Choisis un niveau d'étude :
  (laisser vide pour aucun filtre)
  1 → Bac +1 à +2
  3 → Bac +3
  4 → Bac +4 à +5
  6 → Bac +6 et +
Ton choix (1, 3, 4, 6 ou vide) : 3
```

#### 3. 📍 Localisation géographique
```
📍 Pour une **ville**, indique le code postal** (ex : Nîmes = 30000).
   Pour un **département** ou une **région**, indique son **nom complet** (ex : Gard, Occitanie).
Entrez une localisation (ville ou code postal) : 30000
```

#### 4. 📊 Nombre de résultats
```
Nombre max de résultats (défaut = 10, max = 50) : 20
```

#### 5. 💾 Nom du fichier de sortie
```
Nom du fichier en sortie : formations_informatique_nimes
```

## 📄 Format de sortie

Le fichier CSV généré contient les colonnes suivantes :

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `titre` | Nom de la formation | "Licence informatique" |
| `lien` | URL de la fiche formation | "https://www.onisep.fr/..." |
| `durée` | Durée de la formation | "3 ans" |
| `nature` | Nature de la formation | "Formation universitaire" |
| `type` | Type de formation | "Formation initiale sous statut d'étudiant" |
| `établissements_conseillés` | Liste des établissements | "Université de Montpellier (Montpellier, 34000)" |

### Exemple de fichier CSV
```csv
titre;lien;durée;nature;type;établissements_conseillés
Licence informatique;https://www.onisep.fr/...;3 ans;Formation universitaire;Formation initiale sous statut d'étudiant;Université de Montpellier (Montpellier, 34000) | IUT de Nîmes (Nîmes, 30000)
```

## 🔧 Configuration avancée

### Niveaux d'études supportés
```python
NIVEAU_MAPPING = {
    "1": "après bac/Bac +1 à +2",
    "3": "après bac/Bac +3", 
    "4": "après bac/Bac +4 à +5",
    "6": "après bac/Bac +6 et +"
}
```

### Options Chrome personnalisables
Le script utilise Chrome en mode headless avec les options suivantes :
- `--headless=new` : Mode invisible
- `--no-sandbox` : Sécurité désactivée (pour certains environnements)
- `--disable-dev-shm-usage` : Optimisation mémoire

## 🎯 Exemples d'utilisation

### Recherche générale
- **Mot-clé** : "médecine"
- **Niveau** : 6 (Bac +6 et +)
- **Localisation** : "Île-de-France"
- **Résultats** : 15

### Recherche spécialisée
- **Mot-clé** : "développement web"
- **Niveau** : 3 (Bac +3)
- **Localisation** : "69000" (Lyon)
- **Résultats** : 10

### Recherche par département
- **Mot-clé** : "commerce"
- **Niveau** : 4 (Bac +4 à +5)
- **Localisation** : "Var"
- **Résultats** : 25

## ⚠️ Limitations et bonnes pratiques

### Limitations techniques
- **Délais** : Le script inclut des pauses pour éviter la surcharge des serveurs Onisep
- **Pagination** : Maximum 50 résultats par recherche pour optimiser les performances
- **Sélecteurs** : Les sélecteurs CSS peuvent changer si Onisep modifie son site

### Bonnes pratiques
- **Usage responsable** : Évitez les requêtes trop fréquentes
- **Validation** : Vérifiez toujours les données extraites
- **Sauvegarde** : Conservez vos fichiers CSV dans un dossier dédié

## 🐛 Résolution de problèmes

### Erreurs courantes

#### "ChromeDriver not found"
```bash
# Solution : Réinstaller webdriver-manager
pip uninstall webdriver-manager
pip install webdriver-manager
```

#### "Timeout waiting for element"
- Vérifiez votre connexion internet
- Le site Onisep peut être temporairement indisponible

#### "Champ de localisation non trouvé"
- La localisation sera ignorée automatiquement
- Le script continuera sans filtrage géographique

### Mode debug
Pour activer le mode debug (avec interface Chrome visible) :
```python
# Commentez cette ligne dans create_driver()
# options.add_argument("--headless=new")
```

## 🔄 Mises à jour

Le script s'adapte automatiquement aux changements mineurs du site Onisep grâce à :
- Multiples sélecteurs CSS de fallback
- Gestion d'erreurs robuste
- Timeouts adaptatifs

## 📞 Support

En cas de problème :
1. Vérifiez que Chrome est à jour
2. Redémarrez votre connexion internet
3. Testez avec des paramètres plus simples
4. Consultez les logs d'erreur dans la console

## 📝 Licence

Ce projet est à des fins éducatives et de recherche. Respectez les conditions d'utilisation d'Onisep.fr.

---

**💡 Astuce** : Pour des recherches répétées, créez un script batch avec vos paramètres favoris !
