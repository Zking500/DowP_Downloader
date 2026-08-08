# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\integration_manager.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import os
from src.core.davinci_api import importar_a_davinci
class IntegrationManager:
    def __init__(self, main_app):
        self.main_app = main_app
    def broadcast_import(self, source_path, final_path=None, thumb_path=None, bin_name=None, workflow_type='batch'):
#         # irreducible cflow, using cdg fallback
        """\n        Envía los archivos a las aplicaciones externas activas (Adobe / DaVinci).\n        """
#         # ***<module>.IntegrationManager.broadcast_import: Failure: Compilation Error
        app = self.main_app
        adobe_enabled = False
        if getattr(app, 'adobe_enabled', True):
            if workflow_type == 'single':
                adobe_enabled = getattr(app, 'adobe_import_single', True)
            else:
                if workflow_type == 'batch':
                    adobe_enabled = getattr(app, 'adobe_import_batch', False)
                else:
                    if workflow_type == 'image':
                        adobe_enabled = getattr(app, 'adobe_import_image', False)
        if adobe_enabled:
            self._send_to_adobe(final_path or source_path, thumb_path, bin_name)
        davinci_enabled = False
        if getattr(app, 'davinci_enabled', True):
            if workflow_type == 'single':
                davinci_enabled = getattr(app, 'davinci_import_single', False)
            else:
                if workflow_type == 'batch':
                    davinci_enabled = getattr(app, 'davinci_import_batch', False)
                else:
                    if workflow_type == 'image':
                        davinci_enabled = getattr(app, 'davinci_import_image', False)
        try:
            if davinci_enabled:
                dv_bin = bin_name or 'DowP Imports'
                files_to_davinci = []
                import_all = getattr(app, 'davinci_import_everything', False)
                if import_all and source_path and final_path and (source_path != final_path):
                    if source_path and os.path.exists(source_path):
                            files_to_davinci.append(source_path)
                    if final_path and os.path.exists(final_path):
                            files_to_davinci.append(final_path)
                else:
                    target = final_path or source_path
                    if target and os.path.exists(target):
                            files_to_davinci.append(target)
                if thumb_path and os.path.exists(thumb_path):
                        normalized_thumb = os.path.normpath(thumb_path)
                        if not any((os.path.normpath(f) == normalized_thumb for f in files_to_davinci)):
                            files_to_davinci.append(thumb_path)
                if files_to_davinci:
                    import threading
                    def run_davinci():
    #                     # ***<module>.IntegrationManager.broadcast_import.run_davinci: Failure detected at line number 14 and instruction offset 2: Different bytecode
                        try:
                            importar_a_davinci(files_to_davinci, log_callback=print, import_to_timeline=getattr(app, 'davinci_import_to_timeline', True), bin_name=dv_bin)
                        except Exception as e:
                            print(f'ERROR: Falló la importación a DaVinci: {e}')
                    threading.Thread(target=run_davinci, daemon=True).start()
        except Exception as e:
            print(f'ERROR CRÍTICO en IntegrationManager: {e}')
    def _send_to_adobe(self, file_path, thumb_path, bin_name):
        """Envía el paquete de archivos a Adobe vía SocketIO."""
        if not file_path:
            return
        else:
            active_target = self.main_app.ACTIVE_TARGET_SID_accessor()
            if not active_target:
                return
            else:
                if thumb_path and os.path.normpath(thumb_path) == os.path.normpath(file_path):
                        thumb_path = None
                file_package = {'video': str(file_path).replace('\\', '/'), 'thumbnail': str(thumb_path).replace('\\', '/') if thumb_path else None, 'subtitle': None}
                if bin_name:
                    file_package['targetBin'] = bin_name
                try:
                    self.main_app.socketio.emit('new_file', {'filePackage': file_package}, to=active_target)
                    print(f'LOG: [Adobe] Enviado: {os.path.basename(file_path)}')
                except Exception as e:
                    print(f'ERROR: Falló el envío a Adobe: {e}')
    def broadcast_import_list(self, files, bin_name='DowP Imports', workflow_type='image'):
#         # irreducible cflow, using cdg fallback
        """\n        Versión para múltiples archivos (principalmente para Image Tools).\n        """
#         # ***<module>.IntegrationManager.broadcast_import_list: Failure: Compilation Error
        if not bin_name:
            bin_name = 'DowP Imports'
        app = self.main_app
        adobe_enabled = False
        if getattr(app, 'adobe_enabled', True) and workflow_type == 'image':
                adobe_enabled = getattr(app, 'adobe_import_image', False)
        if adobe_enabled:
            active_target = app.ACTIVE_TARGET_SID_accessor()
            if active_target:
                import_package = {'files': [f.replace('\\', '/') for f in files], 'targetBin': bin_name}
                try:
                    app.socketio.emit('import_files', import_package, to=active_target)
                    print(f'LOG: [Adobe] Paquete de {len(files)} archivos enviado.')
                except Exception as e:
                    print(f'ERROR: Falló el envío de lista a Adobe: {e}')
        davinci_enabled = False
        if getattr(app, 'davinci_enabled', True) and workflow_type == 'image':
                davinci_enabled = getattr(app, 'davinci_import_image', False)
        try:
            if davinci_enabled:
                dv_bin = bin_name or 'DowP Imports'
                import threading
                def run_davinci():
    #                 # ***<module>.IntegrationManager.broadcast_import_list.run_davinci: Failure detected at line number 39 and instruction offset 8: Different bytecode
                    try:
                        importar_a_davinci(files, log_callback=print, import_to_timeline=getattr(app, 'davinci_import_to_timeline', True), bin_name=dv_bin)
                    except Exception as e:
                        print(f'ERROR: Falló la importación por lote a DaVinci: {e}')
                threading.Thread(target=run_davinci, daemon=True).start()
        except Exception as e:
            print(f'ERROR CRÍTICO en IntegrationManager (List): {e}')
