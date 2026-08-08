# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\exceptions.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

class UserCancelledError(Exception):
    """Excepción lanzada cuando el usuario cancela una operación."""
    pass
class LocalRecodeFailedError(Exception):
    """Excepción para un fallo específico en la recodificación local."""
    def __init__(self, message, temp_filepath=None):
        super().__init__(message)
        self.temp_filepath = temp_filepath
class PlaylistDownloadError(Exception):
    """Excepción lanzada cuando yt-dlp falla al descargar un ítem de playlist."""