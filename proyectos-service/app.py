from flask import Flask, request, jsonify
import json, os, requests, time
import redis
from functools import wraps
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "proyectos.json"
USUARIOS_URL = "http://usuarios-service:5001/usuarios"
CIRCUIT_FILE = "circuit_state.json"

FAIL_THRESHOLD = 3
RESET_TIMEOUT = 10

cache = redis.Redis(host="redis", port=6379, decode_responses=True)
CACHE_TTL = 30  # segundos que los datos duran en cache

TOKENS_FILE = "tokens.json"
INTERNAL_SERVICE_TOKEN = "internal-service-token-2024"

# Crear archivo de tokens si no existe
if not os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, "w") as f:
        json.dump([], f)
    
# Registrar token de servicio interno automáticamente
try:
    with open(TOKENS_FILE, "r") as f:
        tokens_data = json.load(f)
except:
    tokens_data = []
    
if not any(t.get("token") == INTERNAL_SERVICE_TOKEN for t in tokens_data):
    tokens_data.append({
        "token": INTERNAL_SERVICE_TOKEN,
        "description": "Token interno para comunicación entre servicios"
    })
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens_data, f, indent=4)
    # Registrar en Redis también
    try:
        cache.setex(f"token:{INTERNAL_SERVICE_TOKEN}", 86400 * 365, "valid")  # 1 año
    except:
        pass  # Redis puede no estar disponible al inicio

# --- Crear archivo JSON si no existe ---
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)



#  Inicializar archivo de circuito 
if not os.path.exists(CIRCUIT_FILE):
    with open(CIRCUIT_FILE, "w") as f:
        json.dump({"fail_count": 0, "circuit_open": False, "last_failure_time": 0}, f)


def read_circuit_state():
    with open(CIRCUIT_FILE) as f:
        return json.load(f)


def write_circuit_state(state):
    with open(CIRCUIT_FILE, "w") as f:
        json.dump(state, f)


# --- Helper para obtener token del request ---
def get_token_from_request():
    """Extrae el token del header Authorization o X-API-Key"""
    auth_header = request.headers.get('Authorization')
    api_key = request.headers.get('X-API-Key')
    
    if auth_header:
        parts = auth_header.split()
        return parts[1] if len(parts) == 2 and parts[0].lower() == 'bearer' else parts[0]
    elif api_key:
        return api_key
    return None

# --- Helper para obtener metadata del valet key ---
def get_valet_key_metadata(token):
    """Obtiene la metadata de un valet key desde Redis"""
    valet_key = f"valet_key:{token}"
    metadata_json = cache.get(valet_key)
    if metadata_json:
        return json.loads(metadata_json)
    return None

# --- Helper para validar permisos del valet key ---
def validate_valet_key_permissions(token, required_scope=None, required_resource=None, required_method=None):
    """
    Valida que el valet key tenga los permisos necesarios
    - required_scope: ej. "read:proyectos", "write:usuarios"
    - required_resource: ej. {"proyecto_id": 1}, {"usuario_id": 2}
    - required_method: "GET", "POST", etc.
    """
    metadata = get_valet_key_metadata(token)
    if not metadata:
        return False, "Valet key no encontrado o expirado"
    
    # Validar expiración
    expires_at = datetime.fromisoformat(metadata.get("expires_at"))
    if datetime.now() > expires_at:
        return False, "Valet key expirado"
    
    # Validar scope si se requiere
    if required_scope:
        scopes = metadata.get("scopes", [])
        if required_scope not in scopes and "*" not in scopes:
            return False, f"Valet key no tiene el permiso requerido: {required_scope}"
    
    # Validar método HTTP si se requiere
    if required_method:
        allowed_methods = metadata.get("allowed_methods", [])
        if required_method not in allowed_methods and "*" not in allowed_methods:
            return False, f"Valet key no permite el método {required_method}"
    
    # Validar recursos específicos si se requiere
    if required_resource:
        resource_constraints = metadata.get("resource_constraints", {})
        for key, value in required_resource.items():
            if key in resource_constraints:
                allowed_values = resource_constraints[key]
                if isinstance(allowed_values, list) and value not in allowed_values:
                    return False, f"Valet key no tiene acceso al recurso {key}={value}"
                elif isinstance(allowed_values, int) and value != allowed_values:
                    return False, f"Valet key solo tiene acceso a {key}={allowed_values}"
    
    return True, None

