# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\inkscape_service.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import os
import subprocess
import shutil
class InkscapeService:
    """\n    Servicio independiente para gestionar la comunicación con Inkscape externo.\n    Permite desacoplar Inkscape del núcleo del programa.\n    """
    def __init__(self, custom_path=None):
        self.base_path = custom_path
        self.actual_bin_path = None
        self.version_info = None
        if self.base_path:
            self._detect_binary()
    def _detect_binary(self):
        """Busca el ejecutable en la raíz o en /bin de la ruta proporcionada."""
        if not self.base_path:
            return False
        else:
            exe_name = 'inkscape.com' if os.name == 'nt' else 'inkscape'
            path_root = os.path.join(self.base_path, exe_name)
            path_bin = os.path.join(self.base_path, 'bin', exe_name)
            if os.path.exists(path_bin):
                self.actual_bin_path = path_bin
                return True
            else:
                if os.path.exists(path_root):
                    self.actual_bin_path = path_root
                    return True
                else:
                    return False
    def is_available(self):
#         # irreducible cflow, using cdg fallback
        """Verifica si Inkscape está configurado y es funcional."""
#         # ***<module>.InkscapeService.is_available: Failure: Compilation Error
        if not self.actual_bin_path and (not self._detect_binary()):
                return False
        result = subprocess.run([self.actual_bin_path, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            if result.returncode == 0:
                self.version_info = result.stdout.decode('utf-8', errors='ignore').strip()
                return True
        except Exception:
            pass
            return False
    def build_command(self, filepath, output_path, page_number=1, dpi=300, artboard_id=None):
        """\n        Construye el comando CLI de Inkscape.\n        """
        if not self.actual_bin_path:
            return
        else:
            filepath = os.path.normpath(os.path.abspath(filepath))
            output_path = os.path.normpath(os.path.abspath(output_path))
            ext = os.path.splitext(filepath)[1].lower()
            cmd = [self.actual_bin_path, filepath, f'--export-filename={output_path}', f'--export-dpi={dpi}', '--export-type=png', '--export-background-opacity=0', '--batch-process']
            if ext in ['.ai', '.pdf']:
                if page_number > 1:
                    cmd.insert(2, f'--pages={page_number}')
                    cmd.insert(4, '--export-area-page')
                else:
                    cmd.insert(4, '--export-area-drawing')
            else:
                if ext in ['.eps', '.ps']:
                    cmd.insert(2, '--export-area-drawing')
                else:
                    if ext == '.svg' and artboard_id:
                        cmd.insert(2, f'--export-id={artboard_id}')
                        cmd.insert(3, '--export-id-only')
                    else:
                        cmd.insert(2, '--export-area-drawing')
            return cmd
    def get_cwd(self):
        """Devuelve el directorio de trabajo ideal para Inkscape."""
        if self.actual_bin_path:
            return os.path.dirname(self.actual_bin_path)
        else:
            return None
    def start_session(self):
        """Inicia una sesión persistente de Inkscape (--shell) para procesamiento por lotes."""
#         # ***<module>.InkscapeService.start_session: Failure: Different control flow
        if self.actual_bin_path and hasattr(self, '_session_process'):
            return False
        else:
            try:
                self._session_process = subprocess.Popen([self.actual_bin_path, '--shell'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                print('INFO: Sesión persistente de Inkscape iniciada.')
            except Exception as e:
                print(f'ERROR iniciando sesión de Inkscape: {e}')
                return False
            else:
                return True
    def stop_session(self):
#         # irreducible cflow, using cdg fallback
        """Cierra la sesión persistente de Inkscape."""
#         # ***<module>.InkscapeService.stop_session: Failure: Compilation Error
        if hasattr(self, '_session_process'):
            pass
        self._session_process.stdin.write('quit\n')
        self._session_process.stdin.flush()
        self._session_process.wait(timeout=5)
        self._session_process.kill()
        pass
        del self._session_process
        print('INFO: Sesión de Inkscape finalizada.')
    def convert_batch(self, filepath, output_path, page_number=1, dpi=300, target_size=None, maintain_aspect=True):
        """Ejecuta una conversión dentro de la sesión activa."""
        if not hasattr(self, '_session_process'):
            return False
        else:
            filepath = os.path.normpath(os.path.abspath(filepath)).replace('\\', '/')
            output_path = os.path.normpath(os.path.abspath(output_path)).replace('\\', '/')
            actions = f'file-open:{filepath}; '
            ext = os.path.splitext(filepath)[1].lower()
            if ext in ['.pdf', '.ai'] and page_number > 1:
                    actions += f'select-page:{page_number}; '
            if target_size:
                w, h = target_size
                actions += f'export-width:{w}; '
                if not maintain_aspect:
                    actions += f'export-height:{h}; '
            else:
                actions += f'export-dpi:{dpi}; '
            actions += 'export-background-opacity:0; export-type:png; export-do; '
            try:
                self._session_process.stdin.write(actions + '\n')
                self._session_process.stdin.flush()
                while True:
                    line = self._session_process.stdout.read(1)
                    if not line or line == '>':
                        break
            except Exception as e:
                print(f'ERROR en batch de Inkscape: {e}')
                return False
            else:
                return True
    def get_env(self):
        """Devuelve el entorno con las rutas necesarias."""
        env = os.environ.copy()
        if self.base_path:
            bin_dir = os.path.join(self.base_path, 'bin')
            if os.path.exists(bin_dir):
                env['PATH'] = f"{bin_dir};{env.get('PATH', '')}"
        return env
    def get_ai_artboard_ids(self, filepath):
#         # irreducible cflow, using cdg fallback
        """\n        Obtiene los IDs de las mesas de trabajo de un archivo .ai usando Inkscape.\n        """
#         # ***<module>.InkscapeService.get_ai_artboard_ids: Failure: Compilation Error
        if not self.actual_bin_path:
            return
        import re
        cmd = [self.actual_bin_path, filepath, '--query-all']
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            if result.returncode != 0:
                return
                stdout = result.stdout.decode('utf-8', errors='ignore')
                artboard_ids = []
                for line in stdout.splitlines():
                    parts = line.strip().split(',')
                    if len(parts) >= 5:
                        obj_id = parts[0]
                        if re.match('^layer-MC\\d+$', obj_id) or re.match('^page\\d+$', obj_id):
                            num = int(re.search('\\d+', obj_id).group())
                            artboard_ids.append((num, obj_id))
                if artboard_ids:
                    artboard_ids.sort()
                    return [oid for _, oid in artboard_ids]
        except Exception:
            return None
