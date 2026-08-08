# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\image_converter.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import os
import io
import re
import tempfile
import threading
import subprocess
import pillow_avif
from src.core.inkscape_service import InkscapeService
from src.core.constants import WAIFU2X_MODELS, SRMD_MODELS
from src.core.constants import IMAGE_RASTER_FORMATS, IMAGE_INPUT_FORMATS, IMAGE_RAW_FORMATS
from main import BIN_DIR, REMBG_MODELS_DIR, MODELS_DIR
try:
    from pdf2image import convert_from_path, pdfinfo_from_path
    CAN_PDF = True
except ImportError:
    CAN_PDF = False
    print('ADVERTENCIA: \'pdf2image\' no instalado. No se podrán convertir archivos .pdf, .ai, .eps')
from PIL import Image, ImageDraw, ImageChops
from src.core.exceptions import UserCancelledError
try:
    import cairosvg
    CAN_SVG = True
except ImportError:
    CAN_SVG = False
    print('ADVERTENCIA: \'cairosvg\' no instalado. No se podrán convertir archivos .svg')
try:
    from pdf2image import convert_from_path, pdfinfo_from_path
    CAN_PDF = True
except ImportError:
    CAN_PDF = False
    print('ADVERTENCIA: \'pdf2image\' no instalado. No se podrán convertir archivos .pdf, .ai, .eps')
try:
    import img2pdf
    CAN_IMG2PDF = True
except ImportError:
    CAN_IMG2PDF = False
    print('ADVERTENCIA: \'img2pdf\' no instalado. Conversión a PDF será más lenta')
