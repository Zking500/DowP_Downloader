# processor.py
# Versión corregida – Elimina errores de indentación y lógica rota

import json
import tempfile
import subprocess
import threading
import os
import re
import sys
import time
from .exceptions import UserCancelledError
from main import FFMPEG_BIN_DIR

# ============================================
# Definición de CODEC_PROFILES (si no existe)
# ============================================
try:
    # Si ya está definido en otro sitio, no lo sobreescribimos
    CODEC_PROFILES
except NameError:
    # Estructura de ejemplo: categoría -> nombre_amigable -> {codec: ..., container: ...}
    CODEC_PROFILES = {
        'Video': {
            'H.264 (libx264)': {'libx264': 'mp4'},
            'H.265 (libx265)': {'libx265': 'mp4'},
            'VP9 (libvpx-vp9)': {'libvpx-vp9': 'webm'},
            'AV1 (libaom-av1)': {'libaom-av1': 'mp4'},
            'H.264 (NVENC)': {'nvenc_h264': 'mp4'},
            'H.265 (NVENC)': {'nvenc_hevc': 'mp4'},
            'H.264 (QSV)': {'h264_qsv': 'mp4'},
            'H.265 (QSV)': {'hevc_qsv': 'mp4'},
            'H.264 (AMF)': {'h264_amf': 'mp4'},
            'H.265 (AMF)': {'hevc_amf': 'mp4'},
            'H.264 (VideoToolbox)': {'h264_videotoolbox': 'mp4'},
            'H.265 (VideoToolbox)': {'hevc_videotoolbox': 'mp4'},
        },
        'Audio': {
            'AAC (aac)': {'aac': 'm4a'},
            'MP3 (libmp3lame)': {'libmp3lame': 'mp3'},
            'FLAC (flac)': {'flac': 'flac'},
            'Opus (libopus)': {'libopus': 'opus'},
            'Vorbis (libvorbis)': {'libvorbis': 'ogg'},
        }
    }

# ============================================
# Utilidades
# ============================================
def parse_time_to_seconds(t_str):
    """Convierte un string HH:MM:SS o MM:SS a segundos."""
    if not t_str:
        return 0.0
    parts = str(t_str).split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    else:
        return float(t_str)

def clean_and_convert_vtt_to_srt(input_path):
    """
    Convierte un archivo VTT a SRT limpio, o limpia un SRT existente.
    Elimina etiquetas de formato, marcas de tiempo duplicadas y texto de karaoke.
    """
    import re
    output_path = input_path
    is_vtt = input_path.lower().endswith('.vtt')
    if is_vtt:
        output_path = os.path.splitext(input_path)[0] + '.srt'
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        cleaned_lines = []
        counter = 1
        skip_next = False
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if (line_stripped.startswith('WEBVTT') or
                line_stripped.startswith('Kind:') or
                line_stripped.startswith('Language:')):
                continue
            if line_stripped.startswith('STYLE') or '::cue' in line:
                skip_next = True
                continue
            if skip_next:
                if line_stripped == '':
                    skip_next = False
                continue
            if line_stripped and '-->' not in line and not line_stripped.isdigit():
                cleaned = re.sub(r'<[^>]+>', '', line)
                cleaned = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', cleaned)
                cleaned = re.sub(r'\{[^}]+\}', '', cleaned)
                cleaned = cleaned.strip()
                if cleaned:
                    cleaned_lines.append(cleaned)
            else:
                if '-->' in line or line_stripped.isdigit() or line_stripped == '':
                    cleaned_lines.append(line_stripped)

        srt_content = []
        i = 0
        while i < len(cleaned_lines):
            line = cleaned_lines[i]
            if '-->' in line:
                srt_content.append(str(counter))
                timestamp = line.replace('.', ',')
                srt_content.append(timestamp)
                i += 1
                text_lines = []
                while i < len(cleaned_lines) and cleaned_lines[i].strip() != '':
                    if '-->' not in cleaned_lines[i]:
                        text_lines.append(cleaned_lines[i])
                    i += 1
                if text_lines:
                    srt_content.extend(text_lines)
                srt_content.append('')
                counter += 1
            else:
                i += 1

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_content))
        if is_vtt and output_path != input_path:
            try:
                os.remove(input_path)
            except Exception:
                pass
        print(f'DEBUG: Subtítulo limpiado y guardado en: {output_path}')
        return output_path
    except Exception as e:
        print(f'ERROR al limpiar subtítulo: {e}')
        return input_path

