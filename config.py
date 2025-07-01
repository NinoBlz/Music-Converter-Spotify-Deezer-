# Exemple de configuration des applications Spotify et Deezer
# Copiez ce fichier vers config.py et remplacez les valeurs par vos vraies identifiants

# Configuration Spotify
# Obtenez vos identifiants sur https://developer.spotify.com/dashboard/
SPOTIFY_CLIENT_ID = "your_spotify_client_id_here"
SPOTIFY_CLIENT_SECRET = "your_spotify_client_secret_here"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8080/callback"
SPOTIFY_SCOPE = "playlist-read-private playlist-modify-public playlist-modify-private"

# Configuration Deezer
# Créez une app sur https://developers.deezer.com/ et obtenez vos identifiants
# IMPORTANT: Configurez l'URI de redirection à http://localhost:8080/deezer_callback
DEEZER_APP_ID = "your_deezer_app_id_here"
DEEZER_APP_SECRET = "your_deezer_app_secret_here"

# URLs de base (ne pas modifier)
DEEZER_BASE_URL = "https://api.deezer.com"
DEEZER_AUTH_URL = "https://connect.deezer.com/oauth/auth.php"
DEEZER_TOKEN_URL = "https://connect.deezer.com/oauth/access_token.php"