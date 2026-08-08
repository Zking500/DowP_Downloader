import os
import io
import re
import subprocess
import tempfile
from PIL import Image, ImageChops, ImageOps

class HideCmdWindow:
    """
    Context Manager que fuerza a todos los subprocesos (Popen) creados dentro
    de su bloque a ejecutarse sin ventana (CREATE_NO_WINDOW) en Windows.
    """
    def __enter__(self):
        if os.name == 'nt':
            self._orig_popen = subprocess.Popen
            def new_popen(*args, **kwargs):
                kwargs.setdefault('creationflags', 134217728)
                return self._orig_popen(*args, **kwargs)
            subprocess.Popen = new_popen
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.name == 'nt':
            subprocess.Popen = self._orig_popen

try:
    import cairosvg
    CAN_SVG = True
except ImportError:
    CAN_SVG = False
    print('ADVERTENCIA: \'cairosvg\' no instalado. No se podrán previsualizar archivos .svg')

try:
    from pdf2image import convert_from_path, pdfinfo_from_path
    CAN_PDF = True
except ImportError:
    CAN_PDF = False
    print('ADVERTENCIA: \'pdf2image\' no instalado. No se podrán previsualizar archivos .pdf, .ai, .eps')

from src.core.constants import IMAGE_RASTER_FORMATS, IMAGE_INPUT_FORMATS, IMAGE_RAW_FORMATS

RASTER_EXT = tuple(f.lower() for f in IMAGE_RASTER_FORMATS)
VECTOR_EXT = tuple(f.lower() for f in IMAGE_INPUT_FORMATS)


