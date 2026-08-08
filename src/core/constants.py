# Constants configuration for DowP

VIDEO_EXTENSIONS = {'webm', 'flv', 'mkv', 'mov', 'mp4', 'avi', 'gif'}
AUDIO_EXTENSIONS = {'flac', 'mp3', 'ogg', 'wav', 'opus', 'm4a'}
SINGLE_STREAM_AUDIO_CONTAINERS = {'.wav', '.ac3', '.flac', '.mp3'}
FAST_MODE_SUPPORTED_DOMAINS = [
    'youtube.com', 'youtu.be', 'soundcloud.com', 'x.com', 'twitter.com', 
    'instagram.com', 'tiktok.com', 'reddit.com', 'facebook.com', 'tumblr.com', 
    'vimeo.com', 'dailymotion.com', 'bandcamp.com', 'twitch.tv', 'smugmug.com', 
    'flickr.com', 'metacafe.com', 'archive.org'
]
FORMAT_MUXER_MAP = {'.m4a': 'mp4', '.wma': 'asf'}

LANG_CODE_MAP = {
    "es": "Español",
    "es-419": "Español (Latinoamérica)",
    "es-es": "Español (España)",
    "es_la": "Español (Latinoamérica)", 
    "en": "Inglés",
    "en-us": "Inglés (EE.UU.)",
    "en-gb": "Inglés (Reino Unido)",
    "en-orig": "Inglés (Original)",
    "ja": "Japonés",
    "fr": "Francés",
    "de": "Alemán",
    "it": "Italiano",
    "pt": "Portugués",
    "pt-br": "Portugués (Brasil)",
    "pt-pt": "Portugués (Portugal)",
    "ru": "Ruso",
    "zh": "Chino",
    "zh-cn": "Chino (Simplificado)",
    "zh-tw": "Chino (Tradicional)",
    "zh-hans": "Chino (Simplificado)", 
    "zh-hant": "Chino (Tradicional)", 
    "ko": "Coreano",
    "ar": "Árabe",
    "hi": "Hindi",
    "iw": "Hebreo (código antiguo)", 
    "he": "Hebreo",
    "fil": "Filipino", 
    "aa": "Afar",
    "ab": "Abjasio",
    "ae": "Avéstico",
    "af": "Afrikáans",
    "ak": "Akán",
    "am": "Amárico",
    "an": "Aragonés",
    "as": "Asamés",
    "av": "Avar",
    "ay": "Aimara",
    "az": "Azerí",
    "ba": "Baskir",
    "be": "Bielorruso",
    "bg": "Búlgaro",
    "bh": "Bhojpuri",
    "bho": "Bhojpuri", 
    "bi": "Bislama",
    "bm": "Bambara",
    "bn": "Bengalí",
    "bo": "Tibetano",
    "br": "Bretón",
    "bs": "Bosnio",
    "ca": "Catalán",
    "ce": "Checheno",
    "ceb": "Cebuano", 
    "ch": "Chamorro",
    "co": "Corso",
    "cr": "Cree",
    "cs": "Checo",
    "cu": "Eslavo eclesiástico",
    "cv": "Chuvash",
    "cy": "Galés",
    "da": "Danés",
    "dv": "Divehi",
    "dz": "Dzongkha",
    "ee": "Ewe",
    "el": "Griego",
    "eo": "Esperanto",
    "et": "Estonio",
    "eu": "Euskera",
    "fa": "Persa",
    "ff": "Fula",
    "fi": "Finlandés",
    "fj": "Fiyiano",
    "fo": "Feroés",
    "fy": "Frisón occidental",
    "ga": "Irlandés",
    "gd": "Gaélico escocés",
    "gl": "Gallego",
    "gn": "Guaraní",
    "gu": "Guyaratí",
    "gv": "Manés",
    "ha": "Hausa",
    "ht": "Haitiano",
    "hu": "Húngaro",
    "hy": "Armenio",
    "hz": "Herero",
    "ia": "Interlingua",
    "id": "Indonesio",
    "ie": "Interlingue",
    "ig": "Igbo",
    "ii": "Yi de Sichuán",
    "ik": "Inupiaq",
    "io": "Ido",
    "is": "Islandés",
    "iu": "Inuktitut",
    "jv": "Javanés",
    "ka": "Georgiano",
    "kg": "Kongo",
    "ki": "Kikuyu",
    "kj": "Kuanyama",
    "kk": "Kazajo",
    "kl": "Groenlandés",
    "km": "Jemer",
    "kn": "Canarés",
    "kr": "Kanuri",
    "ks": "Cachemiro",
    "ku": "Kurdo",
    "kv": "Komi",
    "kw": "Córnico",
    "ky": "Kirguís",
    "la": "Latín",
    "lb": "Luxemburgués",
    "lg": "Ganda",
    "li": "Limburgués",
    "ln": "Lingala",
    "lo": "Lao",
    "lt": "Lituano",
    "lu": "Luba-katanga",
    "lv": "Letón",
    "mg": "Malgache",
    "mh": "Marshalés",
    "mi": "Maorí",
    "mk": "Macedonio",
    "ml": "Malayalam",
    "mn": "Mongol",
    "mr": "Maratí",
    "ms": "Malayo",
    "mt": "Maltés",
    "my": "Birmano",
    "na": "Nauruano",
    "nb": "Noruego bokmål",
    "nd": "Ndebele del norte",
    "ne": "Nepalí",
    "ng": "Ndonga",
    "nl": "Neerlandés",
    "nn": "Noruego nynorsk",
    "no": "Noruego",
    "nr": "Ndebele del sur",
    "nv": "Navajo",
    "ny": "Chichewa",
    "oc": "Occitano",
    "oj": "Ojibwa",
    "om": "Oromo",
    "or": "Oriya",
    "os": "Osético",
    "pa": "Panyabí",
    "pi": "Pali",
    "pl": "Polaco",
    "ps": "Pastún",
    "qu": "Quechua",
    "rm": "Romanche",
    "rn": "Kirundi",
    "ro": "Rumano",
    "rw": "Kinyarwanda",
    "sa": "Sánscrito",
    "sc": "Sardo",
    "sd": "Sindhi",
    "se": "Sami septentrional",
    "sg": "Sango",
    "si": "Cingalés",
    "sk": "Eslovaco",
    "sl": "Esloveno",
    "sm": "Samoano",
    "sn": "Shona",
    "so": "Somalí",
    "sq": "Albanés",
    "sr": "Serbio",
    "ss": "Suazi",
    "st": "Sesotho",
    "su": "Sundanés",
    "sv": "Sueco",
    "sw": "Suajili",
    "ta": "Tamil",
    "te": "Telugu",
    "tg": "Tayiko",
    "th": "Tailandés",
    "ti": "Tigriña",
    "tk": "Turcomano",
    "tl": "Tagalo",
    "tn": "Setsuana",
    "to": "Tongano",
    "tr": "Turco",
    "ts": "Tsonga",
    "tt": "Tártaro",
    "tw": "Twi",
    "ty": "Tahitiano",
    "ug": "Uigur",
    "uk": "Ucraniano",
    "ur": "Urdu",
    "uz": "Uzbeko",
    "ve": "Venda",
    "vi": "Vietnamita",
    "vo": "Volapük",
    "wa": "Valón",
    "wo": "Wolof",
    "xh": "Xhosa",
    "yi": "Yidis",
    "yo": "Yoruba",
    "za": "Zhuang",
    "zu": "Zulú",
    "und": "No especificado",
    "alb-al": "Albanés (Albania)",
    "ara-sa": "Árabe (Arabia Saudita)",
    "aze-az": "Azerí (Azerbaiyán)",
    "ben-bd": "Bengalí (Bangladesh)",
    "bul-bg": "Búlgaro (Bulgaria)",
    "cat-es": "Catalán (España)",
    "ces-cz": "Checo (República Checa)",
    "cmn-hans-cn": "Chino Mandarín (Simplificado, China)",
    "cmn-hant-cn": "Chino Mandarín (Tradicional, China)",
    "crs": "Francés criollo seselwa",
    "dan-dk": "Danés (Dinamarca)",
    "deu-de": "Alemán (Alemania)",
    "ell-gr": "Griego (Grecia)",
    "est-ee": "Estonio (Estonia)",
    "fil-ph": "Filipino (Filipinas)",
    "fin-fi": "Finlandés (Finlandia)",
    "fra-fr": "Francés (Francia)",
    "gaa": "Ga",
    "gle-ie": "Irlandés (Irlanda)",
    "haw": "Hawaiano",
    "heb-il": "Hebreo (Israel)",
    "hin-in": "Hindi (India)",
    "hmn": "Hmong",
    "hrv-hr": "Croata (Croacia)",
    "hun-hu": "Húngaro (Hungría)",
    "ind-id": "Indonesio (Indonesia)",
    "isl-is": "Islandés (Islandia)",
    "ita-it": "Italiano (Italia)",
    "jav-id": "Javanés (Indonesia)",
    "jpn-jp": "Japonés (Japón)",
    "kaz-kz": "Kazajo (Kazajistán)",
    "kha": "Khasi",
    "khm-kh": "Jemer (Camboya)",
    "kor-kr": "Coreano (Corea del Sur)",
    "kri": "Krio",
    "lav-lv": "Letón (Letonia)",
    "lit-lt": "Lituano (Lituania)",
    "lua": "Luba-Lulua",
    "luo": "Luo",
    "mfe": "Morisyen",
    "msa-my": "Malayo (Malasia)",
    "mya-mm": "Birmano (Myanmar)",
    "new": "Newari",
    "nld-nl": "Neerlandés (Países Bajos)",
    "nob-no": "Noruego Bokmål (Noruega)",
    "nso": "Sotho del norte",
    "pam": "Pampanga",
    "pol-pl": "Polaco (Polonia)",
    "por-pt": "Portugués (Portugal)",
    "ron-ro": "Rumano (Rumania)",
    "rus-ru": "Ruso (Rusia)",
    "slk-sk": "Eslovaco (Eslovaquia)",
    "slv-si": "Esloveno (Eslovenia)",
    "spa-es": "Español (España)",
    "swa-sw": "Suajili", 
    "swe-se": "Sueco (Suecia)",
    "tha-th": "Tailandés (Tailandia)",
    "tum": "Tumbuka",
    "tur-tr": "Turco (Turquía)",
    "ukr-ua": "Ucraniano (Ucrania)",
    "urd-pk": "Urdu (Pakistán)",
    "uzb-uz": "Uzbeko (Uzbekistán)",
    "vie-vn": "Vietnamita (Vietnam)",
    "war": "Waray",
    "alb": "Albanés",
    "ara": "Árabe",
    "aze": "Azerí",
    "ben": "Bengalí",
    "bul": "Búlgaro",
    "cat": "Catalán",
    "ces": "Checo",
    "cmn": "Chino Mandarín",
    "dan": "Danés",
    "deu": "Alemán",
    "ell": "Griego",
    "est": "Estonio",
    "fin": "Finlandés",
    "fra": "Francés",
    "gle": "Irlandés",
    "heb": "Hebreo",
    "hin": "Hindi",
    "hrv": "Croata",
    "hun": "Húngaro",
    "ind": "Indonesio",
    "isl": "Islandés",
    "ita": "Italiano",
    "jav": "Javanés",
    "jpn": "Japonés",
    "kaz": "Kazajo",
    "khm": "Jemer",
    "kor": "Coreano",
    "lav": "Letón",
    "lit": "Lituano",
    "msa": "Malayo",
    "mya": "Birmano",
    "nld": "Neerlandés",
    "nob": "Noruego Bokmål",
    "pol": "Polaco",
    "por": "Portugués",
    "ron": "Rumano",
    "rus": "Ruso",
    "slk": "Eslovaco",
    "slv": "Esloveno",
    "spa": "Español",
    "swe": "Sueco",
    "swa": "Suajili",
    "tha": "Tailandés",
    "tur": "Turco",
    "ukr": "Ucraniano",
    "urd": "Urdu",
    "uzb": "Uzbeko",
    "vie": "Vietnamita",
}

