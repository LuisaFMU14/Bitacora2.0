from flask import Flask, request, jsonify, render_template, send_file, redirect,url_for, flash, jsonify
import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob import BlobServiceClient,BlobClient,ContainerClient
from werkzeug.utils import secure_filename
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
from pydub import AudioSegment
import tempfile

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def insert_registro_bitacora(respuestas, id_proyecto):
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO registrosbitacora (
                disciplina,
                lugar_obra,
                especialidad,
                actividades,
                responsable,
                estado,
                foto_base64,
                id_proyecto
                
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            respuestas.get('disciplina'),
            respuestas.get('lugar_obra'),
            respuestas.get('especialidad'),
            respuestas.get('actividades'),
            respuestas.get('responsable'),
            respuestas.get('estado'),
            respuestas.get('foto_base64'),
            id_proyecto,          
        ))

        conn.commit()
        print("Registro guardado en PostgreSQL.")
    except Exception as e:
        print(f"Error al guardar en PostgreSQL: {str(e)}")
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
            """SELECT id_proyecto, nombre_proyecto, fecha_inicio, director_obra, user_id 
               FROM proyectos WHERE user_id = %s ORDER BY fecha_inicio DESC""",
            (user_id,)
        )
        
        projects = []
        for row in cursor.fetchall():
            projects.append({
                'id_proyecto': row[0],
                'name': row[1],
                'fecha_inicio': row[2].strftime('%Y-%m-%d'),
                'director_obra': row[3],
                'user_id': row[4],

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
    if 'user_id' not in session:
        return redirect(url_for('principalscreen'))
    
    project_id = request.args.get('project_id')
    if project_id:
        # Verificar que el proyecto pertenece al usuario
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM proyectos WHERE id_proyecto = %s AND user_id = %s",
            (project_id, session['user_id'])
        )
        if not cursor.fetchone():
            flash('No tienes acceso a este proyecto', 'error')
            return redirect(url_for('history'))
        conn.close()
    
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
def historialregistro():
    # Obtener el ID del proyecto desde los parámetros de la URL
    project_id = request.args.get('project_id')
    project_name = request.args.get('project_name', 'Proyecto')
    
    if not project_id:
        flash("No se proporcionó el ID del proyecto", "error")
        return redirect(url_for('history'))

    # Aquí puedes agregar lógica para obtener registros reales de la base de datos
    # Por ahora usaremos los datos quemados como solicitaste
    
    # Datos quemados de ejemplo (2 registros)
    registros = []
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id_registro, disciplina, lugar_obra, especialidad, actividades, responsable, estado, foto_base64
            FROM registrosbitacora
            WHERE id_proyecto = %s
            ORDER BY id_registro DESC
        """, (project_id,))

        for row in cursor.fetchall():
            registros.append({
                'id': row[0],
                'disciplina': row[1],
                'lugar_obra': row[2],
                'especialidad': row[3],
                'actividades': row[4],
                'responsable': row[5],
                'estado': row[6],
                'foto_base64': row[7],
            })
    except Exception as e:
        print(f"Error al obtener registros: {str(e)}")
    finally:
        if conn:
            conn.close()
    
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
        data = request.get_json()
        print("Datos recibidos:", data)  # 🐞 DEBUG
        respuestas = data.get('respuestas')
        project_id = data.get('project_id')

        if not respuestas or not project_id:
            return jsonify({"error": "Faltan datos requeridos."}), 400

        # Guardar en PostgreSQL
        insert_registro_bitacora(respuestas, int(project_id))

        return jsonify({"mensaje": "Registro guardado exitosamente en PostgreSQL."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/eliminar-proyecto', methods=['POST'])
def eliminar_proyecto():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.get_json()
    proyecto_id = data.get('id_proyecto')

    if not proyecto_id:
        return jsonify({'error': 'Falta el ID del proyecto'}), 400

    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        # Asegurarse de que el proyecto pertenece al usuario
        cursor.execute("""
            DELETE FROM proyectos
            WHERE id_proyecto = %s AND user_id = %s
        """, (proyecto_id, session['user_id']))
        conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/transcribe-audio', methods=['POST'])
def transcribe_audio():
    try:
        if 'audio' not in request.files:
            print("🔴 No se recibió archivo de audio.")
            return jsonify({"error": "No se envió el archivo de audio"}), 400

        file = request.files['audio']
        print(f"📥 Recibido archivo: {file.filename}")

        # Guardar temporalmente el WebM
        temp_webm = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        file.save(temp_webm.name)
        print("💾 Guardado en:", temp_webm.name)

        # Convertir WebM a WAV
        audio = AudioSegment.from_file(temp_webm.name, format="webm")
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.export(temp_wav.name, format="wav")
        print("🔄 Convertido a WAV:", temp_wav.name)

        # Transcribir con Azure
        speech_config = get_speech_config()
        audio_config = speechsdk.audio.AudioConfig(filename=temp_wav.name)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        result = recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("✅ Texto reconocido:", result.text)
            return jsonify({"text": result.text})
        else:
            print("⚠️ No se reconoció el audio:", result.reason)
            return jsonify({"error": "No se reconoció el audio."}), 400

    except Exception as e:
        print("❌ Error en transcribe_audio:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)