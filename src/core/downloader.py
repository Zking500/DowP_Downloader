# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\downloader.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import yt_dlp
from .exceptions import UserCancelledError, PlaylistDownloadError
import threading
import os
import sys
def get_deno_path():
    """Obtiene la ruta absoluta de la carpeta donde está deno.exe."""
    if getattr(sys, 'frozen', False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(root, 'bin', 'deno')
def apply_yt_patch(ydl_opts):
    """Configuración optimizada SOLO para cuando se usan cookies."""
    if getattr(sys, 'frozen', False):
        root = os.path.dirname(sys.executable)
    else:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if sys.platform == 'win32':
        deno_executable = 'deno.exe'
    else:
        deno_executable = 'deno'
    deno_path = os.path.join(root, 'bin', 'deno', deno_executable)
    if not os.path.exists(deno_path):
        print(f'⚠️ Deno no encontrado en {deno_path}')
        import shutil
        system_deno = shutil.which('deno')
        if system_deno:
            deno_path = system_deno
            print(f'✅ Usando Deno del sistema: {deno_path}')
        else:
            print('❌ Deno no disponible. El parche puede no funcionar correctamente.')
            return ydl_opts
    ydl_opts['quiet'] = False
    ydl_opts['no_warnings'] = False
    ydl_opts['js_runtimes'] = {'deno': {'path': deno_path}}
    ydl_opts['remote_components'] = ['ejs:github']
    if 'extractor_args' not in ydl_opts:
        ydl_opts['extractor_args'] = {}
    ydl_opts['extractor_args']['youtube'] = {'player_client': ['web_safari', 'android', 'web', 'tv'], 'n_client': ['web_safari', 'android', 'tv'], 'skip': []}
    print(f'✅ Parche de YouTube aplicado. Deno: {deno_path}')
    return ydl_opts
def get_video_info(url, cookie_opts=None):
#     # irreducible cflow, using cdg fallback
#     # ***<module>.get_video_info: Failure: Compilation Error
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'timeout': 30, 'impersonate': True}
    use_cookies = False
    if cookie_opts:
        if 'cookiefile' in cookie_opts and cookie_opts['cookiefile']:
            ydl_opts['cookiefile'] = cookie_opts['cookiefile']
            use_cookies = True
        else:
            if 'cookiesfrombrowser' in cookie_opts and cookie_opts['cookiesfrombrowser']:
                    ydl_opts['cookiesfrombrowser'] = cookie_opts['cookiesfrombrowser']
                    use_cookies = True
    if use_cookies:
        ydl_opts = apply_yt_patch(ydl_opts)
        print('📝 Modo: Con cookies (parche aplicado)')
    else:
        print('📝 Modo: Sin cookies (configuración predeterminada de yt-dlp)')
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if info_dict:
                info_dict = apply_site_specific_rules(info_dict)
            return info_dict
    except Exception as e:
        print(f'ERROR en get_video_info: {e}')
        return None
def download_media(url, ydl_opts, progress_callback, cancellation_event: threading.Event):
    """\n    Descarga y procesa el medio.\n    """
    use_cookies = 'cookiefile' in ydl_opts or 'cookiesfrombrowser' in ydl_opts
    if use_cookies:
        ydl_opts = apply_yt_patch(ydl_opts)
        print('📥 Descarga: Con cookies (parche aplicado)')
    else:
        print('📥 Descarga: Sin cookies')
    is_fragment = 'download_ranges' in ydl_opts
    fragment_started = False
    def hook(d):
        nonlocal fragment_started
        if cancellation_event.is_set():
            print('DEBUG: Evento de cancelación detectado en el hook de yt-dlp.')
            raise UserCancelledError('Descarga cancelada por el usuario.')
        else:
            status = d.get('status', 'N/A')
            if status == 'downloading':
                fragment_started = True
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                if total_bytes > 0:
                    percentage = downloaded_bytes / total_bytes * 100
                    speed = d.get('speed')
                    if speed:
                        speed_mb = speed / 1024 / 1024
                        if speed_mb >= 1.0:
                            speed_str = f'{speed_mb:.1f} MB/s'
                        else:
                            speed_kb = speed / 1024
                            speed_str = f'{speed_kb:.0f} KB/s'
                    else:
                        speed_str = 'N/A'
                    download_type = 'fragmento' if is_fragment else 'archivo'
                    progress_callback(percentage, f'Descargando {download_type}... {percentage:.1f}% a {speed_str}')
                else:
                    if is_fragment:
                        elapsed = d.get('elapsed', 0)
                        progress_callback((-1), f'Descargando fragmento... {elapsed:.0f}s transcurridos')
            else:
                if status == 'finished':
                    if is_fragment:
                        progress_callback((-1), 'Fragmento descargado. Procesando con FFmpeg...')
                    else:
                        progress_callback(95, 'Descarga completada. Fusionando archivos si es necesario...')
                else:
                    if status == 'error':
                        raise yt_dlp.utils.DownloadError('yt-dlp reportó un error durante la descarga.')
    ydl_opts['progress_hooks'] = [hook]
    ydl_opts['concurrent_fragment_downloads'] = 5
    ydl_opts.setdefault('downloader', 'native')
    if 'external_downloader' in ydl_opts:
        ydl_opts.pop('external_downloader')
    if 'outtmpl' in ydl_opts:
        ydl_opts['restrictfilenames'] = True
    try:
        if cancellation_event.is_set():
            raise UserCancelledError('Descarga cancelada por el usuario antes de iniciar.')
        else:
            if is_fragment:
                progress_callback((-1), 'Descargando fragmento, esto puede tardar...')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
            if is_fragment and (not fragment_started):
                    progress_callback((-1), 'Fragmento extraído. Finalizando...')
            final_filepath = info_dict.get('filepath')
            if not final_filepath and 'requested_downloads' in info_dict:
                    final_filepath = info_dict['requested_downloads'][0].get('filepath')
            if not final_filepath:
                raise PlaylistDownloadError('No se pudo determinar la ruta del archivo descargado después del proceso.')
            else:
                progress_callback(100, '✅ Descarga completada exitosamente')
                return final_filepath
    except UserCancelledError as e:
        print(f'DEBUG: Operación de descarga interrumpida: {e}')
        raise e
    except Exception as e:
        print(f'Error en el proceso de descarga de yt-dlp: {e}')
        raise e
def apply_site_specific_rules(info):
    """\n    Normaliza metadatos de sitios problemáticos antes de que la UI los procese.\n    """
    if not info:
        return info
    else:
        extractor = info.get('extractor_key', '').lower()
        url = info.get('webpage_url', '').lower()
        is_twitch_clip = 'clips' in extractor or '/clip/' in url
        if is_twitch_clip:
            print(f'DEBUG: 🚑 Aplicando parche de compatibilidad para Twitch CLIP ({extractor})')
            info = _fix_twitch_clip_formats(info)
        return info
def _fix_twitch_clip_formats(info):
    """\n    Asigna códecs falsos (h264/aac) si faltan, para que la UI habilite los menús.\n    """
    formats = info.get('formats', [])
    for f in formats:
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')
        if not vcodec or vcodec == 'none' or vcodec == 'unknown':
            f['vcodec'] = 'h264'
        if not acodec or acodec == 'none' or acodec == 'unknown':
            f['acodec'] = 'aac'
        if not f.get('ext') or f.get('ext') == 'unknown':
            f['ext'] = 'mp4'
    return info
