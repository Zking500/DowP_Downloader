# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\text_utils.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import re
import unicodedata
def clean_text_for_davinci(text, clean_emojis=True):
    """\n    Sanitiza el texto para asegurar compatibilidad con DaVinci Resolve y Adobe.\n    \n    Args:\n        text (str): El texto original (título, nombre de archivo).\n        clean_emojis (bool): Si es True, elimina emojis y símbolos gráficos.\n        \n    Returns:\n        str: El texto limpio.\n    """
    if not text:
        return ''
    else:
        text = unicodedata.normalize('NFC', text)
        if clean_emojis:
            cleaned_chars = []
            for char in text:
                category = unicodedata.category(char)
                if category.startswith(('L', 'N', 'P', 'Z')):
                    cleaned_chars.append(char)
                else:
                    if category in ['So', 'Cn']:
                        continue
                    else:
                        cleaned_chars.append(char)
            text = ''.join(cleaned_chars)
        forbidden_chars = '[\\\\/:\\*\\?\"<>|]'
        text = re.sub(forbidden_chars, '', text)
        text = re.sub('\\s+', ' ', text).strip()
        text = text.rstrip('. ')
        if len(text) > 150:
            text = text[:147] + '...'
        return text or 'Sin Titulo'