# ==================================================
#  IMPORTS
# ==================================================
from forms import LoginForm, SolicitudForm, RecetaForm
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response
from flask_wtf import CSRFProtect  # Para protección CSRF
from flask_wtf.csrf import CSRFError
from forms import RecetaForm
from functools import wraps
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from datetime import datetime, date
import csv
from io import StringIO
import socket
import json
import os
from dotenv import load_dotenv
import logging
import html
import requests
import xml.etree.ElementTree as ET
from flask import redirect, url_for, session
from functools import wraps

# <-- Cambio: librerías para sesión y límite de peticiones
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ==================================================
#  Cargar variables de entorno desde .env
# ==================================================
load_dotenv()
print(f"DB_PASSWORD desde .env: {repr(os.getenv('DB_PASSWORD'))}")


app = Flask(__name__)
app.secret_key = "dmc_demian_pro1"  # o la que tengas en tu .env
csrf = CSRFProtect(app)

# ==================================================
#  Configuración de sesiones (almacenamiento en servidor)
# ==================================================
# <-- Cambio: Configurar Flask-Session para almacenar la sesión en el servidor,
# en vez de la cookie firmada por defecto.
app.config['SESSION_TYPE'] = 'filesystem'  # O "redis", etc.
app.config['SESSION_PERMANENT'] = False
Session(app)

# Opcional: endurece la seguridad de las cookies
app.config['SESSION_COOKIE_SECURE'] = False  # <-- Sólo enviar cookie por HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # <-- Evita que JS lea la cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # <-- Controla el envío en peticiones externas
app.config['WTF_CSRF_CHECK_DEFAULT'] = False

# ==================================================
#  Configuración de Flask-Limiter (limitar requests)
# ==================================================
limiter = Limiter(
    get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)

limiter.init_app(app)
# ==================================================
#  Configuración de logging
# ==================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================================================
#  Variables de entorno para la DB
# ==================================================
# DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_HOST = os.getenv('DB_HOST', 'db')
DB_NAME = os.getenv('DB_NAME', 'recetas_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'CANal1')
DB_PORT = os.getenv('DB_PORT', '5432')


# ==================================================
#  Conexión a la base de datos
# ==================================================
def get_db_connection():
    try:
        conn_string = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} port={DB_PORT}"
        logger.info(
            f"Conectando a la base de datos en host {DB_HOST}, DB {DB_NAME}, usuario {DB_USER}, puerto {DB_PORT}")
        conn = psycopg2.connect(conn_string + f" password={DB_PASSWORD}")
        conn.set_client_encoding('UTF8')  # Asegurar que la codificación sea UTF-8
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {repr(e)}")
        raise


