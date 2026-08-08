# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: 'src\\core\\tags_manager.py'
# Bytecode version: 3.11a7e (3495)
# Source timestamp: 1970-01-01 00:00:00 UTC (0)

import os
class TagsManager:
    def __init__(self, app):
        self.app = app
    def load_tags(self):
        """Devuelve el diccionario de etiquetas actual."""
        return getattr(self.app, 'tags', {})
    def save_tags(self, tags_dict):
        """Guarda y persiste el diccionario de etiquetas."""
        self.app.tags = tags_dict
        self.app.save_settings()
    def add_tag(self, name, path):
        """Valida e inserta una nueva etiqueta."""
        name = name.strip()
        path = os.path.normpath(path.strip())
        if not name:
            raise ValueError('El nombre de la etiqueta no puede estar vacío.')
        else:
            if not path or not os.path.isdir(path):
                raise ValueError('La ruta seleccionada no es válida o no existe.')
            else:
                tags = self.load_tags()
                tags[name] = path
                self.save_tags(tags)
                print(f'INFO: Etiqueta \'{name}\' añadida con éxito apuntando a: {path}')
                return tags
    def delete_tag(self, name):
        """Elimina una etiqueta por su nombre."""
        tags = self.load_tags()
        if name in tags:
            del tags[name]
            self.save_tags(tags)
            print(f'INFO: Etiqueta \'{name}\' eliminada con éxito.')
        return tags
    def get_tag_path(self, name):
        """Obtiene la ruta asociada a una etiqueta, o None si no existe."""
        return self.load_tags().get(name)