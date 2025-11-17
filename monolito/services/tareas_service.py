"""
Servicio de tareas - funciones compartidas para acceso directo a datos
(en lugar de hacer requests HTTP)
"""
import json
import os

DATA_FILE = "tareas.json"

def get_tareas():
    """Obtiene todas las tareas"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def get_tarea_by_id(tarea_id):
    """Obtiene una tarea por ID"""
    tareas = get_tareas()
    return next((t for t in tareas if t["id"] == tarea_id), None)

def tarea_exists(tarea_id):
    """Verifica si una tarea existe"""
    return get_tarea_by_id(tarea_id) is not None