LANGUAGE_ORDER = {
    'es-419': 0, 'es-es': 1, 'es': 2, 'en': 3, 'ja': 4, 'fr': 5, 'de': 6, 
    'pt': 7, 'it': 8, 'zh': 9, 'ko': 10, 'ru': 11, 'ar': 12, 'hi': 13, 
    'vi': 15, 'pl': 16, 'id': 17, 'tr': 18, 'bn': 19, 'ta': 20, 'te': 21, 
    'pa': 22, 'mr': 23, 'ca': 24, 'gl': 25, 'eu': 26, 'und': 27
}
DEFAULT_PRIORITY = 99

EDITOR_FRIENDLY_CRITERIA = {
    'compatible_vcodecs': ['h264', 'avc1', 'hevc', 'h265', 'prores', 'dnxhd', 'dnxhr', 'cfhd', 'mpeg2video', 'dvvideo'],
    'compatible_acodecs': ['aac', 'mp4a', 'pcm_s16le', 'pcm_s24le', 'mp3', 'ac3'],
    'compatible_exts': ['mp4', 'mov', 'mxf', 'mts', 'm2ts', 'avi']
}

COMPATIBILITY_RULES = {
    '.gif': {'video': ['gif'], 'audio': []},
    '.mov': {'video': ['prores_aw', 'prores_ks', 'dnxhd', 'cfhd', 'qtrle', 'hap', 'h264_videotoolbox', 'libx264'], 'audio': ['pcm_s16le', 'pcm_s24le', 'alac']},
    '.mp4': {'video': ['libx264', 'libx265', 'h264_nvenc', 'hevc_nvenc', 'h264_amf', 'hevc_amf', 'av1_nvenc', 'av1_amf', 'h264_qsv', 'hevc_qsv', 'av1_qsv', 'vp9_qsv'], 'audio': ['aac', 'mp3', 'ac3', 'opus']},
    '.mkv': {'video': [], 'audio': ['libvorbis']},
    '.webm': {'video': ['libvpx', 'libvpx-vp9', 'libsvtav1'], 'audio': ['libopus', 'libvorbis']}
}

