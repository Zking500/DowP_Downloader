# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\davinci_api.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import os
import sys
def preparar_entorno():
    """Configura las rutas y variables de entorno para usar el Python interno de DowP."""
    base_api = 'C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting'
    ruta_modulos = os.path.join(base_api, 'Modules')
    if os.path.exists(ruta_modulos) and ruta_modulos not in sys.path:
            sys.path.append(ruta_modulos)
    os.environ['RESOLVE_SCRIPT_API'] = base_api
    os.environ['RESOLVE_SCRIPT_LIB'] = 'C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll'
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        internal_dir = os.path.join(exe_dir, '_internal')
        if not os.path.exists(internal_dir):
            internal_dir = exe_dir
        os.environ['PYTHONHOME'] = internal_dir
        os.environ['RESOLVE_PYTHON3_BIN'] = sys.executable
        paths = [ruta_modulos, internal_dir]
        for sub in ['lib', 'lib-dynload', 'site-packages']:
            p = os.path.join(internal_dir, sub)
            if os.path.exists(p):
                paths.append(p)
        os.environ['PYTHONPATH'] = os.pathsep.join(paths)
        if internal_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = internal_dir + os.pathsep + os.environ.get('PATH', '')
    else:
        if 'PYTHONPATH' not in os.environ:
            os.environ['PYTHONPATH'] = ruta_modulos
        else:
            if ruta_modulos not in os.environ['PYTHONPATH']:
                os.environ['PYTHONPATH'] += os.pathsep + ruta_modulos
def timecode_a_frames(timecode, fps=24):
    """Convierte un string de timecode a número de frames."""
    partes = timecode.split(':')
    if len(partes) != 4:
        return 0
    else:
        h, m, s, f = map(int, partes)
        return (h * 3600 + m * 60 + s) * fps + f
def pista_esta_libre(timeline, tipo, indice, inicio, fin):
    """Verifica si hay espacio en una pista específica para un rango de frames."""
    items = timeline.GetItemListInTrack(tipo, indice)
    for item in items:
        i_start = item.GetStart()
        i_end = item.GetEnd()
        if not (fin <= i_start or inicio >= i_end):
                return False
    return True
def get_short_path(long_name):
    """Obtiene la ruta corta (8.3) de Windows para evitar problemas con caracteres especiales en el API."""
    try:
        import ctypes
        from ctypes import wintypes
        _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
        _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        _GetShortPathNameW.restype = wintypes.DWORD
        output_buf_size = 260
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        result = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        if result == 0 or result > output_buf_size:
            return long_name
        else:
            return output_buf.value
    except Exception:
        return long_name
def obtener_o_crear_carpeta(media_pool, parent_folder, name):
    """Busca o crea una subcarpeta en el Media Pool de forma robusta."""
    if not parent_folder:
        return
    else:
        subfolders = parent_folder.GetSubFolderList()
        if isinstance(subfolders, dict):
            for folder in subfolders.values():
                if folder.GetName() == name:
                    return folder
        else:
            if isinstance(subfolders, list):
                for folder in subfolders:
                    if folder.GetName() == name:
                        return folder
        try:
            return media_pool.AddSubFolder(parent_folder, name)
        except Exception:
            return None
