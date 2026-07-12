"""Récitateurs, sourates et constantes partagées."""

# source:
#   everyayah = MP3 verset par verset (everyayah.com)
#   surah     = MP3 sourate complete, decoupee proportionnellement
RECITEURS = {
    1: {"nom": "Abderrahman Al Soudais", "dossier": "Abdurrahmaan_As-Sudais_192kbps", "source": "everyayah"},
    2: {"nom": "Saad El Ghamidi", "dossier": "Ghamadi_40kbps", "source": "everyayah"},
    3: {"nom": "Mishary Rashid Alafasy", "dossier": "Alafasy_128kbps", "source": "everyayah"},
    4: {"nom": "Maher Al Mueaqly", "dossier": "MaherAlMuaiqly128kbps", "source": "everyayah"},
    5: {"nom": "Abdelbasset Abdessamad", "dossier": "Abdul_Basit_Murattal_192kbps", "source": "everyayah"},
    6: {"nom": "Ahmed Al Ajmi", "dossier": "ahmed_ibn_ali_al_ajamy_128kbps", "source": "everyayah"},
    7: {"nom": "Saoud Shuraim", "dossier": "Saood_ash-Shuraym_128kbps", "source": "everyayah"},
    8: {"nom": "Fares Abbad", "dossier": "Fares_Abbad_64kbps", "source": "everyayah"},
    9: {"nom": "Mahmoud Khalil Al Hussary", "dossier": "Husary_128kbps", "source": "everyayah"},
    10: {"nom": "Mohamed Seddik El Menchaoui", "dossier": "Minshawy_Murattal_128kbps", "source": "everyayah"},
    11: {"nom": "Abdallah Matroud", "dossier": "Abdullah_Matroud_128kbps", "source": "everyayah"},
    12: {"nom": "Abu Bakr Al Shatri", "dossier": "Abu_Bakr_Ash-Shaatree_128kbps", "source": "everyayah"},
    13: {
        "nom": "Omar Hisham Al Arabi",
        "dossier": "Omar_Hisham_Al_Arabi",
        "source": "surah",
        "surah_url": "https://archive.org/download/OmarHishamAl-Arabi/{surah:03d}.mp3",
        # Sourates disponibles sur Archive.org (pas le Coran complet)
        "surahs": [
            1, 12, 14, 16, 17, 18, 19, 20, 22, 25, 32, 36, 40, 44, 49, 50, 51, 52,
            53, 54, 55, 56, 58, 59, 61, 62, 66, 67, 68, 69, 70, 71, 72, 73, 75, 76,
            77, 78, 79, 80, 81, 82, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96,
            97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 109, 110, 111, 112,
            113, 114,
        ],
    },
    14: {
        "nom": "Noreen Mohammad Siddiq",
        "dossier": "Noreen_Mohammad_Siddiq",
        "source": "surah",
        "surah_url": "https://server16.mp3quran.net/nourin_siddig/Rewayat-Aldori-A-n-Abi-Amr/{surah:03d}.mp3",
    },
    15: {"nom": "Yasser Al Dossari", "dossier": "Yasser_Ad-Dussary_128kbps", "source": "everyayah"},
    16: {"nom": "Hani Ar-Rifai", "dossier": "Hani_Rifai_192kbps", "source": "everyayah"},
    17: {"nom": "Ali Al Hudhaify", "dossier": "Hudhaify_128kbps", "source": "everyayah"},
    18: {"nom": "Muhammad Ayyoub", "dossier": "Muhammad_Ayyoub_128kbps", "source": "everyayah"},
    19: {"nom": "Muhammad Jibreel", "dossier": "Muhammad_Jibreel_128kbps", "source": "everyayah"},
    20: {"nom": "Nasser Al Qatami", "dossier": "Nasser_Alqatami_128kbps", "source": "everyayah"},
    21: {"nom": "Abdullah Basfar", "dossier": "Abdullah_Basfar_192kbps", "source": "everyayah"},
    22: {"nom": "Salah Al Budair", "dossier": "Salah_Al_Budair_128kbps", "source": "everyayah"},
    23: {"nom": "Khalid Al Qahtani", "dossier": "Khaalid_Abdullaah_al-Qahtaanee_192kbps", "source": "everyayah"},
    24: {"nom": "Mahmoud Ali Al Banna", "dossier": "mahmoud_ali_al_banna_32kbps", "source": "everyayah"},
}

NB_VERSETS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99,
    128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38,
    29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18,
    12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29,
    19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8,
    11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
]

