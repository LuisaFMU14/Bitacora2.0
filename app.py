from flask import Flask, request, jsonify, render_template, send_file, redirect,url_for, flash
import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob import BlobServiceClient,BlobClient,ContainerClient
import base64
import io
from io import BytesIO
from PIL import Image
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_cors import CORS
from datetime import datetime
from azure.storage.blob import ContentSettings
from dotenv import load_dotenv
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.lists.list import List
from office365.sharepoint.listitems.listitem import ListItem
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import secrets



# Configuración PostgreSQL
POSTGRES_CONFIG = {
    "host": "localhost",
    "database": "Bitacora",
    "user": "postgres",  # Normalmente 'postgres' por defecto
    "password": "Daniel2030#",
    "port": "5432"  # Puerto predeterminado de PostgreSQL
}

# Configura SharePoint (modifica con tus datos)
SHAREPOINT_SITE_URL = "https://iacsas.sharepoint.com/sites/Pruebasproyectossantiago"
LIST_NAME = "Proyectos"  # Nombre de la biblioteca
LIST_NAME_REGISTROS = "RegistrosBitacora"
SHAREPOINT_USER = "santiago.giraldo@iac.com.co"
SHAREPOINT_PASSWORD = "Latumbanuncamuere3"


# Cargar variables de entorno
#load_dotenv('config/settings.env')  # Ruta relativa al archivo .env

app = Flask(__name__,template_folder='templates')
app.secret_key = secrets.token_hex(16)  # Clave secreta para sesiones
#app.secret_key = '78787878tyg8987652vgdfdf3445'
CORS(app)

projects = []

# Conecta con el servicio de Blob Storage de Azure
connection_string = "DefaultEndpointsProtocol=https;AccountName=registrobitacora;AccountKey=ZyHZAOvOBijiOfY3BR3ZEDZsCAHOu3swEPnS+D7AacR2Yr94HS+jBMa2/20sJpZ71decGXYHQxE2+AStBWI/wA==;EndpointSuffix=core.windows.net"
container_name = "registros"


# Inicializa el cliente de BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

def create_user(nombre, apellido, email, password, cargo, rol, empresa):
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            """INSERT INTO usuario (name, apellido, email, password, cargo, rol, empresa)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id""",
            (nombre, apellido, email, hashed_password, cargo, rol, empresa)
        )
        
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id
    except psycopg2.Error as e:
        print(f"Error al crear usuario: {e}")
        return None
    finally:
        if conn:
            conn.close()

