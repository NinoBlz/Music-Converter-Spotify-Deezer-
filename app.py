#!/usr/bin/env python3
"""
Convertisseur de playlists entre Spotify et Deezer
Permet de transférer des playlists d'une plateforme à l'autre
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import json
import time
from typing import List, Dict, Optional, Tuple
import re
from urllib.parse import urlencode, urlparse, parse_qs
import webbrowser
import http.server
import socketserver
import threading

# Import de la configuration
try:
    from config import (
        SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE,
        DEEZER_APP_ID, DEEZER_APP_SECRET, DEEZER_BASE_URL, DEEZER_AUTH_URL, DEEZER_TOKEN_URL
    )
except ImportError:
    print("❌ Fichier config.py introuvable!")
    print("💡 Créez un fichier config.py avec vos identifiants d'application")
    exit(1)

class DeezerOAuth:
    def __init__(self, app_id: str, app_secret: str, redirect_uri: str = "http://localhost:8080/deezer_callback"):
        """
        Initialise la classe OAuth Deezer
        
        Args:
            app_id: ID de votre application Deezer
            app_secret: Secret de votre application Deezer
            redirect_uri: URI de redirection (doit être configurée dans votre app Deezer)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        self.access_token: Optional[str] = None
        self.authorization_code: Optional[str] = None
        
    def get_auth_url(self, perms: str = "basic_access,email,offline_access,manage_library") -> str:
        """
        Génère l'URL d'authentification Deezer
        
        Args:
            perms: Permissions demandées (séparées par des virgules)
                   Options: basic_access, email, offline_access, manage_library, 
                           manage_community, delete_library, listening_history
        
        Returns:
            URL d'authentification Deezer
        """
        params = {
            'app_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'perms': perms,
            'response_type': 'code'  # Important pour le server-side flow
        }
        return f"{DEEZER_AUTH_URL}?{urlencode(params)}"
    
    def start_auth_flow(self, perms: str = "basic_access,email,offline_access,manage_library") -> bool:
        """
        Démarre le processus d'authentification complet
        
        Args:
            perms: Permissions demandées
            
        Returns:
            True si l'authentification réussit, False sinon
        """
        # Démarre le serveur local pour écouter le callback
        callback_received = threading.Event()
        
        class CallbackHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path.startswith('/deezer_callback'):
                    # Parse l'URL pour extraire le code d'autorisation
                    parsed_url = urlparse(self.path)
                    query_params = parse_qs(parsed_url.query)
                    
                    if 'code' in query_params:
                        outer_self.authorization_code = query_params['code'][0]
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'''
                        <html>
                            <body>
                                <h2>Authentification reussie!</h2>
                                <p>Vous pouvez fermer cette fenetre.</p>
                                <script>window.close();</script>
                            </body>
                        </html>
                        ''')
                    else:
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        error = query_params.get('error_reason', ['Unknown error'])[0]
                        self.wfile.write(f'<h2>Erreur: {error}</h2>'.encode())
                    
                    callback_received.set()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Supprime les logs du serveur
        
        outer_self = self
        
        # Démarre le serveur local
        try:
            with socketserver.TCPServer(("", 8080), CallbackHandler) as httpd:
                server_thread = threading.Thread(target=httpd.serve_forever)
                server_thread.daemon = True
                server_thread.start()
                
                # Ouvre l'URL d'authentification dans le navigateur
                auth_url = self.get_auth_url(perms)
                print(f"🌐 Ouverture du navigateur pour l'authentification...")
                print(f"URL: {auth_url}")
                webbrowser.open(auth_url)
                
                # Attend le callback (timeout de 5 minutes)
                if callback_received.wait(timeout=300):
                    httpd.shutdown()
                    
                    if self.authorization_code:
                        # Échange le code contre un access token
                        return self.exchange_code_for_token()
                    else:
                        print("❌ Aucun code d'autorisation reçu")
                        return False
                else:
                    httpd.shutdown()
                    print("❌ Timeout - Authentification non terminée")
                    return False
                    
        except OSError as e:
            print(f"❌ Erreur serveur local: {e}")
            print("💡 Assurez-vous que le port 8080 est libre")
            return False
    
    def exchange_code_for_token(self) -> bool:
        """
        Échange le code d'autorisation contre un access token
        
        Returns:
            True si l'échange réussit, False sinon
        """
        if not self.authorization_code:
            print("❌ Aucun code d'autorisation disponible")
            return False
        
        params = {
            'app_id': self.app_id,
            'secret': self.app_secret,
            'code': self.authorization_code
        }
        
        try:
            response = requests.get(DEEZER_TOKEN_URL, params=params)
            
            if response.status_code == 200:
                # La réponse contient access_token=TOKEN&expires=TIME
                response_data = parse_qs(response.text)
                
                if 'access_token' in response_data:
                    self.access_token = response_data['access_token'][0]
                    expires_in = response_data.get('expires', ['3600'])[0]
                    print(f"✅ Access token obtenu! (expire dans {expires_in}s)")
                    
                    # Test de la connexion
                    return self.test_connection()
                else:
                    print(f"❌ Erreur dans la réponse: {response.text}")
                    return False
            else:
                print(f"❌ Erreur HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors de l'échange du token: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test la validité de l'access token
        
        Returns:
            True si le token est valide, False sinon
        """
        if not self.access_token:
            print("❌ Aucun access token disponible")
            return False
        
        try:
            response = requests.get(
                f"{DEEZER_BASE_URL}/user/me",
                params={'access_token': self.access_token}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Connexion Deezer réussie! Bonjour {user_data.get('name', 'Utilisateur')}")
                print(f"📧 Email: {user_data.get('email', 'Non disponible')}")
                print(f"🌍 Pays: {user_data.get('country', 'Non disponible')}")
                return True
            else:
                print(f"❌ Token invalide: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur test connexion: {e}")
            return False

class PlaylistConverter:
    def __init__(self):
        self.spotify = None
        self.deezer_access_token = None
        self.deezer_oauth = None
        self.setup_spotify()
    
    def setup_spotify(self):
        """Configure l'authentification Spotify"""
        try:
            auth_manager = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope=SPOTIFY_SCOPE,
                cache_path=".spotify_cache"
            )
            self.spotify = spotipy.Spotify(auth_manager=auth_manager)
            print("✅ Connexion Spotify réussie!")
        except Exception as e:
            print(f"❌ Erreur connexion Spotify: {e}")
    
    def setup_deezer(self, access_token: str):
        """Configure l'authentification Deezer"""
        self.deezer_access_token = access_token
        # Test de la connexion
        try:
            response = requests.get(f"{DEEZER_BASE_URL}/user/me?access_token={access_token}")
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Connexion Deezer réussie! Bonjour {user_data.get('name', 'Utilisateur')}")
                return True
            else:
                print("❌ Token Deezer invalide")
                return False
        except Exception as e:
            print(f"❌ Erreur connexion Deezer: {e}")
            return False
    
    def setup_deezer_oauth(self):
        """Configure l'authentification Deezer OAuth automatique"""
        if DEEZER_APP_ID == "YOUR_DEEZER_APP_ID" or DEEZER_APP_SECRET == "YOUR_DEEZER_APP_SECRET":
            print("❌ Veuillez configurer DEEZER_APP_ID et DEEZER_APP_SECRET dans le code")
            print("💡 Créez une app sur https://developers.deezer.com/")
            return False
        
        self.deezer_oauth = DeezerOAuth(DEEZER_APP_ID, DEEZER_APP_SECRET)
        
        print("🔄 Démarrage de l'authentification Deezer...")
        success = self.deezer_oauth.start_auth_flow()
        
        if success and self.deezer_oauth.access_token:
            self.deezer_access_token = self.deezer_oauth.access_token
            return True
        else:
            print("❌ Échec de l'authentification Deezer")
            return False
    
    def get_deezer_auth_url(self) -> str:
        """Génère l'URL d'authentification Deezer (méthode manuelle)"""
        params = {
            'app_id': DEEZER_APP_ID,
            'redirect_uri': 'http://localhost:8080/deezer_callback',
            'perms': 'basic_access,email,offline_access,manage_library,manage_community,delete_library'
        }
        return f"https://connect.deezer.com/oauth/auth.php?{urlencode(params)}"
    
    def parse_spotify_playlist_url(self, url: str) -> Optional[str]:
        """Extrait l'ID de playlist depuis une URL Spotify"""
        try:
            # Formats supportés:
            # https://open.spotify.com/playlist/37i9dAZF1DXcBZIGnYBM5M
            # spotify:playlist:37i9dAZF1DXcBZIGnYBM5M
            
            if url.startswith('spotify:playlist:'):
                return url.split(':')[-1]
            
            parsed = urlparse(url)
            if 'spotify.com' in parsed.netloc and '/playlist/' in parsed.path:
                playlist_id = parsed.path.split('/playlist/')[-1].split('?')[0]
                return playlist_id
            
            return None
        except Exception as e:
            print(f"❌ Erreur analyse URL Spotify: {e}")
            return None
    
    def parse_deezer_playlist_url(self, url: str) -> Optional[str]:
        """Extrait l'ID de playlist depuis une URL Deezer"""
        try:
            # Formats supportés:
            # https://www.deezer.com/playlist/1234567890
            # https://deezer.com/fr/playlist/1234567890
            # https://link.deezer.com/s/shortcode (liens courts)
            
            parsed = urlparse(url)
            
            # Gestion des liens courts Deezer
            if 'link.deezer.com' in parsed.netloc:
                # Suit la redirection pour obtenir l'URL complète
                try:
                    response = requests.head(url, allow_redirects=True)
                    if response.status_code == 200:
                        final_url = response.url
                        return self.parse_deezer_playlist_url(final_url)
                except:
                    pass
            
            # Gestion des URLs standards
            if 'deezer.com' in parsed.netloc and '/playlist/' in parsed.path:
                playlist_id = parsed.path.split('/playlist/')[-1].split('?')[0]
                return playlist_id
            
            return None
        except Exception as e:
            print(f"❌ Erreur analyse URL Deezer: {e}")
            return None
    
    def get_deezer_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Récupère les morceaux d'une playlist Deezer publique avec pagination"""
        try:
            tracks = []
            url = f"{DEEZER_BASE_URL}/playlist/{playlist_id}/tracks"
            
            while url:
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for track in data.get('data', []):
                        tracks.append({
                            'title': track['title'],
                            'artist': track['artist']['name'],
                            'album': track['album']['title'],
                            'duration': track['duration'],
                            'deezer_id': track['id']
                        })
                    
                    # Pagination - continue avec l'URL suivante
                    url = data.get('next')
                    if url:
                        print(f"📋 Récupération de {len(tracks)} morceaux...")
                
                elif response.status_code == 403:
                    print("❌ Playlist Deezer privée ou accès refusé")
                    return []
                elif response.status_code == 404:
                    print("❌ Playlist Deezer introuvable")
                    return []
                else:
                    print(f"❌ Erreur accès playlist Deezer: {response.status_code}")
                    break
            
            return tracks
        except Exception as e:
            print(f"❌ Erreur récupération morceaux Deezer: {e}")
            return []
    
    def get_spotify_playlists(self) -> List[Dict]:
        """Récupère toutes les playlists Spotify de l'utilisateur"""
        if not self.spotify:
            return []
        
        try:
            playlists = []
            results = self.spotify.current_user_playlists(limit=50)
            
            while results:
                for playlist in results['items']:
                    if playlist['owner']['id'] == self.spotify.current_user()['id']:
                        playlists.append({
                            'id': playlist['id'],
                            'name': playlist['name'],
                            'description': playlist['description'],
                            'tracks_total': playlist['tracks']['total']
                        })
                
                if results['next']:
                    results = self.spotify.next(results)
                else:
                    break
            
            return playlists
        except Exception as e:
            print(f"❌ Erreur récupération playlists Spotify: {e}")
            return []
    
    def get_spotify_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Récupère les morceaux d'une playlist Spotify"""
        if not self.spotify:
            return []
        
        try:
            tracks = []
            results = self.spotify.playlist_tracks(playlist_id)
            
            while results:
                for item in results['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        artists = [artist['name'] for artist in track['artists']]
                        tracks.append({
                            'title': track['name'],
                            'artist': artists[0] if artists else '',
                            'artists': artists,
                            'album': track['album']['name'],
                            'duration': track['duration_ms'] // 1000,
                            'spotify_id': track['id']
                        })
                
                if results['next']:
                    results = self.spotify.next(results)
                else:
                    break
            
            return tracks
        except Exception as e:
            print(f"❌ Erreur récupération morceaux Spotify: {e}")
            return []
    
    def search_deezer_track(self, title: str, artist: str) -> Optional[Dict]:
        """Recherche un morceau sur Deezer"""
        try:
            # Nettoie les titres pour une meilleure recherche
            clean_title = re.sub(r'[^\w\s]', '', title)
            clean_artist = re.sub(r'[^\w\s]', '', artist)
            
            query = f"{clean_artist} {clean_title}".strip()
            
            response = requests.get(
                f"{DEEZER_BASE_URL}/search",
                params={'q': query, 'limit': 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('data'):
                    # Trouve la meilleure correspondance
                    for track in data['data']:
                        track_title = track['title'].lower()
                        track_artist = track['artist']['name'].lower()
                        
                        if (clean_title.lower() in track_title or track_title in clean_title.lower()) and \
                           (clean_artist.lower() in track_artist or track_artist in clean_artist.lower()):
                            return {
                                'id': track['id'],
                                'title': track['title'],
                                'artist': track['artist']['name'],
                                'album': track['album']['title'],
                                'duration': track['duration']
                            }
                    
                    # Si pas de correspondance exacte, prend le premier résultat
                    track = data['data'][0]
                    return {
                        'id': track['id'],
                        'title': track['title'],
                        'artist': track['artist']['name'],
                        'album': track['album']['title'],
                        'duration': track['duration']
                    }
            
            return None
        except Exception as e:
            print(f"❌ Erreur recherche Deezer pour '{title}' - '{artist}': {e}")
            return None
    
    def create_deezer_playlist(self, name: str, track_ids: List[int]) -> bool:
        """Crée une playlist sur Deezer"""
        if not self.deezer_access_token:
            print("❌ Token Deezer requis pour créer une playlist")
            return False
        
        try:
            # Crée la playlist
            response = requests.post(
                f"{DEEZER_BASE_URL}/user/me/playlists",
                data={
                    'title': name,
                    'access_token': self.deezer_access_token
                }
            )
            
            if response.status_code == 200:
                playlist_data = response.json()
                playlist_id = playlist_data.get('id')
                
                if playlist_id and track_ids:
                    # Ajoute les morceaux à la playlist
                    tracks_str = ','.join(map(str, track_ids))
                    add_response = requests.post(
                        f"{DEEZER_BASE_URL}/playlist/{playlist_id}/tracks",
                        data={
                            'songs': tracks_str,
                            'access_token': self.deezer_access_token
                        }
                    )
                    
                    if add_response.status_code == 200:
                        print(f"✅ Playlist '{name}' créée sur Deezer avec {len(track_ids)} morceaux")
                        return True
                    else:
                        print(f"❌ Erreur ajout morceaux à la playlist Deezer")
                        return False
                else:
                    print(f"✅ Playlist '{name}' créée sur Deezer (vide)")
                    return True
            else:
                print(f"❌ Erreur création playlist Deezer: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Erreur création playlist Deezer: {e}")
            return False
    
    def search_spotify_track(self, title: str, artist: str) -> Optional[Dict]:
        """Recherche un morceau sur Spotify"""
        if not self.spotify:
            return None
        
        try:
            clean_title = re.sub(r'[^\w\s]', '', title)
            clean_artist = re.sub(r'[^\w\s]', '', artist)
            
            query = f"track:{clean_title} artist:{clean_artist}"
            
            results = self.spotify.search(q=query, type='track', limit=5)
            
            if results['tracks']['items']:
                for track in results['tracks']['items']:
                    track_title = track['name'].lower()
                    track_artists = [a['name'].lower() for a in track['artists']]
                    
                    if (clean_title.lower() in track_title or track_title in clean_title.lower()) and \
                       any(clean_artist.lower() in ta or ta in clean_artist.lower() for ta in track_artists):
                        return {
                            'id': track['id'],
                            'title': track['name'],
                            'artists': [a['name'] for a in track['artists']],
                            'album': track['album']['name'],
                            'duration': track['duration_ms'] // 1000
                        }
                
                # Si pas de correspondance exacte, prend le premier résultat
                track = results['tracks']['items'][0]
                return {
                    'id': track['id'],
                    'title': track['name'],
                    'artists': [a['name'] for a in track['artists']],
                    'album': track['album']['name'],
                    'duration': track['duration_ms'] // 1000
                }
            
            return None
        except Exception as e:
            print(f"❌ Erreur recherche Spotify pour '{title}' - '{artist}': {e}")
            return None
    
    def create_spotify_playlist(self, name: str, track_ids: List[str]) -> bool:
        """Crée une playlist sur Spotify"""
        if not self.spotify:
            return False
        
        try:
            user_id = self.spotify.current_user()['id']
            playlist = self.spotify.user_playlist_create(
                user=user_id,
                name=name,
                public=False
            )
            
            if track_ids:
                # Spotify limite à 100 morceaux par requête
                for i in range(0, len(track_ids), 100):
                    batch = track_ids[i:i+100]
                    self.spotify.playlist_add_items(playlist['id'], batch)
            
            print(f"✅ Playlist '{name}' créée sur Spotify avec {len(track_ids)} morceaux")
            return True
        except Exception as e:
            print(f"❌ Erreur création playlist Spotify: {e}")
            return False
    
    def convert_spotify_to_deezer(self, spotify_playlist_id: str, new_playlist_name: str = None):
        """Convertit une playlist Spotify vers Deezer"""
        print("🔄 Conversion Spotify → Deezer en cours...")
        
        # Récupère les morceaux Spotify
        tracks = self.get_spotify_playlist_tracks(spotify_playlist_id)
        if not tracks:
            print("❌ Aucun morceau trouvé dans la playlist Spotify")
            return
        
        print(f"📋 {len(tracks)} morceaux à convertir")
        
        # Recherche les morceaux sur Deezer
        found_tracks = []
        not_found = []
        
        for i, track in enumerate(tracks, 1):
            print(f"🔍 ({i}/{len(tracks)}) Recherche: {track['artist']} - {track['title']}")
            
            deezer_track = self.search_deezer_track(track['title'], track['artist'])
            if deezer_track:
                found_tracks.append(deezer_track['id'])
                print(f"  ✅ Trouvé: {deezer_track['artist']} - {deezer_track['title']}")
            else:
                not_found.append(f"{track['artist']} - {track['title']}")
                print(f"  ❌ Non trouvé")
            
            time.sleep(0.1)  # Évite le rate limiting
        
        # Crée la playlist Deezer
        if not new_playlist_name:
            new_playlist_name = f"From Spotify - {int(time.time())}"
        
        if found_tracks:
            success = self.create_deezer_playlist(new_playlist_name, found_tracks)
            if success:
                print(f"\n🎉 Conversion terminée!")
                print(f"✅ {len(found_tracks)} morceaux ajoutés à Deezer")
                if not_found:
                    print(f"❌ {len(not_found)} morceaux non trouvés:")
                    for track in not_found[:10]:  # Limite l'affichage
                        print(f"  - {track}")
                    if len(not_found) > 10:
                        print(f"  ... et {len(not_found) - 10} autres")
        else:
            print("❌ Aucun morceau trouvé sur Deezer")
    
    def convert_deezer_to_spotify(self, deezer_playlist_id: str, new_playlist_name: str = None):
        """Convertit une playlist Deezer vers Spotify"""
        print("🔄 Conversion Deezer → Spotify en cours...")
        
        # Récupère les morceaux Deezer
        tracks = self.get_deezer_playlist_tracks(deezer_playlist_id)
        if not tracks:
            print("❌ Aucun morceau trouvé dans la playlist Deezer")
            return
        
        print(f"📋 {len(tracks)} morceaux à convertir")
        
        # Recherche les morceaux sur Spotify
        found_tracks = []
        not_found = []
        
        for i, track in enumerate(tracks, 1):
            print(f"🔍 ({i}/{len(tracks)}) Recherche: {track['artist']} - {track['title']}")
            
            spotify_track = self.search_spotify_track(track['title'], track['artist'])
            if spotify_track:
                found_tracks.append(spotify_track['id'])
                print(f"  ✅ Trouvé: {spotify_track['artists'][0]} - {spotify_track['title']}")
            else:
                not_found.append(f"{track['artist']} - {track['title']}")
                print(f"  ❌ Non trouvé")
            
            time.sleep(0.1)  # Évite le rate limiting
        
        # Crée la playlist Spotify
        if not new_playlist_name:
            new_playlist_name = f"From Deezer - {int(time.time())}"
        
        if found_tracks:
            success = self.create_spotify_playlist(new_playlist_name, found_tracks)
            if success:
                print(f"\n🎉 Conversion terminée!")
                print(f"✅ {len(found_tracks)} morceaux ajoutés à Spotify")
                if not_found:
                    print(f"❌ {len(not_found)} morceaux non trouvés:")
                    for track in not_found[:10]:  # Limite l'affichage
                        print(f"  - {track}")
                    if len(not_found) > 10:
                        print(f"  ... et {len(not_found) - 10} autres")
        else:
            print("❌ Aucun morceau trouvé sur Spotify")
    
    def convert_playlist_by_url(self, url: str, new_playlist_name: str = None):
        """Convertit une playlist en utilisant son URL"""
        # Détecte le type de plateforme
        if 'spotify.com' in url or url.startswith('spotify:'):
            # Conversion Spotify vers Deezer
            playlist_id = self.parse_spotify_playlist_url(url)
            if playlist_id:
                print(f"🎵 Playlist Spotify détectée (ID: {playlist_id})")
                self.convert_spotify_to_deezer(playlist_id, new_playlist_name)
            else:
                print("❌ URL Spotify invalide")
        
        elif 'deezer.com' in url:
            # Conversion Deezer vers Spotify
            playlist_id = self.parse_deezer_playlist_url(url)
            if playlist_id:
                print(f"🎵 Playlist Deezer détectée (ID: {playlist_id})")
                self.convert_deezer_to_spotify(playlist_id, new_playlist_name)
            else:
                print("❌ URL Deezer invalide")
        
        else:
            print("❌ URL non supportée. Utilisez une URL Spotify ou Deezer.")

def main():
    print("🎵 Convertisseur de Playlists Spotify ↔ Deezer")
    print("=" * 50)
    
    converter = PlaylistConverter()
    
    while True:
        print("\n📋 Options disponibles:")
        print("1. Voir mes playlists Spotify")
        print("2. Convertir playlist Spotify → Deezer")
        print("3. Convertir playlist par lien URL")
        print("4. Configurer Deezer (token manuel)")
        print("5. Authentification Deezer automatique")
        print("6. Obtenir URL d'authentification Deezer")
        print("7. Quitter")
        
        choice = input("\n🎯 Votre choix (1-7): ").strip()
        
        if choice == "1":
            print("\n🎵 Vos playlists Spotify:")
            playlists = converter.get_spotify_playlists()
            if playlists:
                for i, playlist in enumerate(playlists, 1):
                    print(f"{i:2d}. {playlist['name']} ({playlist['tracks_total']} morceaux)")
            else:
                print("❌ Aucune playlist trouvée")
        
        elif choice == "2":
            playlists = converter.get_spotify_playlists()
            if not playlists:
                print("❌ Aucune playlist Spotify disponible")
                continue
            
            print("\n🎵 Choisissez une playlist à convertir:")
            for i, playlist in enumerate(playlists, 1):
                print(f"{i:2d}. {playlist['name']} ({playlist['tracks_total']} morceaux)")
            
            try:
                idx = int(input("\n🎯 Numéro de la playlist: ")) - 1
                if 0 <= idx < len(playlists):
                    selected = playlists[idx]
                    new_name = input(f"📝 Nouveau nom (ou Entrée pour '{selected['name']}'): ").strip()
                    if not new_name:
                        new_name = selected['name']
                    
                    converter.convert_spotify_to_deezer(selected['id'], new_name)
                else:
                    print("❌ Numéro invalide")
            except ValueError:
                print("❌ Veuillez entrer un numéro valide")
        
        elif choice == "3":
            url = input("🔗 Entrez l'URL de la playlist à convertir: ").strip()
            if url:
                new_name = input("📝 Nouveau nom de playlist (ou Entrée pour nom automatique): ").strip()
                if not new_name:
                    new_name = None
                
                converter.convert_playlist_by_url(url, new_name)
            else:
                print("❌ URL requise")
        
        elif choice == "4":
            token = input("🔑 Entrez votre token d'accès Deezer: ").strip()
            if token:
                converter.setup_deezer(token)
            else:
                print("❌ Token requis")
        
        elif choice == "5":
            print("\n🔄 Authentification Deezer automatique...")
            converter.setup_deezer_oauth()
        
        elif choice == "6":
            print("\n🔗 URL d'authentification Deezer:")
            print("⚠️  Vous devez d'abord créer une app sur https://developers.deezer.com/")
            print(converter.get_deezer_auth_url())
            print("\n💡 Suivez le lien, autorisez l'app et copiez le token depuis l'URL de retour")
        
        elif choice == "7":
            print("👋 Au revoir!")
            break
        
        else:
            print("❌ Choix invalide")

if __name__ == "__main__":
    main()