# ==================================================
#  Decoradores de roles y seguridad
# ==================================================


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role')
            print(f"Rol del usuario en sesión: {user_role}")  # Agrega esta línea para depurar
            if user_role not in roles:
                return redirect(url_for('login'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def login_required(f):
    """ Verifica si el usuario ha iniciado sesión. """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Por favor, inicia sesión primero.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """ Verifica si el usuario es admin. """

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Acceso denegado: Se requieren permisos de administrador.')
            return redirect(url_for('formulario'))
        return f(*args, **kwargs)

    return decorated_function


# ==================================================
#  Funciones Auxiliares
# ==================================================
def construir_receta_json(receta, conn):
    """
    Construye el JSON necesario para enviar a Mirth basado en la receta y sus prescripciones.
    """
    try:
        logger.info("Iniciando construir_receta_json")

        receta_id = receta[0]
        rut = receta[1]
        nombre = receta[2]
        primer_apellido = receta[3]
        segundo_apellido = receta[4]
        fecha_nacimiento = receta[5]  # datetime.date o datetime.datetime
        sexo = receta[6]
        nombre_profesional = receta[7]
        primer_apellido_profesional = receta[8]
        segundo_apellido_profesional = receta[9]
        run_profesional = receta[10]
        tipo_profesional = receta[11]
        codigo_diagnostico = receta[12]
        descripcion_diagnostico = receta[13]
        identificador_cama = receta[14]
        identificador_servicio = receta[15]
        fecha_hora_mensaje = receta[16]  # datetime.datetime

        logger.info(
            f"Datos de la receta: id={receta_id}, rut={rut}, nombre={nombre}, fecha_nacimiento={fecha_nacimiento}, ...")

        # Obtener descripción del servicio
        descripcion_servicio = obtener_descripcion_servicio(str(identificador_servicio))
        logger.info(f"Descripción del servicio: {descripcion_servicio}")

        # Obtener prescripciones
        cur = conn.cursor()
        cur.execute("""
            SELECT codigo_producto, producto, dosis_por_toma,
                   unidad_entrega, posologia, duracion, via, observacion
            FROM prescripciones
            WHERE receta_id = %s
        """, (receta_id,))
        prescripciones = cur.fetchall()
        cur.close()
        logger.info(f"Prescripciones encontradas: {prescripciones}")

        prescripciones_json = []
        for p in prescripciones:
            prescripciones_json.append({
                "CodigoProducto": p[0],
                "Producto": p[1],
                "DosisPorToma": p[2],
                "UnidadEntrega": p[3],
                "Posologia": p[4],
                "Duracion": p[5],
                "Via": p[6],
                "Observacion": p[7]
            })

        # Manejo de FechaNacimiento
        try:
            if isinstance(fecha_nacimiento, (datetime, date)):
                fecha_nacimiento_str = fecha_nacimiento.strftime("%Y-%m-%d")
                logger.info(f"Fecha de nacimiento formateada: {fecha_nacimiento_str}")
            else:
                fecha_nacimiento_str = fecha_nacimiento  # Asume que ya es string
                logger.info(f"Fecha de nacimiento ya es string: {fecha_nacimiento_str}")
        except Exception as e:
            logger.error(f"Error al formatear FechaNacimiento: {e}")
            raise

        receta_json = {
            "ParametroNotificarSolicitudDispensacion": {
                "IdTransaccion": f"RC{receta_id:04d}",
                "CodigoEstablecimiento": "HEC",
                "FechaHoraMensaje": fecha_hora_mensaje.strftime("%Y-%m-%d %H:%M:%S"),
                "TipoIdentificacion": 1,
                "Receta": {
                    "IdentificadorReceta": f"RC{receta_id:04d}",
                    "TipoReceta": "Receta_Contingencia",
                    "FechaReceta": fecha_hora_mensaje.strftime("%Y-%m-%d %H:%M:%S"),
                    "Paciente": {
                        "paciente_run": rut,
                        "Nombres": nombre,
                        "FechaNacimiento": fecha_nacimiento_str if fecha_nacimiento else "",
                        "Sexo": sexo
                    },
                    "Profesional": {
                        "Nombres": nombre_profesional,
                        "PrimerApellido": primer_apellido_profesional,
                        "SegundoApellido": segundo_apellido_profesional,
                        "Run": run_profesional,
                        "TipoProfesional": tipo_profesional
                    },
                    "Diagnostico": {
                        "CodigoDiagnostico": codigo_diagnostico,
                        "DescripcionDiagnostico": descripcion_diagnostico,
                        "EsPrincipal": 1
                    },
                    "Prescripciones": prescripciones_json,
                    "Ubicacion": {
                        "IdentificadorServicio": identificador_servicio,
                        "DescripcionServicio": descripcion_servicio,
                        "IdentificadorCama": identificador_cama
                    }
                }
            }
        }

        logger.info(f"Receta JSON construida: {receta_json}")
        return receta_json

    except Exception as e:
        logger.error(f"Error en construir_receta_json: {e}")
        raise


def obtener_descripcion_servicio(id_servicio):
    """
    Obtiene la descripción del servicio basado en el identificador.
    Debes ajustar este diccionario según tus servicios reales.
    """
    servicios = {
        "1": "MEDICINA 1",
        "2": "MEDICINA 2",
        "3": "MEDICINA 3",
        "4": "GERIATRIA",
        "5": "GINECOLOGIA - ARO",
        "6": "PUERPERIO",
        "7": "CIRUGIA 1",
        "8": "CIRUGIA 2",
        "9": "MQI5TO PISO",
        "10": "PEDIATRIA AGUDO",
        "11": "PEDIATRIA BASICO",
        "12": "MQI2DO PISO",
        "13": "HOSPITALIZACION DOMICILIARIA",
        "14": "NEONATOLOGIA",
        "15": "SAIP",
        "16": "UPC INFANTIL",
        "17": "UPC ADULTO",
        "18": "MQI3ER PISO",
        "19": "HOSPITAL DE DIA - SALUD MENTAL",
        "20": "URGENCIA PEDIATRICA",
        "21": "URGENCIA MATERNIDAD",
        "22": "CMA",
        "23": "URGENCIA ADULTO"
    }
    return servicios.get(id_servicio, "Desconocido")


def enviar_json_mirth(json_data, host='localhost', port=6661):
    """
    Envía el JSON a Mirth a través de un socket.
    """
    try:
        logger.info(f"Enviando JSON a Mirth: {json_data}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(10)  # Timeout de 10 segundos
            sock.connect((host, port))
            mensaje_json = '\x0b' + json.dumps(json_data) + '\x1c' + '\x0d'
            sock.sendall(mensaje_json.encode('utf-8'))
            response = sock.recv(1024)
            logger.info(f"Respuesta de Mirth: {response.decode('utf-8')}")
            return response.decode('utf-8')
    except socket.timeout:
        logger.error("Timeout al conectar con Mirth.")
        return None
    except Exception as e:
        logger.error(f"Error enviando JSON a Mirth: {e}")
        return None


def calcular_edad(fecha_nacimiento):
    today = date.today()
    return today.year - fecha_nacimiento.year - (
            (today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


# ==================================================
#  Servicio SOAP (Fonasa) - ejemplo
# ==================================================
def obtener_datos_paciente(rut):
    """
    Ejemplo de consulta a un servicio SOAP (Fonasa).
    Ajustar según tu servicio real o descomentar si no lo usarás.
    """
    try:
        rut_numero = rut[:-1]
        rut_dv = rut[-1]

        solicitud_json = {
            "Aplicacion_Envia": "HIS",
            "Cod_Establecimiento": "11101",
            "Aplicacion_Recibe": "FONASA",
            "Tipo_Mensaje": "Validador FONASA",
            "Fecha_Hora_Mensaje": datetime.now().strftime("%Y%m%d%H%M%S"),
            "Usuario": "XXXXXXXXX",
            "Datos_Paciente": [
                {
                    "RUT_Beneficiario": rut_numero,
                    "DGV_Beneficiario": rut_dv
                }
            ]
        }

        solicitud_json_str = json.dumps(solicitud_json)
        soap_envelope = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.connectors.connect.mirth.com/">
   <soapenv:Header/>
   <soapenv:Body>
      <ws:acceptMessage>
         <arg0><![CDATA[{solicitud_json_str}]]></arg0>
      </ws:acceptMessage>
   </soapenv:Body>
</soapenv:Envelope>
"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        }

        # Ajusta la URL de tu servicio SOAP
        response = requests.post('http://localhost:9091/services/FONASA', data=soap_envelope, headers=headers)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            namespaces = {
                'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns2': 'http://ws.connectors.connect.mirth.com/'
            }
            response_element = root.find('.//ns2:acceptMessageResponse', namespaces)
            if response_element is not None:
                return_element = response_element.find('return')
                if return_element is not None:
                    xml_data = html.unescape(return_element.text)
                    xml_root = ET.fromstring(xml_data)
                    ns = {'cert': 'http://certificadorprevisional.fonasa.gov.cl.ws/'}
                    beneficiario = xml_root.find('.//cert:beneficiarioTO', ns)
                    if beneficiario is not None:
                        datos_paciente = {
                            "rutbenef": beneficiario.find('cert:rutbenef', ns).text,
                            "dgvbenef": beneficiario.find('cert:dgvbenef', ns).text,
                            "nombres": beneficiario.find('cert:nombres', ns).text,
                            "apell1": beneficiario.find('cert:apell1', ns).text,
                            "apell2": beneficiario.find('cert:apell2', ns).text,
                            "fechaNacimiento": beneficiario.find('cert:fechaNacimiento', ns).text,
                            "genero": beneficiario.find('cert:genero', ns).text,
                            "generoDes": beneficiario.find('cert:generoDes', ns).text,
                            "direccion": beneficiario.find('cert:direccion', ns).text,
                            "telefono": beneficiario.find('cert:telefono', ns).text
                        }
                        return datos_paciente
                    else:
                        logger.error("El elemento <beneficiarioTO> no se encontró.")
                        return None
                else:
                    logger.error("El elemento <return> no se encontró.")
                    return None
            else:
                logger.error("El elemento <ns2:acceptMessageResponse> no se encontró.")
                return None
        else:
            logger.error(f"Error en la respuesta del webservice: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error al consultar el webservice: {e}")
        return None


# ==================================================
#  Rutas principales
# ==================================================
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/formulario', methods=['GET'])
@roles_required('medico', 'usuario', 'admin')  # Ajusta según tus roles
def formulario():
    """
    Muestra el formulario (GET), inyectando el token CSRF dentro de form.hidden_tag().
    """
    form = RecetaForm()  # Instancia
    return render_template('formulario.html', form=form)


@app.route('/historial')
@roles_required('usuario', 'admin', 'medico')  # Ajusta según roles que puedan acceder
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    # Si quieres filtrar para que un usuario sólo vea SU historial,
    # podrías validar "if session['role'] == 'usuario':" aquí
    # y filtrar el RUT asociado en la base de datos.
    cur.execute("""
        SELECT id, rut, nombre, primer_apellido, segundo_apellido, fecha_nacimiento, sexo,
               fecha_hora_mensaje, run_profesional, nombre_profesional, primer_apellido_profesional
        FROM recetas
        ORDER BY fecha_hora_mensaje DESC
    """)
    recetas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', recetas=recetas)


# ==================================================
#  Búsqueda de recetas y descarga CSV
# ==================================================
@app.route('/buscar_recetas', methods=['POST'])
@roles_required('usuario', 'admin', 'medico')
def buscar_recetas():
    rut = request.form.get('rut')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT id,
               rut,
               nombre,
               primer_apellido,
               segundo_apellido,
               fecha_nacimiento,
               sexo,
               fecha_hora_mensaje,
               run_profesional,
               nombre_profesional,
               primer_apellido_profesional
        FROM recetas
        WHERE 1=1
    """
    params = {}

    # <-- Cambio: si rol = 'usuario' y quieres mostrar solo su RUT, haz:
    if session['role'] == 'usuario':
        # Supongamos que en la sesión tienes session['rut_usuario']
        # para que un usuario normal solo pueda ver su RUT:
        query += " AND rut = %(rut_session)s"
        params['rut_session'] = session.get('rut_usuario', None)
    else:
        # Si es admin o medico, puede filtrar por RUT
        if rut:
            query += " AND rut = %(rut)s"
            params['rut'] = rut

    # Manejo de fechas
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query += " AND fecha_hora_mensaje BETWEEN %(fecha_inicio)s AND %(fecha_fin)s"
            params['fecha_inicio'] = fecha_inicio_obj
            params['fecha_fin'] = fecha_fin_obj
        except ValueError:
            flash("Error: Formato de fecha incorrecto.")
            return redirect(url_for('formulario'))
    elif fecha_inicio:
        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            query += " AND fecha_hora_mensaje >= %(fecha_inicio)s"
            params['fecha_inicio'] = fecha_inicio_obj
        except ValueError:
            flash("Error: Formato de fecha incorrecto.")
            return redirect(url_for('formulario'))
    elif fecha_fin:
        try:
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d')
            query += " AND fecha_hora_mensaje <= %(fecha_fin)s"
            params['fecha_fin'] = fecha_fin_obj
        except ValueError:
            flash("Error: Formato de fecha incorrecto.")
            return redirect(url_for('formulario'))

    query += " ORDER BY fecha_hora_mensaje DESC"
    cur.execute(query, params)
    recetas = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('resultados.html', recetas=recetas)


@app.route('/descargar_csv', methods=['GET'])
@roles_required('usuario', 'admin', 'medico')
def descargar_csv():
    rut = request.args.get('rut')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT id, 
               rut, 
               nombre, 
               primer_apellido, 
               segundo_apellido, 
               fecha_nacimiento, 
               sexo, 
               fecha_hora_mensaje, 
               run_profesional,
               nombre_profesional,
               primer_apellido_profesional
        FROM recetas
        WHERE 1=1
    """
    params = {}

    if session['role'] == 'usuario':
        query += " AND rut = %(rut_session)s"
        params['rut_session'] = session.get('rut_usuario', None)
    else:
        if rut:
            query += " AND rut = %(rut)s"
            params['rut'] = rut

    if fecha_inicio and fecha_fin:
        query += " AND fecha_hora_mensaje BETWEEN %(fecha_inicio)s AND %(fecha_fin)s"
        params['fecha_inicio'] = fecha_inicio
        params['fecha_fin'] = fecha_fin
    elif fecha_inicio:
        query += " AND fecha_hora_mensaje >= %(fecha_inicio)s"
        params['fecha_inicio'] = fecha_inicio
    elif fecha_fin:
        query += " AND fecha_hora_mensaje <= %(fecha_fin)s"
        params['fecha_fin'] = fecha_fin

    query += " ORDER BY fecha_hora_mensaje DESC"
    cur.execute(query, params)
    recetas = cur.fetchall()

    si = StringIO()
    csv_writer = csv.writer(si)
    csv_writer.writerow(['ID', 'RUT', 'Nombre', 'Primer Apellido', 'Segundo Apellido',
                         'Fecha de Nacimiento', 'Sexo', 'Fecha de Receta', 'Run Profesional',
                         'Nombre Profesional', 'Primer Apellido Profesional'])

    for receta in recetas:
        csv_writer.writerow(receta)

    cur.close()
    conn.close()

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=recetas.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ==================================================
#  Búsqueda de diagnósticos (ej. AJAX)
# ==================================================
@app.route('/buscar_diagnostico')
@roles_required('usuario', 'admin', 'medico')
def buscar_diagnostico():
    termino = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, descripcion
        FROM diagnosticos
        WHERE descripcion ILIKE %s
        ORDER BY id
        LIMIT 10
    """, (f'%{termino}%',))
    resultados = cur.fetchall()
    cur.close()
    conn.close()

    diagnosticos = []
    for r in resultados:
        diagnosticos.append({
            "id": r[0],
            "descripcion": r[1]
        })
    return jsonify(diagnosticos)


# ==================================================
#  Endpoints para obtener paciente
# ==================================================
@app.route('/obtener_datos_paciente', methods=['GET'])
@roles_required('usuario', 'admin', 'medico')
def ruta_obtener_datos_paciente():
    rut = request.args.get('rut')
    datos_paciente = obtener_datos_paciente(rut)
    if datos_paciente:
        return jsonify(datos_paciente)
    else:
        return jsonify({'error': 'No se encontraron datos del paciente'}), 500


# ==================================================
#  Ruta /crear_solicitud_receta (médico)
# ==================================================
def separar_nombre_apellidos(nombre_completo):
    """
    Separa un string en (nombres, primer_apellido, segundo_apellido).
    Ajusta esta lógica según tu convención:
      - 3 palabras => las 2 primeras son 'nombres', la última es 'primer_apellido'.
      - 4 o más => las 2 últimas van a apellidos, el resto a nombres.
      - etc.
    """
    partes = nombre_completo.strip().split()
    if len(partes) == 0:
        return (".", ".", ".")
    elif len(partes) == 1:
        # "KRISSE"
        return (partes[0], ".", ".")
    elif len(partes) == 2:
        # "KRISSE DANIELA"
        return (partes[0], partes[1], ".")
    elif len(partes) == 3:
        # "KRISSE DANIELA VERA"
        return (" ".join(partes[:2]), partes[2], ".")
    else:
        # 4+ =>
        # e.g. "KRISSE DANIELA VERA SOTO" => nombres="KRISSE DANIELA", primer="VERA", seg="SOTO"
        nombres = " ".join(partes[:-2])
        primer_apellido = partes[-2]
        segundo_apellido = partes[-1]
        return (nombres, primer_apellido, segundo_apellido)


@app.route('/crear_solicitud_receta', methods=['POST'])
@roles_required('medico')  # Solo rol 'medico' puede crear solicitudes
def crear_solicitud_receta():
    """
    Recibe el formulario de 'solicitudes.html' (método POST).
    Guarda la receta en la tabla 'recetas' y crea registro 'pending' en solicitudes_recetas.
    """
    conn = None
    try:
        # 1) Capturar campos del form
        rut = request.form.get('rut', '').strip()
        nombre_completo = request.form.get('nombre', '').strip()  # "KRISSE DANIELA VERA" etc.
        fecha_nacimiento = request.form.get('fecha_nacimiento', '').strip()
        sexo = request.form.get('sexo', '').strip()
        diagnostico = request.form.get('diagnostico', '').strip()
        servicio = request.form.get('servicio', '').strip()
        cama = request.form.get('cama', '').strip()

        # 2) Separar el 'nombre' (nombres + apellidos)
        nombres_paciente, primer_apellido_paciente, segundo_apellido_paciente = separar_nombre_apellidos(
            nombre_completo)

        # 3) Datos del profesional
        run_profesional = request.form.get('run_profesional', '').strip()
        nombre_profesional = request.form.get('nombre_profesional', '').strip()
        apellido_profesional = request.form.get('apellido_profesional', '').strip()
        tipo_profesional = request.form.get('tipo_profesional', '').strip()

        # Dividir el apellido del profesional en 2 si tu DB lo requiere
        apell_split = apellido_profesional.split(' ', 1)
        primer_apellido_profesional = apell_split[0] if len(apell_split) > 0 else '.'
        segundo_apellido_profesional = apell_split[1] if len(apell_split) > 1 else '.'

        # 4) Arrays de medicamentos
        medicamentos = request.form.getlist('medicamento[]')
        codigos_meds = request.form.getlist('codigo_medicamento[]')
        dosis_por_toma = request.form.getlist('dosis_por_toma[]')
        unidad_dosis = request.form.getlist('unidad_dosis[]')
        posologias = request.form.getlist('posologia[]')
        duraciones = request.form.getlist('duracion[]')
        vias = request.form.getlist('via[]')
        observaciones = request.form.getlist('observacion[]')

        # 5) Conectar a la DB
        conn = get_db_connection()
        cur = conn.cursor()

        # 6) Insertar en la tabla 'recetas'
        # Ajusta a tu esquema real (si se llama 'nombre' la columna, en vez de 'nombres')
        cur.execute("""
            INSERT INTO recetas (
                rut,
                nombre,                 -- O 'nombres' si así se llama la columna
                primer_apellido,
                segundo_apellido,
                fecha_nacimiento,
                sexo,

                nombre_profesional,
                primer_apellido_profesional,
                segundo_apellido_profesional,
                run_profesional,
                tipo_profesional,

                codigo_diagnostico,
                descripcion_diagnostico,

                identificador_servicio,
                identificador_cama,

                fecha_hora_mensaje
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                NOW()
            )
            RETURNING id
        """, (
            rut,
            nombres_paciente,  # p.ej. "KRISSE DANIELA"
            primer_apellido_paciente,  # p.ej. "VERA"
            segundo_apellido_paciente,  # p.ej. ".", si no hay 2do
            fecha_nacimiento,
            sexo,

            nombre_profesional,
            primer_apellido_profesional,
            segundo_apellido_profesional,
            run_profesional,
            tipo_profesional,

            diagnostico[:5],  # si la BD espera un código corto (opcional)
            diagnostico,

            servicio,
            cama
        ))
        receta_id = cur.fetchone()[0]

        # 7) Insertar prescripciones (tabla prescripciones)
        num_prescripciones = min(
            len(medicamentos),
            len(codigos_meds),
            len(dosis_por_toma),
            len(unidad_dosis),
            len(posologias),
            len(duraciones),
            len(vias),
            len(observaciones)
        )
        for i in range(num_prescripciones):
            med = medicamentos[i].strip()
            cod_med = codigos_meds[i].strip()
            dosis = dosis_por_toma[i].strip()
            unidad = unidad_dosis[i].strip()
            posol = posologias[i].strip()
            dur = duraciones[i].strip()
            via = vias[i].strip()
            obs = observaciones[i].strip()

            cur.execute("""
                INSERT INTO prescripciones (
                    receta_id, codigo_producto, producto, dosis_por_toma,
                    unidad_entrega, posologia, duracion, via, observacion
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                receta_id,
                cod_med,
                med,
                dosis or None,
                unidad,
                posol,
                dur or None,
                via,
                obs
            ))

        # 8) Insertar en solicitudes_recetas (estado pending)
        cur.execute("""
            INSERT INTO solicitudes_recetas (
                receta_id, estado, creada_por, creada_en
            )
            VALUES (%s, %s, %s, NOW())
        """, (receta_id, 'pending', session.get('username', 'desconocido')))

        conn.commit()
        return jsonify({"ok": True, "message": "Solicitud de receta creada con éxito."})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en /crear_solicitud_receta: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/obtener_datos_profesional', methods=['GET'])
@roles_required('medico')
def obtener_datos_profesional():
    username = session.get('username')

    if not username:
        return jsonify({"error": "No se encontró el usuario en la sesión"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT run_profesional, nombre_profesional, primer_apellido_profesional,
                   segundo_apellido_profesional, tipo_profesional
            FROM usuarios
            WHERE username = %s
        """, (username,))
        profesional = cur.fetchone()
        if profesional:
            return jsonify({
                "run_profesional": profesional[0],
                "nombre_profesional": profesional[1],
                "primer_apellido_profesional": profesional[2],
                "segundo_apellido_profesional": profesional[3],
                "tipo_profesional": profesional[4]
            })
        else:
            return jsonify({"error": "No se encontraron datos del profesional"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ==================================================
#  Rutas para solicitudes
# ==================================================
from forms import SolicitudForm  # Importa tu formulario


@app.route('/solicitudes')
@login_required
def solicitudes():
    if session.get('role') not in ['medico', 'usuario', 'admin']:
        flash('Acceso denegado.')
        return redirect(url_for('formulario'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.id, r.rut, r.nombre, sr.estado, sr.creada_en, sr.creada_por
        FROM solicitudes_recetas sr
        JOIN recetas r ON sr.receta_id = r.id
        WHERE sr.estado = 'pendiente'
    """)
    solicitudes = cur.fetchall()
    cur.close()
    conn.close()

    form = SolicitudForm()  # Crear el formulario

    return render_template('solicitudes.html', solicitudes=solicitudes, form=form)


# En tu app.py
@app.template_filter('datetimeformat')
def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    return value.strftime(format)


# ... tus otros imports ...

@app.route('/gestionar_solicitud', methods=['GET'])
@roles_required('usuario', 'admin')
def gestionar_solicitud():
    """
    Muestra y filtra las solicitudes en estado pending, approved, canceled, etc.
    Con posibilidad de buscar por ID, rut, nombre paciente, estado, etc.
    """
    # 1) Capturar parámetros de filtro desde la URL (GET)
    id_sol = request.args.get('id_solicitud', '')
    rut_pac = request.args.get('rut_paciente', '')
    nom_pac = request.args.get('nombre_paciente', '')
    estado = request.args.get('estado', '')

    # 2) Construir la query base
    #    - Observa que en el SELECT concatenamos (r.nombre || ' ' || r.primer_apellido || ' ' || r.segundo_apellido)
    #      para formar el nombre completo.
    #    - Usamos to_char para formatear la fecha/hora sin milisegundos.
    query = """
        SELECT sr.id,
               r.rut,
               (r.nombre || ' ' || r.primer_apellido || ' ' || r.segundo_apellido) AS nombre_completo,
               sr.estado,
               to_char(sr.creada_en, 'YYYY-MM-DD HH24:MI:SS') AS creada_en_fmt,
               sr.creada_por
        FROM solicitudes_recetas sr
        JOIN recetas r ON sr.receta_id = r.id
        WHERE 1=1
    """
    params = []

    # 3) Añadir filtros condicionalmente
    if id_sol:
        query += " AND sr.id = %s"
        params.append(id_sol)
    if rut_pac:
        query += " AND r.rut ILIKE %s"
        params.append(f"%{rut_pac}%")
    if nom_pac:
        # Filtramos el 'nombre completo' que concatenamos
        query += " AND (r.nombre || ' ' || r.primer_apellido || ' ' || r.segundo_apellido) ILIKE %s"
        params.append(f"%{nom_pac}%")
    if estado:
        query += " AND sr.estado = %s"
        params.append(estado)

    # 4) Ordenar por creada_en desc
    query += " ORDER BY sr.creada_en DESC"

    # 5) Ejecutar la query
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    solicitudes = cur.fetchall()
    cur.close()
    conn.close()

    # 6) Renderizar la plantilla
    return render_template('gestionar_solicitud.html', solicitudes=solicitudes)


@app.route('/aprobar_solicitud', methods=['POST'])
@roles_required('usuario', 'admin')
def aprobar_solicitud():
    """
    Actualiza la solicitud con estado='pending' a estado='approved'.
    Envía la receta correspondiente a Mirth.
    Devuelve JSON con {ok: True} o error.
    """
    logger.info("DEBUG: llegó la solicitud a /aprobar_solicitud")

    solicitud_id = request.form.get('solicitud_id')
    if not solicitud_id:
        logger.warning("Falta solicitud_id en la solicitud POST")
        return jsonify({"ok": False, "error": "Falta solicitud_id."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1) Verificar que la solicitud está en estado 'pending'
        cur.execute("""
            SELECT estado, receta_id
            FROM solicitudes_recetas
            WHERE id = %s
        """, (solicitud_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            logger.warning(f"Solicitud no encontrada: id={solicitud_id}")
            return jsonify({"ok": False, "error": "Solicitud no encontrada."}), 404

        estado_actual = row[0]
        receta_id = row[1]

        if estado_actual != 'pending':
            conn.rollback()
            logger.warning(f"Solicitud id={solicitud_id} no está en estado 'pending' (estado actual: {estado_actual})")
            return jsonify({"ok": False, "error": "La solicitud no está en estado 'pending'."}), 400

        # 2) Marcar estado='approved'
        cur.execute("""
            UPDATE solicitudes_recetas
            SET estado = 'approved',
                aprobada_en = NOW(),
                aprobada_por = %s
            WHERE id = %s
        """, (session.get('username', 'desconocido'), solicitud_id))
        logger.info(f"Solicitud id={solicitud_id} marcada como 'approved' por {session.get('username', 'desconocido')}")

        # 3) Obtener la receta y construir el JSON
        cur.execute("SELECT * FROM recetas WHERE id = %s", (receta_id,))
        receta = cur.fetchone()
        if not receta:
            conn.rollback()
            logger.error(f"No se encontró la receta asociada: receta_id={receta_id}")
            return jsonify({"ok": False, "error": "No se encontró la receta asociada."}), 404

        logger.info(f"Receta encontrada para receta_id={receta_id}")

        # 4) Usar tu función construir_receta_json
        receta_json = construir_receta_json(receta, conn)
        logger.info(f"JSON construido para receta_id={receta_id}: {receta_json}")

        # 5) Enviar a Mirth
        respuesta_mirth = enviar_json_mirth(receta_json)
        logger.info(f"Respuesta de Mirth para receta_id={receta_id}: {respuesta_mirth}")

        conn.commit()
        return jsonify({"ok": True, "respuesta_mirth": respuesta_mirth})

    except Exception as e:
        conn.rollback()
        logger.error(f"Error al aprobar la solicitud: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/cancelar_solicitud', methods=['POST'])
@roles_required('usuario', 'admin')
def cancelar_solicitud():
    """
    Actualiza la solicitud con estado='pending' a estado='canceled'.
    Devuelve JSON con {ok: True} o error.
    """
    solicitud_id = request.form.get('solicitud_id')
    if not solicitud_id:
        return jsonify({"ok": False, "error": "Falta solicitud_id."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1) Verificar que la solicitud está en estado 'pending'
        cur.execute("""
            SELECT estado
            FROM solicitudes_recetas
            WHERE id = %s
        """, (solicitud_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"ok": False, "error": "Solicitud no encontrada."}), 404

        if row[0] != 'pending':
            conn.rollback()
            return jsonify({"ok": False, "error": "La solicitud no está en estado 'pending'."}), 400

        # 2) Marcar estado='canceled'
        cur.execute("""
            UPDATE solicitudes_recetas
            SET estado = 'canceled',
                cancelada_en = NOW(),
                cancelada_por = %s
            WHERE id = %s
        """, (session.get('username', 'desconocido'), solicitud_id))
        conn.commit()
        return jsonify({"ok": True})

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ==================================================
# NUEVA RUTA: Editar Solicitud
# ==================================================
@app.route('/editar_solicitud/<int:id>', methods=['GET', 'POST'])
@roles_required('usuario', 'admin')
def editar_solicitud(id):
    """
    Permite a rol 'usuario' o 'admin' editar SOLO los medicamentos
    asociados a la receta. No toca rut, nombre, etc.
    La solicitud debe estar en estado 'pending'.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Verificar que la solicitud está 'pending'
    cur.execute("""
        SELECT sr.id, sr.receta_id, sr.estado
        FROM solicitudes_recetas sr
        WHERE sr.id = %s
    """, (id,))
    sol_row = cur.fetchone()
    if not sol_row:
        flash("Solicitud no encontrada.")
        cur.close()
        conn.close()
        return redirect(url_for('gestionar_solicitud'))

    solicitud_id = sol_row[0]
    receta_id = sol_row[1]
    estado = sol_row[2]

    if estado != 'pending':
        flash("Solo se pueden editar medicamentos en solicitudes 'pending'.")
        cur.close()
        conn.close()
        return redirect(url_for('gestionar_solicitud'))

    if request.method == 'POST':
        # POST => actualizar medicamentos
        try:
            # Obtener arrays del formulario
            prescripcion_ids = request.form.getlist('prescripcion_id[]')  # hidden inputs
            productos = request.form.getlist('producto[]')
            dosis_por_tomas = request.form.getlist('dosis_por_toma[]')
            unidades = request.form.getlist('unidad_entrega[]')
            posologias = request.form.getlist('posologia[]')
            duraciones = request.form.getlist('duracion[]')
            vias = request.form.getlist('via[]')
            observaciones = request.form.getlist('observacion[]')

            # Iterar y hacer UPDATE prescripciones
            for i in range(len(prescripcion_ids)):
                p_id = prescripcion_ids[i]  # ID de la prescripción en la DB
                p_producto = productos[i].strip()
                p_dosis = dosis_por_tomas[i].strip()
                p_unidad = unidades[i].strip()
                p_posologia = posologias[i].strip()
                p_duracion = duraciones[i].strip()
                p_via = vias[i].strip()
                p_obs = observaciones[i].strip()

                # Hacer UPDATE en la DB. Nos aseguramos de que sea la misma receta.
                cur.execute("""
                    UPDATE prescripciones
                    SET producto = %s,
                        dosis_por_toma = %s,
                        unidad_entrega = %s,
                        posologia = %s,
                        duracion = %s,
                        via = %s,
                        observacion = %s
                    WHERE id = %s
                      AND receta_id = %s
                """, (
                    p_producto,
                    p_dosis or None,
                    p_unidad,
                    p_posologia,
                    p_duracion or None,
                    p_via,
                    p_obs,
                    p_id,
                    receta_id
                ))

            conn.commit()
            flash("Medicamentos actualizados correctamente.")
            cur.close()
            conn.close()
            return redirect(url_for('gestionar_solicitud'))
        except Exception as e:
            conn.rollback()
            flash(f"Error al actualizar medicamentos: {e}")
            cur.close()
            conn.close()
            return redirect(url_for('gestionar_solicitud'))

    else:
        # GET => mostrar los medicamentos en un formulario editable
        # 2. Buscar las prescripciones asociadas a esa receta
        cur.execute("""
            SELECT id, producto, dosis_por_toma, unidad_entrega,
                   posologia, duracion, via, observacion
            FROM prescripciones
            WHERE receta_id = %s
            ORDER BY id
        """, (receta_id,))
        prescripciones = cur.fetchall()
        cur.close()
        conn.close()

        return render_template('editar_solicitud.html',
                               solicitud_id=solicitud_id,
                               prescripciones=prescripciones)


# ==================================================
#  Ruta para buscar medicamentos (Autocompletado)
# ==================================================
@app.route('/buscar_medicamentos', methods=['GET'])
@roles_required('usuario', 'admin', 'medico')
def buscar_medicamentos():
    termino = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name
        FROM farmacos
        WHERE name ILIKE %s
        ORDER BY name
        LIMIT 10
    """, (f'%{termino}%',))
    resultados = cur.fetchall()
    cur.close()
    conn.close()

    farmacos = []
    for r in resultados:
        farmacos.append({
            "id": r[0],
            "name": r[1]
        })
    return jsonify(farmacos)


# ==================================================
#  Envío de recetas a Mirth (form tradicional)
# ==================================================
@app.route('/enviar', methods=['POST'])
@roles_required('medico', 'admin', 'usuarios')  # Permite múltiples roles
def enviar_receta():
    """
    Procesa los datos enviados desde <form> en formulario.html.
    Valida el token CSRF y luego guarda en DB, etc.
    """
    form = RecetaForm()

    nombre = request.form.get('nombre')
    rut = request.form.get('rut')
    diagnostico_input = request.form.get('diagnostico')
    fecha_nacimiento = request.form.get('fecha_nacimiento') or None
    sexo = request.form.get('sexo') or None

    if ' - ' in diagnostico_input:
        codigo_diagnostico, descripcion_diagnostico = diagnostico_input.split(' - ', 1)
    else:
        codigo_diagnostico = diagnostico_input[:5]
        descripcion_diagnostico = diagnostico_input

    nombre_profesional = request.form.get('nombre_profesional') or "."
    apellidos_profesional = request.form.get('apellido_profesional') or "."
    apellidos_split = apellidos_profesional.strip().split(' ', 1)
    primer_apellido_profesional = apellidos_split[0] if len(apellidos_split) > 0 else "."
    segundo_apellido_profesional = apellidos_split[1] if len(apellidos_split) > 1 else "."
    run_profesional = request.form.get('run_profesional') or "."
    tipo_profesional = request.form.get('tipo_profesional') or "."

    identificador_servicio = request.form.get('servicio') or "."
    identificador_cama = request.form.get('cama') or "."
    descripcion_servicio = request.form.get('descripcion_servicio') or "."

    medicamentos = request.form.getlist('medicamento[]')
    codigos_medicamentos = request.form.getlist('codigo_medicamento[]')
    dosis_por_toma = request.form.getlist('dosis_por_toma[]')
    unidad_dosis = request.form.getlist('unidad_dosis[]')
    posologias = request.form.getlist('posologia[]')
    duraciones = request.form.getlist('duracion[]')
    vias = request.form.getlist('via[]')
    observaciones = request.form.getlist('observacion[]')

    prescripciones = []
    num_prescripciones = min(
        len(medicamentos),
        len(codigos_medicamentos),
        len(dosis_por_toma),
        len(unidad_dosis),
        len(posologias),
        len(duraciones),
        len(vias),
        len(observaciones)
    )

    for i in range(num_prescripciones):
        try:
            prescripcion = {
                'CodigoProducto': codigos_medicamentos[i],
                'Producto': medicamentos[i],
                'DosisPorToma': float(dosis_por_toma[i]) if dosis_por_toma[i] else None,
                'UnidadEntrega': unidad_dosis[i] if unidad_dosis[i] else 'N/A',
                'Posologia': posologias[i] if posologias[i] else 'N/A',
                'Duracion': int(duraciones[i]) if duraciones[i] else None,
                'Via': vias[i] if vias[i] else 'N/A',
                'Observacion': observaciones[i] if observaciones[i] else 'Sin observaciones'
            }
            prescripciones.append(prescripcion)
        except Exception as e:
            logger.error(f"Error procesando prescripción en índice {i}: {e}")
            continue

    fecha_hora_mensaje = datetime.now()

    # Insertar la receta y obtener el ID generado
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO recetas (
                rut, nombre, primer_apellido, segundo_apellido,
                fecha_nacimiento, sexo, nombre_profesional, primer_apellido_profesional,
                segundo_apellido_profesional, run_profesional, tipo_profesional,
                codigo_diagnostico, descripcion_diagnostico,
                identificador_cama, identificador_servicio, fecha_hora_mensaje
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            rut,
            nombre.split()[0],
            nombre.split()[1] if len(nombre.split()) > 1 else ".",
            nombre.split()[2] if len(nombre.split()) > 2 else ".",
            fecha_nacimiento,
            sexo,
            nombre_profesional,
            primer_apellido_profesional,
            segundo_apellido_profesional,
            run_profesional,
            tipo_profesional,
            codigo_diagnostico,
            descripcion_diagnostico,
            identificador_cama,
            identificador_servicio,
            fecha_hora_mensaje
        ))
        receta_id = cur.fetchone()[0]

        # Insertar las prescripciones relacionadas
        for prescripcion in prescripciones:
            cur.execute("""
                INSERT INTO prescripciones (
                    receta_id, codigo_producto, producto, dosis_por_toma,
                    unidad_entrega, posologia, duracion, via, observacion
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                receta_id,
                prescripcion['CodigoProducto'],
                prescripcion['Producto'],
                prescripcion['DosisPorToma'],
                prescripcion['UnidadEntrega'],
                prescripcion['Posologia'],
                prescripcion['Duracion'],
                prescripcion['Via'],
                prescripcion['Observacion']
            ))

        # Generar identificadores únicos
        id_transaccion = f"RC{receta_id:04d}"

        # Construir el JSON
        receta_json = {
            "ParametroNotificarSolicitudDispensacion": {
                "IdTransaccion": id_transaccion,
                "CodigoEstablecimiento": "HEC",
                "FechaHoraMensaje": fecha_hora_mensaje.strftime("%Y-%m-%d %H:%M:%S"),
                "TipoIdentificacion": 1,
                "Receta": {
                    "IdentificadorReceta": id_transaccion,
                    "TipoReceta": "Receta_Contingencia",
                    "FechaReceta": fecha_hora_mensaje.strftime("%Y-%m-%d %H:%M:%S"),
                    "Paciente": {
                        "paciente_run": rut,
                        "Nombres": nombre,
                        "FechaNacimiento": fecha_nacimiento,
                        "Sexo": sexo
                    },
                    "Profesional": {
                        "Nombres": nombre_profesional,
                        "PrimerApellido": primer_apellido_profesional,
                        "SegundoApellido": segundo_apellido_profesional,
                        "Run": run_profesional,
                        "TipoProfesional": tipo_profesional
                    },
                    "Diagnostico": {
                        "CodigoDiagnostico": codigo_diagnostico,
                        "DescripcionDiagnostico": descripcion_diagnostico,
                        "EsPrincipal": 0
                    },
                    "Prescripciones": prescripciones,
                    "Ubicacion": {
                        "IdentificadorServicio": identificador_servicio,
                        "DescripcionServicio": descripcion_servicio,
                        "IdentificadorCama": identificador_cama
                    }
                }
            }
        }

        # Enviar JSON a Mirth
        respuesta = enviar_json_mirth(receta_json)

        # Insertar solicitud de receta
        cur.execute("""
            INSERT INTO solicitudes_recetas (receta_id, estado, creada_por)
            VALUES (%s, %s, %s)
        """, (receta_id, 'pending', session['username']))

        conn.commit()
        return jsonify({"status": "Prescripción enviada", "respuesta": respuesta})

    except Exception as e:
        conn.rollback()
        logger.error(f"Error al guardar en la base de datos: {e}")
        return jsonify({"status": "Error",
                        "mensaje": "No se pudo guardar la receta en la base de datos."}), 500

    finally:
        cur.close()
        conn.close()


# ==================================================
#  Rutas de Login
# ==================================================

# <-- Cambio: limitamos el login a 5 intentos por minuto
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, password, role
            FROM usuarios
            WHERE username = %s
        """, (username,))
        user = cur.fetchone()

        if user and check_password_hash(user[2], password):
            session['username'] = user[1]
            session['role'] = user[3]

            # Si el rol es 'medico', buscar datos en la tabla profesionales
            if session['role'] == 'medico':
                cur.execute("""
                    SELECT run_profesional, nombre_profesional, primer_apellido_profesional,
                           segundo_apellido_profesional, tipo_profesional
                    FROM profesionales
                    WHERE user_id = %s
                """, (user[0],))
                profesional = cur.fetchone()
                if profesional:
                    session['run_profesional'] = profesional[0]
                    session['nombre_profesional'] = profesional[1]
                    session['apellido_profesional'] = f"{profesional[2]} {profesional[3]}"
                    session['tipo_profesional'] = profesional[4]

            cur.close()
            conn.close()

            # Redirigir según el rol
            if session['role'] == 'medico':
                return redirect(url_for('solicitudes'))
            elif session['role'] == 'usuario':
                return redirect(url_for('formulario'))
            elif session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Nombre de usuario o contraseña incorrectos')
            cur.close()
            conn.close()

    return render_template('login.html', form=form)


# ==================================================
#  Vistas de Administración
# ==================================================
@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')


@app.route('/usuarios')
@admin_required
def listar_usuarios():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, role,
               run_profesional, nombre_profesional,
               primer_apellido_profesional, segundo_apellido_profesional,
               tipo_profesional
        FROM usuarios
        ORDER BY username
    """)
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios)


@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']  # Debe ser EXACTAMENTE 'medico', 'usuario' o 'admin'

        # Campos del profesional (opcional, solo si role=medico)
        run_profesional = request.form.get('run_profesional', '').strip()
        nombre_profesional = request.form.get('nombre_profesional', '').strip()

        # Un único campo para ambos apellidos
        apellidos_profesional = request.form.get('apellido_profesional', '').strip()
        # Separa en dos partes
        apellidos_split = apellidos_profesional.split(' ', 1)
        primer_apellido_profesional = apellidos_split[0] if len(apellidos_split) > 0 else ''
        segundo_apellido_profesional = apellidos_split[1] if len(apellidos_split) > 1 else ''

        tipo_profesional = request.form.get('tipo_profesional', '').strip()

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # 1) Insertar en tabla usuarios
            cur.execute("""
                INSERT INTO usuarios (username, password, role)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (username, password, role))
            user_id = cur.fetchone()[0]

            # 2) Si es medico, insertar en la tabla profesionales
            if role == 'medico':
                cur.execute("""
                    INSERT INTO profesionales (
                        user_id, run_profesional, nombre_profesional,
                        primer_apellido_profesional, segundo_apellido_profesional,
                        tipo_profesional
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    run_profesional,
                    nombre_profesional,
                    primer_apellido_profesional,
                    segundo_apellido_profesional,
                    tipo_profesional
                ))

            conn.commit()
            flash('Usuario creado correctamente.')
            return redirect(url_for('listar_usuarios'))

        except Exception as e:
            conn.rollback()
            flash(f'Error al crear usuario: {e}')
        finally:
            cur.close()
            conn.close()

    # Si GET, mostramos el formulario
    return render_template('nuevo_usuario.html')


@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, role,
               run_profesional, nombre_profesional,
               primer_apellido_profesional, segundo_apellido_profesional,
               tipo_profesional
        FROM usuarios
        WHERE id = %s
    """, (id,))
    usuario = cur.fetchone()

    if not usuario:
        flash('Usuario no encontrado.')
        cur.close()
        conn.close()
        return redirect(url_for('listar_usuarios'))

    if request.method == 'POST':
        username = request.form['username']
        role = request.form['role']
        new_password = request.form['password']

        run_profesional = request.form.get('run_profesional') or None
        nombre_profesional = request.form.get('nombre_profesional') or None
        primer_apellido_profesional = request.form.get('primer_apellido_profesional') or None
        segundo_apellido_profesional = request.form.get('segundo_apellido_profesional') or None
        tipo_profesional = request.form.get('tipo_profesional') or None

        if new_password:
            password = generate_password_hash(new_password)
            query = """
                UPDATE usuarios
                SET username = %s, password = %s, role = %s,
                    run_profesional = %s, nombre_profesional = %s,
                    primer_apellido_profesional = %s, segundo_apellido_profesional = %s,
                    tipo_profesional = %s
                WHERE id = %s
            """
            params = (
                username, password, role,
                run_profesional, nombre_profesional,
                primer_apellido_profesional, segundo_apellido_profesional,
                tipo_profesional, id
            )
        else:
            query = """
                UPDATE usuarios
                SET username = %s, role = %s,
                    run_profesional = %s, nombre_profesional = %s,
                    primer_apellido_profesional = %s, segundo_apellido_profesional = %s,
                    tipo_profesional = %s
                WHERE id = %s
            """
            params = (
                username, role,
                run_profesional, nombre_profesional,
                primer_apellido_profesional, segundo_apellido_profesional,
                tipo_profesional, id
            )

        try:
            cur.execute(query, params)
            conn.commit()
            flash('Usuario actualizado correctamente.')
        except Exception as e:
            conn.rollback()
            flash(f'Error al actualizar usuario: {e}')
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('listar_usuarios'))

    cur.close()
    conn.close()
    return render_template('editar_usuario.html', usuario=usuario)


@app.route('/usuarios/eliminar/<int:id>', methods=['GET', 'POST'])
@admin_required
def eliminar_usuario(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM usuarios WHERE id = %s", (id,))
    usuario = cur.fetchone()

    if not usuario:
        flash('Usuario no encontrado.')
        return redirect(url_for('listar_usuarios'))

    if request.method == 'POST':
        cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        flash('Usuario eliminado correctamente.')
        return redirect(url_for('listar_usuarios'))

    cur.close()
    conn.close()
    return render_template('eliminar_usuario.html', usuario=usuario)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Manejo de errores CSRF
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('csrf_error.html', reason=e.description), 400


# ==================================================
#  Arranque de Flask
# ==================================================
if __name__ == "__main__":
    # En desarrollo:
    app.run(debug=True, host='0.0.0.0', port=5000)


