"""
Servicio de usuarios - funciones compartidas para acceso directo a datos
(en lugar de hacer requests HTTP)
"""
import json
import os

DATA_FILE = "usuarios.json"

def get_usuarios():
    """Obtiene todos los usuarios"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def get_usuario_by_id(usuario_id):
    """Obtiene un usuario por ID"""
    usuarios = get_usuarios()
    return next((u for u in usuarios if u["id"] == usuario_id), None)

def usuario_exists(usuario_id):
    """Verifica si un usuario existe"""
    return get_usuario_by_id(usuario_id) is not None