def importar_a_davinci(file_paths, log_callback=None, import_to_timeline=True, bin_name='DowP Imports'):
    """
    Importa una lista de archivos a DaVinci Resolve.
    """
    import time

    if not file_paths:
        return False

    time.sleep(0.5)
    if log_callback:
        log_callback('INFO: Iniciando conexión con DaVinci Resolve...')

    preparar_entorno()

    try:
        import DaVinciResolveScript as dvr_script
    except ImportError:
        if log_callback:
            log_callback('ERROR: DaVinci Resolve no parece estar instalado o el API no es accesible.')
        return False

    resolve = dvr_script.scriptapp('Resolve')
    if not resolve:
        if log_callback:
            log_callback('ERROR: No se pudo conectar con DaVinci Resolve Studio.')
            log_callback('TIP: Asegúrate de que Resolve esté abierto y que en Preferencias > Sistema > General > \'External scripting using\' esté en \'Local\' o \'All\'.')
            log_callback('TIP: En Resolve 19+, intenta ejecutar DowP como Administrador.')
        return False

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if not project:
        if log_callback:
            log_callback('WARNING: No hay ningún proyecto abierto en DaVinci Resolve.')
        return False

    mp = project.GetMediaPool()
    root = mp.GetRootFolder()
    timeline = project.GetCurrentTimeline()

    main_folder = obtener_o_crear_carpeta(mp, root, bin_name)

    ext_map = {
        'Video': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'],
        'Imagen': ['.jpg', '.jpeg', '.png', '.gif', '.tiff', '.webp', '.bmp'],
        'Audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus']
    }

    exito_total = True

    for path in file_paths:
        if not os.path.exists(path):
            if log_callback:
                log_callback(f'WARNING: El archivo no existe: {os.path.basename(path)}')
            exito_total = False
            continue

        # Determinar tipo por extensión
        ext = os.path.splitext(path)[1].lower()
        folder_type = 'Otros'
        for category, extensions in ext_map.items():
            if ext in extensions:
                folder_type = category
                break

        mp.SetCurrentFolder(root)
        abs_path = os.path.abspath(path)

        if log_callback:
            log_callback(f'DEBUG: [DaVinci] Intentando ImportMedia (Raíz): {abs_path}')

        clips_pool = mp.ImportMedia([abs_path])

        # Fallback a ruta corta (8.3) si falla
        if not clips_pool or len(clips_pool) == 0:
            if log_callback:
                log_callback('DEBUG: Falló ruta larga. Intentando con ruta corta (8.3)...')
            short_path = get_short_path(abs_path)
            if short_path != abs_path:
                if log_callback:
                    log_callback(f'DEBUG: [DaVinci] Reintentando con ruta corta: {short_path}')
                clips_pool = mp.ImportMedia([short_path])

        if not clips_pool or len(clips_pool) == 0:
            if log_callback:
                log_callback(f'ERROR: Falló la importación al Media Pool: {os.path.basename(path)}')
            exito_total = False
            continue

        clip_item = clips_pool[0]
        has_video = folder_type in ('Video', 'Imagen')
        has_audio = folder_type in ('Audio', 'Video')

        # Detección de "audio puro" dentro de contenedor de vídeo
        if folder_type == 'Video':
            try:
                props = clip_item.GetClipProperty()
                if isinstance(props, dict):
                    v_codec = props.get('Video Codec', '')
                    v_res = props.get('Resolution', '')
                else:
                    v_codec = clip_item.GetClipProperty('Video Codec')
                    v_res = clip_item.GetClipProperty('Resolution')

                if (not v_codec or v_codec == 'N/A' or v_codec == '') and (not v_res or v_res == ''):
                    if log_callback:
                        log_callback(f'INFO: [DaVinci] \'{os.path.basename(path)}\' detectado como AUDIO PURO (contenedor {ext}).')
                    folder_type = 'Audio'
                    has_video = False
                    has_audio = True
            except Exception as e:
                if log_callback:
                    log_callback(f'DEBUG: Error inspeccionando propiedades del clip: {e}')

        # Mover clip a su carpeta correspondiente dentro de bin_name
        target_folder = obtener_o_crear_carpeta(mp, main_folder, folder_type)
        if target_folder:
            if log_callback:
                log_callback(f'DEBUG: Moviendo clip a carpeta: {folder_type}')
            mp.MoveClips([clip_item], target_folder)

        # Insertar en timeline si procede
        if timeline and import_to_timeline:
            tc_string = timeline.GetCurrentTimecode()
            fps = float(project.GetSetting('timelineFrameRate'))
            start_frame = timecode_a_frames(tc_string, fps)

            # Obtener duración del clip (Start/End son frames internos)
            try:
                start_p = float(clip_item.GetClipProperty('Start'))
                end_p = float(clip_item.GetClipProperty('End'))
                duracion = end_p - start_p
            except Exception:
                duracion = 0  # si no se puede, se inserta con duración 0 (podría fallar)

            end_frame = start_frame + duracion

            # Buscar una pista libre (tanto de vídeo como de audio)
            num_v_tracks = timeline.GetTrackCount('video')
            num_a_tracks = timeline.GetTrackCount('audio')
            max_pistas = max(num_v_tracks, num_a_tracks)

            pista_final = None
            for i in range(1, max_pistas + 2):  # +1 para permitir crear nueva pista
                video_ok = True
                if has_video and i <= num_v_tracks:
                    video_ok = pista_esta_libre(timeline, 'video', i, start_frame, end_frame)

                audio_ok = True
                if has_audio and i <= num_a_tracks:
                    audio_ok = pista_esta_libre(timeline, 'audio', i, start_frame, end_frame)

                if video_ok and audio_ok:
                    pista_final = i
                    break

            # Si no se encontró pista, usamos max_pistas+1 (creará nuevas)
            if pista_final is None:
                pista_final = max_pistas + 1

            # Añadir pistas de vídeo solo si el clip tiene vídeo y la pista no existe
            if has_video:
                while timeline.GetTrackCount('video') < pista_final:
                    timeline.AddTrack('video')

            # Añadir pistas de audio solo si el clip tiene audio y la pista no existe
            if has_audio:
                while timeline.GetTrackCount('audio') < pista_final:
                    timeline.AddTrack('audio', 'stereo')

            # Preparar info para AppendToTimeline
            clip_info = {
                'mediaPoolItem': clip_item,
                'trackIndex': int(pista_final),
                'recordFrame': float(start_frame),
                'mediaType': 0  # 0 = video? (según el original)
            }

            if mp.AppendToTimeline([clip_info]):
                if log_callback:
                    log_callback(f'LOG: [DaVinci] Importado: {os.path.basename(path)} en Pista {pista_final}')
            else:
                if log_callback:
                    log_callback(f'ERROR: [DaVinci] Falló inserción en timeline: {os.path.basename(path)}')
                exito_total = False
        else:
            if log_callback:
                log_callback(f'LOG: [DaVinci] Importado al Media Pool (sin timeline activa): {os.path.basename(path)}')

    return exito_total