# Noms FR + arabe (standard)
SOURATES = [
    ("Al-Fatiha", "الفاتحة"),
    ("Al-Baqara", "البقرة"),
    ("Al-Imran", "آل عمران"),
    ("An-Nisa", "النساء"),
    ("Al-Maida", "المائدة"),
    ("Al-Anam", "الأنعام"),
    ("Al-Araf", "الأعراف"),
    ("Al-Anfal", "الأنفال"),
    ("At-Tawba", "التوبة"),
    ("Yunus", "يونس"),
    ("Hud", "هود"),
    ("Yusuf", "يوسف"),
    ("Ar-Rad", "الرعد"),
    ("Ibrahim", "إبراهيم"),
    ("Al-Hijr", "الحجر"),
    ("An-Nahl", "النحل"),
    ("Al-Isra", "الإسراء"),
    ("Al-Kahf", "الكهف"),
    ("Maryam", "مريم"),
    ("Ta-Ha", "طه"),
    ("Al-Anbiya", "الأنبياء"),
    ("Al-Hajj", "الحج"),
    ("Al-Muminun", "المؤمنون"),
    ("An-Nur", "النور"),
    ("Al-Furqan", "الفرقان"),
    ("Ash-Shuara", "الشعراء"),
    ("An-Naml", "النمل"),
    ("Al-Qasas", "القصص"),
    ("Al-Ankabut", "العنكبوت"),
    ("Ar-Rum", "الروم"),
    ("Luqman", "لقمان"),
    ("As-Sajda", "السجدة"),
    ("Al-Ahzab", "الأحزاب"),
    ("Saba", "سبأ"),
    ("Fatir", "فاطر"),
    ("Ya-Sin", "يس"),
    ("As-Saffat", "الصافات"),
    ("Sad", "ص"),
    ("Az-Zumar", "الزمر"),
    ("Ghafir", "غافر"),
    ("Fussilat", "فصلت"),
    ("Ash-Shura", "الشورى"),
    ("Az-Zukhruf", "الزخرف"),
    ("Ad-Dukhan", "الدخان"),
    ("Al-Jathiya", "الجاثية"),
    ("Al-Ahqaf", "الأحقاف"),
    ("Muhammad", "محمد"),
    ("Al-Fath", "الفتح"),
    ("Al-Hujurat", "الحجرات"),
    ("Qaf", "ق"),
    ("Adh-Dhariyat", "الذاريات"),
    ("At-Tur", "الطور"),
    ("An-Najm", "النجم"),
    ("Al-Qamar", "القمر"),
    ("Ar-Rahman", "الرحمن"),
    ("Al-Waqia", "الواقعة"),
    ("Al-Hadid", "الحديد"),
    ("Al-Mujadila", "المجادلة"),
    ("Al-Hashr", "الحشر"),
    ("Al-Mumtahina", "الممتحنة"),
    ("As-Saff", "الصف"),
    ("Al-Jumua", "الجمعة"),
    ("Al-Munafiqun", "المنافقون"),
    ("At-Taghabun", "التغابن"),
    ("At-Talaq", "الطلاق"),
    ("At-Tahrim", "التحريم"),
    ("Al-Mulk", "الملك"),
    ("Al-Qalam", "القلم"),
    ("Al-Haqqa", "الحاقة"),
    ("Al-Maarij", "المعارج"),
    ("Nuh", "نوح"),
    ("Al-Jinn", "الجن"),
    ("Al-Muzzammil", "المزمل"),
    ("Al-Muddaththir", "المدثر"),
    ("Al-Qiyama", "القيامة"),
    ("Al-Insan", "الإنسان"),
    ("Al-Mursalat", "المرسلات"),
    ("An-Naba", "النبأ"),
    ("An-Naziat", "النازعات"),
    ("Abasa", "عبس"),
    ("At-Takwir", "التكوير"),
    ("Al-Infitar", "الانفطار"),
    ("Al-Mutaffifin", "المطففين"),
    ("Al-Inshiqaq", "الانشقاق"),
    ("Al-Buruj", "البروج"),
    ("At-Tariq", "الطارق"),
    ("Al-Ala", "الأعلى"),
    ("Al-Ghashiya", "الغاشية"),
    ("Al-Fajr", "الفجر"),
    ("Al-Balad", "البلد"),
    ("Ash-Shams", "الشمس"),
    ("Al-Layl", "الليل"),
    ("Ad-Duha", "الضحى"),
    ("Ash-Sharh", "الشرح"),
    ("At-Tin", "التين"),
    ("Al-Alaq", "العلق"),
    ("Al-Qadr", "القدر"),
    ("Al-Bayyina", "البينة"),
    ("Az-Zalzala", "الزلزلة"),
    ("Al-Adiyat", "العاديات"),
    ("Al-Qaria", "القارعة"),
    ("At-Takathur", "التكاثر"),
    ("Al-Asr", "العصر"),
    ("Al-Humaza", "الهمزة"),
    ("Al-Fil", "الفيل"),
    ("Quraysh", "قريش"),
    ("Al-Maun", "الماعون"),
    ("Al-Kawthar", "الكوثر"),
    ("Al-Kafirun", "الكافرون"),
    ("An-Nasr", "النصر"),
    ("Al-Masad", "المسد"),
    ("Al-Ikhlas", "الإخلاص"),
    ("Al-Falaq", "الفلق"),
    ("An-Nas", "الناس"),
]

BISMILLAH_ARABE = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
BISMILLAH_FR = "Au nom d'Allah, le Tout Misericordieux, le Tres Misericordieux."
BISMILLAH_EN = "In the name of Allah, the Entirely Merciful, the Especially Merciful."
EVERYAYAH_BASE = "https://everyayah.com/data"
API_TEXTE_ARABE = "https://api.alquran.cloud/v1/surah/{numero}/quran-uthmani"
API_TRADUCTION = "https://api.alquran.cloud/v1/surah/{numero}/{edition}"
TRADUCTIONS = {
    "none": None,
    "fr": "fr.hamidullah",
    "en": "en.sahih",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; QuranVideoStudio/1.0; usage personnel)"}

LARGEUR_SORTIE = 1080
HAUTEUR_SORTIE = 1920


def liste_reciteurs():
    out = []
    for rid, info in RECITEURS.items():
        item = {
            "id": rid,
            "nom": info["nom"],
            "dossier": info["dossier"],
            "source": info.get("source", "everyayah"),
        }
        if info.get("surahs"):
            item["surahs"] = list(info["surahs"])
        out.append(item)
    return out


def liste_sourates():
    return [
        {
            "number": i + 1,
            "name_fr": SOURATES[i][0],
            "name_ar": SOURATES[i][1],
            "verses": NB_VERSETS[i],
        }
        for i in range(114)
    ]