# --- Gatekeeper: Decorador para validar tokens/API keys y Valet Keys ---
def gatekeeper_required(f):
    """Decorador que valida tokens/API keys antes de permitir acceso a endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({"error": "Token de acceso requerido. Use header 'Authorization: Bearer <token>' o 'X-API-Key: <token>'"}), 401
        
        # Primero verificar si es un valet key
        valet_key_metadata = get_valet_key_metadata(token)
        if valet_key_metadata:
            # Es un valet key, validar permisos básicos
            expires_at = datetime.fromisoformat(valet_key_metadata.get("expires_at"))
            if datetime.now() > expires_at:
                return jsonify({"error": "Valet key expirado"}), 403
            # Guardar metadata en request para uso en endpoints
            request.valet_key_metadata = valet_key_metadata
        else:
            # Es un token regular, validar como antes
            token_key = f"token:{token}"
            if not cache.exists(token_key):
                try:
                    with open(TOKENS_FILE) as f:
                        tokens_data = json.load(f)
                    if token not in [t.get("token") for t in tokens_data]:
                        return jsonify({"error": "Token inválido o expirado"}), 403
                    cache.setex(token_key, 3600, "valid")
                except Exception:
                    return jsonify({"error": "Token inválido o expirado"}), 403
            request.valet_key_metadata = None
        
        return f(*args, **kwargs)
    return decorated_function

# --- Decorador para validar permisos específicos de Valet Key ---
def valet_key_required(scope=None, resource_key=None, method=None):
    """
    Decorador que valida permisos específicos de Valet Key
    - scope: permiso requerido (ej. "read:proyectos")
    - resource_key: clave del recurso a validar (ej. "proyecto_id", "usuario_id")
    - method: método HTTP requerido
    """
    def decorator(f):
        @wraps(f)
        @gatekeeper_required
        def decorated_function(*args, **kwargs):
            token = get_token_from_request()
            valet_key_metadata = getattr(request, 'valet_key_metadata', None)
            
            # Si es un token regular (no valet key), permitir acceso completo
            if not valet_key_metadata:
                return f(*args, **kwargs)
            
            # Para valet keys, validar permisos específicos
            required_resource = None
            if resource_key and resource_key in kwargs:
                required_resource = {resource_key: kwargs[resource_key]}
            
            is_valid, error_msg = validate_valet_key_permissions(
                token, 
                required_scope=scope,
                required_resource=required_resource,
                required_method=method or request.method
            )
            
            if not is_valid:
                return jsonify({"error": error_msg or "Permisos insuficientes"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/proyectos/<int:proyecto_id>", methods=["GET"])
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

@app.route("/proyectos", methods=["GET"])
def get_all_proyectos():
    try:
        with open(DATA_FILE) as f:
            proyectos = json.load(f)
        return jsonify({"data": proyectos}), 200
    except Exception as e:
        return jsonify({"error": f"No se pudieron obtener los proyectos: {str(e)}"}), 500


@app.route("/proyectos", methods=["POST"])
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
        # Usar token de servicio interno para llamadas entre servicios
        headers = {"X-API-Key": INTERNAL_SERVICE_TOKEN}
        response = requests.get(USUARIOS_URL, headers=headers, timeout=2)
        response.raise_for_status()
        usuarios = response.json().get("data", response.json())

        # Resetea el circuito si todo va bien
        state.update({"fail_count": 0, "circuit_open": False})
        write_circuit_state(state)

    except Exception:
        state["fail_count"] += 1
        state["last_failure_time"] = time.time()
        if state["fail_count"] >= FAIL_THRESHOLD:
            state["circuit_open"] = True
            print(" Circuit breaker abierto: demasiadas fallas en usuarios-service.")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
