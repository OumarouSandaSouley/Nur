# Nur — Studio Vidéo Coranique

<p align="center">
  <img src="frontend/public/nur-logo.png" alt="Nur" width="72" />
</p>

**Nur** (*Noor* — « Lumière » en arabe نور) est un studio vidéo local qui transforme une récitation du Coran en vidéo verticale prête pour TikTok, Reels ou Shorts. Tu choisis un récitateur, une sourate et des versets : Nur télécharge l'audio, synchronise les sous-titres arabes (avec traduction française ou anglaise si tu veux), compose le fond vidéo, grave le logo Nur, et exporte un MP4 en 1080×1920.

Le tout se pilote depuis un vrai studio : tableau de bord, historique, bibliothèque de fonds (Pexels, upload), cache audio classé, puis trim et montage une fois la vidéo générée. Aucun compte distant — tout tourne sur ta machine.

![Nur — page Créer avec aperçu téléphone](docs/studio-creer.jpg)
## 📑 Table des matières

- [En bref](#en-bref)
- [Aperçu de l'interface](#aperçu-de-linterface)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Lancer l'app](#lancer-lapp)
- [Configuration (API Pexels)](#clé-pexels-optionnel)
- [Structure du projet](#structure-du-projet)


## En bref

- **Récitation** — récitateur, sourate, intervalle de versets, aperçu audio
- **Sous-titres** — arabe seul ou bilingue (FR / EN), styles, animations, versets longs
- **Vidéo** — fonds Pexels / upload / bibliothèque, styles de rendu, watermark Nur obligatoire
- **Studio** — dashboard, historique, crédits en bas, trim & assemblage, sons en cache



## Aperçu de l’interface

### Tableau de bord

Vue d’ensemble : vidéos récentes, fonds, file d’attente, accès rapide au studio.

![Nur — tableau de bord](docs/tableau-de-bord.jpg)

### Fonds

Bibliothèque de fonds : recherche Pexels → **Ajouter**, puis **Utiliser** pour charger le fond dans une création.

![Nur — bibliothèque de fonds](docs/fonds.jpg)

### Sons

Audio déjà téléchargé, classé par récitateur puis sourate — prêt à réécouter sans re-télécharger.

![Nur — cache audio classé](docs/sons.jpg)



## Prérequis

- **Python 3.10+**  
  Télécharge : [python.org](https://www.python.org/downloads/)  
  Vérifie : `python --version`

- **Node.js 18+**  
  Télécharge : [nodejs.org](https://nodejs.org/)  
  Vérifie : `node --version` et `npm --version`

- **ffmpeg & ffprobe** (dans le `PATH`)  
  - **Windows** : [Builds Gyan](https://www.gyan.dev/ffmpeg/builds/) (essentials)  
    → Ajoute le dossier `bin/` au PATH système  
    Vérifie : `ffmpeg -version` et `ffprobe -version` dans un nouveau terminal

  - **macOS** :  
    ```bash
    brew install ffmpeg
    ```

  - **Linux (Ubuntu/Debian)** :  
    ```bash
    sudo apt-get install ffmpeg
    ```



## Installation

### 1️⃣ Cloner le repository

```bash
git clone https://github.com/OumarouSandaSouley/Nur.git
cd Nur
```

Ou télécharger directement : [Archive ZIP](https://github.com/OumarouSandaSouley/Nur/archive/refs/heads/main.zip)

### 2️⃣ Installer les dépendances

**Windows (PowerShell)** :

```powershell
python -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
```

**macOS / Linux (Bash)** :

```bash
python -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```



## Lancer l’app

**Windows** — double-clic sur `start.bat` :

```powershell
.\start.bat
```

**macOS / Linux** :

```bash
bash start.sh
```

| Script | Plateforme |
|--------|-----------|
| `start.bat` | Windows (cmd) |
| `start.ps1` | Windows (PowerShell) |
| `start.sh` | Git Bash / macOS / Linux |

✅ Puis ouvre **http://localhost:5173** dans ton navigateur  
🔗 API locale : `http://127.0.0.1:8000`

## Configuration (API Pexels)

Pour utiliser la recherche de fonds dans l'onglet **Fonds → Recherche Pexels** :

1. Crée une clé gratuite : [pexels.com/api](https://www.pexels.com/api/)
2. Avant de lancer l'app :

**Windows (PowerShell)** :
```powershell
$env:PEXELS_API_KEY = "ta_cle_ici"
.\start.ps1
```

**macOS / Linux** :
```bash
export PEXELS_API_KEY="ta_cle_ici"
bash start.sh
```

Ou crée un fichier `.env` à la racine du projet :
```
PEXELS_API_KEY=ta_cle_ici
```



## Premier essai (≈ 1 minute)

1. **Créer** → récitateur (ex. Alafasy) → sourate courte (**Al-Ikhlas 112**, versets 1–4)
2. **Sous-titres** → style Or ou Classique
3. **Vidéo** → style Épuré, ou **Utiliser** un fond depuis **Fonds**
4. **Générer** → attendre la progression → **Télécharger**

Astuce : les MP3 restent en cache (`cache/audio/`) et les vidéos sortent dans `outputs/`.



## Navigation du studio

| Page | Rôle |
|------|------|
| **Tableau de bord** | Stats, vidéos récentes, file d’attente |
| **Créer** | Wizard Contenu → Sous-titres → Vidéo → Générer |
| **Historique** | Prévisualiser, télécharger, trimmer, assembler |
| **Fonds** | Bibliothèque, Pexels, upload — **Utiliser** = fond de création |
| **Sons** | MP3 déjà téléchargés, classés par récitateur / sourate |

Le logo **Nur** est toujours gravé sur les vidéos (pas d’option pour le retirer).  
Option **crédits bas** : sourate + versets sur une ligne, récitateur en dessous.



## Structure du projet

```
Nur/
├── backend/app/     API FastAPI + pipeline ffmpeg
├── frontend/        UI Vite + React (dashboard)
├── assets/          Logo Nur, polices, fonds locaux
├── cache/audio/     Cache MP3 par récitateur
├── cache/fonds_url/ Fonds téléchargés (Pexels / URL)
├── outputs/         Vidéos générées (+ sidecars JSON / SRT)
├── docs/            Captures d’écran
└── start.bat        Lance API + frontend
```



## Dépannage rapide

| Problème | Piste |
|----------|--------|
| « API inaccessible » | Relance `start.bat` ; vérifie le port **8000** |
| ffmpeg introuvable | Réinstalle les essentials et rouvre un nouveau terminal |
| Recherche Pexels vide | Vérifie que `PEXELS_API_KEY` est défini dans l'environnement |
| Génération bloquée | Un seul worker mémoire : ne lance pas l'API avec `reload=True` |
| Port 5173 déjà utilisé | Change le port dans `frontend/vite.config.ts` |



## 🔗 Liens utiles

- 📺 Récitateurs : [EveryAyat](https://everyayat.com/) (source des récitations)
- 📖 Quran : [Quran.com](https://quran.com/)
- 🎨 Fonds : [Pexels](https://www.pexels.com/) (gratuit, licence libre)
- 🎬 Guide ffmpeg : [ffmpeg.org](https://ffmpeg.org/)
- ⚙️ API docs : [FastAPI](https://fastapi.tiangolo.com/)

## 📄 Licence

Nur — usage personnel · récitations publiques · fonds : licence Pexels

Crée par [Oumarou Sanda Souley](https://github.com/OumarouSandaSouley)



**Besoin d'aide ?** Ouvre une issue sur [GitHub](https://github.com/OumarouSandaSouley/Nur/issues)