IMAGE_RAW_FORMATS = {'.PEF', '.RW2', '.CR3', '.RAF', '.ARW', '.DNG', '.CR2', '.NEF', '.SR2', '.ORF'}
IMAGE_INPUT_FORMATS = {'.svg', '.pdf', '.ai', '.eps', '.ps'}.union(IMAGE_RAW_FORMATS)
IMAGE_EXPORT_FORMATS = ['PNG', 'JPG', 'JPEG', 'WEBP', 'AVIF', 'BMP', 'PDF', 'TIFF']
IMAGE_RASTER_FORMATS = {'PNG', 'JPG', 'JPEG', 'BMP', 'TIFF', 'WEBP', 'AVIF'}
IMAGE_VECTOR_FORMATS = {'PDF'}
FORMATS_WITH_TRANSPARENCY = {'ICO', 'TIFF', 'PNG', 'WEBP', 'AVIF', 'PDF'}

DEFAULT_RASTER_DPI = 300
MAX_RECOMMENDED_DPI = 600
MAX_SAFE_DIMENSION = 8192
CRITICAL_DPI_THRESHOLD = 1200
CRITICAL_DIMENSION_THRESHOLD = 16384

INTERPOLATION_METHODS = {
    'Lanczos (Mejor Calidad)': 'LANCZOS',
    'Bicúbico (Rápido)': 'BICUBIC',
    'Bilineal (Muy Rápido)': 'BILINEAR',
    'Nearest (Pixelado)': 'NEAREST'
}