def verify_user(email, password):
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, password FROM usuario WHERE email = %s",
            (email,)
        )
        
        user = cursor.fetchone()
        if user and check_password_hash(user[1], password):
            return user[0]  # Devuelve el ID del usuario
        return None
    except psycopg2.Error as e:
        print(f"Error al verificar usuario: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_project(user_id, nombre, fecha_inicio, fecha_fin, director, ubicacion, coordenadas):
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        #conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO proyectos (nombre_proyecto, fecha_inicio, fecha_fin, director_obra, ubicacion, coordenadas, user_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_proyecto""",
            (nombre, fecha_inicio, fecha_fin, director, ubicacion, coordenadas, user_id)
        )
        
        project_id = cursor.fetchone()[0]
        conn.commit()
        return project_id
    except psycopg2.Error as e:
        print(f"Error al crear proyecto: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_projects(user_id):
    conn = None
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        #conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT id_proyecto, nombre_proyecto, fecha_inicio, director_obra 
               FROM proyectos WHERE user_id = %s ORDER BY fecha_inicio DESC""",
            (user_id,)
        )
        
        projects = []
        for row in cursor.fetchall():
            projects.append({
                'user_id': row[0],
                'name': row[1],
                'fecha_inicio': row[2].strftime('%Y-%m-%d'),
                'director_obra': row[3]
            })
        
        return projects
    except psycopg2.Error as e:
        print(f"Error al obtener proyectos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Función para subir archivos a Azure Blob Storage
def upload_to_blob(file_name, data, content_type):
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        blob_client.upload_blob(data, blob_type="BlockBlob", content_settings={"content_type": content_type})
        print(f"Archivo {file_name} subido con éxito.")
    except Exception as e:
        print(f"Error al subir {file_name}: {e}")
        raise


def get_speech_config():
    speech_key = '999fcb4d3f34436ab454ec47920febe0'
    service_region = 'centralus'
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "es-CO"
    speech_config.speech_synthesis_language = "es-CO"
    speech_config.speech_synthesis_voice_name = "es-CO-GonzaloNeural"
    speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "8000")
    return speech_config

def synthesize_speech(text):
    speech_config = get_speech_config()
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_text_async(text).get()
    return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted

#Obtener los proyectos desde Azure Blob Storage
def get_projects_from_blob():
    projects = []
    try:
        # Obtener el cliente del contenedor
        container_client = blob_service_client.get_container_client(container_name)
        
        # Listar los blobs en el directorio de proyectos
        blobs = list(container_client.list_blobs(name_starts_with="Proyectos/"))
        
        for blob in blobs:
            if blob.name.endswith('.txt'):
                # Obtener el cliente del blob
                blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob.name)
                
                # Descargar el contenido del blob
                content = blob_client.download_blob().readall().decode('utf-8')
                
                # Extraer información del proyecto
                project_info = {}
                for line in content.strip().split('\n'):
                    line = line.strip()
                    if line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            project_info[key] = value
                
                # Extraer el nombre del proyecto del nombre del archivo
                file_name = blob.name.split('/')[-1]
                project_name = file_name.replace('proyecto_', '').replace('.txt', '')
                
                # Crear un objeto de proyecto
                project = {
                    'name': project_info.get('Nombre del Proyecto', project_name),
                    'date': project_info.get('Fecha de Inicio', 'Fecha no disponible'),
                    'blob_name': blob.name,
                    # Añadir más campos según sea necesario
                }
                
                projects.append(project)
                
    except Exception as e:
        print(f"Error al obtener proyectos del Blob Storage: {e}")
    
    return projects

@app.after_request
def add_header(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

@app.route('/')
def principalscreen():
    return render_template('PrincipalScreen.html')

@app.route('/paginaprincipal')
def paginaprincipal():
    return render_template('paginaprincipal.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        empresa = request.form.get('empresa')
        cargo = request.form.get('cargo')
        rol = request.form.get('rol')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('registro'))
        
        user_id = create_user(nombre, apellido, email, password, empresa, cargo, rol)
        if user_id:
            flash('Registro exitoso. Por favor inicie sesión.', 'success')
            return redirect(url_for('principalscreen'))
        else:
            flash('Error al registrar el usuario', 'error')
    
    return render_template('registro.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Validación básica de campos vacíos
    if not email or not password:
        flash('Por favor ingrese ambos campos: email y contraseña', 'error')
        return redirect(url_for('principalscreen'))

    user_id = verify_user(email, password)
    if user_id:
        # Aquí puedes implementar sesiones o JWT
        session['user_id'] = user_id #Establecer sesión
        flash('Inicio de sesión exitoso', 'success')
        return redirect(url_for('registros'))
    else:
        flash('Email o contraseña incorrectos', 'error')
        return redirect(url_for('principalscreen'))

@app.route('/index')
def index():
    return render_template('index.html')

'''
@app.route('/registros')
def registros():
    # Obtener proyectos del Blob Storage
    blob_projects = get_projects_from_blob()

    # Combinar con proyectos estáticos si es necesario
    #static_projects = [
        #{'name': 'Proyecto A', 'date': '2024-09-22'},
        #{'name': 'Proyecto B', 'date': '2024-09-21'},
        #{'name': 'Proyecto C', 'date': '2024-09-20'}
    #]

    return render_template('registros.html', blob_projects=blob_projects)
'''
@app.route('/registros')
def registros():
    if 'user_id' not in session:
        return redirect(url_for('principalscreen'))
    
    # Obtener proyectos de PostgreSQL
    db_projects = get_user_projects(session['user_id'])
    
    # Obtener proyectos de Azure Blob (si aún los necesitas)
    #blob_projects = get_projects_from_blob()  # Tu función existente
    
    # Combinar proyectos (o usar solo los de PostgreSQL)
    return render_template('registros.html', 
                         db_projects=db_projects)

# Ruta para la vista "history"
@app.route('/history')
def history():
    # Obtener proyectos del Blob Storage
    #blob_projects = get_projects_from_blob()
    # Obtener proyectos de PostgreSQL
    db_projects = get_user_projects(session['user_id'])
    
    # Obtener proyectos de Azure Blob (si aún los necesitas)
    #blob_projects = get_projects_from_blob()  # Tu función existente
    
    # Combinar proyectos (o usar solo los de PostgreSQL)
    return render_template('history.html', 
                         db_projects=db_projects)

@app.route('/usuario')
def usuario():
    return render_template('usuario.html')

@app.route('/inventario')
def inventario():
    return render_template('inventario.html')

@app.route('/historialRegistro')
def historialRegistro():

    # Verificar si el usuario está autenticado
    if 'user_id' not in session:
        return redirect(url_for('principalscreen'))
    
    # Obtener el ID del proyecto desde los parámetros de la URL
    project_id = request.args.get('project_id')
    project_name = request.args.get('project_name', 'Proyecto')
    
    # Aquí puedes agregar lógica para obtener registros reales de la base de datos
    # Por ahora usaremos los datos quemados como solicitaste
    
    # Datos quemados de ejemplo (2 registros)
    registros = [
        {
            'id': 1,
            'fecha': '2024-05-15',
            'disciplina': 'Electricidad',
            'lugar_obra': 'Edificio Principal',
            'especialidad': 'Instalación eléctrica',
            'actividades': 'Instalación de cableado en planta baja',
            'responsable': 'Juan Pérez',
            'estado': 'Completado'
        },
        {
            'id': 2,
            'fecha': '2024-05-14',
            'disciplina': 'Plomería',
            'lugar_obra': 'Edificio Principal',
            'especialidad': 'Instalación hidráulica',
            'actividades': 'Instalación de tuberías en baños',
            'responsable': 'María Gómez',
            'estado': 'En progreso'
        }
    ]
    
    return render_template('historialRegistro.html',
                         registros=registros,
                         project_name=project_name,
                         project_id=project_id)

@app.route('/disciplinerecords')
def disciplinerecords():
    return render_template('disciplinerecords.html')

@app.route('/projectdetails')
def projectdetails():
    return render_template('projectdetails.html')

'''
@app.route('/addproject', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:
        return redirect(url_for('principalscreen'))
    
    if request.method == 'POST':
        try:
            project_name = request.form['project-name']
            start_date = request.form['start-date']
            end_date = request.form['end-date']
            director = request.form['director']
            location = request.form['location']
            coordinates = request.form['coordinates']

             # Conexión a SharePoint
            ctx_auth = AuthenticationContext(SHAREPOINT_SITE_URL)
            if ctx_auth.acquire_token_for_user(SHAREPOINT_USER, SHAREPOINT_PASSWORD):

                ctx = ClientContext(SHAREPOINT_SITE_URL, ctx_auth)
                
                # Obtener la lista de SharePoint
                sp_list = ctx.web.lists.get_by_title(LIST_NAME)

                # Crear el item en SharePoint
                item_properties = {
                    'Title': project_name,
                    'FechaInicio': start_date,
                    'FechaFin': end_date,
                    'Director': director,
                    'Ubicacion': location,
                    'Coordenadas': coordinates
                }
                
                new_item = sp_list.add_item(item_properties)
                ctx.execute_query()

            # Crear el nuevo proyecto y agregarlo a la lista
            # Crear el contenido del proyecto
            project_content = f"""
            Nombre del Proyecto: {project_name}
            Fecha de Inicio: {start_date}
            Fecha de Fin: {end_date}
            Director: {director}
            Ubicación: {location}
            Coordenadas: {coordinates}
            """
            # Nombre único para el archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            blob_name = f"Proyectos/{project_name}/{project_name}.txt"
            ##projects.append(new_project)
            # Subir a Azure Blob Storage
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_client.upload_blob(project_content, content_settings=ContentSettings(content_type='text/plain'))
        
            # Redirigir a la página principal (donde se muestra la lista de proyectos)
            return redirect(url_for('registros'))
        except KeyError as e:
            return f"Falta el campo requerido: {str(e)}", 400
        except Exception as e:
            return f"Error al guardar el proyecto: {str(e)}", 500
        
    return render_template('addproject.html')
'''
@app.route('/addproject', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:  # Asegúrate de tener el user_id en la sesión
        return redirect(url_for('principalscreen'))
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            project_data = {
                'name': request.form['project-name'],
                'start_date': request.form['start-date'],
                'end_date': request.form['end-date'],
                'director': request.form['director'],
                'location': request.form['location'],
                'coordinates': request.form['coordinates'],
                'user_id': session['user_id']  # ID del usuario actual
            }
            
            # Guardar en PostgreSQL
            project_id = create_project(
                project_data['user_id'],
                project_data['name'],
                project_data['start_date'],
                project_data['end_date'],
                project_data['director'],
                project_data['location'],
                project_data['coordinates']
            )
            
            if project_id:
                flash('Proyecto creado exitosamente', 'success')
                return redirect(url_for('registros'))
            else:
                flash('Error al crear el proyecto', 'error')
                
        except Exception as e:
            flash(f'Error al guardar el proyecto: {str(e)}', 'error')
    
    return render_template('addproject.html')


@app.route('/delete_project', methods=['POST'])
def delete_project():
    if 'user_id' not in session:
        return redirect(url_for('principalscreen'))
    
    try:
        project_id = request.form.get('project_id')
        
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        
        # Verificar que el proyecto pertenece al usuario
        cursor.execute(
            "DELETE FROM proyectos WHERE id_proyecto = %s AND user_id = %s RETURNING nombre_proyecto",
            (project_id, session['user_id'])
        )
        
        deleted_project = cursor.fetchone()
        if deleted_project:
            conn.commit()
            flash(f'Proyecto "{deleted_project[0]}" eliminado', 'success')
        else:
            flash('No se pudo eliminar el proyecto', 'error')
            
    except Exception as e:
        flash(f'Error al eliminar proyecto: {str(e)}', 'error')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('registros'))

@app.route('/ask', methods=['POST'])
def ask_question_route():
    data = request.json
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    success = synthesize_speech(question)
    if success:
        return jsonify({'response': ''}), 200
    else:
        return jsonify({'error': 'Error al sintetizar la pregunta.'}), 500


@app.route('/guardar-registro', methods=['POST'])
def guardar_registro():
    try:
        # Obtener datos del frontend
        data = request.get_json()
        foto_base64 = data.get('foto')
        respuestas = data.get('respuestas')

        if not foto_base64 or not respuestas:
            return jsonify({"error": "Faltan datos."}), 400

        # Procesar la imagen Base64
        foto_data = base64.b64decode(foto_base64.split(',')[1])
        imagen_nombre = f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        # Guardar la imagen en Azure Blob Storage
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=imagen_nombre)
        blob_client.upload_blob(foto_data, overwrite=True, content_settings=ContentSettings(content_type='image/png'))

        # Crear el archivo .txt con las respuestas
        respuestas_texto = "\n".join([f"{clave}: {valor}" for clave, valor in respuestas.items()])
        archivo_nombre = f"registro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        # Guardar el archivo .txt en Azure Blob Storage
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=archivo_nombre)
        blob_client.upload_blob(respuestas_texto, overwrite=True, content_settings=ContentSettings(content_type='text/plain'))

        # Guardar en SharePoint (nueva funcionalidad)
        try:
            ctx_auth = AuthenticationContext(SHAREPOINT_SITE_URL)
            if ctx_auth.acquire_token_for_user(SHAREPOINT_USER, SHAREPOINT_PASSWORD):
                ctx = ClientContext(SHAREPOINT_SITE_URL, ctx_auth)
                registros_list = ctx.web.lists.get_by_title(LIST_NAME_REGISTROS)
                
                # Mapeo de campos a SharePoint
                item_properties = {
                    'Title': f"Registro_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'Disciplina': respuestas.get('disciplina', ''),
                    'LugarObra': respuestas.get('lugar_obra', ''),
                    'Especialidad': respuestas.get('especialidad', ''),
                    'Descripcion': respuestas.get('descripcion_actividades', ''),
                    'Responsable': respuestas.get('responsable', ''),
                    'Estado': respuestas.get('estado_actividad', 'Pendiente'),          
                    'FechaRegistro': datetime.now().isoformat(),
                    'Foto': foto_base64,
                }
                
                new_item = registros_list.add_item(item_properties)
                ctx.execute_query()
        except Exception as sp_ex:
            app.logger.error(f"Error al guardar en SharePoint: {str(sp_ex)}")
            # No falla la operación, solo registra el error


        return jsonify({"mensaje": "Registro guardado exitosamente."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True)