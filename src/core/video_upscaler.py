# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\video_upscaler.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

"""\nvideo_upscaler.py\nModulo de reescalado de video usando motores NCNN (Real-ESRGAN, Waifu2x, RealSR, SRMD).\nFlujo: extraer frames (FFmpeg) -> reescalar carpeta (NCNN) -> reensamblar + audio (FFmpeg).\n"""
import os
import json
import shutil
import tempfile
import subprocess
import multiprocessing
import time
import threading
from src.core.constants import WAIFU2X_MODELS, SRMD_MODELS, UPSCALING_TOOLS
from src.core.exceptions import UserCancelledError
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.normpath(os.path.join(_THIS_DIR, '..', '..', 'bin'))
CONTAINER_CODECS = {'.mp4': {'vcodec': 'libx264', 'acodec': 'aac', 'pix_fmt': 'yuv420p'}, '.mkv': {'vcodec': 'libx264', 'acodec': 'copy', 'pix_fmt': 'yuv420p'}, '.mov': {'vcodec': 'libx264', 'acodec': 'aac', 'pix_fmt': 'yuv420p'}, '.avi': {'vcodec': 'libx264', 'acodec': 'libmp3lame', 'pix_fmt': 'yuv420p'}, '.gif': {'vcodec': 'gif', 'acodec': None, 'pix_fmt': 'rgb24'}}
class VideoUpscaler:
    """\n    Motor de reescalado de video usando ejecutables NCNN.\n    """
    def __init__(self, ffmpeg_dir: str, upscaling_dir: str=None, cancellation_event=None, progress_callback=None):
        """\n        Args:\n            ffmpeg_dir: Carpeta donde vive ffmpeg.exe / ffprobe.exe\n            upscaling_dir: Ruta base de los modelos de upscaling (opcional)\n            cancellation_event: threading.Event para cancelacion externa\n            progress_callback: callable(pct: float, msg: str)\n        """
        self.ffmpeg_dir = ffmpeg_dir
        self.ffmpeg_exe = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
        self.ffprobe_exe = os.path.join(ffmpeg_dir, 'ffprobe.exe')
        self.cancellation_event = cancellation_event
        self.progress_callback = progress_callback or (lambda p, m: None)
        if upscaling_dir:
            self.models_root = upscaling_dir
        else:
            _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
            BIN_DIR = os.path.normpath(os.path.join(_THIS_DIR, '..', '..', 'bin'))
            self.models_root = os.path.join(BIN_DIR, 'models', 'upscaling')
    def _check_dependencies(self):
        """Verifica que FFmpeg y FFprobe existan."""
        for exe in [self.ffmpeg_exe, self.ffprobe_exe]:
            if not os.path.exists(exe):
                raise Exception(f'Dependencia no encontrada: {exe}. Por favor, reinstala FFmpeg.')
    def _check_cancel(self, proc=None):
        if self.cancellation_event and self.cancellation_event.is_set():
                if proc:
                    try:
                        print(f'DEBUG [VideoUpscaler] Cancelación detectada. Terminando proceso {proc.pid}...')
                        proc.kill()
                        proc.wait(timeout=2.0)
                    except:
                        pass
                raise UserCancelledError('Proceso cancelado por el usuario.')
    def _report(self, pct: float, msg: str):
        self.progress_callback(pct, msg)
    def _creationflags(self):
        return subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    def _thread_args(self) -> str:
        """\n        Calcula los hilos de carga:proceso:guardado.\n        En video somos más conservadores que en imagen para evitar crashes de GPU por saturación.\n        """
        n = multiprocessing.cpu_count()
        if n >= 12:
            return '1:2:1'
        else:
            if n >= 6:
                return '1:1:1'
            else:
                return '1:1:1'
    def _get_video_info(self, input_path: str) -> dict:
        """Usa ffprobe para obtener FPS, extension, codec de audio."""
        self._report(2, 'Analizando video original...')
        cmd = [self.ffprobe_exe, '-v', 'quiet', '-print_format', 'json', '-show_streams', input_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=self._creationflags())
            data = json.loads(result.stdout)
        except Exception as e:
            print(f'ADVERTENCIA: ffprobe fallo ({e}), usando valores por defecto.')
            return {'fps': '30', 'ext': os.path.splitext(input_path)[1].lower(), 'has_audio': False}
        fps = '30'
        has_audio = False
        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type', '')
            if codec_type == 'video':
                r_fps = stream.get('r_frame_rate', '30/1')
                try:
                    num, den = r_fps.split('/')
                    fps = str(round(int(num) / int(den), 3))
                except Exception:
                    fps = '30'
            else:
                if codec_type == 'audio':
                    has_audio = True
        ext = os.path.splitext(input_path)[1].lower()
        return {'fps': fps, 'ext': ext, 'has_audio': has_audio}
    def _extract_frames(self, input_path: str, frames_dir: str, fps: str):
        """Extrae todos los frames como PNG con FFmpeg."""
        self._check_cancel()
        self._report(5, 'Preparando extracción de fotogramas...')
        pattern = os.path.join(frames_dir, 'frame_%08d.png')
        cmd = [self.ffmpeg_exe, '-i', input_path, '-vsync', '0', '-f', 'image2', pattern, '-y']
        print(f"DEBUG [VideoUpscaler] Ejecutando FFmpeg: {' '.join(cmd)}")
        _logs = []
        def log_reader(pipe):
            try:
                for line in pipe:
                    if line:
                        _logs.append(line)
                        if 'error' in line.lower() or 'warning' in line.lower():
                            print(f'FFMPEG LOG: {line.strip()}')
            except:
                return None
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=self._creationflags(), text=True, errors='ignore', bufsize=1)
        reader_thread = threading.Thread(target=log_reader, args=(proc.stderr,), daemon=True)
        reader_thread.start()
        start_t = time.time()
        while proc.poll() is None:
            self._check_cancel(proc)
            elapsed = time.time() - start_t
            p = min(14.9, 5 + elapsed / 2.0)
            self._report(p, f'Extrayendo fotogramas ({int(elapsed)}s)...')
            time.sleep(0.5)
        proc.wait()
        reader_thread.join(timeout=1.0)
        if proc.returncode != 0:
            stderr_out = ''.join(_logs)
            print(f'ERROR FFMPEG EXTRACT: {stderr_out}')
            raise Exception(f'FFmpeg fallo al extraer frames (Codigo {proc.returncode}).\n\n{stderr_out[:200]}')
        else:
            frames = [f for f in os.listdir(frames_dir) if f.endswith('.png')]
            total = len(frames)
            print(f'INFO [VideoUpscaler] Extraction completa. Total frames: {total}')
            self._report(15, f'Extracción lista: {total} fotogramas.')
            return total
    def _build_ncnn_cmd(self, engine: str, model_friendly: str, scale: str, in_dir: str, out_dir: str, tile_size: str='0', denoise: str='-1', tta: bool=False, concurrency: str='Automático') -> list:
        """Construye el comando NCNN para procesar un directorio de frames."""
        if not tile_size:
            tile_size = '0'
        if concurrency == 'Seguro (Estabilidad)':
            threads_arg = '1:1:1'
        else:
            if concurrency == 'Equilibrado':
                threads_arg = '1:2:1'
            else:
                if concurrency == 'Máximo (Potente)':
                    threads_arg = '2:4:2'
                else:
                    threads_arg = self._thread_args()
        if engine == 'SRMD':
            info = SRMD_MODELS.get(model_friendly, {})
            internal = info.get('model', 'models-srmd')
            exe = os.path.join(self.models_root, 'srmd', 'srmd-ncnn-vulkan.exe')
            model_path = os.path.join(self.models_root, 'srmd', internal)
            cmd = [exe, '-i', in_dir, '-o', out_dir, '-m', model_path, '-n', denoise, '-s', scale, '-t', tile_size, '-f', 'png', '-j', threads_arg]
            if tta:
                cmd += ['-x']
            return cmd
        else:
            if engine == 'Upscayl':
                from src.core.constants import UPSCAYL_MODELS_MAP
                rev_map = {v: k for k, v in UPSCAYL_MODELS_MAP.items()}
                internal_model = rev_map.get(model_friendly, model_friendly)
                exe = os.path.join(self.models_root, 'upscayl', 'upscayl-bin.exe')
                model_path = os.path.join(self.models_root, 'upscayl', 'models')
                cmd = [exe, '-i', in_dir, '-o', out_dir, '-n', internal_model, '-m', model_path, '-s', scale, '-f', 'png', '-j', threads_arg]
                import re
                match = re.search('[xX]([2-3])', internal_model)
                if match:
                    cmd.extend(['-z', match.group(1)])
                if tile_size and tile_size != '0':
                        cmd += ['-t', tile_size]
                if tta:
                    cmd += ['-x']
                return cmd
            else:
                info = WAIFU2X_MODELS.get(model_friendly, {})
                internal = info.get('model', 'models-cunet')
                exe = os.path.join(self.models_root, 'waifu2x', 'waifu2x-ncnn-vulkan.exe')
                model_path = os.path.join(self.models_root, 'waifu2x', internal)
                cmd = [exe, '-i', in_dir, '-o', out_dir, '-m', model_path, '-n', denoise, '-s', scale, '-t', tile_size, '-f', 'png', '-j', threads_arg]
                if tta:
                    cmd += ['-x']
                return cmd
    def _run_ncnn(self, engine: str, model_friendly: str, scale: str, in_dir: str, out_dir: str, total_frames: int, tile_size: str='0', denoise: str='-1', tta: bool=False, concurrency: str='Automático'):
        """Ejecuta el proceso NCNN y reporta progreso estimado."""
        self._check_cancel()
        self._report(15, f'Iniciando motor AI ({engine})...')
        cmd = self._build_ncnn_cmd(engine, model_friendly, scale, in_dir, out_dir, tile_size, denoise, tta, concurrency)
        print(f"DEBUG [VideoUpscaler] NCNN cmd: {' '.join(cmd)}")
        exe = cmd[0]
        if not os.path.exists(exe):
            raise Exception(f'El motor \'{engine}\' no está instalado.\n\nBúscalo en \'Herramientas de Imagen\' y descárgalo desde allí antes de usar el reescalador de video.')
        else:
            _logs = []
            def log_reader(pipe):
                try:
                    for line in pipe:
                        if line:
                            _logs.append(line)
                            if 'error' in line.lower() or 'failed' in line.lower():
                                print(f'UPSCALER LOG: {line.strip()}')
                except:
                    return None
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=self._creationflags(), text=True, errors='ignore', bufsize=1)
            reader_thread = threading.Thread(target=log_reader, args=(proc.stderr,), daemon=True)
            reader_thread.start()
            start_time = time.time()
            last_done = (-1)
            while proc.poll() is None:
                self._check_cancel(proc)
                try:
                    done = len([f for f in os.listdir(out_dir) if f.endswith('.png')])
                except:
                    done = last_done
                if done != last_done:
                    pct = 15 + done / max(total_frames, 1) * 70
                    elapsed = int(time.time() - start_time)
                    msg = f'Procesando: {done}/{total_frames} fotogramas ({elapsed}s)'
                    self._report(min(pct, 84.9), msg)
                    print(f'UPSCALER: {msg}')
                    last_done = done
                time.sleep(1.0)
            proc.wait()
            reader_thread.join(timeout=1.0)
            stderr_out = ''.join(_logs)
            if proc.returncode != 0:
                print(f'ERROR NCNN: {stderr_out}')
                raise Exception(f'El motor AI falló (Código {proc.returncode}).\n\nDetalles:\n{stderr_out[:500]}')
            else:
                vulkan_errors = ['vkQueueSubmit failed', 'vkAllocateMemory failed', 'invalid gpu device', 'out of gpu memory']
                if any((err in stderr_out for err in vulkan_errors)):
                    print(f'CRITICAL ERROR (Vulkan): {stderr_out}')
                    raise Exception('Error de Hardware (Vulkan) detectado.\n\nTu tarjeta gráfica no pudo procesar los fotogramas. Intenta reducir el \'Tamaño de Mosaico (Tile Size)\' a 128 o 64 en los ajustes.')
                else:
                    out_frames = [f for f in os.listdir(out_dir) if f.endswith('.png')]
                    if not out_frames:
                        raise Exception('El motor AI terminó pero no se generó ningún fotograma reescalado.')
                    else:
                        first_frame = os.path.join(out_dir, out_frames[0])
                        if os.path.getsize(first_frame) < 100:
                            raise Exception('Error de procesamiento: Los fotogramas generados están vacíos o corruptos (posible incompatibilidad de driver GPU).')
                        else:
                            self._report(85, 'Reescalado completado con éxito.')
    def _reassemble(self, upscaled_dir: str, original_path: str, output_path: str, fps: str, container: str, has_audio: bool, transparency: bool=False):
        """Ensambla los frames reescalados + audio original en el video final."""
        self._check_cancel()
        self._report(86, 'Preparando ensamblado final...')
        ext = container if container.startswith('.') else f'.{container}'
        codec_info = CONTAINER_CODECS.get(ext, CONTAINER_CODECS['.mp4'])
        frame_pattern = os.path.join(upscaled_dir, 'frame_%08d.png')
        cmd = [self.ffmpeg_exe, '-framerate', fps, '-i', frame_pattern]
        if has_audio:
            cmd += ['-i', original_path]
        if ext == '.gif':
            cmd += ['-vf', 'fps=' + fps + ',scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse', '-loop', '0']
        else:
            if transparency and ext == '.mov':
                cmd += ['-c:v', 'qtrle', '-pix_fmt', 'rgba']
            else:
                cmd += ['-c:v', codec_info['vcodec'], '-pix_fmt', codec_info['pix_fmt'], '-crf', '18', '-preset', 'fast']
        if has_audio and ext != '.gif':
            cmd += ['-c:a', codec_info['acodec'], '-map', '0:v:0', '-map', '1:a:0?']
        else:
            cmd += ['-map', '0:v:0']
        cmd += ['-y', output_path]
        print(f"DEBUG [VideoUpscaler] Reensamblando: {' '.join(cmd)}")
        _logs = []
        def log_reader(pipe):
            try:
                for line in pipe:
                    if line:
                        _logs.append(line)
                        if 'error' in line.lower() or 'warning' in line.lower():
                            print(f'FFMPEG REASSEMBLE LOG: {line.strip()}')
            except:
                return None
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=self._creationflags(), text=True, errors='ignore', bufsize=1)
        reader_thread = threading.Thread(target=log_reader, args=(proc.stderr,), daemon=True)
        reader_thread.start()
        start_t = time.time()
        while proc.poll() is None:
            self._check_cancel(proc)
            elapsed = int(time.time() - start_t)
            p = min(98, 86 + elapsed * 2)
            self._report(p, 'Guardando video final (unificando audio)...')
            time.sleep(0.5)
        proc.wait()
        reader_thread.join(timeout=1.0)
        if proc.returncode != 0:
            stderr_out = ''.join(_logs)
            print(f'ERROR FFMPEG REASSEMBLE: {stderr_out}')
            raise Exception(f'FFmpeg falló al crear el video final (Codigo {proc.returncode}):\n{stderr_out[(-500):]}')
        else:
            self._report(100, '¡Vídeo reescalado con éxito!')
    def upscale_video(self, input_path: str, output_path: str, options: dict) -> str:
        """\n        Proceso completo: extraer -> reescalar -> reensamblar.\n        """
        self._check_dependencies()
        engine = options.get('upscale_engine', 'Real-ESRGAN')
        model = options.get('upscale_model_friendly', '')
        if not model:
            if engine == 'Upscayl':
                upscayl_models_dir = os.path.join(self.models_root, 'upscayl', 'models')
                if os.path.exists(upscayl_models_dir):
                    models = [f[:(-6)] for f in os.listdir(upscayl_models_dir) if f.endswith('.param')]
                    model = sorted(models)[0] if models else 'realesrgan-x4plus'
                else:
                    model = 'realesrgan-x4plus'
            else:
                model_map = {'Waifu2x': WAIFU2X_MODELS, 'SRMD': SRMD_MODELS}
                model = list(model_map.get(engine, WAIFU2X_MODELS).keys())[0]
        scale = options.get('upscale_scale', '2').replace('x', '')
        container_choice = options.get('upscale_container', '')
        info = self._get_video_info(input_path)
        fps = info['fps']
        has_audio = info['has_audio']
        if not container_choice or container_choice.lower() == 'mismo que el original':
            ext_out = info['ext'] if info['ext'] else '.mp4'
        else:
            ext_out = container_choice if container_choice.startswith('.') else f'.{container_choice}'
        base, _ = os.path.splitext(output_path)
        output_path = base + ext_out
        frames_dir = None
        upscaled_dir = None
        try:
            frames_dir = tempfile.mkdtemp(prefix='dowp_upscale_in_')
            upscaled_dir = tempfile.mkdtemp(prefix='dowp_upscale_out_')
            total = self._extract_frames(input_path, frames_dir, fps)
            if total == 0:
                raise Exception('No se pudieron extraer fotogramas del video.')
            else:
                tile_size = options.get('upscale_tile', '0')
                denoise = options.get('upscale_denoise', '-1')
                tta = options.get('upscale_tta', False)
                concurrency = options.get('upscale_concurrency', 'Automático')
                transparency = options.get('upscale_transparency', False)
                self._run_ncnn(engine, model, scale, frames_dir, upscaled_dir, total, tile_size=tile_size, denoise=denoise, tta=tta, concurrency=concurrency)
                self._reassemble(upscaled_dir, input_path, output_path, fps, ext_out, has_audio, transparency=transparency)
        finally:
            for d in (frames_dir, upscaled_dir):
                if d and os.path.exists(d):
                    try:
                        shutil.rmtree(d, ignore_errors=True)
                    except:
                        pass
        return output_path