AI_FAMILY_HOLDER = 'Seleccione la familia...'
AI_ENGINE_HOLDER = 'Seleccione el motor...'
AI_MODEL_HOLDER = 'Seleccione el modelo...'

CANVAS_OPTIONS = [
    'Sin ajuste', 'Añadir Margen Externo', 'Añadir Margen Interno', 
    'Instagram Post (1080×1080)', 'Instagram Story (1080×1920)', 
    'YouTube Thumbnail (1280×720)', 'Twitter Header (1500×500)', 
    'Facebook Cover (820×312)', 'Personalizado...'
]
CANVAS_PRESET_SIZES = {
    'Instagram Post (1080×1080)': (1080, 1080),
    'Instagram Story (1080×1920)': (1080, 1920),
    'YouTube Thumbnail (1280×720)': (1280, 720),
    'Twitter Header (1500×500)': (1500, 500),
    'Facebook Cover (820×312)': (820, 312)
}
CANVAS_POSITIONS = [
    'Centro', 'Arriba Izquierda', 'Arriba Centro', 'Arriba Derecha', 
    'Centro Izquierda', 'Centro Derecha', 'Abajo Izquierda', 'Abajo Centro', 'Abajo Derecha'
]
CANVAS_OVERFLOW_MODES = ['Reducir hasta que quepa', 'Centrar (puede recortar)', 'Recortar al canvas', 'Advertir y no procesar']
BACKGROUND_TYPES = ['Color Sólido', 'Degradado', 'Imagen de Fondo']
GRADIENT_DIRECTIONS = ['Horizontal (Izq → Der)', 'Vertical (Arr → Aba)', 'Diagonal (↘)', 'Diagonal (↙)', 'Radial (Centro)']

