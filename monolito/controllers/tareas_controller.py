"""
Blueprint de tareas para el monolito
"""
from flask import Blueprint, request, jsonify
import json
import os
import redis
import time
from middleware.auth import valet_key_required
from services.proyectos_service import get_proyecto_by_id

tareas_bp = Blueprint('tareas', __name__)

DATA_FILE = "tareas.json"

# Conexión a Redis (cola de tareas)
queue = redis.Redis(host="redis", port=6379, decode_responses=True)
QUEUE_KEY = "tareas_pendientes"

# Crear archivo si no existe
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)


@tareas_bp.route("/tareas", methods=["GET"])
@valet_key_required(scope="read:tareas", method="GET")
def get_tareas():
    try:
        with open(DATA_FILE) as f:
            tareas = json.load(f)
        return jsonify({"data": tareas}), 200
    except Exception as e:
        return jsonify({"error": f"Error al leer tareas: {str(e)}"}), 500


@tareas_bp.route("/tareas", methods=["POST"])
@valet_key_required(scope="write:tareas", method="POST")
def enqueue_tarea():
    try:
        data = request.json

        # Chequear los campos requeridos
        if not data or not data.get("nombre") or not data.get("proyecto_id"):
            return jsonify({"error": "Campos 'nombre' y 'proyecto_id' son obligatorios"}), 400

        # En el monolito, acceso directo a datos (sin HTTP)
        try:
            proyecto = get_proyecto_by_id(data['proyecto_id'])
            if not proyecto:
                return jsonify({"error": "Proyecto no encontrado"}), 404
        except Exception:
            return jsonify({"error": "Servicio de proyectos no disponible"}), 503

        # Enviar tarea a la cola (Redis)
        queue.rpush(QUEUE_KEY, json.dumps(data))
        print(f"📩 Tarea encolada: {data}")

        return jsonify({"mensaje": "Tarea encolada correctamente"}), 202

    except Exception as e:
        return jsonify({"error": f"No se pudo encolar la tarea: {str(e)}"}), 500


@tareas_bp.route("/procesar_tareas", methods=["POST"])
@valet_key_required(scope="write:tareas", method="POST")
def procesar_tareas():
    procesadas = []
    while queue.llen(QUEUE_KEY) > 0:
        tarea_json = queue.lpop(QUEUE_KEY)
        if not tarea_json:
            break

        tarea = json.loads(tarea_json)
        print(f"⚙️ Procesando tarea: {tarea['nombre']}")
        time.sleep(2)  # simula tiempo de ejecución

        with open(DATA_FILE) as f:
            tareas = json.load(f)

        tarea["id"] = (tareas[-1]["id"] + 1) if tareas else 1
        tareas.append(tarea)

        with open(DATA_FILE, "w") as f:
            json.dump(tareas, f, indent=4)

        procesadas.append(tarea)

    return jsonify({"mensaje": "Tareas procesadas", "data": procesadas}), 200
