from flask import Flask, request, jsonify
import requests,os

app = Flask(__name__)

API_KEY = os.getenv("API_KEY", "defaultkey")

# Rutas base de los microservicios internos
SERVICES = {
    "usuarios": "http://usuarios-service:5001",
    "proyectos": "http://proyectos-service:5002",
    "tareas": "http://tareas-service:5003"
}

@app.route("/<service>/<path:endpoint>", methods=["GET", "POST"])
def gateway(service, endpoint):
    # Verificar si el servicio existe
    if service not in SERVICES:
        return jsonify({"error": "Servicio no encontrado"}), 404

    # Validar API Key
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        return jsonify({"error": "Acceso denegado: API Key inválida"}), 403

    # Reenviar solicitud al microservicio correspondiente
    target_url = f"{SERVICES[service]}/{endpoint}"

    try:
        if request.method == "GET":
            resp = requests.get(target_url)
        elif request.method == "POST":
            resp = requests.post(target_url, json=request.json)
        else:
            return jsonify({"error": "Método no soportado"}), 405

        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": f"No se pudo contactar al servicio destino: {str(e)}"}), 503


# Endpoint para probar salud del Gatekeeper
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "gateway"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
