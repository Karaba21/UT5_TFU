"""
Blueprint SOAP para el monolito
Implementa un servicio SOAP con XML para consultar estadísticas
"""
from flask import Blueprint, request, Response
from spyne import Application, rpc, ServiceBase, Unicode, Integer
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
import json
import os

soap_bp = Blueprint('soap', __name__)

# Definir el servicio SOAP
class EstadisticasService(ServiceBase):
    """Servicio SOAP para obtener estadísticas del sistema"""
    
    @rpc(Unicode, _returns=Unicode)
    def obtener_estadisticas(ctx, tipo):
        """
        Obtiene estadísticas del sistema según el tipo solicitado
        
        Args:
            tipo: Tipo de estadística ('proyectos', 'tareas', 'usuarios', 'general')
        
        Returns:
            XML con las estadísticas solicitadas
        """
        try:
            estadisticas = {}
            
            if tipo == 'proyectos' or tipo == 'general':
                proyectos_file = "proyectos.json"
                if os.path.exists(proyectos_file):
                    with open(proyectos_file) as f:
                        proyectos = json.load(f)
                    estadisticas['total_proyectos'] = len(proyectos)
                    estadisticas['proyectos'] = proyectos
                else:
                    estadisticas['total_proyectos'] = 0
                    estadisticas['proyectos'] = []
            
            if tipo == 'tareas' or tipo == 'general':
                tareas_file = "tareas.json"
                if os.path.exists(tareas_file):
                    with open(tareas_file) as f:
                        tareas = json.load(f)
                    estadisticas['total_tareas'] = len(tareas)
                    estadisticas['tareas'] = tareas
                else:
                    estadisticas['total_tareas'] = 0
                    estadisticas['tareas'] = []
            
            if tipo == 'usuarios' or tipo == 'general':
                usuarios_file = "usuarios.json"
                if os.path.exists(usuarios_file):
                    with open(usuarios_file) as f:
                        usuarios = json.load(f)
                    estadisticas['total_usuarios'] = len(usuarios)
                    estadisticas['usuarios'] = usuarios
                else:
                    estadisticas['total_usuarios'] = 0
                    estadisticas['usuarios'] = []
            
            # Convertir a XML manualmente para mantener compatibilidad
            xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<estadisticas>
    <tipo>{tipo}</tipo>
    <total_proyectos>{estadisticas.get('total_proyectos', 0)}</total_proyectos>
    <total_tareas>{estadisticas.get('total_tareas', 0)}</total_tareas>
    <total_usuarios>{estadisticas.get('total_usuarios', 0)}</total_usuarios>
    <timestamp>{json.dumps(estadisticas)}</timestamp>
</estadisticas>"""
            
            return xml_response
            
        except Exception as e:
            error_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<error>
    <mensaje>Error al obtener estadísticas: {str(e)}</mensaje>
</error>"""
            return error_xml
    
    @rpc(Integer, _returns=Unicode)
    def obtener_proyecto_por_id(ctx, proyecto_id):
        """
        Obtiene un proyecto específico por su ID en formato XML
        
        Args:
            proyecto_id: ID del proyecto a consultar
        
        Returns:
            XML con la información del proyecto
        """
        try:
            proyectos_file = "proyectos.json"
            if not os.path.exists(proyectos_file):
                return """<?xml version="1.0" encoding="UTF-8"?>
<error>
    <mensaje>Archivo de proyectos no encontrado</mensaje>
</error>"""
            
            with open(proyectos_file) as f:
                proyectos = json.load(f)
            
            proyecto = next((p for p in proyectos if p.get("id") == proyecto_id), None)
            
            if not proyecto:
                return f"""<?xml version="1.0" encoding="UTF-8"?>
<error>
    <mensaje>Proyecto con ID {proyecto_id} no encontrado</mensaje>
</error>"""
            
            xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<proyecto>
    <id>{proyecto.get('id', '')}</id>
    <nombre>{proyecto.get('nombre', '')}</nombre>
    <usuario_id>{proyecto.get('usuario_id', '')}</usuario_id>
    <descripcion>{proyecto.get('descripcion', '')}</descripcion>
</proyecto>"""
            
            return xml_response
            
        except Exception as e:
            error_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<error>
    <mensaje>Error al obtener proyecto: {str(e)}</mensaje>
</error>"""
            return error_xml


# Crear aplicación SOAP
soap_app = Application(
    [EstadisticasService],
    'estadisticas',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

# Crear aplicación WSGI
soap_wsgi = WsgiApplication(soap_app)

# Registrar ruta SOAP
@soap_bp.route('/soap', methods=['POST', 'GET'])
def soap_service():
    """Endpoint SOAP para consultar estadísticas"""
    status_headers = [None, None]
    
    def start_response(status, headers):
        status_headers[0] = status
        status_headers[1] = headers
    
    response = soap_wsgi(request.environ, start_response)
    
    # Convertir respuesta WSGI a string
    response_body = b''.join(response).decode('utf-8')
    
    # Crear respuesta Flask
    flask_response = Response(response_body, mimetype='text/xml; charset=utf-8')
    
    # Copiar headers si existen
    if status_headers[1]:
        for header, value in status_headers[1]:
            flask_response.headers[header] = value
    
    return flask_response

