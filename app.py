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


# Configura SharePoint (modifica con tus datos)
SHAREPOINT_SITE_URL = "https://iacsas.sharepoint.com/sites/Pruebasproyectossantiago"
LIST_NAME = "Proyectos"  # Nombre de la biblioteca
LIST_NAME_REGISTROS = "RegistrosBitacora"
SHAREPOINT_USER = "santiago.giraldo@iac.com.co"
SHAREPOINT_PASSWORD = "Latumbanuncamuere3"


# Cargar variables de entorno
#load_dotenv('config/settings.env')  # Ruta relativa al archivo .env

app = Flask(__name__,template_folder='templates')
CORS(app)

projects = []

# Conecta con el servicio de Blob Storage de Azure
connection_string = "DefaultEndpointsProtocol=https;AccountName=registrobitacora;AccountKey=ZyHZAOvOBijiOfY3BR3ZEDZsCAHOu3swEPnS+D7AacR2Yr94HS+jBMa2/20sJpZ71decGXYHQxE2+AStBWI/wA==;EndpointSuffix=core.windows.net"
container_name = "registros"


# Inicializa el cliente de BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

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

@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/index')
def index():
    return render_template('index.html')

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

# Ruta para la vista "history"
@app.route('/history')
def history():
    # Obtener proyectos del Blob Storage
    blob_projects = get_projects_from_blob()

    return render_template('history.html', blob_projects=blob_projects)

@app.route('/usuario')
def usuario():
    return render_template('usuario.html')

@app.route('/inventario')
def inventario():
    return render_template('inventario.html')

@app.route('/historialRegistro')
def historialregistro():
    return render_template('historialRegistro.html')

@app.route('/disciplinerecords')
def disciplinerecords():
    return render_template('disciplinerecords.html')

@app.route('/projectdetails')
def projectdetails():
    return render_template('projectdetails.html')

@app.route('/addproject', methods=['GET', 'POST'])
def add_project():
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

@app.route('/delete_project', methods=['GET', 'POST'])
def delete_project():
    try:
        # Para depuración
        app.logger.info(f"Delete project request received. Method: {request.method}")
        app.logger.info(f"Request args: {request.args}")
        
        project_name = request.args.get('project')
        app.logger.info(f"Project name: {project_name}")
        
        if not project_name:
            flash('No se especificó un nombre de proyecto', 'error')
            return redirect(url_for('registros'))
        
        # Inicializar cliente de servicio de blob
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        # Obtener una lista de todos los blobs relacionados con este proyecto
        # Asumimos que los blobs relacionados comienzan con el nombre del proyecto
        blob_list = container_client.list_blobs(name_starts_with=f"Proyectos/{project_name}/")
        deleted = False
        # Eliminar cada blob relacionado con el proyecto
        for blob in blob_list:
            container_client.delete_blob(blob.name)
            deleted = True

        if deleted:
            flash(f'Proyecto "{project_name}" eliminado correctamente', 'success')
        else:
            flash(f'No se encontraron archivos para el proyecto "{project_name}"', 'warning')
        
        return redirect(url_for('registros'))
    
    except Exception as e:
        flash(f'Error al eliminar el proyecto: {str(e)}', 'error')
        return redirect(url_for('registros')), 500

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