def slice_subtitle(ffmpeg_path, input_path, output_path, start_time, end_time=None):
    """Corta el subtítulo usando FFmpeg con Input Seeking."""
    cmd = [ffmpeg_path, '-y']
    if start_time:
        cmd.extend(['-ss', str(start_time)])
    cmd.extend(['-i', input_path])
    if end_time:
        s_sec = parse_time_to_seconds(start_time)
        e_sec = parse_time_to_seconds(end_time)
        duration = e_sec - s_sec
        if duration > 0:
            cmd.extend(['-t', str(duration)])
    cmd.append(output_path)
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=creationflags)
    except Exception as e:
        print(f'ERROR cortando subtítulo con FFmpeg: {e}')
        return False
    return True

# ============================================
# Clase principal
# ============================================
class FFmpegProcessor:
    def __init__(self, app_version=None, cache_dir=None):
        ffmpeg_exe_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
        self.ffmpeg_path = os.path.join(FFMPEG_BIN_DIR, ffmpeg_exe_name)
        self.gpu_vendor = None
        self.is_detection_complete = False
        self.available_encoders = {'CPU': {'Video': {}, 'Audio': {}}, 'GPU': {'Video': {}}}
        self.current_process = None
        self.app_version = app_version or 'unknown'
        self.cache_dir = cache_dir

    def cancel_current_process(self):
        """Cancela el proceso de FFmpeg que se esté ejecutando actualmente."""
        if self.current_process and self.current_process.poll() is None:
            print('DEBUG: Enviando señal de terminación al proceso de FFmpeg...')
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
                print('DEBUG: Proceso de FFmpeg terminado.')
            except Exception as e:
                print(f'ERROR: No se pudo terminar el proceso de FFmpeg: {e}')
            finally:
                self.current_process = None

    def run_detection_async(self, callback):
        threading.Thread(target=self._detect_encoders, args=(callback,), daemon=True).start()

    def _detect_encoders(self, callback):
        """Detecta los códecs disponibles en FFmpeg, usando caché si existe."""
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            version_bytes = subprocess.check_output(
                [self.ffmpeg_path, '-version'],
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
                cwd=os.path.dirname(self.ffmpeg_path)
            )
            ffmpeg_version_str = version_bytes.decode('utf-8', errors='ignore').split('\n')[0].strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.is_detection_complete = True
            callback(False, 'Error: ffmpeg no está instalado o no se encuentra en el PATH.')
            return

        if self.cache_dir:
            cache_path = os.path.join(self.cache_dir, 'encoder_cache.json')
            try:
                if os.path.exists(cache_path):
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    if (cache_data.get('ffmpeg_version') == ffmpeg_version_str and
                        cache_data.get('app_version') == self.app_version and
                        cache_data.get('encoders')):
                        self.available_encoders = cache_data['encoders']
                        self.gpu_vendor = cache_data.get('gpu_vendor')
                        self.is_detection_complete = True
                        print(f'INFO: Caché de códecs cargado (FFmpeg: {ffmpeg_version_str}).')
                        callback(True, 'Detección completada (caché).')
                        return
            except Exception as e:
                print(f'ADVERTENCIA: No se pudo leer el caché de encoders, se re-detectará: {e}')

        try:
            all_encoders_output = subprocess.check_output(
                [self.ffmpeg_path, '-encoders'],
                text=True, encoding='utf-8', stderr=subprocess.STDOUT,
                creationflags=creationflags, cwd=os.path.dirname(self.ffmpeg_path)
            )
        except subprocess.CalledProcessError as e:
            self.is_detection_complete = True
            callback(False, f'Error al ejecutar ffmpeg -encoders: {e}')
            return

        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            log_path = os.path.join(base_path, 'ffmpeg_encoders_log.txt')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('--- ENCODERS DETECTADOS POR FFmpeg ---\n')
                f.write(all_encoders_output)
            print(f'DEBUG: Registro de códecs guardado en {log_path}')
        except Exception as e:
            print(f'ADVERTENCIA: No se pudo escribir el log de códecs: {e}')

        self.gpu_vendor = None
        for category, codecs in CODEC_PROFILES.items():
            for friendly_name, details in codecs.items():
                ffmpeg_codec_name = None
                for key in details:
                    if key != 'container':
                        ffmpeg_codec_name = key
                        break
                if not ffmpeg_codec_name:
                    continue
                search_pattern = r'^\s[A-Z\.]{6}\s+' + re.escape(ffmpeg_codec_name) + r'\s'
                if re.search(search_pattern, all_encoders_output, re.MULTILINE):
                    proc_type = 'GPU' if any(x in ffmpeg_codec_name for x in ['nvenc', 'qsv', 'amf', 'videotoolbox']) else 'CPU'
                    if proc_type == 'GPU' and self.gpu_vendor is None:
                        if 'nvenc' in ffmpeg_codec_name:
                            self.gpu_vendor = 'NVIDIA'
                        elif 'qsv' in ffmpeg_codec_name:
                            self.gpu_vendor = 'Intel'
                        elif 'amf' in ffmpeg_codec_name:
                            self.gpu_vendor = 'AMD'
                        elif 'videotoolbox' in ffmpeg_codec_name:
                            self.gpu_vendor = 'Apple'
                    if proc_type not in self.available_encoders:
                        self.available_encoders[proc_type] = {}
                    if category not in self.available_encoders[proc_type]:
                        self.available_encoders[proc_type][category] = {}
                    self.available_encoders[proc_type][category][friendly_name] = details

        if self.cache_dir:
            cache_path = os.path.join(self.cache_dir, 'encoder_cache.json')
            try:
                cache_data = {
                    'ffmpeg_version': ffmpeg_version_str,
                    'app_version': self.app_version,
                    'gpu_vendor': self.gpu_vendor,
                    'encoders': self.available_encoders
                }
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                print(f'INFO: Caché de códecs guardado en {cache_path}')
            except Exception as e:
                print(f'ADVERTENCIA: No se pudo guardar el caché de encoders: {e}')

        self.is_detection_complete = True
        callback(True, 'Detección completada.')

    def extract_audio(self, input_file, output_file, duration, progress_callback, cancellation_event: threading.Event):
        """Extrae la pista de audio sin recodificar (rápido)."""
        if cancellation_event.is_set():
            raise UserCancelledError('Extracción de audio cancelada antes de iniciar.')

        command = [
            self.ffmpeg_path, '-y', '-nostdin', '-progress', '-',
            '-i', input_file, '-vn', '-c:a', 'copy',
            '-map_metadata', '-1', '-acodec', 'copy', output_file
        ]
        print('--- Comando FFmpeg para extracción de audio ---')
        print(' '.join(command))
        print('---------------------------------------------')

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        error_output_buffer = []
        process = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='ignore',
                creationflags=creationflags
            )
            self.current_process = process

            def read_stream_into_buffer(stream, buffer):
                for line in iter(stream.readline, ''):
                    buffer.append(line.strip())

            stdout_thread = threading.Thread(
                target=self._read_stdout_for_progress,
                args=(process.stdout, progress_callback, cancellation_event, duration),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream_into_buffer,
                args=(process.stderr, error_output_buffer),
                daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            while process.poll() is None:
                if cancellation_event.is_set():
                    self.cancel_current_process()
                    raise UserCancelledError('Extracción de audio cancelada por el usuario.')
                time.sleep(0.1)

            stdout_thread.join()
            stderr_thread.join()

            if process.returncode != 0:
                raise Exception(f"FFmpeg falló al extraer audio: {' '.join(error_output_buffer)}")

            return output_file

        except UserCancelledError:
            raise
        except Exception as e:
            self.cancel_current_process()
            raise e
        finally:
            if process:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
            self.current_process = None

    def execute_recode(self, options, progress_callback, cancellation_event: threading.Event):
        """Recodifica video/audio según opciones."""
        if cancellation_event.is_set():
            raise UserCancelledError('Recodificación cancelada por el usuario antes de iniciar.')

        input_file = options['input_file']
        output_file = os.path.normpath(options['output_file'])

        try:
            media_info = self.get_local_media_info(input_file)
            actual_duration = float(media_info['format']['duration'])
        except Exception:
            actual_duration = options.get('duration', 0)

        command = [self.ffmpeg_path, '-y', '-nostdin', '-progress', '-']
        pre_params = options.get('pre_params', [])
        if pre_params:
            command.extend(pre_params)

        command.extend(['-i', input_file])

        mode = options.get('mode')
        video_idx = options.get('selected_video_stream_index')
        audio_idx = options.get('selected_audio_stream_index')

        if mode == 'Video+Audio':
            if video_idx is not None:
                command.extend(['-map', f'0:{video_idx}?'])
            if audio_idx == 'all':
                command.extend(['-map', '0:a?'])
            elif audio_idx is not None:
                command.extend(['-map', f'0:{audio_idx}?'])
        elif mode == 'Solo Audio':
            if audio_idx == 'all':
                command.extend(['-map', '0:a?'])
            elif audio_idx is not None:
                command.extend(['-map', f'0:{audio_idx}?'])

        final_params = options.get('ffmpeg_params', [])
        command.extend(final_params)
        command.append(output_file)

        print('--- Comando FFmpeg a ejecutar ---')
        print(' '.join(command))
        print('---------------------------------')

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        error_output_buffer = []
        process = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='ignore',
                creationflags=creationflags
            )
            self.current_process = process

            def read_stream_into_buffer(stream, buffer):
                for line in iter(stream.readline, ''):
                    buffer.append(line.strip())

            stdout_reader_thread = threading.Thread(
                target=self._read_stdout_for_progress,
                args=(process.stdout, progress_callback, cancellation_event, actual_duration),
                daemon=True
            )
            stderr_reader_thread = threading.Thread(
                target=read_stream_into_buffer,
                args=(process.stderr, error_output_buffer),
                daemon=True
            )
            stdout_reader_thread.start()
            stderr_reader_thread.start()

            while process.poll() is None:
                if cancellation_event.is_set():
                    self.cancel_current_process()
                    raise UserCancelledError('Recodificación cancelada por el usuario.')
                time.sleep(0.1)

            stdout_reader_thread.join()
            stderr_reader_thread.join()

            if process.returncode != 0 and not cancellation_event.is_set():
                full_error_log = '\n'.join(error_output_buffer)
                print(f'\n--- ERROR DETALLADO DE FFmpeg ---\n{full_error_log}\n---------------------------------\n')
                lines = [L for L in full_error_log.split('\n') if L.strip()]
                relevant_lines = lines[-8:] if len(lines) > 8 else lines
                error_summary = '\n'.join(relevant_lines)
                raise Exception(f'FFmpeg falló. Detalles:\n\n{error_summary}')

            if cancellation_event.is_set():
                raise UserCancelledError('Recodificación cancelada por el usuario.')

            return output_file

        except UserCancelledError:
            self.cancel_current_process()
            raise
        except Exception as e:
            self.cancel_current_process()
            raise Exception(f'Error en recodificación: {e}')
        finally:
            if process:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
            self.current_process = None

    def _read_stdout_for_progress(self, stream, progress_callback, cancellation_event, duration):
        """Lee el stdout de FFmpeg para el progreso."""
        last_reported_percentage = -1.0
        for line in iter(stream.readline, ''):
            if cancellation_event.is_set():
                return
            if 'out_time_ms=' in line:
                try:
                    progress_us = int(line.strip().split('=')[1])
                    if duration > 0:
                        progress_seconds = progress_us / 1000000
                        percentage = progress_seconds / duration * 100
                        if (percentage >= last_reported_percentage + 1.0 or
                            percentage >= 99.9 or percentage <= 0.1):
                            progress_callback(percentage, f'Recodificando... {percentage:.1f}%')
                            last_reported_percentage = percentage
                except ValueError:
                    continue

    def get_local_media_info(self, input_file):
        """Usa ffprobe para obtener información detallada de un archivo local."""
        ffprobe_exe_name = 'ffprobe.exe' if os.name == 'nt' else 'ffprobe'
        ffprobe_path = os.path.join(os.path.dirname(self.ffmpeg_path), ffprobe_exe_name)
        command = [
            ffprobe_path, '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', input_file
        ]
        print(f"DEBUG: Ejecutando comando ffprobe con Popen: {' '.join(command)}")
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='ignore',
                creationflags=creationflags
            )
            stdout, stderr = process.communicate(timeout=60)
            if process.returncode != 0:
                print('--- ERROR DETALLADO DE FFPROBE (Popen) ---')
                print(f'Código de salida: {process.returncode}')
                print(f'stdout:\n{stdout}')
                print(f'stderr:\n{stderr}')
                print('-----------------------------------------')
                return None
            return json.loads(stdout)
        except subprocess.TimeoutExpired:
            print('--- ERROR: TIMEOUT DE FFPROBE ---')
            print('La operación tardó más de 60s y fue cancelada.')
            if 'process' in locals() and process:
                process.kill()
                process.communicate()
            print('---------------------------------')
            return None
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f'ERROR: No se pudo obtener información de \'{input_file}\' con ffprobe: {e}')
            return None

    def get_frame_from_video(self, input_file, duration=0):
        """Extrae un fotograma de un video en un punto seguro."""
        if duration > 0:
            seek_time_seconds = min(duration / 2, 5.0)
            at_time = f'{seek_time_seconds:.3f}'
        else:
            at_time = '00:00:01'
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f'dowp_thumbnail_{os.path.basename(input_file)}.jpg')
        command = [
            self.ffmpeg_path, '-y', '-i', input_file,
            '-ss', at_time, '-vframes', '1', '-q:v', '2', output_path
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(command, check=True, capture_output=True, creationflags=creationflags)
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f'ERROR: No se pudo extraer el fotograma: {e}')
            return None

    def execute_video_to_images(self, options, progress_callback, cancellation_event: threading.Event):
        """Convierte un video en secuencia de imágenes."""
        if cancellation_event.is_set():
            raise UserCancelledError('Extracción cancelada por el usuario antes de iniciar.')

        input_file = options['input_file']
        output_folder = os.path.normpath(options['output_folder'])
        image_format = options.get('image_format', 'png')
        fps = options.get('fps')
        jpg_quality = options.get('jpg_quality', '2')

        try:
            jpg_quality_int = int(jpg_quality)
            if not 1 <= jpg_quality_int <= 31:
                jpg_quality = '2'
        except (ValueError, TypeError):
            jpg_quality = '2'

        os.makedirs(output_folder, exist_ok=True)

        command = [self.ffmpeg_path, '-y', '-nostdin', '-progress', '-']
        pre_params = options.get('pre_params', [])
        if pre_params:
            command.extend(pre_params)
        command.extend(['-i', input_file])

        final_params = []
        if fps:
            try:
                fps_value = float(fps)
                final_params.extend(['-vf', f'fps={fps_value}'])
                print(f'INFO: Extrayendo a {fps_value} FPS.')
            except (ValueError, TypeError):
                print('INFO: FPS inválido, extrayendo todos los fotogramas.')
        else:
            print('INFO: Extrayendo todos los fotogramas (FPS no especificado).')

        if image_format == 'jpg':
            final_params.extend(['-q:v', str(jpg_quality)])
            output_pattern = 'frame_%06d.jpg'
        else:
            output_pattern = 'frame_%06d.png'

        command.extend(final_params)
        command.append(os.path.join(output_folder, output_pattern))

        print('--- Comando FFmpeg para Extracción de Imágenes ---')
        print(' '.join(command))
        print('-------------------------------------------------')

        try:
            media_info = self.get_local_media_info(input_file)
            actual_duration = float(media_info['format']['duration'])
        except Exception:
            actual_duration = options.get('duration', 0)

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        error_output_buffer = []
        process = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='ignore',
                creationflags=creationflags
            )
            self.current_process = process

            def read_stream_into_buffer(stream, buffer):
                for line in iter(stream.readline, ''):
                    buffer.append(line.strip())

            stdout_reader_thread = threading.Thread(
                target=self._read_stdout_for_progress,
                args=(process.stdout, progress_callback, cancellation_event, actual_duration),
                daemon=True
            )
            stderr_reader_thread = threading.Thread(
                target=read_stream_into_buffer,
                args=(process.stderr, error_output_buffer),
                daemon=True
            )
            stdout_reader_thread.start()
            stderr_reader_thread.start()

            while process.poll() is None:
                if cancellation_event.is_set():
                    self.cancel_current_process()
                    raise UserCancelledError('Extracción cancelada por el usuario.')
                time.sleep(0.1)

            stdout_reader_thread.join()
            stderr_reader_thread.join()

            if process.returncode != 0 and not cancellation_event.is_set():
                full_error_log = ' '.join(error_output_buffer)
                print(f'\n--- ERROR DETALLADO DE FFmpeg ---\n{full_error_log}\n---------------------------------\n')
                raise Exception('FFmpeg falló (ver consola para detalles técnicos).')

            if cancellation_event.is_set():
                raise UserCancelledError('Extracción cancelada por el usuario.')

            return output_folder

        except UserCancelledError:
            self.cancel_current_process()
            raise
        except Exception as e:
            self.cancel_current_process()
            raise Exception(f'Error en extracción de imágenes: {e}')
        finally:
            if process:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
            self.current_process = None