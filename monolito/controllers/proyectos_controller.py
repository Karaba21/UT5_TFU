"""
Blueprint de proyectos para el monolito
"""
from flask import Blueprint, request, jsonify
import json
import os
import time
import redis
from middleware.auth import valet_key_required
from services.usuarios_service import get_usuarios

proyectos_bp = Blueprint('proyectos', __name__)

DATA_FILE = "proyectos.json"
CIRCUIT_FILE = "circuit_state.json"

FAIL_THRESHOLD = 3
RESET_TIMEOUT = 10

cache = redis.Redis(host="redis", port=6379, decode_responses=True)
CACHE_TTL = 30  # segundos que los datos duran en cache

# Crear archivo JSON si no existe
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

# Inicializar archivo de circuito
if not os.path.exists(CIRCUIT_FILE):
    with open(CIRCUIT_FILE, "w") as f:
        json.dump({"fail_count": 0, "circuit_open": False, "last_failure_time": 0}, f)


def read_circuit_state():
    with open(CIRCUIT_FILE) as f:
        return json.load(f)


def write_circuit_state(state):
    with open(CIRCUIT_FILE, "w") as f:
        json.dump(state, f)


@proyectos_bp.route("/proyectos/<int:proyecto_id>", methods=["GET"])
@valet_key_required(scope="read:proyectos", resource_key="proyecto_id", method="GET")
def get_proyecto_by_id(proyecto_id):
    try:
        # 1️⃣ Buscar en cache
        cache_key = f"proyecto:{proyecto_id}"
        cached_proyecto = cache.get(cache_key)
        if cached_proyecto:
            print(f"Cache hit -> proyecto {proyecto_id}")
            return jsonify(json.loads(cached_proyecto)), 200

        # 2️⃣ Si no está en cache, leer del archivo
        print(f"Cache miss -> leyendo proyecto {proyecto_id} del archivo")
        with open(DATA_FILE) as f:
            proyectos = json.load(f)

        proyecto = next((p for p in proyectos if p["id"] == proyecto_id), None)
        if not proyecto:
            return jsonify({"error": "Proyecto no encontrado"}), 404

        # 3️⃣ Guardar en cache
        cache.setex(cache_key, CACHE_TTL, json.dumps(proyecto))

        return jsonify(proyecto), 200

    except Exception as e:
        print(f"Error al obtener proyecto: {e}")
        return jsonify({"error": "No se pudo obtener el proyecto"}), 500


@proyectos_bp.route("/proyectos", methods=["GET"])
def get_all_proyectos():
    try:
        with open(DATA_FILE) as f:
            proyectos = json.load(f)
        return jsonify({"data": proyectos}), 200
    except Exception as e:
        return jsonify({"error": f"No se pudieron obtener los proyectos: {str(e)}"}), 500


@proyectos_bp.route("/proyectos", methods=["POST"])
@valet_key_required(scope="write:proyectos", method="POST")
def add_proyecto():
    state = read_circuit_state()
    data = request.json

    if not data or not data.get("nombre") or not data.get("usuario_id"):
        return jsonify({"error": "Campos 'nombre' y 'usuario_id' son obligatorios"}), 400

    # --- Circuit Breaker Logic ---
    if state["circuit_open"]:
        if time.time() - state["last_failure_time"] < RESET_TIMEOUT:
            return jsonify({"error": "Circuito abierto: servicio de usuarios no disponible temporalmente"}), 503
        else:
            # Reinicia el circuito después del timeout
            state.update({"fail_count": 0, "circuit_open": False})
            write_circuit_state(state)

    try:
        # En el monolito, acceso directo a datos (sin HTTP)
        usuarios = get_usuarios()

        # Resetea el circuito si todo va bien
        state.update({"fail_count": 0, "circuit_open": False})
        write_circuit_state(state)

    except Exception as e:
        state["fail_count"] += 1
        state["last_failure_time"] = time.time()
        if state["fail_count"] >= FAIL_THRESHOLD:
            state["circuit_open"] = True
            print("⚠️ Circuit breaker abierto: demasiadas fallas en usuarios-service.")
        write_circuit_state(state)
        return jsonify({"error": "Servicio de usuarios no disponible"}), 503

    # Validar usuario existente
    if not any(u["id"] == data["usuario_id"] for u in usuarios):
        return jsonify({"error": "Usuario no encontrado"}), 400

    # Guardar proyecto
    with open(DATA_FILE) as f:
        proyectos = json.load(f)
    data["id"] = (proyectos[-1]["id"] + 1) if proyectos else 1
    proyectos.append(data)
    with open(DATA_FILE, "w") as f:
        json.dump(proyectos, f, indent=4)

    return jsonify({"mensaje": "Proyecto creado exitosamente", "data": data}), 201
