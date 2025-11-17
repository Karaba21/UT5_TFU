"""
Servicio de proyectos - funciones compartidas para acceso directo a datos
(en lugar de hacer requests HTTP)
"""
import json
import os

DATA_FILE = "proyectos.json"

def get_proyectos():
    """Obtiene todos los proyectos"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def get_proyecto_by_id(proyecto_id):
    """Obtiene un proyecto por ID"""
    proyectos = get_proyectos()
    return next((p for p in proyectos if p["id"] == proyecto_id), None)

def proyecto_exists(proyecto_id):
    """Verifica si un proyecto existe"""
    return get_proyecto_by_id(proyecto_id) is not None