class ImageProcessor:
    def __init__(self, poppler_path=None, inkscape_service=None, ffmpeg_path=None):
        self.poppler_path = poppler_path
        self.inkscape_service = inkscape_service
        self.ffmpeg_path = ffmpeg_path
        self._page_count_cache = {}

        if CAN_PDF and self.poppler_path:
            print(f'INFO: ImageProcessor usará Poppler desde: {self.poppler_path}')

        self.gs_exe = self._find_ghostscript()
        if self.gs_exe:
            print(f'INFO: ImageProcessor usará Ghostscript desde: {self.gs_exe}')

        if self.inkscape_service:
            print('INFO: ImageProcessor usará Inkscape Service')
        else:
            print('INFO: Inkscape no habilitado. Usando motores nativos.')

    def _command_exists(self, cmd):
        """Verifica si un comando está disponible en el PATH."""
        import shutil
        return shutil.which(cmd) is not None

    def _fix_svg_attributes(self, svg_path):
        """
        Lee un SVG y corrige atributos width/height inválidos.
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

            simple_patterns = [
                ('width\\s*=\\s*\"px\"', 'width=\"180\"'),
                ('width\\s*=\\s*\"\"', 'width=\"180\"'),
                ('width\\s*=\\s*\"\\s*px\\s*\"', 'width=\"180\"'),
                ('height\\s*=\\s*\"px\"', 'height=\"180\"'),
                ('height\\s*=\\s*\"\"', 'height=\"180\"'),
                ('height\\s*=\\s*\"\\s*px\\s*\"', 'height=\"180\"'),
            ]
            for pattern, replacement in simple_patterns:
                if re.search(pattern, fixed_attributes, re.IGNORECASE):
                    fixed_attributes = re.sub(pattern, replacement, fixed_attributes, flags=re.IGNORECASE)
                    needs_fix = True

            def clean_px_width(m):
                value = m.group(0).split('\"')[1]
                value_clean = value.replace('px', '').strip()
                return f'width=\"{value_clean}\"'

            def clean_px_height(m):
                value = m.group(0).split('\"')[1]
                value_clean = value.replace('px', '').strip()
                return f'height=\"{value_clean}\"'

            if re.search('width\\s*=\\s*\"\\d+px\"', fixed_attributes, re.IGNORECASE):
                fixed_attributes = re.sub('width\\s*=\\s*\"\\d+px\"', clean_px_width, fixed_attributes, flags=re.IGNORECASE)
                needs_fix = True
            if re.search('height\\s*=\\s*\"\\d+px\"', fixed_attributes, re.IGNORECASE):
                fixed_attributes = re.sub('height\\s*=\\s*\"\\d+px\"', clean_px_height, fixed_attributes, flags=re.IGNORECASE)
                needs_fix = True

            if not needs_fix:
                return None

            fixed_svg_content = re.sub(
                svg_tag_pattern,
                f'<svg{fixed_attributes}>',
                svg_content,
                count=1,
                flags=re.IGNORECASE
            )

            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8')
            temp_file.write(fixed_svg_content)
            temp_file.close()
            print(f'DEBUG: SVG corregido guardado en: {temp_file.name}')
            return temp_file.name
        except Exception as e:
            print(f'ADVERTENCIA: No se pudo preprocesar el SVG: {e}')
            return None

    def get_document_page_count(self, filepath):
        """
        Obtiene el número de páginas de un documento con caché para evitar bloqueos.
        """
        if filepath in self._page_count_cache:
            return self._page_count_cache[filepath]

        ext = os.path.splitext(filepath)[1].lower()
        count = 1

        try:
            if ext == '.pdf':
                try:
                    with HideCmdWindow():
                        info = pdfinfo_from_path(filepath, poppler_path=self.poppler_path)
                    count = int(info.get('Pages', 1))
                except Exception as e:
                    print(f'ADVERTENCIA: Poppler falló leyendo PDF {filepath}: {e}')
                    count = 1
            else:
                if ext in ['.eps', '.ai', '.ps']:
                    try:
                        with open(filepath, 'rb') as f:
                            header = f.read(4096).decode('latin-1', errors='ignore')
                            match = re.search(r'%%Pages:\s*(\d+)', header)
                            if match:
                                count = max(1, int(match.group(1)))
                            # .ai files may actually be PDFs
                            if ext == '.ai' and b'%PDF' in header.encode('latin-1'):
                                try:
                                    with HideCmdWindow():
                                        info = pdfinfo_from_path(filepath, poppler_path=self.poppler_path)
                                    count = int(info.get('Pages', 1))
                                    print(f'DEBUG: Archivo .ai detectado como PDF con {count} página(s)')
                                except Exception as e:
                                    print(f'DEBUG: .ai no pudo leerse como PDF: {e}')
                    except Exception as e:
                        print(f'DEBUG: No se pudo leer cabecera EPS/AI de {filepath}: {e}')
                        count = 1
        except Exception as e:
            print(f'ERROR CRÍTICO obteniendo páginas: {e}')
            count = 1

        self._page_count_cache[filepath] = count
        return count

    def generate_thumbnail(self, filepath, size=(400, 400), page_number=None, dpi=None):
        """
        Genera una miniatura (PIL.Image) para un archivo.
        OPTIMIZADO: Prioriza velocidad sobre calidad.
        """
        print(f'DEBUG: [Thumb] Iniciando generación para: {os.path.basename(filepath)} (Size: {size}, Page: {page_number}, DPI: {dpi})')
        ext = os.path.splitext(filepath)[1].lower()
        pil_image = None

        # --- RAW processing ---
        if ext.upper() in IMAGE_RAW_FORMATS:
            try:
                import rawpy
                import numpy as np
                with rawpy.imread(filepath) as raw:
                    try:
                        thumb = raw.extract_thumb()
                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            pil_image = Image.open(io.BytesIO(thumb.data))
                        elif thumb.format == rawpy.ThumbFormat.BITMAP:
                            pil_image = Image.fromarray(thumb.data)
                        print(f'DEBUG: [RAW] Miniatura extraída: {pil_image.size}, Formato: {thumb.format}')
                        if pil_image and max(pil_image.size) < 800:
                            print(f'DEBUG: [RAW] Miniatura demasiado pequeña ({pil_image.size}), forzando revelado.')
                            raise Exception('Miniatura demasiado pequeña')
                        else:
                            print(f'DEBUG: [RAW] Miniatura validada exitosamente: {pil_image.size}')
                    except Exception:
                        print(f'DEBUG: [RAW] Realizando revelado de alta calidad para {os.path.basename(filepath)}...')
                        rgb = raw.postprocess(
                            use_camera_wb=True,
                            half_size=False,
                            no_auto_bright=False,
                            output_bps=8,
                            output_color=rawpy.ColorSpace.sRGB,
                            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD
                        )
                        pil_image = Image.fromarray(rgb)
                        print(f'DEBUG: [RAW] Revelado finalizado. Tamaño: {pil_image.size}')

                try:
                    pil_image = ImageOps.exif_transpose(pil_image)
                    print(f'DEBUG: [RAW] Tras rotación EXIF: {pil_image.size}')
                except Exception as e:
                    print(f'DEBUG: [RAW] Error en rotación: {e}')

            except ImportError:
                print('⚠️ rawpy no instalado. Ejecuta: pip install rawpy')
                pil_image = None
            except Exception as e:
                print(f'❌ ERROR al revelar RAW: {e}')
                pil_image = None

        # --- Raster / Vector / Fallback ---
        if pil_image is None:
            if ext in RASTER_EXT:
                print(f'DEBUG: [Thumb] Procesando como RASTER: {ext}')
                try:
                    pil_image = Image.open(filepath)
                    pil_image.load()
                except OSError as e:
                    print(f'ADVERTENCIA: [Thumb] Archivo corrupto o ilegible \'{os.path.basename(filepath)}\': {e}')
                    return None
                except Exception as e:
                    print(f'ADVERTENCIA: [Thumb] Formato no soportado o error desconocido en \'{filepath}\': {e}')
                    return None
            elif ext in VECTOR_EXT:
                print(f'DEBUG: [Thumb] Procesando como VECTORIAL: {ext}')
                pil_image = self._generate_vector_thumbnail(filepath, size, page_number, dpi=dpi)
            else:
                print(f'DEBUG: [Thumb] Procesando como RASTER/FALLBACK: {ext}')
                try:
                    pil_image = Image.open(filepath)
                    pil_image.load()
                except Exception as e:
                    print(f'ADVERTENCIA: [Thumb] Formato no soportado o error desconocido en \'{filepath}\': {e}')
                    return None

        if pil_image is None:
            print(f'DEBUG: [Thumb] ❌ Falló la carga de imagen para {os.path.basename(filepath)}')
            return None

        # --- Convert to RGBA ---
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')

        # --- Resize only for small previews, keep high-res for viewer ---
        ext_upper = ext.upper() if ext else ''
        is_large_preview = max(size) > 500
        if ext_upper in IMAGE_RAW_FORMATS:
            print(f'DEBUG: [RAW] Saltando thumbnail final para mantener resolución: {pil_image.size}')
        elif ext in VECTOR_EXT and is_large_preview:
            print(f'DEBUG: [Thumb] Saltando thumbnail final para Vector (Preview HD): {pil_image.size}')
        else:
            pil_image.thumbnail(size, Image.Resampling.LANCZOS)

        print(f'DEBUG: [Thumb] ✅ Miniatura generada exitosamente ({pil_image.size})')
        return pil_image

    def _generate_vector_thumbnail(self, filepath, size, page_number=1, dpi=None):
        """
        Genera miniatura para archivos vectoriales con fondo inteligente:
        - PDF: Fondo Blanco (Documento)
        - AI, EPS, SVG: Transparente (Logo/Icono)
        - SIEMPRE usa motores nativos para velocidad.
        """
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.svg':
                return self._generate_svg_thumbnail(filepath, size)
            elif ext == '.pdf':
                return self._generate_pdf_thumbnail(filepath, size, page_number, transparent=False, dpi=dpi)
            elif ext == '.ai':
                return self._generate_pdf_thumbnail(filepath, size, page_number, transparent=True, dpi=dpi)
            elif ext in ['.eps', '.ps']:
                return self._generate_eps_thumbnail(filepath, size, page_number, dpi=dpi)
            else:
                return None
        except Exception as e:
            print(f'DEBUG: Error generando miniatura vectorial ({ext}): {e}')
            return None

    def _generate_thumbnail_with_inkscape(self, filepath, size, page_number, dpi=96):
        """Usa Inkscape para la miniatura (Lento pero preciso)."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_png:
            tmp_png_path = tmp_png.name
        if os.path.exists(tmp_png_path):
            os.remove(tmp_png_path)

        render_dpi = dpi if dpi else 96
        try:
            cmd = self.inkscape_service.build_command(filepath, tmp_png_path, page_number, dpi=render_dpi)
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.inkscape_service.get_env(),
                cwd=self.inkscape_service.get_cwd(),
                timeout=20,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if os.path.exists(tmp_png_path) and os.path.getsize(tmp_png_path) > 0:
                img = Image.open(tmp_png_path)
                img.load()
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img
            else:
                return None
        except Exception as e:
            print(f'DEBUG: Error con Inkscape: {e}')
            return None
        finally:
            if os.path.exists(tmp_png_path):
                os.remove(tmp_png_path)

    def _generate_svg_thumbnail(self, filepath, size):
        """Usa CairoSVG para la miniatura con corrección automática y fallback a Inkscape."""
        if not CAN_SVG:
            if self.inkscape_service:
                return self._generate_thumbnail_with_inkscape(filepath, size, 1)
            else:
                return None

        w, h = size
        temp_svg = None
        try:
            # Try CairoSVG directly
            out = cairosvg.svg2png(url=filepath, output_width=w, output_height=h)
            img = Image.open(io.BytesIO(out))
            img.load()
            return img
        except (ValueError, TypeError, Exception) as e:
            print(f'DEBUG: [Thumb] CairoSVG falló para {os.path.basename(filepath)}: {e}. Intentando corrección...')
            temp_svg = self._fix_svg_attributes(filepath)
            try:
                if temp_svg:
                    out = cairosvg.svg2png(url=temp_svg, output_width=w, output_height=h)
                    img = Image.open(io.BytesIO(out))
                    img.load()
                    return img
                else:
                    raise Exception('No se pudo corregir SVG')
            except Exception as e2:
                print(f'DEBUG: [Thumb] CairoSVG también falló con SVG corregido: {e2}')
                if self.inkscape_service:
                    print('DEBUG: [Thumb] Usando Inkscape como fallback para vista previa de SVG.')
                    return self._generate_thumbnail_with_inkscape(temp_svg if temp_svg else filepath, size, 1)
                else:
                    return None
        finally:
            if temp_svg and os.path.exists(temp_svg):
                os.remove(temp_svg)

    def _generate_pdf_thumbnail(self, filepath, size, page_number, transparent=False, dpi=None):
        """Usa Poppler para la miniatura con fondo controlado."""
        if not CAN_PDF or not self.poppler_path:
            return None

        is_large_preview = max(size) > 500
        if is_large_preview:
            render_dpi = max(200, dpi if dpi else 300)
        else:
            render_dpi = 100

        try:
            images = convert_from_path(
                filepath,
                dpi=render_dpi,
                first_page=page_number,
                last_page=page_number,
                poppler_path=self.poppler_path,
                transparent=transparent,
                use_pdftocairo=True
            )
            if images:
                img = images[0].convert('RGBA')
                if not is_large_preview:
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                else:
                    print(f'DEBUG: [Thumb] Render de alta calidad para visor ({img.size})')
                return img
            else:
                return None
        except Exception as e:
            print(f'DEBUG: [Thumb] Error en render PDF/EPS: {e}')
            return None

    def _find_ghostscript(self):
        """Busca Ghostscript localmente para miniaturas EPS."""
        try:
            base_path = os.getcwd()
            possible_dirs = [
                os.path.join(base_path, 'bin', 'ghostscript', 'bin'),
                os.path.join(base_path, 'bin', 'ghostscript')
            ]
            binaries = ['gswin64c.exe', 'gswin32c.exe', 'gs.exe', 'gs']
            for folder in possible_dirs:
                if os.path.exists(folder):
                    for binary in binaries:
                        path = os.path.join(folder, binary)
                        if os.path.exists(path):
                            return path
            return None
        except Exception:
            return None

    def _generate_eps_thumbnail(self, filepath, size, page_number, dpi=None):
        """Genera miniatura EPS con transparencia usando Ghostscript."""
        if self.gs_exe and CAN_PDF:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                temp_pdf = tmp_pdf.name
            try:
                cmd = [
                    self.gs_exe,
                    '-q', '-dNOPAUSE', '-dBATCH',
                    '-sDEVICE=pdfwrite',
                    f'-sOutputFile={temp_pdf}',
                    '-dEPSCrop',
                    filepath
                ]
                subprocess.run(
                    cmd,
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                return self._generate_pdf_thumbnail(temp_pdf, size, page_number, transparent=True, dpi=dpi)
            except Exception as e:
                print(f'DEBUG: Error convirtiendo EPS a PDF con Ghostscript: {e}')
                return None
            finally:
                if os.path.exists(temp_pdf):
                    os.remove(temp_pdf)
        else:
            # Fallback: try opening with PIL (may fail for vector EPS)
            try:
                img = Image.open(filepath)
                img.load()
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img
            except Exception:
                return None