REMBG_MODELS = {
    'Rembg Standard (U2Net)': {
        'General (Estándar)': {'file': 'isnet-general-use.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx', 'folder': 'rembg'},
        'General Lite (Rápido)': {'file': 'u2netp.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx', 'folder': 'rembg'},
        'Portrait (Retratos)': {'file': 'u2net.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx', 'folder': 'rembg'},
        'DIS (Bordes Finos/Complejo)': {'file': 'u2net_human_seg.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx', 'folder': 'rembg'},
        'COD (Objetos Camuflados)': {'file': 'isnet-anime.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-anime.onnx', 'folder': 'rembg'},
        'HRSOD (Alta Detección)': {'file': 'birefnet-cod.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-COD-epoch_125.onnx', 'folder': 'rembg'},
        'Massive (Entrenamiento Masivo)': {'file': 'birefnet-hrsod.onnx', 'url': 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-HRSOD_DHU-epoch_115.onnx', 'folder': 'rembg'}
    }
}

UPSCALING_TOOLS = {
    'Waifu2x': {'name': 'Waifu2x', 'folder': 'waifu2x', 'exe': 'waifu2x-ncnn-vulkan.exe', 'url': 'https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/20250915/waifu2x-ncnn-vulkan-20250915-windows.zip'},
    'SRMD': {'name': 'SRMD', 'folder': 'srmd', 'exe': 'srmd-ncnn-vulkan.exe', 'url': 'https://github.com/nihui/srmd-ncnn-vulkan/releases/download/20220728/srmd-ncnn-vulkan-20220728-windows.zip'},
    'Upscayl': {'name': 'Upscayl (Global Engine)', 'folder': 'upscayl', 'exe': 'upscayl-bin.exe', 'url': 'https://github.com/upscayl/upscayl-ncnn/releases/download/20251207-174704/upscayl-bin-20251207-174704-windows.zip', 'models_url': 'https://github.com/upscayl/custom-models/archive/refs/heads/main.zip'}
}

UPSCAYL_MODELS_MAP = {
    'realesrgan-x4plus': 'Real-ESRGAN (General / Fotografía)',
    'realesrgan-x4plus-anime': 'Real-ESRGAN (Anime / Ilustración)',
    'realesr-animevideov3-x4': 'Anime Video V3 (x4)',
    'RealESRGAN_General_x4_v3': 'Real-ESRGAN V3 (Ligero y Rápido)',
    'RealESRGAN_General_WDN_x4_v3': 'Real-ESRGAN V3 WDN (Red Profunda)',
    '4xHFA2k': 'HFA2k (Texturas de Alta Frecuencia)',
    '4xLSDIR': 'LSDIR (Fotografía Realista)',
    '4xLSDIRCompactC3': 'LSDIR Compacto (Procesamiento Rápido)',
    '4xLSDIRplusC': 'LSDIR PlusC (Alta Fidelidad)',
    '4xNomos8kSC': 'Nomos8k (Detalles a Escala 8k)',
    '4x_NMKD-Siax_200k': 'NMKD Siax (Universal / Calidad JPEG)',
    '4x_NMKD-Superscale-SP_178000_G': 'NMKD Superscale (Fotos sin Artefactos)',
    'uniscale_restore': 'Uniscale Restore (Restauración de Daños)',
    'unknown-2.0.1': 'The Unknown (Experimental / Nitidez Extrema)',
    'DF2K_x4': 'RealSR (Detalle de Texturas)',
    'DF2K_JPEG_x4': 'RealSR JPEG (Reduce Compresión)',
    'x4': 'Modelo Genérico x4'
}

WAIFU2X_MODELS = {
    'CU-Net (Alta Calidad)': {'model': 'models-cunet', 'scales': ['1x', '2x', '4x', '8x', '16x', '32x']},
    'Anime Style Art (Clásico)': {'model': 'models-upconv_7_anime_style_art_rgb', 'scales': ['1x', '2x', '4x', '8x', '16x', '32x']},
    'Photo (Fotos Reales)': {'model': 'models-upconv_7_photo', 'scales': ['1x', '2x', '4x', '8x', '16x', '32x']}
}

SRMD_MODELS = {
    'Estándar (General)': {'model': 'models-srmd', 'scales': ['2x', '3x', '4x']}
}

FFMPEG_SAFE_VERSION = '8.0.1'
FFMPEG_SAFE_URL = 'https://github.com/GyanD/codexffmpeg/releases/download/8.0.1/ffmpeg-8.0.1-full_build.zip'

REMBG_MODEL_FAMILIES = {
    "Rembg Standard (U2Net)": {
        "isnet-general-use (Recomendado)": {
            "file": "isnet-general-use.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
            "folder": "rembg"
        },
        "u2netp (Rápido)": {
            "file": "u2netp.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx",
            "folder": "rembg"
        },
        "u2net (Alta Precisión)": {
            "file": "u2net.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
            "folder": "rembg"
        },
        "u2net_human_seg (Humanos)": {
            "file": "u2net_human_seg.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx",
            "folder": "rembg"
        },
        "isnet-anime (Anime)": {
            "file": "isnet-anime.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-anime.onnx",
            "folder": "rembg"
        }
    },
    "BiRefNet (Next-Gen 2024)": {
        "General (Estándar)": {
            "file": "birefnet-general.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-epoch_244.onnx",
            "folder": "rembg"
        },
        "General Lite (Rápido)": {
            "file": "birefnet-general-lite.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx",
            "folder": "rembg"
        },
        "Portrait (Retratos)": {
            "file": "birefnet-portrait.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-portrait-epoch_150.onnx",
            "folder": "rembg"
        },
        "DIS (Bordes Finos/Complejo)": {
            "file": "birefnet-dis.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-DIS-epoch_590.onnx",
            "folder": "rembg"
        },
        "COD (Objetos Camuflados)": {
            "file": "birefnet-cod.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-COD-epoch_125.onnx",
            "folder": "rembg"
        },
        "HRSOD (Alta Detección)": {
            "file": "birefnet-hrsod.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-HRSOD_DHU-epoch_115.onnx",
            "folder": "rembg"
        },
        "Massive (Entrenamiento Masivo)": {
            "file": "birefnet-massive.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-massive-TR_DIS5K_TR_TEs-epoch_420.onnx",
            "folder": "rembg"
        },
        "HR General (4K/8K)": {
            "file": "birefnet-hr-general.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet_HR-general-epoch_130.onnx",
            "folder": "rembg"
        },
        "HR Matting (Recorte Ultra Fino)": {
            "file": "birefnet-hr-matting.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet_HR-matting-epoch_135.onnx",
            "folder": "rembg"
        }
    },
    "RMBG 2.0 (BriaAI)": {
        "Standard (Automático - 977 MB)": {
            "file": "rmbg2_gatis.onnx",
            "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/bria-rmbg-2.0.onnx",
            "folder": "rmbg2"
        },
        "Standard (1.02 GB)": {
            "file": "model.onnx",
            "url": "https://huggingface.co/briaai/RMBG-2.0/tree/main/onnx",
            "folder": "rmbg2"
        },
        "BnB4 (Recomendado - 355 MB)": {
            "file": "model_bnb4.onnx",
            "url": "https://huggingface.co/briaai/RMBG-2.0/tree/main/onnx",
            "folder": "rmbg2"
        },
        "FP16 (Media - 514 MB)": {
            "file": "model_fp16.onnx",
            "url": "https://huggingface.co/briaai/RMBG-2.0/tree/main/onnx",
            "folder": "rmbg2"
        },
        "Int8 (Rápido - 366 MB)": {
            "file": "model_int8.onnx",
            "url": "https://huggingface.co/briaai/RMBG-2.0/tree/main/onnx",
            "folder": "rmbg2"
        },
        "Quantized (366 MB)": {
            "file": "model_quantized.onnx",
            "url": "https://huggingface.co/briaai/RMBG-2.0/tree/main/onnx",
            "folder": "rmbg2"
        }
    }
}