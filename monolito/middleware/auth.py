"""
Módulo de autenticación compartido para el monolito.
Incluye validación de API Key del gateway, tokens, y Valet Keys.
"""
from flask import request, jsonify
import json
import os
import redis
import secrets
from functools import wraps
from datetime import datetime, timedelta

# Conexión a Redis compartida
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

# Archivos compartidos
TOKENS_FILE = "tokens.json"
INTERNAL_SERVICE_TOKEN = "internal-service-token-2024"

# API Key del gateway (migrado de gateway-service)
API_KEY = os.getenv("API_KEY", "supersecreta123")

# Inicializar archivo de tokens si no existe
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
        redis_client.setex(f"token:{INTERNAL_SERVICE_TOKEN}", 86400 * 365, "valid")  # 1 año
    except:
        pass  # Redis puede no estar disponible al inicio


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


def get_valet_key_metadata(token):
    """Obtiene la metadata de un valet key desde Redis"""
    valet_key = f"valet_key:{token}"
    metadata_json = redis_client.get(valet_key)
    if metadata_json:
        return json.loads(metadata_json)
    return None


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


def validate_api_key():
    """
    Valida la API Key del gateway (migrado de gateway-service).
    Retorna True si la API Key es válida, False en caso contrario.
    """
    key = request.headers.get("X-API-Key")
    if key and key == API_KEY:
        return True
    return False


def gatekeeper_required(f):
    """Decorador que valida tokens/API keys antes de permitir acceso a endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Primero verificar API Key del gateway (compatibilidad con gateway-service)
        if validate_api_key():
            # API Key válida del gateway, permitir acceso
            request.valet_key_metadata = None
            return f(*args, **kwargs)
        
        # Si no es API Key del gateway, validar token/valet key
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
                try:
                    with open(TOKENS_FILE) as f:
                        tokens_data = json.load(f)
                    if token not in [t.get("token") for t in tokens_data]:
                        return jsonify({"error": "Token inválido o expirado"}), 403
                    redis_client.setex(token_key, 3600, "valid")
                except Exception:
                    return jsonify({"error": "Token inválido o expirado"}), 403
            request.valet_key_metadata = None
        
        return f(*args, **kwargs)
    return decorated_function


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
            # Si pasó la validación de API Key del gateway, permitir acceso completo
            if validate_api_key():
                return f(*args, **kwargs)
            
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

