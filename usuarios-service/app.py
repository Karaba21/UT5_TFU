from flask import Flask, request, jsonify
import json, os
import redis
import secrets
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)

DATA_FILE = "usuarios.json"
TOKENS_FILE = "tokens.json"

# Conexión a Redis para almacenar tokens activos
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

# Crear archivo de tokens si no existe
if not os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, "w") as f:
        json.dump([], f)

INTERNAL_SERVICE_TOKEN = "internal-service-token-2024"

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
        redis_client.setex(f"token:{INTERNAL_SERVICE_TOKEN}", 86400 * 365, "valid")  # 1 año
    except:
        pass  # Redis puede no estar disponible al inicio


if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

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
    metadata_json = redis_client.get(valet_key)
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
            if not redis_client.exists(token_key):
                with open(TOKENS_FILE) as f:
                    tokens_data = json.load(f)
                if token not in [t.get("token") for t in tokens_data]:
                    return jsonify({"error": "Token inválido o expirado"}), 403
                redis_client.setex(token_key, 3600, "valid")
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

# verificar estado del servicio 
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200



# --- Generar token/API key (sin autenticación requerida para facilitar demo) ---
@app.route("/tokens", methods=["POST"])
def generate_token():
    """Genera un nuevo token/API key para acceso a los servicios"""
    try:
        # Generar token seguro
        token = secrets.token_urlsafe(32)
        
        # Guardar token en archivo
        with open(TOKENS_FILE) as f:
            tokens_data = json.load(f)
        
        tokens_data.append({
            "token": token,
            "description": "API Key generada para acceso a servicios"
        })
        
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens_data, f, indent=4)
        
        # Guardar en Redis con expiración de 24 horas
        redis_client.setex(f"token:{token}", 86400, "valid")
        
        return jsonify({
            "mensaje": "Token generado exitosamente",
            "token": token,
            "instrucciones": "Use este token en el header 'Authorization: Bearer <token>' o 'X-API-Key: <token>'"
        }), 201
    except Exception as e:
        return jsonify({"error": f"No se pudo generar token: {str(e)}"}), 500

# --- Generar Valet Key (Patrón Valet Key) ---
@app.route("/valet-keys", methods=["POST"])
@gatekeeper_required
def generate_valet_key():
    """
    Genera un Valet Key con permisos limitados y específicos.
    El Valet Key permite acceso temporal a recursos específicos con permisos restringidos.
    
    Body esperado:
    {
        "scopes": ["read:proyectos", "read:usuarios"],  # Permisos específicos
        "allowed_methods": ["GET"],  # Métodos HTTP permitidos
        "resource_constraints": {  # Restricciones de recursos
            "proyecto_id": 1,  # Solo acceso a proyecto_id=1
            "usuario_id": [2, 3]  # Solo acceso a usuario_id 2 o 3
        },
        "expires_in_hours": 1  # Expiración en horas (default: 1)
    }
    """
    try:
        data = request.json or {}
        
        # Generar token seguro para el valet key
        valet_key_token = secrets.token_urlsafe(32)
        
        # Obtener configuración del request
        scopes = data.get("scopes", [])
        allowed_methods = data.get("allowed_methods", ["*"])
        resource_constraints = data.get("resource_constraints", {})
        expires_in_hours = data.get("expires_in_hours", 1)
        
        # Validar que haya al menos un scope
        if not scopes:
            return jsonify({"error": "Debe especificar al menos un scope (permiso)"}), 400
        
        # Crear metadata del valet key
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        valet_key_metadata = {
            "token": valet_key_token,
            "scopes": scopes,
            "allowed_methods": allowed_methods,
            "resource_constraints": resource_constraints,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now().isoformat(),
            "type": "valet_key"
        }
        
        # Guardar en Redis con expiración automática
        ttl_seconds = int(expires_in_hours * 3600)
        redis_client.setex(
            f"valet_key:{valet_key_token}",
            ttl_seconds,
            json.dumps(valet_key_metadata)
        )
        
        return jsonify({
            "mensaje": "Valet Key generado exitosamente",
            "valet_key": valet_key_token,
            "metadata": {
                "scopes": scopes,
                "allowed_methods": allowed_methods,
                "resource_constraints": resource_constraints,
                "expires_at": expires_at.isoformat()
            },
            "instrucciones": "Use este Valet Key en el header 'Authorization: Bearer <valet_key>' o 'X-API-Key: <valet_key>'. Este token tiene permisos limitados y expira automáticamente."
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"No se pudo generar Valet Key: {str(e)}"}), 500

@app.route("/usuarios", methods=["GET"])
@valet_key_required(scope="read:usuarios", method="GET")
def get_usuarios():
    try:
        with open(DATA_FILE) as f:
            usuarios = json.load(f)
        return jsonify({"data": usuarios}), 200
    except Exception as e:
        return jsonify({"error": f"Error al leer usuarios: {str(e)}"}), 500



@app.route("/usuarios", methods=["POST"])
@valet_key_required(scope="write:usuarios", method="POST")
def add_usuario():
    try:
        data = request.json


        if not data or not data.get("nombre"):
            return jsonify({"error": "El campo 'nombre' es obligatorio"}), 400

        with open(DATA_FILE) as f:
            usuarios = json.load(f)

      
        nuevo_id = (usuarios[-1]["id"] + 1) if usuarios else 1
        data["id"] = nuevo_id
        usuarios.append(data)

        with open(DATA_FILE, "w") as f:
            json.dump(usuarios, f, indent=4)

        return jsonify({
            "mensaje": "Usuario creado exitosamente",
            "data": data
        }), 201

    except Exception as e:
        return jsonify({"error": f"No se pudo crear el usuario: {str(e)}"}), 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
