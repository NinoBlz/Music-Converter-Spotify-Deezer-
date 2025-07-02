# 🎵 Convertisseur de Playlists Spotify ↔ Deezer

Un outil Python en ligne de commande pour transférer des playlists entre Spotify et Deezer dans les deux sens.

## ✨ Fonctionnalités

- **Conversion bidirectionnelle** : Spotify → Deezer et Deezer → Spotify
- **Conversion par URL** : Collez simplement le lien de votre playlist
- **Support des liens courts** : Compatible avec les liens partagés Deezer (link.deezer.com)
- **Authentification automatique** : OAuth automatisé pour Deezer avec ouverture de navigateur
- **Pagination complète** : Gère les playlists avec des centaines de morceaux
- **Recherche intelligente** : Algorithme de correspondance fuzzy pour trouver les morceaux équivalents
- **Interface conviviale** : Menu interactif avec indicateurs de progression

## 🚀 Installation

### Prérequis
- Python 3.7+
- Compte Spotify (gratuit ou premium)
- Compte Deezer (gratuit ou premium)

### Étapes d'installation

1. **Clonez le projet**
   ```bash
   git clone <url-du-repo>
   cd "convertiseur playlist/V2"
   ```

2. **Créez un environnement virtuel (recommandé)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate     # Windows
   ```

3. **Installez les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurez vos applications**
   ```bash
   cp config.example.py config.py
   ```
   Puis éditez `config.py` avec vos identifiants (voir section Configuration).

## ⚙️ Configuration

### Configuration Spotify

1. Allez sur [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Créez une nouvelle application
3. Récupérez votre **Client ID** et **Client Secret**
4. Ajoutez `http://127.0.0.1:8080/callback` comme URI de redirection
5. Mettez à jour `config.py` avec ces valeurs

### Configuration Deezer

1. Allez sur [Deezer Developers](https://developers.deezer.com/)
2. Créez une nouvelle application
3. Récupérez votre **App ID** et **App Secret**
4. Ajoutez `http://localhost:8080/deezer_callback` comme URI de redirection
5. Mettez à jour `config.py` avec ces valeurs

### Exemple de config.py
```python
SPOTIFY_CLIENT_ID = "votre_client_id_spotify"
SPOTIFY_CLIENT_SECRET = "votre_client_secret_spotify"

DEEZER_APP_ID = "votre_app_id_deezer"
DEEZER_APP_SECRET = "votre_app_secret_deezer"
```

## 🎯 Utilisation

### Lancement de l'application
```bash
python app.py
```

### Menu principal
```
📋 Options disponibles:
1. Voir mes playlists Spotify
2. Convertir playlist Spotify → Deezer
3. Convertir playlist par lien URL
4. Configurer Deezer (token manuel)
5. Authentification Deezer automatique
6. Obtenir URL d'authentification Deezer
7. Quitter
```

### Conversion par URL (Option 3)

Formats d'URL supportés :

**Spotify :**
- `https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`
- `spotify:playlist:37i9dQZF1DXcBWIGoYBM5M`

**Deezer :**
- `https://www.deezer.com/playlist/1234567890`
- `https://deezer.com/fr/playlist/1234567890`
- `https://link.deezer.com/s/shortcode` (liens courts)

### Première utilisation

1. **Authentification Spotify** : Se fait automatiquement au premier lancement
2. **Authentification Deezer** : Choisissez l'option 5 pour l'authentification automatique

## 📁 Structure du projet

```
convertiseur playlist/V2/
├── app.py                 # Application principale
├── config.py             # Configuration (à créer)
├── config.example.py     # Modèle de configuration
├── requirements.txt      # Dépendances Python
├── README.md            # Ce fichier
├── CLAUDE.md           # Documentation pour Claude Code
├── .gitignore          # Fichiers à ignorer par Git
└── .spotify_cache      # Cache Spotify (généré automatiquement)
```

## 🔧 Fonctionnalités techniques

### Classes principales

- **`PlaylistConverter`** : Gestionnaire principal des conversions
- **`DeezerOAuth`** : Système d'authentification OAuth automatisé pour Deezer

### Algorithme de correspondance

L'application utilise un algorithme intelligent pour faire correspondre les morceaux :
1. Nettoyage des titres (suppression des caractères spéciaux)
2. Recherche par correspondance partielle titre/artiste
3. Fallback sur le premier résultat si pas de correspondance exacte

### Gestion des erreurs

- Playlists privées détectées et signalées
- Morceaux non trouvés listés en fin de conversion
- Gestion des timeouts et erreurs réseau
- Validation des URLs avant traitement

## 📊 Limitations

- **Playlists privées Deezer** : Nécessitent une authentification pour être lues
- **Correspondance parfaite** : Certains morceaux peuvent ne pas être trouvés (remixes, versions alternatives)
- **Rate limiting** : Délai de 0.1s entre les requêtes pour éviter les limitations API
- **Port 8080** : Doit être libre pour l'authentification OAuth

## 🐛 Dépannage

### Erreurs courantes

**"Fichier config.py introuvable"**
```bash
cp config.example.py config.py
# Puis éditez config.py avec vos identifiants
```

**"Port 8080 est occupé"**
- Fermez les autres applications utilisant ce port
- Ou modifiez le port dans la configuration

**"Token Deezer invalide"**
- Réessayez l'authentification automatique (option 5)
- Vérifiez que l'URI de redirection est correctement configurée

### Support

Pour signaler un bug ou demander une fonctionnalité, créez une issue sur le repository GitHub.

## 📝 Licence

Ce projet est sous licence libre. Vous pouvez l'utiliser, le modifier et le distribuer selon vos besoins.

## 🙏 Remerciements

- [Spotipy](https://spotipy.readthedocs.io/) pour l'excellente bibliothèque Spotify
- APIs [Spotify](https://developer.spotify.com/) et [Deezer](https://developers.deezer.com/) pour leurs services
- La communauté Python pour les outils et bibliothèques
