# Nur — Studio Vidéo Coranique

Interface web pour générer des vidéos verticales (1080×1920) à partir d’une récitation coranique, avec sous-titres arabes synchronisés.

## Prérequis

1. **Python 3.10+**
2. **Node.js 18+**
3. **ffmpeg** dans le PATH (`ffmpeg -version` et `ffprobe -version` doivent marcher)
   - Windows : https://www.gyan.dev/ffmpeg/builds/ (essentials) → ajouter `bin/` au PATH

## Installation (une seule fois)

```powershell
cd F:\others\Tiktok
python -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
```

## Lancer l’app

**Windows (le plus simple)** — double-clic ou :

```powershell
cd F:\others\Tiktok
.\start.bat
```

Ou PowerShell : `.\start.ps1`  
Ou Git Bash : `bash start.sh`

Puis ouvre **http://localhost:5173**

### Recherche Pexels (optionnel)

1. Clé gratuite : https://www.pexels.com/api/
2. Avant de lancer :
   ```powershell
   $env:PEXELS_API_KEY = "ta_cle"
   .\start.ps1
   ```

## Tester rapidement

1. Ouvre l’UI Nur
2. Contenu : Alafasy (ou autre) → **Al-Ikhlas (112)** → versets **1–4** (court)
3. Sous-titres : choisis **Or** ou **Classique**
4. Vidéo : **Épuré** (fond uni auto si tu n’uploades rien)
5. Générer → attends la barre de progression → **Télécharger**

Les MP3 sont mis en cache dans `cache/audio/` (pas re-téléchargés ensuite).  
Les MP4 finaux sont dans `outputs/`.

### Fond personnalisé (optionnel)

- Upload depuis l’UI, **ou**
- Place un `.mp4` dans `assets/fonds/` puis recharge la page

## Structure

```
backend/app/     API FastAPI + pipeline ffmpeg
frontend/        UI Vite + React
cache/audio/     Cache MP3 EveryAyah
outputs/         Vidéos générées
assets/fonds/    Fonds vidéo optionnels
```
