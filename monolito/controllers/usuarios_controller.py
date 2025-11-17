"""
Blueprint de usuarios para el monolito
"""
from flask import Blueprint, request, jsonify
import json
import os
import secrets
from datetime import datetime, timedelta
from middleware.auth import (
    gatekeeper_required, 
    valet_key_required, 
    get_token_from_request,
    get_valet_key_metadata,
    redis_client,
    TOKENS_FILE
)

usuarios_bp = Blueprint('usuarios', __name__)

DATA_FILE = "usuarios.json"

# Crear archivo si no existe
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)


@usuarios_bp.route("/usuarios", methods=["GET"])
@valet_key_required(scope="read:usuarios", method="GET")
def get_usuarios():
    try:
        with open(DATA_FILE) as f:
            usuarios = json.load(f)
        return jsonify({"data": usuarios}), 200
    except Exception as e:
        return jsonify({"error": f"Error al leer usuarios: {str(e)}"}), 500


@usuarios_bp.route("/usuarios", methods=["POST"])
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


@usuarios_bp.route("/tokens", methods=["POST"])
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


@usuarios_bp.route("/valet-keys", methods=["POST"])
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