class ImageConverter:
    """\n    Motor de conversión de imágenes que soporta múltiples formatos\n    de entrada/salida con opciones avanzadas.\n    """
    def __init__(self, poppler_path=None, inkscape_service=None, ffmpeg_processor=None):
        self.poppler_path = poppler_path
        self.inkscape_service = inkscape_service
        self.ffmpeg_processor = ffmpeg_processor
        self.rembg_module = None
        self.rembg_sessions = {}
        self.gs_dir, self.gs_exe = self._find_local_ghostscript()
        if self.gs_exe:
            print(f'INFO: Ghostscript local detectado: {self.gs_exe}')
        else:
            print('ADVERTENCIA: Ghostscript no encontrado. Conversión EPS/PS limitada.')
        self.RASTER_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif', '.avif')
        self.VECTOR_FORMATS = ('.pdf', '.svg', '.eps', '.ai', '.ps')
        self.OTHER_FORMATS = ('.psd', '.tga', '.jp2', '.ico')
        from src.core.constants import INTERPOLATION_METHODS
        self.INTERPOLATION_METHODS = INTERPOLATION_METHODS
        from src.core.constants import CANVAS_POSITIONS, CANVAS_OVERFLOW_MODES
        self.CANVAS_POSITIONS = CANVAS_POSITIONS
        self.CANVAS_OVERFLOW_MODES = CANVAS_OVERFLOW_MODES
    def _find_local_ghostscript(self):
        """Busca Ghostscript y devuelve (carpeta_bin, ruta_exe)."""
        try:
            base_path = os.getcwd()
            possible_dirs = [os.path.join(base_path, 'bin', 'ghostscript', 'bin'), os.path.join(base_path, 'bin', 'ghostscript'), os.path.join(base_path, 'bin', 'gs', 'bin')]
            binaries = ['gswin64c.exe', 'gswin32c.exe', 'gs.exe', 'gs']
            for folder in possible_dirs:
                if os.path.exists(folder):
                    for binary in binaries:
                        full_path = os.path.join(folder, binary)
                        if os.path.exists(full_path):
                            print(f'DEBUG: Ghostscript encontrado en: {full_path}')
                            return (folder, full_path)
            print('DEBUG: Ghostscript no encontrado en rutas locales')
        except Exception as e:
            print(f'ERROR buscando Ghostscript: {e}')
            return (None, None)
        else:
            return (None, None)
    def _load_rembg_lazy(self, progress_callback=None):
        """\n        Intenta cargar la librería rembg solo cuando se solicita.\n        Retorna True si se cargó (o ya estaba cargada), False si falló.\n        """
        if self.rembg_module is not None:
            return True
        else:
            print('INFO: Inicializando motor de IA (Rembg)...')
            if progress_callback:
                try:
                    progress_callback(None, 'Inicializando Motor IA (esto puede tardar unos segundos)...')
                except Exception:
                    pass
            try:
                import rembg
                self.rembg_module = rembg
            except ImportError as e:
                print(f'ERROR CRÍTICO: No se pudo cargar el módulo \'rembg\': {e}')
                return False
            except Exception as e:
                print(f'ERROR INESPERADO cargando rembg: {e}')
                return False
            else:
                return True
    def clear_ai_sessions(self):
        """Libera la memoria de los modelos de IA cargados."""
        if self.rembg_sessions:
            print(f'DEBUG: Liberando {len(self.rembg_sessions)} sesiones de IA de la memoria.')
            self.rembg_sessions.clear()
        import gc
        gc.collect()
    def prepare_ai_sessions(self, options, progress_callback=None):
        """\n        Pre-carga los modelos de IA necesarios según las opciones para evitar \n        congelamientos durante el procesamiento.\n        """
        if options.get('rembg_enabled', False):
            if not self._load_rembg_lazy(progress_callback):
                return False
            else:
                model_name = options.get('rembg_model', 'u2net')
                use_gpu = options.get('use_gpu', True)
                from main import MODELS_DIR
                model_path = os.path.join(MODELS_DIR, 'rembg', f'{model_name}.onnx')
                if not os.path.exists(model_path):
                    return True
                else:
                    session_key = f"{model_path}_{('gpu' if use_gpu else 'cpu')}"
                    if session_key not in self.rembg_sessions:
                        if progress_callback:
                            hw = 'GPU/DirectML' if use_gpu else 'CPU'
                            progress_callback(None, f'Inicializando modelo {model_name} en {hw}...')
                        try:
                            import onnxruntime as ort
                            sess_opts = ort.SessionOptions()
                            if use_gpu:
                                providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
                                sess_opts.enable_mem_pattern = False
                            else:
                                providers = ['CPUExecutionProvider']
                            self.rembg_sessions[session_key] = ort.InferenceSession(model_path, providers=providers, sess_options=sess_opts)
                            print(f'DEBUG: Sesión {model_name} pre-cargada con éxito.')
                        except Exception as e:
                            print(f'WARNING: No se pudo pre-cargar el modelo: {e}')
        return True
    def _process_high_res_onnx(self, pil_image, model_path, use_gpu=True):
        """\n        Ejecuta la inferencia específica para modelos de alta resolución (RMBG 2.0, InSPyReNet) \n        usando ONNX Runtime con redimensión a 1024x1024 y normalización ImageNet.\n        """
        try:
            import numpy as np
            import onnxruntime as ort
            session_key = f"{model_path}_{('gpu' if use_gpu else 'cpu')}"
            if session_key not in self.rembg_sessions:
                hw_label = 'GPU' if use_gpu else 'CPU'
                print(f'DEBUG: Cargando Modelo de Alta Res. en [{hw_label}]: {os.path.basename(model_path)}')
                sess_opts = ort.SessionOptions()
                if use_gpu:
                    providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
                    sess_opts.enable_mem_pattern = False
                else:
                    providers = ['CPUExecutionProvider']
                    sess_opts.enable_cpu_mem_arena = True
                    sess_opts.execution_mode = ort.ExecutionMode.ORT_PARALLEL
                self.rembg_sessions[session_key] = ort.InferenceSession(model_path, providers=providers, sess_options=sess_opts)
            session = self.rembg_sessions[session_key]
            original_image = pil_image.convert('RGB')
            orig_w, orig_h = original_image.size
            img_resized = original_image.resize((1024, 1024), Image.Resampling.BILINEAR)
            img_np = np.array(img_resized).astype(np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            img_np = (img_np - mean) / std
            img_np = img_np.astype(np.float32)
            img_np = img_np.transpose(2, 0, 1)
            img_np = np.expand_dims(img_np, 0)
            input_name = session.get_inputs()[0].name
            result = session.run(None, {input_name: img_np})
            mask = result[0][0, 0]
            mask = (mask * 255).clip(0, 255).astype(np.uint8)
            mask_img = Image.fromarray(mask, mode='L')
            mask_img = mask_img.resize((orig_w, orig_h), Image.Resampling.LANCZOS)
            final_image = pil_image.convert('RGBA')
            final_image.putalpha(mask_img)
            return final_image
        except Exception as e:
            print(f'ERROR en inferencia de alta resolución: {e}')
            return pil_image
    def _process_onnx_manual(self, pil_image, session, target_size):
        """\n        Inferencia manual universal con corrección matemática para BiRefNet.\n        """
        import numpy as np
        original_image = pil_image.convert('RGB')
        orig_w, orig_h = original_image.size
        img_resized = original_image.resize(target_size, Image.Resampling.BILINEAR)
        img_np = np.array(img_resized).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img_np = (img_np - mean) / std
        img_np = img_np.transpose(2, 0, 1)
        img_np = np.expand_dims(img_np, 0)
        input_name = session.get_inputs()[0].name
        result = session.run(None, {input_name: img_np})
        raw_mask = result[0][0, 0]
        min_val, max_val = (raw_mask.min(), raw_mask.max())
        if min_val < (-1.0) or max_val > 1.5:
            mask = 1 / (1 + np.exp(-raw_mask))
        else:
            mask = raw_mask
        mask = (mask - mask.min()) / (mask.max() - mask.min() + 1e-08)
        mask = (mask * 255).astype(np.uint8)
        mask_img = Image.fromarray(mask, mode='L')
        mask_img = mask_img.resize((orig_w, orig_h), Image.Resampling.LANCZOS)
        final_image = pil_image.convert('RGBA')
        final_image.putalpha(mask_img)
        return final_image
    def remove_background(self, pil_image, model_filename='u2netp.onnx', progress_callback=None, use_gpu=True):
        # irreducible cflow, using cdg fallback
        """Elimina el fondo.
        Args:
            use_gpu (bool): True = GPU (DirectML Anti-Freeze), False = CPU (Full Performance)
        """
        from main import MODELS_DIR
        import onnxruntime as ort
        import os

        high_res_names = ['bria-rmbg-2.0.onnx', 'model.onnx', 'model_bnb4.onnx', 'model_fp16.onnx', 'model_int8.onnx', 'model_quantized.onnx', 'model_q4.onnx', 'model_q4f16.onnx', 'model_uint8.onnx', 'inspyrenet_ultra.onnx', 'inspyrenet_ultra_fp16.onnx']
        possible_paths = [os.path.join(MODELS_DIR, 'rmbg2', model_filename), os.path.join(MODELS_DIR, 'inspyrenet', model_filename)]
        target_model_path = None
        for p in possible_paths:
            if os.path.exists(p):
                target_model_path = p
                break

        # High-resolution models
        if model_filename in high_res_names or target_model_path:
            if not target_model_path:
                print(f'ERROR: El modelo de alta resolución no se encuentra localmente: {model_filename}')
                return pil_image
            else:
                return self._process_high_res_onnx(pil_image, target_model_path, use_gpu=use_gpu)
        else:
            # Load rembg lazily for standard models
            if not self._load_rembg_lazy(progress_callback):
                print('ERROR: La librería de IA no pudo cargarse.')
                return pil_image

        # Create or retrieve ONNX session
        session_key = f"{model_filename}_{('gpu' if use_gpu else 'cpu')}"
        if session_key not in self.rembg_sessions:
            full_model_path = os.path.join(REMBG_MODELS_DIR, model_filename)  # REMBG_MODELS_DIR must be defined
            if not os.path.exists(full_model_path):
                full_model_path = os.path.join(MODELS_DIR, 'rembg', model_filename)
            if not os.path.exists(full_model_path):
                print(f'ERROR: No encuentro el modelo {model_filename}')
                return pil_image
            else:
                hw_label = 'GPU' if use_gpu else 'CPU'
                print(f'DEBUG: Cargando Manualmente {model_filename} en [{hw_label}]')
                sess_opts = ort.SessionOptions()
                if use_gpu:
                    providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
                    sess_opts.enable_mem_pattern = False
                    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
                    sess_opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                    sess_opts.inter_op_num_threads = 1
                    sess_opts.intra_op_num_threads = 1
                else:
                    providers = ['CPUExecutionProvider']
                    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    sess_opts.execution_mode = ort.ExecutionMode.ORT_PARALLEL
                self.rembg_sessions[session_key] = ort.InferenceSession(full_model_path, providers=providers, sess_options=sess_opts)

        session = self.rembg_sessions[session_key]
        model_lower = model_filename.lower()

        # Determine target size based on model type
        if 'birefnet' in model_lower:
            size = (1024, 1024)
        elif 'isnet' in model_lower:
            size = (1024, 1024)
        elif 'u2net' in model_lower:
            size = (320, 320)
        else:
            size = (1024, 1024)

        # Process with try-except to handle GPU failures
        try:
            output_image = self._process_onnx_manual(pil_image, session, target_size=size)
            return output_image
        except Exception as run_error:
            error_msg = repr(run_error)
            if use_gpu and ('DmlFusedNode' in error_msg or '887A0007' in error_msg or 'Non-zero status' in error_msg):
                print('⚠️ ADVERTENCIA: La GPU falló o se agotó el tiempo. Reintentando con CPU...')
                return self.remove_background(pil_image, model_filename, progress_callback, use_gpu=False)
            else:
                # Re-raise if not a known GPU error
                raise run_error
        except Exception as e:  # This outer except is not needed if we handle all in one, but we can have a catch-all
            print(f'ERROR CRÍTICO al procesar IA ({model_filename}): {repr(e)}')
            return pil_image
    def _apply_alpha_postprocess(self, pil_image, smooth_px=0, expand_px=0):
        """\n        Aplica post-procesado al canal alfa de una imagen RGBA:\n          - smooth_px: radio de GaussianBlur sobre el alpha (suaviza bordes).\n          - expand_px: positivo = expande (dilata), negativo = contrae (erosiona).\n        Solo usa Pillow, sin dependencias extra.\n        """
        from PIL import ImageFilter
        try:
            if pil_image.mode != 'RGBA':
                pil_image = pil_image.convert('RGBA')
            r, g, b, alpha = pil_image.split()
            if expand_px != 0:
                size = abs(expand_px) * 2 + 1
                if expand_px > 0:
                    alpha = alpha.filter(ImageFilter.MaxFilter(size))
                else:
                    alpha = alpha.filter(ImageFilter.MinFilter(size))
            if smooth_px > 0:
                alpha = alpha.filter(ImageFilter.GaussianBlur(radius=smooth_px))
            pil_image = Image.merge('RGBA', (r, g, b, alpha))
            return pil_image
        except Exception as e:
            print(f'ADVERTENCIA: Error en post-procesado de bordes: {e}')
            return pil_image
    def convert_file(self, input_path, output_path, options, page_number=None, progress_callback=None, cancellation_event=None):
        """\n        Convierte un archivo de imagen al formato especificado.\n        \n        Args:\n            input_path (str): Ruta del archivo de entrada\n            output_path (str): Ruta del archivo de salida\n            page_number (int, optional): La página específica a procesar\n            options (dict): Diccionario con opciones de conversión:\n                - format: str - Formato de salida (\"PNG\", \"JPG\", \"WEBP\", etc.)\n                - png_transparency: bool\n                - png_compression: int (0-9)\n                - jpg_quality: int (1-100)\n                - jpg_subsampling: str\n                - jpg_progressive: bool\n                - webp_lossless: bool\n                - webp_quality: int (1-100)\n                - webp_transparency: bool\n                - webp_metadata: bool\n                - pdf_combine: bool (manejado fuera)\n                - tiff_compression: str\n                - tiff_transparency: bool\n                - ico_sizes: list[int]\n                - bmp_rle: bool\n                - resize_enabled: bool (si está activo el escalado)\n                - resize_width: int (ancho objetivo)\n                - resize_height: int (alto objetivo)\n                - resize_maintain_aspect: bool (mantener proporción)\n                - interpolation_method: str (método de interpolación para raster)\n                - canvas_enabled: bool (si está activo el canvas)\n                - canvas_width: int (ancho del canvas)\n                - canvas_height: int (alto del canvas)\n                - canvas_margin: int (margen interno en píxeles)\n                - canvas_position: str (posición del contenido)\n                - canvas_overflow_mode: str (qué hacer si imagen > espacio disponible)\n        \n        Returns:\n            bool: True si la conversión fue exitosa\n        """
        try:
            if progress_callback:
                progress_callback(5)
            input_ext = os.path.splitext(input_path)[1].lower()
            output_format = options.get('format', 'PNG').upper()
            resize_enabled = options.get('resize_enabled', False)
            target_size = None
            maintain_aspect = True
            if resize_enabled:
                target_width = options.get('resize_width')
                target_height = options.get('resize_height')
                maintain_aspect = options.get('resize_maintain_aspect', True)
                if target_width and target_height:
                        target_size = (int(target_width), int(target_height))
            if cancellation_event and cancellation_event.is_set():
                raise UserCancelledError('Cancelado por usuario')
            else:
                pil_image = self._load_image(input_path, input_ext, target_size, maintain_aspect, options, page_number=page_number)
                if not pil_image:
                    raise Exception(f'No se pudo cargar la imagen desde {input_path}')
                else:
                    if progress_callback:
                        progress_callback(30)
                    if cancellation_event and cancellation_event.is_set():
                        raise UserCancelledError('Cancelado por usuario')
                    else:
                        if resize_enabled and target_size and (input_ext not in self.VECTOR_FORMATS):
                                    pil_image = self._resize_raster_image(pil_image, target_size, maintain_aspect, options)
                        if progress_callback:
                            progress_callback(40)
                        if cancellation_event and cancellation_event.is_set():
                            raise UserCancelledError('Cancelado por usuario')
                        else:
                            if options.get('rembg_enabled', False):
                                model_name = options.get('rembg_model', 'u2netp')
                                use_gpu = options.get('rembg_gpu', True)
                                print(f"INFO: Eliminando fondo con IA ({model_name} en {('GPU' if use_gpu else 'CPU')})...")
                                if progress_callback:
                                    progress_callback(45, f"Preparando IA ({('GPU' if use_gpu else 'CPU')})...")
                                pil_image = self.remove_background(pil_image, model_name, progress_callback, use_gpu=use_gpu)
                                edge_smooth = options.get('rembg_edge_smooth', 0)
                                edge_expand = options.get('rembg_edge_expand', 0)
                                if edge_smooth != 0 or edge_expand != 0:
                                    pil_image = self._apply_alpha_postprocess(pil_image, edge_smooth, edge_expand)
                                if progress_callback:
                                    progress_callback(80)
                            if cancellation_event and cancellation_event.is_set():
                                raise UserCancelledError('Cancelado por usuario')
                            else:
                                if options.get('upscale_enabled', False):
                                    print('INFO: Iniciando reescalado con IA...')
                                    if progress_callback:
                                        progress_callback(50, f"Reescalando ({options['upscale_engine']})...")
                                    input_path_override = None
                                    input_ext = os.path.splitext(input_path)[1].lower()
                                    if not options.get('rembg_enabled', False) and input_ext in ['.jpg', '.jpeg', '.png']:
                                            input_path_override = input_path
                                    pil_image = self._upscale_image_ai(pil_image, options, cancellation_event, input_path_override, progress_callback)
                                    if progress_callback:
                                        progress_callback(60)
                                if cancellation_event and cancellation_event.is_set():
                                    raise UserCancelledError('Cancelado por usuario')
                                else:
                                    canvas_enabled = options.get('canvas_enabled', False)
                                    if canvas_enabled:
                                        canvas_option = options.get('canvas_option', 'Sin ajuste')
                                        if canvas_option != 'Sin ajuste':
                                            pil_image = self._apply_canvas_by_option(pil_image, canvas_option, options)
                                    background_enabled = options.get('background_enabled', False)
                                    if background_enabled:
                                        pil_image = self._apply_background(pil_image, options)
                                    if progress_callback:
                                        progress_callback(85)
                                    if output_format == 'NO CONVERTIR':
                                        input_ext = os.path.splitext(input_path)[1].lower()
                                        if input_ext in self.RASTER_FORMATS:
                                            if input_ext in ['.jpg', '.jpeg']:
                                                self._save_as_jpg(pil_image, output_path, options)
                                            else:
                                                if input_ext == '.png':
                                                    self._save_as_png(pil_image, output_path, options)
                                                else:
                                                    if input_ext == '.webp':
                                                        self._save_as_webp(pil_image, output_path, options)
                                                    else:
                                                        if input_ext in ['.tiff', '.tif']:
                                                            self._save_as_tiff(pil_image, output_path, options)
                                                        else:
                                                            if input_ext == '.bmp':
                                                                self._save_as_bmp(pil_image, output_path, options)
                                                            else:
                                                                pil_image.save(output_path)
                                        else:
                                            self._save_as_png(pil_image, output_path, options)
                                    else:
                                        if output_format == 'PNG':
                                            self._save_as_png(pil_image, output_path, options)
                                        else:
                                            if output_format in ['JPG', 'JPEG']:
                                                self._save_as_jpg(pil_image, output_path, options)
                                            else:
                                                if output_format == 'WEBP':
                                                    self._save_as_webp(pil_image, output_path, options)
                                                else:
                                                    if output_format == 'AVIF':
                                                        self._save_as_avif(pil_image, output_path, options)
                                                    else:
                                                        if output_format == 'PDF':
                                                            self._save_as_pdf(pil_image, output_path, options)
                                                        else:
                                                            if output_format == 'TIFF':
                                                                self._save_as_tiff(pil_image, output_path, options)
                                                            else:
                                                                if output_format == 'ICO':
                                                                    self._save_as_ico(pil_image, output_path, options)
                                                                else:
                                                                    if output_format == 'BMP':
                                                                        self._save_as_bmp(pil_image, output_path, options)
                                                                    else:
                                                                        raise Exception(f'Formato de salida no soportado: {output_format}')
                                    if progress_callback:
                                        progress_callback(100)
        except UserCancelledError:
            print(f'INFO: Conversión cancelada para {input_path}')
            return False
        except Exception as e:
            print(f'ERROR: Fallo la conversión de {input_path}: {e}')
            return False
        else:
            return True
    def _load_raw_with_rawpy(self, filepath):
        """\n        Revela archivos RAW usando rawpy (LibRaw).\n        ✅ CORREGIDO: Gamma y espacio de color correctos para PNG.\n        """
        try:
            import rawpy
            import numpy as np
            print(f'INFO: Revelando RAW de alta calidad: {os.path.basename(filepath)}')
            with rawpy.imread(filepath) as raw:
                rgb = raw.postprocess(use_camera_wb=True, half_size=False, no_auto_bright=False, output_bps=8, output_color=rawpy.ColorSpace.sRGB, demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD, use_auto_wb=False, gamma=(2.222, 4.5), bright=1.0, highlight_mode=rawpy.HighlightMode.Blend)
            img = Image.fromarray(rgb)
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except:
                pass
            print(f'✅ RAW revelado: {img.size[0]}x{img.size[1]} píxeles')
            return img
        except ImportError:
            raise Exception('❌ rawpy no está instalado.\n\nEjecuta en tu terminal:\npip install rawpy imageio\n\nO descarga desde: https://pypi.org/project/rawpy/')
        except rawpy.LibRawFileUnsupportedError:
            raise Exception(f'Formato RAW no soportado por LibRaw: {os.path.splitext(filepath)[1]}')
        except rawpy.LibRawIOError:
            raise Exception('Archivo RAW corrupto o inaccesible')
        except Exception as e:
            raise Exception(f'Error al revelar RAW: {e}')
    def _load_image(self, filepath, ext, target_size=None, maintain_aspect=True,
                    options=None, page_number=None):
        """
        Carga una imagen desde cualquier formato soportado.
        🔧 MEJORADO: Manejo robusto de errores para SVG y PNG corruptos
        """
        original_path = os.environ.get('PATH', '')
        if options is None:
            options = {}

        # Ensure extension has a dot
        if not ext.startswith('.'):
            ext = '.' + ext

        # ---------- RAW formats ----------
        if ext.upper() in IMAGE_RAW_FORMATS:   # IMAGE_RAW_FORMATS should be defined globally
            try:
                return self._load_raw_with_rawpy(filepath)
            finally:
                os.environ['PATH'] = original_path   # restore PATH even if raw loading fails

        # ---------- RASTER formats (PNG, JPG, etc.) ----------
        if ext in self.RASTER_FORMATS or ext in self.OTHER_FORMATS:
            try:
                # Increase max text chunk for PNG metadata
                PngImagePlugin.MAX_TEXT_CHUNK = 10485760
                return Image.open(filepath)
            except Exception as e:
                print(f'ADVERTENCIA: Error al cargar {os.path.basename(filepath)}: {e}')
                print('  → Intentando carga sin verificación de metadatos...')
                try:
                    img = Image.open(filepath)
                    img.load()   # force decode
                    return img
                except Exception as e2:
                    raise Exception(f'No se pudo cargar la imagen raster: {e2}')

        # ---------- SVG ----------
        if ext == '.svg' and CAN_SVG:   # CAN_SVG should be defined
            fixed_svg_path = self._fix_svg_attributes(filepath)
            svg_to_use = fixed_svg_path if fixed_svg_path else filepath
            is_no_convert = options.get('format', 'PNG') == 'NO CONVERTIR'

            try:
                if target_size and (not is_no_convert):
                    width, height = target_size
                    if maintain_aspect:
                        # First render to get original size
                        temp_png_data = cairosvg.svg2png(url=svg_to_use)
                        temp_img = Image.open(io.BytesIO(temp_png_data))
                        original_width, original_height = temp_img.size
                        original_aspect = original_width / original_height
                        target_aspect = width / height

                        if original_aspect > target_aspect:
                            final_width = width
                            final_height = int(width / original_aspect)
                        else:
                            final_height = height
                            final_width = int(height * original_aspect)

                        # Clamp to target bounds
                        if final_width > width:
                            final_width = width
                            final_height = int(width / original_aspect)
                        if final_height > height:
                            final_height = height
                            final_width = int(height * original_aspect)

                        print(f'SVG escalado: {original_width}×{original_height} → {final_width}×{final_height}')
                        png_data = cairosvg.svg2png(url=svg_to_use,
                                                    output_width=final_width,
                                                    output_height=final_height)
                    else:
                        png_data = cairosvg.svg2png(url=svg_to_use,
                                                    output_width=width,
                                                    output_height=height)
                else:
                    png_data = cairosvg.svg2png(url=svg_to_use)

                return Image.open(io.BytesIO(png_data))

            except (ValueError, TypeError) as e:
                # CairoSVG failed – fallback to Inkscape
                print(f'DEBUG: CairoSVG falló para {os.path.basename(filepath)}: {e}')
                print('  → Usando Inkscape como fallback...')
                try:
                    if fixed_svg_path and os.path.exists(fixed_svg_path):
                        os.remove(fixed_svg_path)
                except:
                    pass
                return self._convert_with_inkscape(filepath, target_size, maintain_aspect,
                                                   page_number, options)

            except Exception as e:
                # Any other SVG error – try Inkscape as last resort
                print(f'ERROR: Fallo completo en SVG {os.path.basename(filepath)}: {e}')
                print('  → Intentando Inkscape como último recurso...')
                try:
                    if fixed_svg_path and os.path.exists(fixed_svg_path):
                        os.remove(fixed_svg_path)
                except:
                    pass
                return self._convert_with_inkscape(filepath, target_size, maintain_aspect,
                                                   page_number, options)

            finally:
                # Clean up temporary fixed SVG file (if it exists and wasn't removed earlier)
                if fixed_svg_path and os.path.exists(fixed_svg_path):
                    try:
                        os.remove(fixed_svg_path)
                    except:
                        pass

        # ---------- VECTOR formats (AI, EPS, PS) ----------
        if ext in self.VECTOR_FORMATS:
            if ext in ['.ai', '.eps', '.ps']:
                if self.inkscape_service and self.inkscape_service.is_available():
                    return self._convert_with_inkscape(filepath, target_size, maintain_aspect,
                                                       page_number, options)
                else:
                    # Inkscape not available – try native fallbacks
                    try:
                        if ext in ('.eps', '.ps'):
                            return self._convert_eps_native(filepath, page_number,
                                                            target_size, maintain_aspect, options)
                        else:
                            # probably AI or other
                            return self._convert_pdf_ai_native(filepath, page_number,
                                                               target_size, maintain_aspect, options)
                    except Exception:
                        # If native fails, re-raise a meaningful error
                        raise Exception(f'No se pudo convertir {ext} sin Inkscape')

        # ---------- PDF (if supported) ----------
        if ext == '.pdf' and CAN_PDF:   # CAN_PDF should be defined
            return self._convert_pdf_ai_native(filepath, page_number, target_size,
                                               maintain_aspect, options)

        # ---------- Fallback: try to open as generic image ----------
        try:
            return Image.open(filepath)
        except Exception as e:
            raise Exception(f'No se pudo cargar la imagen: {e}')
        finally:
            # Restore original PATH after all operations
            os.environ['PATH'] = original_path
            os.environ['PATH'] = '_Node__children'
    def _load_eps_with_pillow(self, filepath, target_size=None):
        """Respaldo: Carga EPS calculando la escala exacta para HD/4K."""
        try:
            img = Image.open(filepath)
            base_width, base_height = img.size
            scale = 4
            if target_size and base_width > 0 and (base_height > 0):
                        target_w, target_h = target_size
                        scale_x = target_w / base_width
                        scale_y = target_h / base_height
                        required_scale = max(scale_x, scale_y) * 1.2
                        scale = int(max(1, round(required_scale)))
                        if scale > 50:
                            scale = 50
            print(f'DEBUG: Renderizando EPS con escala x{scale} para alcanzar objetivo.')
            img.load(scale=scale)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            bg = Image.new(img.mode, img.size, (255, 255, 255, 0))
            diff = ImageChops.difference(img, bg)
            bbox = diff.getbbox()
            if bbox:
                img = img.crop(bbox)
            return img
        except Exception as e:
            raise Exception(f'Fallo total (Inkscape y Pillow): {e}')
    def _convert_with_inkscape(self, filepath, target_size=None, maintain_aspect=True,page_number=1, options=None):
        """
        Convierte un archivo vectorial (EPS, PS, AI, PDF, SVG) a imagen raster.
        Usa Ghostscript para EPS/PS → PDF, luego Inkscape o motor nativo.
        """
        if options is None:
            options = {}

        ext = os.path.splitext(filepath)[1].lower()
        temp_pdf_path = None

        # ---------- EPS/PS → PDF via Ghostscript ----------
        if ext in ['.eps', '.ps']:
            if not self.gs_exe or not os.path.exists(self.gs_exe):
                error_msg = f'Ghostscript no disponible. gs_exe={self.gs_exe}'
                print(f'ERROR: {error_msg}')
                raise Exception(error_msg)

            # Create temporary PDF file
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_pdf.close()
            temp_pdf_path = temp_pdf.name

            print(f'DEBUG: Convirtiendo {ext.upper()} a PDF temporal con Ghostscript...')
            print(f'DEBUG: Usando Ghostscript: {self.gs_exe}')

            gs_cmd = [
                self.gs_exe,
                '-dNOPAUSE', '-dBATCH', '-dSAFER',
                '-sDEVICE=pdfwrite',
                '-dEPSCrop',
                f'-sOutputFile={temp_pdf_path}',
                filepath
            ]
            print(f"DEBUG: Comando GS: {' '.join(gs_cmd)}")

            try:
                result = subprocess.run(
                    gs_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if result.returncode != 0:
                    stderr = result.stderr.decode('utf-8', errors='ignore')
                    raise Exception(f'Ghostscript falló (código {result.returncode}): {stderr[:300]}')

                if not os.path.exists(temp_pdf_path):
                    raise Exception('Ghostscript no generó archivo de salida')

                pdf_size = os.path.getsize(temp_pdf_path)
                if pdf_size == 0:
                    raise Exception('Ghostscript generó un PDF vacío')

                print(f'✅ PDF temporal creado: {temp_pdf_path} ({pdf_size} bytes)')
                filepath = temp_pdf_path   # use the PDF for further processing
                ext = '.pdf'               # update extension

            except Exception as e:
                print(f'ERROR en Ghostscript: {e}')
                # Clean up temp file before re-raising
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except OSError:
                        pass
                raise e   # re-raise the original exception

        # ---------- Now process the (possibly converted) file ----------
        # Determine which engine to use
        if self.inkscape_service and self.inkscape_service.is_available():
            print(f'DEBUG: Usando Inkscape Externo para {ext}')
            try:
                result = self._convert_with_inkscape_external(
                    filepath, page_number, target_size, maintain_aspect, options
                )
                return result
            finally:
                # Clean up temp PDF if it was created and still exists
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except OSError:
                        pass
        else:
            print(f'DEBUG: Usando motor nativo para {ext}')
            try:
                if ext == '.svg':
                    result = self._convert_svg_native(filepath, target_size, maintain_aspect)
                elif ext in ['.ai', '.pdf']:
                    result = self._convert_pdf_ai_native(
                        filepath, page_number, target_size, maintain_aspect, options
                    )
                elif ext in ['.eps', '.ps']:
                    result = self._convert_eps_native(
                        filepath, page_number, target_size, maintain_aspect, options
                    )
                else:
                    raise Exception(f'Formato vectorial no soportado para motor nativo: {ext}')
                return result
            finally:
                # Clean up temp PDF after native conversion (if any)
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except OSError:
                        pass
    def _convert_with_inkscape_external(self, filepath, page_number, target_size, maintain_aspect, options):
        """Conversión usando el nuevo servicio de Inkscape."""
        # Crear archivo temporal para la salida PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            temp_png = tmp_file.name

        try:
            ext = os.path.splitext(filepath)[1].lower()
            dpi = options.get('vector_dpi', 300) if ext != '.svg' else 300

            # Usar sesión persistente o comando único
            if hasattr(self.inkscape_service, '_session_process'):
                print(f'DEBUG: [Batch] Usando sesión persistente de Inkscape para {os.path.basename(filepath)}')
                success = self.inkscape_service.convert_batch(
                    filepath, temp_png, page_number, dpi, target_size, maintain_aspect
                )
                if not success:
                    raise Exception('Fallo en conversión por lotes de Inkscape.')
            else:
                cmd = self.inkscape_service.build_command(filepath, temp_png, page_number, dpi=dpi)
                if target_size:
                    w, h = target_size
                    # Eliminar cualquier --export-dpi existente
                    cmd = [c for c in cmd if not c.startswith('--export-dpi')]
                    # Insertar argumentos de tamaño
                    cmd.insert(2, f'--export-width={w}')
                    if not maintain_aspect:
                        cmd.insert(3, f'--export-height={h}')
                env = self.inkscape_service.get_env()
                if self.gs_dir:
                    env['PATH'] = f"{self.gs_dir};{env.get('PATH', '')}"
                    env['GS_PROG'] = self.gs_exe

                subprocess.run(
                    cmd, check=True, env=env,
                    cwd=self.inkscape_service.get_cwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            # Verificar que se generó el archivo
            if not os.path.exists(temp_png) or os.path.getsize(temp_png) == 0:
                raise Exception('Inkscape no generó salida.')

            # Cargar la imagen
            img = Image.open(temp_png)
            img.load()
            return img

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_png):
                try:
                    os.remove(temp_png)
                except OSError:
                    pass
    def _convert_svg_native(self, filepath, target_size, maintain_aspect):
        """Conversión nativa de SVG usando CairoSVG."""
        if not CAN_SVG:
            raise Exception('CairoSVG no está instalado.')

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            temp_png = tmp_file.name

        try:
            render_kwargs = {}
            if target_size:
                w, h = target_size
                render_kwargs['output_width'] = w
                if not maintain_aspect:
                    render_kwargs['output_height'] = h

            cairosvg.svg2png(url=filepath, write_to=temp_png, **render_kwargs)

            img = Image.open(temp_png)
            img.load()
            return img

        finally:
            if os.path.exists(temp_png):
                try:
                    os.remove(temp_png)
                except OSError:
                    pass
    def _convert_pdf_ai_native(self, filepath, page_number, target_size, maintain_aspect, options, original_ext=None):
        """Conversión nativa de PDF/AI usando Poppler con soporte real de transparencia."""
        if not CAN_PDF or not self.poppler_path:
            raise Exception('Poppler no está configurado.')
        else:
            ext = original_ext if original_ext else os.path.splitext(filepath)[1].lower()
            print(f'DEBUG: [Render] Iniciando renderizado de {ext}: {os.path.basename(filepath)}')
            if ext == '.pdf':
                use_transparent = options.get('pdf_transparent', False)
            else:
                use_transparent = not options.get('force_background', False)
            dpi = options.get('vector_dpi', 300)
            if target_size:
                dpi = self._calculate_optimal_dpi(filepath, ext, target_size, maintain_aspect)
            print(f'DEBUG: [Render] Parámetros: Transparent={use_transparent}, DPI={dpi}, Size={target_size}')
            images = convert_from_path(filepath, dpi=dpi, first_page=page_number, last_page=page_number, poppler_path=self.poppler_path, transparent=use_transparent, use_pdftocairo=True)
            if not images:
                raise Exception('Poppler no pudo renderizar el archivo.')
            else:
                img = images[0]
                if not use_transparent:
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        bg.paste(img, (0, 0), img)
                    else:
                        bg.paste(img, (0, 0))
                    img = bg
                else:
                    img = img.convert('RGBA')
                if target_size:
                    if not maintain_aspect:
                        img = img.resize(target_size, Image.Resampling.LANCZOS)
                    else:
                        img.thumbnail(target_size, Image.Resampling.LANCZOS)
                return img
    def _convert_eps_native(self, filepath, page_number, target_size, maintain_aspect, options):
        """Conversión nativa de EPS/PS usando Ghostscript + Poppler."""
        if not self.gs_exe:
            raise Exception('Ghostscript no está instalado (necesario para EPS).')

        # Crear PDF temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            temp_pdf = tmp_pdf.name

        try:
            # Convertir EPS/PS a PDF con Ghostscript
            gs_cmd = [
                self.gs_exe,
                '-q', '-dNOPAUSE', '-dBATCH',
                '-sDEVICE=pdfwrite',
                '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/prepress',
                f'-sOutputFile={temp_pdf}',
                '-dEPSCrop',
                filepath
            ]
            print(f"DEBUG: Ejecutando Ghostscript para EPS transparente: {' '.join(gs_cmd)}")
            subprocess.run(
                gs_cmd,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Convertir el PDF resultante usando el método nativo para PDF
            return self._convert_pdf_ai_native(
                temp_pdf, page_number, target_size, maintain_aspect,
                options, original_ext='.eps'
            )

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except OSError:
                    pass
    def _fix_svg_attributes(self, svg_path):
        """
        Lee un SVG y corrige atributos width/height inválidos.
        🔧 MEJORADO: Maneja casos más complejos como height="px" sin número
        """
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            svg_tag_pattern = '<svg([^>]*)>'
            match = re.search(svg_tag_pattern, svg_content, re.IGNORECASE)
            if not match:
                return None

            svg_attributes = match.group(1)
            needs_fix = False
            fixed_attributes = svg_attributes

            # Corregir atributos con valores inválidos (px vacío, cadena vacía, etc.)
            simple_patterns = [
                ('width\\s*=\\s*"px"', 'width="180"'),
                ('width\\s*=\\s*""', 'width="180"'),
                ('width\\s*=\\s*"\\s*px\\s*"', 'width="180"'),
                ('height\\s*=\\s*"px"', 'height="180"'),
                ('height\\s*=\\s*""', 'height="180"'),
                ('height\\s*=\\s*"\\s*px\\s*"', 'height="180"')
            ]
            for pattern, replacement in simple_patterns:
                if re.search(pattern, fixed_attributes, re.IGNORECASE):
                    fixed_attributes = re.sub(pattern, replacement, fixed_attributes, flags=re.IGNORECASE)
                    needs_fix = True

            # Corregir width="123px" -> width="123"
            def clean_px_width(match):
                value = match.group(0).split('"')[1]
                value_clean = value.replace('px', '').strip()
                return f'width="{value_clean}"'

            def clean_px_height(match):
                value = match.group(0).split('"')[1]
                value_clean = value.replace('px', '').strip()
                return f'height="{value_clean}"'

            if re.search('width\\s*=\\s*"\\d+px"', fixed_attributes, re.IGNORECASE):
                fixed_attributes = re.sub('width\\s*=\\s*"\\d+px"', clean_px_width, fixed_attributes, flags=re.IGNORECASE)
                needs_fix = True

            if re.search('height\\s*=\\s*"\\d+px"', fixed_attributes, re.IGNORECASE):
                fixed_attributes = re.sub('height\\s*=\\s*"\\d+px"', clean_px_height, fixed_attributes, flags=re.IGNORECASE)
                needs_fix = True

            if not needs_fix:
                return None

            # Reescribir el SVG con los atributos corregidos
            fixed_svg_content = re.sub(svg_tag_pattern, f'<svg{fixed_attributes}>', svg_content, count=1, flags=re.IGNORECASE)

            # Guardar en un archivo temporal
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8')
            temp_file.write(fixed_svg_content)
            temp_file.close()
            print(f'DEBUG: ✅ SVG corregido guardado: {temp_file.name}')
            return temp_file.name

        except Exception as e:
            print(f'ADVERTENCIA: No se pudo preprocesar el SVG: {e}')
            return None
    def _quote_path_if_needed(self, path):
        """Envuelve la ruta en comillas si contiene espacios (solo para debugging)."""
        if ' ' in path and (not path.startswith('\"')):
            return f'\"{path}\"'
        else:
            return path
    def _save_as_png(self, img, output_path, options):
        """Guarda como PNG con opciones optimizadas para imágenes grandes."""
        try:
            if options.get('png_transparency', True) and img.mode in ['RGBA', 'LA', 'PA']:
                save_img = img
            else:
                save_img = img.convert('RGB')
            compression = options.get('png_compression', 6)
            width, height = save_img.size
            total_pixels = width * height
            is_huge_image = total_pixels > 8294400
            use_optimize = True
            if is_huge_image:
                print(f'DEBUG: Imagen gigante detectada ({width}x{height}). Optimizando velocidad de guardado...')
                use_optimize = False
                if compression > 3:
                    print(f'DEBUG: Reduciendo compresión de {compression} a 3 para velocidad.')
                    compression = 3
            save_img.save(output_path, 'PNG', compress_level=compression, optimize=use_optimize)
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f'ERROR al guardar PNG: {e}')
    def _save_as_jpg(self, img, output_path, options):
        """Guarda como JPG con opciones."""
        if img.mode in ['RGBA', 'LA', 'PA']:
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            save_img = background
        else:
            save_img = img.convert('RGB')
        quality = options.get('jpg_quality', 90)
        subsampling_map = {'4:2:0 (Estándar)': '4:2:0', '4:2:2 (Alta)': '4:2:2', '4:4:4 (Máxima)': '4:4:4'}
        subsampling_str = options.get('jpg_subsampling', '4:2:0 (Estándar)')
        subsampling = subsampling_map.get(subsampling_str, '4:2:0')
        progressive = options.get('jpg_progressive', False)
        save_img.save(output_path, 'JPEG', quality=quality, subsampling=subsampling, progressive=progressive, optimize=True)
        try:
            temp_img = Image.open(output_path)
            temp_img.load()
            temp_img.save(output_path, 'JPEG', quality=quality, subsampling=subsampling, progressive=progressive, optimize=True)
            temp_img.close()
            print(f'✅ JPG regenerado: {os.path.basename(output_path)}')
        except Exception as e:
            print(f'⚠️ Advertencia al regenerar JPG: {e}')
    def _save_as_webp(self, img, output_path, options):
        """Guarda como WEBP con opciones."""
        try:
            if options.get('webp_transparency', True) and img.mode in ['RGBA', 'LA', 'PA']:
                save_img = img
            else:
                save_img = img.convert('RGB')
            save_kwargs = {'format': 'WEBP', 'lossless': options.get('webp_lossless', False)}
            if not save_kwargs['lossless']:
                save_kwargs['quality'] = options.get('webp_quality', 90)
            if options.get('webp_metadata', False) and hasattr(img, 'info') and ('exif' in img.info):
                save_kwargs['exif'] = img.info['exif']
            save_img.save(output_path, **save_kwargs)
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            return None
    def _save_as_pdf(self, img, output_path, options):
        """Guarda como PDF."""
        try:
            if img.mode not in ['RGB', 'L']:
                save_img = img.convert('RGB')
            else:
                save_img = img

            if CAN_IMG2PDF:
                # Usar img2pdf para mejor calidad
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    temp_png = tmp_file.name
                try:
                    save_img.save(temp_png, 'PNG')
                    with open(output_path, 'wb') as f:
                        f.write(img2pdf.convert(temp_png))
                finally:
                    if os.path.exists(temp_png):
                        try:
                            os.remove(temp_png)
                        except OSError:
                            pass
            else:
                # Fallback a PIL
                save_img.save(output_path, 'PDF', resolution=100.0)

            # Asegurar que se escriba en disco
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())

        except Exception:
            return None
    def _save_as_tiff(self, img, output_path, options):
        """Guarda como TIFF con opciones."""
        try:
            if options.get('tiff_transparency', True) and img.mode in ['RGBA', 'LA', 'PA']:
                save_img = img
            else:
                save_img = img.convert('RGB')
            compression_map = {
                'Ninguna': None,
                'LZW (Recomendada)': 'tiff_lzw',
                'Deflate (ZIP)': 'tiff_deflate',
                'PackBits': 'packbits'
            }
            compression_str = options.get('tiff_compression', 'LZW (Recomendada)')
            compression = compression_map.get(compression_str)
            save_kwargs = {'format': 'TIFF'}
            if compression:
                save_kwargs['compression'] = compression
            save_img.save(output_path, **save_kwargs)
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            return None
    def _save_as_ico(self, img, output_path, options):
        """Guarda como ICO con múltiples tamaños."""
        try:
            if img.mode != 'RGBA':
                save_img = img.convert('RGBA')
            else:
                save_img = img
            ico_sizes_dict = options.get('ico_sizes', {})
            selected_sizes = [size for size, selected in ico_sizes_dict.items() if selected]
            if not selected_sizes:
                selected_sizes = [32, 256]
            sizes_list = [(size, size) for size in selected_sizes]
            save_img.save(output_path, 'ICO', sizes=sizes_list)
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            return None
    def _save_as_bmp(self, img, output_path, options):
        """Guarda como BMP con opciones."""
        try:
            if img.mode in ['RGBA', 'LA', 'PA']:
                save_img = img.convert('RGB')
            else:
                save_img = img.convert('RGB')
            save_img.save(output_path, 'BMP')
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            return None
    def _calculate_optimal_dpi(self, filepath, ext, target_size, maintain_aspect):
        """\n        Calcula el DPI óptimo para rasterizar un vector al tamaño objetivo sondeando sus dimensiones reales.\n        """
        target_width, target_height = target_size
        doc_width_pts = 612
        doc_height_pts = 792
        try:
            import re
            if ext in ['.pdf', '.ai']:
                info = pdfinfo_from_path(filepath, poppler_path=self.poppler_path)
                page_size = info.get('Page size', '')
                match = re.search('([\\d.]+)\\s*x\\s*([\\d.]+)', page_size)
                if match:
                    doc_width_pts = float(match.group(1))
                    doc_height_pts = float(match.group(2))
            else:
                if ext in ['.eps', '.ps']:
                    found_bbox = False
                    with open(filepath, 'rb') as f:
                        header = f.read(16384).decode('latin-1', errors='ignore')
                        match = re.search('%%HiResBoundingBox:\\s*([\\d.-]+)\\s+([\\d.-]+)\\s+([\\d.-]+)\\s+([\\d.-]+)', header)
                        if not match:
                            match = re.search('%%BoundingBox:\\s*([\\d.-]+)\\s+([\\d.-]+)\\s+([\\d.-]+)\\s+([\\d.-]+)', header)
                        if match:
                            x1, y1, x2, y2 = map(float, match.groups())
                            doc_width_pts = abs(x2 - x1)
                            doc_height_pts = abs(y2 - y1)
                            found_bbox = True
                    if not found_bbox and self.gs_exe:
                            print(f'DEBUG: [Render] BBox no encontrado en cabecera. Usando Ghostscript para sondear: {ext}')
                            try:
                                gs_cmd = [self.gs_exe, '-q', '-dBATCH', '-dNOPAUSE', '-sDEVICE=bbox', filepath]
                                result = subprocess.run(gs_cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                                bbox_info = result.stderr
                                match = re.search('%%HiResBoundingBox:\\s*([\\d.-]+)\\s+([\\d.-]+)\\s+([\\d.-]+)\\s+([\\d.-]+)', bbox_info)
                                if match:
                                    x1, y1, x2, y2 = map(float, match.groups())
                                    doc_width_pts = abs(x2 - x1)
                                    doc_height_pts = abs(y2 - y1)
                                    print(f'DEBUG: [Render] GS detectó BBox: {doc_width_pts}x{doc_height_pts} pts')
                            except Exception as ge:
                                print(f'DEBUG: [Render] Ghostscript falló al sondear BBox: {ge}')
        except Exception as e:
            print(f'DEBUG: [Render] No se pudo obtener dimensiones reales de {ext} ({e}). Usando default 8.5x11.')
        doc_width_inches = max(0.1, doc_width_pts / 72.0)
        doc_height_inches = max(0.1, doc_height_pts / 72.0)
        dpi_width = target_width / doc_width_inches
        dpi_height = target_height / doc_height_inches
        if maintain_aspect:
            optimal_dpi = min(dpi_width, dpi_height)
        else:
            optimal_dpi = max(dpi_width, dpi_height)
        optimal_dpi = max(72, min(optimal_dpi, 4800))
        print(f'DEBUG: Vector {doc_width_pts:.0f}x{doc_height_pts:.0f} pts -> DPI óptimo: {optimal_dpi:.0f}')
        return int(optimal_dpi)
    def _resize_raster_image(self, img, target_size, maintain_aspect, options):
        """\n        Reescala una imagen raster usando el método de interpolación especificado.\n        """
        from PIL import Image as PILImage
        target_width, target_height = target_size
        original_width, original_height = img.size
        interp_method_name = options.get('interpolation_method', 'Lanczos (Mejor Calidad)')
        method_map = {'LANCZOS': PILImage.Resampling.LANCZOS, 'BICUBIC': PILImage.Resampling.BICUBIC, 'BILINEAR': PILImage.Resampling.BILINEAR, 'NEAREST': PILImage.Resampling.NEAREST}
        from src.core.constants import INTERPOLATION_METHODS
        method_key = INTERPOLATION_METHODS.get(interp_method_name, 'LANCZOS')
        resampling = method_map.get(method_key, PILImage.Resampling.LANCZOS)
        if maintain_aspect:
            original_aspect = original_width / original_height
            target_aspect = target_width / target_height
            if original_aspect > target_aspect:
                new_width = target_width
                new_height = int(target_width / original_aspect)
            else:
                new_height = target_height
                new_width = int(target_height * original_aspect)
            if new_width > target_width:
                new_width = target_width
                new_height = int(target_width / original_aspect)
            if new_height > target_height:
                new_height = target_height
                new_width = int(target_height * original_aspect)
            return img.resize((new_width, new_height), resampling)
        else:
            return img.resize((target_width, target_height), resampling)
    def validate_target_size(self, target_size):
        """\n        Valida el tamaño objetivo y retorna warnings si es necesario.\n        Returns: (is_safe, warning_message)\n        """
        from src.core.constants import MAX_RECOMMENDED_DPI, MAX_SAFE_DIMENSION, CRITICAL_DPI_THRESHOLD, CRITICAL_DIMENSION_THRESHOLD
        width, height = target_size
        max_dimension = max(width, height)
        if max_dimension > CRITICAL_DIMENSION_THRESHOLD:
            return (False, f'⚠️ ADVERTENCIA: Resolución muy alta ({width}×{height}).\n\nEsto puede causar:\n• Consumo excesivo de RAM (>4GB)\n• Posible crasheo de la aplicación\n• Tiempo de procesamiento muy largo\n\nRecomendación: Usar máximo {CRITICAL_DIMENSION_THRESHOLD}×{CRITICAL_DIMENSION_THRESHOLD}.')
        else:
            if max_dimension > MAX_SAFE_DIMENSION:
                return (True, f'⚠️ Resolución alta ({width}×{height}).\n\nPuede requerir bastante RAM.\nTiempo estimado: 30s-2min por archivo.\n\n¿Continuar?')
            else:
                return (True, None)
    def _apply_canvas_by_option(self, img, canvas_option, options):
        """\n        Aplica canvas según la opción seleccionada.\n        ✅ CORREGIDO: Mantiene transparencia correctamente.\n        """
        from PIL import Image as PILImage
        from src.core.constants import CANVAS_PRESET_SIZES
        img_width, img_height = img.size
        if img.mode != 'RGBA':
            print(f'DEBUG: Convirtiendo imagen de {img.mode} a RGBA para canvas')
            img = img.convert('RGBA')
        if canvas_option == 'Añadir Margen Externo':
            margin = options.get('canvas_margin', 100)
            canvas_width = img_width + margin * 2
            canvas_height = img_height + margin * 2
            print(f'Margen Externo: Canvas expandido a {canvas_width}×{canvas_height} (margen: {margin}px)')
        else:
            if canvas_option == 'Añadir Margen Interno':
                margin = options.get('canvas_margin', 100)
                canvas_width = img_width
                canvas_height = img_height
                new_width = max(1, img_width - margin * 2)
                new_height = max(1, img_height - margin * 2)
                if new_width < img_width or new_height < img_height:
                    img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                    img_width, img_height = (new_width, new_height)
                    print(f'Margen Interno: Imagen reducida a {new_width}×{new_height} (margen: {margin}px)')
                else:
                    print(f'ADVERTENCIA: Margen interno ({margin}px) demasiado grande, imagen no reducida')
            else:
                if canvas_option in CANVAS_PRESET_SIZES:
                    canvas_width, canvas_height = CANVAS_PRESET_SIZES[canvas_option]
                    print(f'Preset aplicado: Canvas {canvas_width}×{canvas_height}')
                else:
                    if canvas_option == 'Personalizado...':
                        canvas_width = int(options.get('canvas_width', img_width))
                        canvas_height = int(options.get('canvas_height', img_height))
                        print(f'Canvas personalizado: {canvas_width}×{canvas_height}')
                    else:
                        return img
        if canvas_option not in ['Añadir Margen Externo', 'Añadir Margen Interno']:
            exceeds_canvas = img_width > canvas_width or img_height > canvas_height
            if exceeds_canvas:
                overflow_mode = options.get('canvas_overflow_mode', 'Centrar (puede recortar)')
                if overflow_mode == 'Advertir y no procesar':
                    raise Exception(f'La imagen ({img_width}×{img_height}) excede el canvas ({canvas_width}×{canvas_height}). Activa \'Cambiar Tamaño\' para escalar primero.')
                else:
                    if overflow_mode == 'Reducir hasta que quepa':
                        scale_w = canvas_width / img_width
                        scale_h = canvas_height / img_height
                        scale = min(scale_w, scale_h)
                        new_w = int(img_width * scale)
                        new_h = int(img_height * scale)
                        img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
                        img_width, img_height = (new_w, new_h)
                        print(f'Imagen escalada manteniendo aspecto: {new_w}×{new_h}')
                    else:
                        if overflow_mode in ['Recortar al canvas', 'Centrar (puede recortar)']:
                            left = max(0, (img_width - canvas_width) // 2)
                            top = max(0, (img_height - canvas_height) // 2)
                            right = left + canvas_width
                            bottom = top + canvas_height
                            img = img.crop((left, top, right, bottom))
                            img_width, img_height = img.size
                            print(f'Imagen recortada a {img_width}×{img_height} para ajustar al canvas')
        print(f'DEBUG: Creando canvas RGBA transparente de {canvas_width}×{canvas_height}')
        canvas = PILImage.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
        position = options.get('canvas_position', 'Centro')
        x, y = self._calculate_canvas_position(canvas_width, canvas_height, img_width, img_height, position)
        print(f'DEBUG: Pegando imagen RGBA en posición ({x}, {y})')
        canvas.paste(img, (x, y), img)
        print(f'Canvas final: {canvas_width}×{canvas_height} con imagen {img_width}×{img_height} en posición {position}')
        print(f'✅ Modo del canvas resultante: {canvas.mode}')
        return canvas
    def _calculate_canvas_position(self, canvas_w, canvas_h, img_w, img_h, position):
        """\n        Calcula las coordenadas X,Y para colocar la imagen en el canvas.\n        \n        Args:\n            canvas_w, canvas_h: Dimensiones del canvas\n            img_w, img_h: Dimensiones de la imagen\n            position: str - Posición deseada\n        \n        Returns:\n            (x, y): Coordenadas para pegar la imagen\n        """
        position_map = {'Centro': ('center', 'center'), 'Arriba Izquierda': ('left', 'top'), 'Arriba Centro': ('center', 'top'), 'Arriba Derecha': ('right', 'top'), 'Centro Izquierda': ('left', 'center'), 'Centro Derecha': ('right', 'center'), 'Abajo Izquierda': ('left', 'bottom'), 'Abajo Centro': ('center', 'bottom'), 'Abajo Derecha': ('right', 'bottom')}
        h_align, v_align = position_map.get(position, ('center', 'center'))
        if h_align == 'left':
            x = 0
        else:
            if h_align == 'center':
                x = (canvas_w - img_w) // 2
            else:
                x = canvas_w - img_w
        if v_align == 'top':
            y = 0
        else:
            if v_align == 'center':
                y = (canvas_h - img_h) // 2
            else:
                y = canvas_h - img_h
        return (x, y)
    def _apply_background(self, img, options):
        """\n        Reemplaza el fondo transparente de una imagen con un color, degradado o imagen.\n        \n        Args:\n            img: PIL.Image - Imagen con transparencia\n            options: dict - Opciones de fondo\n        \n        Returns:\n            PIL.Image - Imagen con fondo aplicado\n        """
        from PIL import Image as PILImage, ImageDraw
        if img.mode not in ['RGBA', 'LA', 'PA']:
            print('ADVERTENCIA: La imagen no tiene canal de transparencia, no se aplica fondo')
            return img
        else:
            background_type = options.get('background_type', 'Color Sólido')
            width, height = img.size
            if background_type == 'Color Sólido':
                bg_color_hex = options.get('background_color', '#FFFFFF')
                bg_color = self._hex_to_rgb(bg_color_hex)
                background = PILImage.new('RGB', (width, height), bg_color)
                print(f'Fondo sólido aplicado: {bg_color_hex}')
            else:
                if background_type == 'Degradado':
                    color1_hex = options.get('background_gradient_color1', '#FF0000')
                    color2_hex = options.get('background_gradient_color2', '#0000FF')
                    direction = options.get('background_gradient_direction', 'Horizontal (Izq → Der)')
                    background = self._create_gradient(width, height, color1_hex, color2_hex, direction)
                    print(f'Degradado aplicado: {color1_hex} → {color2_hex} ({direction})')
                else:
                    if background_type == 'Imagen de Fondo':
                        bg_image_path = options.get('background_image_path')
                        if not bg_image_path or not os.path.exists(bg_image_path):
                            print('ADVERTENCIA: Ruta de imagen de fondo no válida, usando blanco')
                            background = PILImage.new('RGB', (width, height), (255, 255, 255))
                        else:
                            try:
                                bg_img = PILImage.open(bg_image_path)
                                background = bg_img.resize((width, height), PILImage.Resampling.LANCZOS)
                                if background.mode != 'RGB':
                                    background = background.convert('RGB')
                                print(f'Imagen de fondo aplicada: {os.path.basename(bg_image_path)}')
                            except Exception as e:
                                print(f'ERROR: No se pudo cargar imagen de fondo: {e}')
                                background = PILImage.new('RGB', (width, height), (255, 255, 255))
                    else:
                        background = PILImage.new('RGB', (width, height), (255, 255, 255))
            background.paste(img, (0, 0), img)
            return background
    def _hex_to_rgb(self, hex_color):
        """Convierte un color hexadecimal (#RRGGBB) a tupla RGB."""
        hex_color = hex_color.lstrip('#')
        try:
            return tuple((int(hex_color[i:i + 2], 16) for i in (0, 2, 4)))
        except:
            print(f'ADVERTENCIA: Color hexadecimal inválido \'{hex_color}\', usando blanco')
            return (255, 255, 255)
    def _create_gradient(self, width, height, color1_hex, color2_hex, direction):
        """\n        Crea un degradado entre dos colores.\n        \n        Args:\n            width, height: Dimensiones de la imagen\n            color1_hex, color2_hex: Colores en formato hexadecimal\n            direction: Dirección del degradado\n        \n        Returns:\n            PIL.Image - Imagen con degradado\n        """
        from PIL import Image as PILImage, ImageDraw
        color1 = self._hex_to_rgb(color1_hex)
        color2 = self._hex_to_rgb(color2_hex)
        base = PILImage.new('RGB', (width, height), color1)
        draw = ImageDraw.Draw(base)
        if direction == 'Horizontal (Izq → Der)':
            for x in range(width):
                ratio = x / width
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                draw.line([(x, 0), (x, height)], fill=(r, g, b))
        else:
            if direction == 'Vertical (Arr → Aba)':
                for y in range(height):
                    ratio = y / height
                    r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                    g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                    b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))
            else:
                if direction == 'Diagonal (↘)':
                    for i in range(width + height):
                        ratio = i / (width + height)
                        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                        draw.line([(0, i), (i, 0)], fill=(r, g, b), width=2)
                else:
                    if direction == 'Diagonal (↙)':
                        for i in range(width + height):
                            ratio = i / (width + height)
                            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                            draw.line([(width, i), (width - i, 0)], fill=(r, g, b), width=2)
                    else:
                        if direction == 'Radial (Centro)':
                            center_x, center_y = (width // 2, height // 2)
                            max_radius = int(((width / 2) ** 2 + (height / 2) ** 2) ** 0.5)
                            for radius in range(max_radius, 0, (-1)):
                                ratio = radius / max_radius
                                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                                draw.ellipse([(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)], fill=(r, g, b))
        return base
    def combine_pdfs(self, pdf_paths, output_path):
        """\n        Combina múltiples PDFs en uno solo.\n        Requiere PyPDF2.\n        """
        try:
            import PyPDF2
            pdf_writer = PyPDF2.PdfWriter()
            for pdf_path in pdf_paths:
                if not os.path.exists(pdf_path):
                    print(f'ADVERTENCIA: {pdf_path} no existe, omitiendo')
                    continue
                else:
                    try:
                        with open(pdf_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            for page_num in range(len(pdf_reader.pages)):
                                pdf_writer.add_page(pdf_reader.pages[page_num])
                    except Exception as e:
                        print(f'ERROR: No se pudo leer {pdf_path}: {e}')
            with open(output_path, 'wb') as f:
                pdf_writer.write(f)
        except ImportError:
            print('ERROR: PyPDF2 no está instalado. No se pueden combinar PDFs.')
            return False
        except Exception as e:
            print(f'ERROR: Falló la combinación de PDFs: {e}')
            return False
        else:
            return True
    def _parse_video_resolution(self, options):
        """Parsea la opción de resolución y devuelve una tupla (width, height)."""
        res_str = options.get('video_resolution', '1920x1080 (1080p)')
        if res_str == 'Personalizado...':
            try:
                width = int(options.get('video_custom_width', '1920'))
                height = int(options.get('video_custom_height', '1080'))
                return (width, height)
            except ValueError:
                return (1920, 1080)
        else:
            try:
                width_str, height_str = res_str.split(' ')[0].split('x')
                return (int(width_str), int(height_str))
            except Exception:
                return (1920, 1080)
    def _create_background_canvas(self, target_size, options):
        """Crea un canvas de fondo con las opciones de \'Cambiar Fondo\'."""
        if not options.get('background_enabled', False):
            return Image.new('RGB', target_size, (0, 0, 0))
        else:
            empty_canvas = Image.new('RGBA', target_size, (0, 0, 0, 0))
            background_canvas = self._apply_background(empty_canvas, options)
            return background_canvas
    def _apply_video_fit_mode(self, fg_image, target_size, fit_mode):
        """\n        Escala la imagen (fg_image) según el modo de ajuste para\n        encajar en el target_size (ej. 1920x1080).\n        """
        from PIL import Image as PILImage
        img_w, img_h = fg_image.size
        target_w, target_h = target_size
        if fit_mode == 'Mantener Tamaño Original':
            return fg_image
        else:
            if fit_mode == 'Ajustar al Fotograma (Barras)':
                ratio = min(target_w / img_w, target_h / img_h)
                if ratio < 1.0:
                    new_w = int(img_w * ratio)
                    new_h = int(img_h * ratio)
                    return fg_image.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
                else:
                    return fg_image
            else:
                if fit_mode == 'Ajustar al Marco (Recortar)':
                    img_aspect = img_w / img_h
                    target_aspect = target_w / target_h
                    if img_aspect > target_aspect:
                        new_h = target_h
                        new_w = int(new_h * img_aspect)
                    else:
                        new_w = target_w
                        new_h = int(new_w / img_aspect)
                    scaled_img = fg_image.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
                    left = (new_w - target_w) / 2
                    top = (new_h - target_h) / 2
                    right = (new_w + target_w) / 2
                    bottom = (new_h + target_h) / 2
                    return scaled_img.crop((left, top, right, bottom))
                else:
                    return fg_image
    def _composite_images(self, bg_canvas, fg_image):
        """\n        Pega la imagen (fg_image) en el centro del lienzo (bg_canvas).\n        """
        canvas_w, canvas_h = bg_canvas.size
        img_w, img_h = fg_image.size
        x = (canvas_w - img_w) // 2
        y = (canvas_h - img_h) // 2
        if fg_image.mode in ['RGBA', 'LA', 'PA']:
            bg_canvas.paste(fg_image, (x, y), fg_image)
        else:
            bg_canvas.paste(fg_image, (x, y))
        return bg_canvas
    def _build_ffmpeg_video_options(self, options, input_fps):
        """Construye el comando de FFmpeg basado en las opciones de la UI."""
        video_format = options.get('format')
        output_fps = options.get('video_fps', '30')
        pre_params = ['-r', str(input_fps)]
        final_params = ['-r', str(output_fps)]
        if video_format == '.mp4 (H.264)':
            final_params.extend(['-c:v', 'libx264', '-pix_fmt', 'yuv420p'])
        else:
            if video_format == '.mov (ProRes)':
                final_params.extend(['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le'])
            else:
                if video_format == '.webm (VP9)':
                    final_params.extend(['-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '30'])
                else:
                    if video_format == '.gif (Animado)':
                        final_params.extend(['-filter_complex', '[0:v] split [a][b];[a] palettegen [p];[b][p] paletteuse'])
                    else:
                        final_params.extend(['-c:v', 'libx264', '-pix_fmt', 'yuv420p'])
        return (pre_params, final_params)
    def create_video_from_images(self, file_data_list, output_path, options, progress_callback, cancellation_event):
        """
        Motor principal para convertir una lista de imágenes a un video.
        ✅ VERSIÓN BLINDADA: Limpieza garantizada y cancelación instantánea.
        """
        if not self.ffmpeg_processor:
            raise Exception('FFmpeg processor no está inicializado.')

        import tempfile
        import shutil
        import threading
        import time
        import os

        temp_frame_dir = None
        try:
            # Crear directorio temporal para frames
            temp_frame_dir = tempfile.mkdtemp(prefix='dowp_frames_')
            print(f'INFO: Creando frames temporales en: {temp_frame_dir}')

            target_size = self._parse_video_resolution(options)
            fit_mode = options.get('video_fit_mode', 'Ajustar al Fotograma (Barras)')
            total_files = len(file_data_list)

            # Procesar cada imagen
            for i, (filepath, page_num) in enumerate(file_data_list):
                if cancellation_event.is_set():
                    raise UserCancelledError('Proceso cancelado por el usuario.')

                base_progress = i / total_files * 100
                step_size = 100 / total_files
                current_pct = base_progress + step_size * 0.1
                progress_callback('Standardizing', current_pct, f'Procesando: {os.path.basename(filepath)}')

                try:
                    bg_canvas = self._create_background_canvas(target_size, options)
                    fg_image = self._load_image(filepath, os.path.splitext(filepath)[1].lower(),
                                                page_number=page_num, options=options)
                    if not fg_image:
                        continue

                    # Remover fondo si está habilitado
                    if options.get('rembg_enabled', False):
                        if cancellation_event.is_set():
                            raise UserCancelledError('Cancelado')
                        current_pct = base_progress + step_size * 0.3
                        model_name = options.get('rembg_model', 'u2netp')
                        use_gpu = options.get('rembg_gpu', True)
                        progress_callback('Standardizing', current_pct,
                                        f"🤖 IA ({'GPU' if use_gpu else 'CPU'}): {os.path.basename(filepath)}")

                        def temp_callback(p, m):
                            progress_callback('Standardizing', current_pct, m)

                        fg_image = self.remove_background(pil_image=fg_image,
                                                        model_filename=model_name,
                                                        progress_callback=temp_callback,
                                                        use_gpu=use_gpu)

                    if cancellation_event.is_set():
                        raise UserCancelledError('Cancelado')

                    current_pct = base_progress + step_size * 0.8
                    progress_callback('Standardizing', current_pct, f'Componiendo: {os.path.basename(filepath)}')
                    scaled_fg_image = self._apply_video_fit_mode(fg_image, target_size, fit_mode)
                    final_frame = self._composite_images(bg_canvas, scaled_fg_image)

                    frame_path = os.path.join(temp_frame_dir, f'frame_{i:06d}.png')
                    final_frame.save(frame_path, 'PNG')

                except UserCancelledError:
                    raise
                except Exception as e:
                    print(f'ERROR: Falló frame {filepath}: {e}')
                    continue

            # Verificar cancelación antes de codificar
            if cancellation_event.is_set():
                raise UserCancelledError('Cancelado antes de codificar.')

            print('INFO: Fase A completada. Iniciando FFmpeg...')

            # Configurar FPS
            try:
                output_fps = int(options.get('video_fps', '30'))
                duration_frames = int(options.get('video_frame_duration', '3'))
                input_fps = output_fps / duration_frames
            except ValueError:
                raise Exception('FPS y Duración deben ser números válidos')

            pre_params, final_params = self._build_ffmpeg_video_options(options, input_fps)
            input_pattern = os.path.join(temp_frame_dir, 'frame_%06d.png')
            ffmpeg_options = {
                'input_file': input_pattern,
                'output_file': output_path,
                'duration': total_files / input_fps,
                'ffmpeg_params': final_params,
                'pre_params': pre_params,
                'mode': 'Video+Audio'
            }

            # Ejecutar FFmpeg
            self.ffmpeg_processor.execute_recode(
                ffmpeg_options,
                lambda p, m: progress_callback('Encoding', p, m),
                cancellation_event
            )

            # Limpieza exitosa (se hará en finally)

        except UserCancelledError as e:
            print(f'DEBUG: Cancelación capturada en create_video_from_images: {e}')
            raise e
        except Exception as e:
            print(f'ERROR en create_video_from_images: {e}')
            raise e
        finally:
            # Limpieza del directorio temporal
            if temp_frame_dir and os.path.exists(temp_frame_dir):
                try:
                    print(f'INFO: Limpiando carpeta temporal de frames: {temp_frame_dir}')
                    shutil.rmtree(temp_frame_dir)
                    print('INFO: Limpieza completada.')
                except Exception as e:
                    print(f'ADVERTENCIA: No se pudo eliminar carpeta temporal inmediatamente: {e}')
                    # Intentar eliminar en un hilo separado después de un retraso
                    def retry_delete():
                        time.sleep(2)
                        if os.path.exists(temp_frame_dir):
                            try:
                                shutil.rmtree(temp_frame_dir)
                                print('INFO: Limpieza diferida completada.')
                            except Exception:
                                pass
                    threading.Thread(target=retry_delete, daemon=True).start()
    def _save_as_avif(self, img, output_path, options):
        """Guarda como AVIF con opciones avanzadas."""
        try:
            if options.get('avif_transparency', True) and img.mode in ['RGBA', 'LA', 'PA']:
                save_img = img
            else:
                save_img = img.convert('RGB')
            save_kwargs = {
                'format': 'AVIF',
                'lossless': options.get('avif_lossless', False),
                'speed': options.get('avif_speed', 6)
            }
            if not save_kwargs['lossless']:
                save_kwargs['quality'] = options.get('avif_quality', 80)
            save_img.save(output_path, **save_kwargs)
            with open(output_path, 'r+b') as f:
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            return None
    def _upscale_image_ai(self, img, options, cancellation_event=None, input_path_override=None, progress_callback=None):
        """
        Ejecuta Real-ESRGAN o Waifu2x nativamente.
        Versión blindada contra errores de variables no definidas.
        """
        import subprocess
        import tempfile
        import multiprocessing
        import queue
        import threading
        import re
        import time
        import os
        from PIL import Image

        temp_input_path = None
        temp_output_path = None
        needs_input_cleanup = False

        try:
            # --- Preparar entrada ---
            if input_path_override and os.path.exists(input_path_override):
                temp_input_path = input_path_override
                needs_input_cleanup = False
            else:
                ext_temp = '.png'
                if img.mode not in ('RGBA', 'LA'):
                    ext_temp = '.jpg'
                with tempfile.NamedTemporaryFile(suffix=ext_temp, delete=False) as temp_in:
                    temp_input_path = temp_in.name
                    needs_input_cleanup = True
                    if ext_temp == '.jpg':
                        img.convert('RGB').save(temp_input_path, 'JPEG', quality=100, subsampling=0)
                    else:
                        img.save(temp_input_path, 'PNG')

            # --- Configuración del motor ---
            engine = options.get('upscale_engine')
            friendly_model = options.get('upscale_model_friendly')
            scale = options.get('upscale_scale', '2')
            tile_size = options.get('upscale_tile', '0') or '0'
            denoise = options.get('upscale_denoise', '0')
            use_tta = options.get('upscale_tta', False)

            # Mapeo de modelos internos
            if 'SRMD' in engine:
                from src.core.constants import SRMD_MODELS
                model_info = SRMD_MODELS.get(friendly_model, {})
                internal_model_name = model_info.get('model', 'models-srmd')
            elif engine == 'Upscayl':
                from src.core.constants import UPSCAYL_MODELS_MAP
                rev_map = {v: k for k, v in UPSCAYL_MODELS_MAP.items()}
                internal_model_name = rev_map.get(friendly_model, friendly_model)
            else:  # Waifu2x
                from src.core.constants import WAIFU2X_MODELS
                model_info = WAIFU2X_MODELS.get(friendly_model, {})
                internal_model_name = model_info.get('model', 'models-cunet')

            # --- Configurar concurrencia ---
            concurrency = options.get('upscale_concurrency', 'Automático')
            if concurrency == 'Seguro (Estabilidad)':
                threads_arg = '1:1:1'
            elif concurrency == 'Equilibrado':
                threads_arg = '1:2:1'
            elif concurrency == 'Máximo (Potente)':
                threads_arg = '2:4:2'
            else:
                cpu_count = multiprocessing.cpu_count()
                if cpu_count >= 8:
                    threads_arg = '2:4:2'
                elif cpu_count >= 4:
                    threads_arg = '1:2:2'
                else:
                    threads_arg = '1:1:1'

            # --- Construir comando ---
            models_root = os.path.join(BIN_DIR, 'models', 'upscaling')  # BIN_DIR debe estar definido
            temp_output_path = os.path.splitext(temp_input_path)[0] + '_out.png'
            cmd = []

            if 'SRMD' in engine:
                exe_path = os.path.join(models_root, 'srmd', 'srmd-ncnn-vulkan.exe')
                full_model_path = os.path.join(models_root, 'srmd', internal_model_name)
                cmd = [exe_path, '-i', temp_input_path, '-o', temp_output_path,
                    '-m', full_model_path, '-n', denoise, '-s', scale,
                    '-t', tile_size, '-f', 'png', '-j', threads_arg]
                if use_tta:
                    cmd.append('-x')
            elif engine == 'Waifu2x':
                exe_path = os.path.join(models_root, 'waifu2x', 'waifu2x-ncnn-vulkan.exe')
                full_model_path = os.path.join(models_root, 'waifu2x', internal_model_name)
                cmd = [exe_path, '-i', temp_input_path, '-o', temp_output_path,
                    '-m', full_model_path, '-n', denoise, '-s', scale,
                    '-t', tile_size, '-f', 'png', '-j', threads_arg]
                if use_tta:
                    cmd.append('-x')
            elif engine == 'Upscayl':
                exe_path = os.path.join(models_root, 'upscayl', 'upscayl-bin.exe')
                full_model_path = os.path.join(models_root, 'upscayl', 'models')
                cmd = [exe_path, '-i', temp_input_path, '-o', temp_output_path,
                    '-n', internal_model_name, '-m', full_model_path,
                    '-s', scale, '-f', 'png', '-j', threads_arg]
                match = re.search(r'[xX]([2-3])', internal_model_name)
                if match:
                    cmd.extend(['-z', match.group(1)])
                if tile_size and tile_size != '0':
                    cmd.extend(['-t', tile_size])
                if use_tta:
                    cmd.append('-x')
            else:
                raise ValueError(f'Motor de upscaling no soportado: {engine}')

            if not os.path.exists(exe_path):
                print(f'ERROR: No se encontró el ejecutable: {exe_path}')
                return img

            # --- Ejecutar proceso ---
            print(f"DEBUG: Ejecutando Upscale ({engine}): {' '.join(cmd)}")
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags
            )

            # Cola para leer stderr en tiempo real
            def enqueue_output(out, q):
                for line in iter(out.readline, ''):
                    q.put(line)
                out.close()

            q = queue.Queue()
            t = threading.Thread(target=enqueue_output, args=(process.stderr, q))
            t.daemon = True
            t.start()

            last_update_time = 0
            while process.poll() is None:
                if cancellation_event and cancellation_event.is_set():
                    print('DEBUG: Cancelación detectada durante Upscaling. Matando proceso...')
                    process.kill()
                    raise UserCancelledError('Reescalado cancelado por usuario')
                try:
                    line = q.get_nowait()
                    match = re.search(r'(\d+)[.,](\d+)%', line)
                    if match:
                        pct = float(match.group(1) + '.' + match.group(2))
                        current_time = time.time()
                        if current_time - last_update_time >= 0.25 or pct >= 100.0:
                            last_update_time = current_time
                            print(f'Progreso Upscayl: {pct:.1f}%')
                            if progress_callback:
                                scaled_pct = 50 + pct / 10.0
                                progress_callback(scaled_pct, f'Reescalando ({engine}): {pct:.1f}%')
                except queue.Empty:
                    time.sleep(0.05)

            # Verificar resultado
            if process.returncode != 0 or not os.path.exists(temp_output_path):
                remaining_stderr = ''
                while not q.empty():
                    remaining_stderr += q.get_nowait()
                print(f'ERROR Upscaling CLI: {remaining_stderr}')
                return img

            # Cargar imagen reescalada
            upscaled_img = Image.open(temp_output_path)
            upscaled_img.load()
            print(f'INFO: Reescalado finalizado. Tamaño: {upscaled_img.size}')
            return upscaled_img

        except Exception as e:
            print(f'ERROR CRÍTICO en reescalado: {e}')
            return img

        finally:
            # Limpiar archivos temporales (excepto si se pasó un path externo)
            if temp_input_path and needs_input_cleanup and os.path.exists(temp_input_path):
                try:
                    os.remove(temp_input_path)
                except OSError:
                    pass
            if temp_output_path and os.path.exists(temp_output_path):
                try:
                    os.remove(temp_output_path)
                except OSError:
                    pass