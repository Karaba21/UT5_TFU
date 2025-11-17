"""
Aplicación monolítica principal
Unifica todos los controllers y aplica validación de API Key del gateway
"""
from flask import Flask, jsonify
from controllers.usuarios_controller import usuarios_bp
from controllers.proyectos_controller import proyectos_bp
from controllers.tareas_controller import tareas_bp
from controllers.soap_controller import soap_bp

app = Flask(__name__)

# Registrar blueprints
app.register_blueprint(usuarios_bp)
app.register_blueprint(proyectos_bp)
app.register_blueprint(tareas_bp)
app.register_blueprint(soap_bp)


@app.route("/health", methods=["GET"])
def health():
    """Endpoint de salud del monolito"""
    return jsonify({"status": "ok", "service": "monolito"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
