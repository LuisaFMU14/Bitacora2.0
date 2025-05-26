// Variables globales
let currentQuestionIndex = 0;
let currentFacingMode = "environment";
let currentStream = null;
const questions = [
    "¿Cuál es la disciplina?",
    "¿Cuál es el lugar de la obra?",
    "¿Cuál es la especialidad?",
    "Describe las actividades realizadas.",
    "¿Quién es el responsable?",
    "¿Cuál es el estado de la actividad?"
];
const responses = [];

async function saveToSharePointList() {
    try {
        const respuestas = {
            disciplina: document.getElementById('question_0').value,
            lugar: document.getElementById('question_1').value,
            especialidad: document.getElementById('question_2').value,
            descripcion: document.getElementById('question_3').value,
            responsable: document.getElementById('question_4').value,
            estado: document.getElementById('question_5').value
        };

        const response = await fetch('/guardar-en-lista-sharepoint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ respuestas })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Error al guardar");
        
        alert("¡Registro guardado en la lista de SharePoint!");
        console.log("ID del registro:", result.id_registro);
    } catch (error) {
        console.error("Error:", error);
        alert(`Error: ${error.message}`);
    }
}

// Función para iniciar el reconocimiento de voz mediante Azure
function startRecording() {
    console.log("🎙️ Iniciando grabación...");

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        const audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            console.log("🛑 Grabación terminada. Enviando a Azure...");
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });

            const formData = new FormData();
            formData.append('audio', audioBlob, 'respuesta.webm');

            fetch('/transcribe-audio', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.text) {
                    console.log("✅ Azure respondió:", data.text);
                    const input = document.getElementById(`question_${currentQuestionIndex}`);
                    if (input) input.value = data.text;

                    currentQuestionIndex++;
                    if (currentQuestionIndex < questions.length) {
                        askNextQuestion();
                    } else {
                        console.log("🎉 Todas las preguntas respondidas.");
                        startCamera();
                    }
                } else {
                    console.error("⚠️ Transcripción fallida:", data.error);
                }
            }).catch(err => {
                console.error("❌ Error al enviar a Azure:", err);
            });
        };

        mediaRecorder.start();
        setTimeout(() => mediaRecorder.stop(), 5000);
    }).catch(err => {
        console.error("❌ Error al acceder al micrófono:", err);
    });
}

// Función para iniciar la grabación de voz
function startSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("Este navegador no soporta reconocimiento de voz.");
        return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = function() {
        console.log("Reconocimiento de voz iniciado.");
    };

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        console.log(`Respuesta recibida: ${transcript}`);
        handleResponse(transcript);
    };

    recognition.onerror = function(event) {
        console.log('Error de reconocimiento de voz:', event.error);
    };

    recognition.onend = function() {
        // Si hay más preguntas, continuar
        if (currentQuestionIndex < questions.length) {
            askNextQuestion();
        } else {
            // Todas las preguntas contestadas, mostrar la cámara
            startCamera();
        }
    };

    recognition.start();
}

// Función para manejar la respuesta y colocarla en el campo correspondiente
function handleResponse(response) {
    responses.push(response);
    document.getElementById(`question_${currentQuestionIndex}`).value = response;
    currentQuestionIndex++;
}

// Función para preguntar la siguiente pregunta en voz alta
function askNextQuestion() {
    if (currentQuestionIndex < questions.length) {
        const question = questions[currentQuestionIndex];
        const utterance = new SpeechSynthesisUtterance(question);
        utterance.lang = 'es-ES';
        speechSynthesis.speak(utterance);

        utterance.onend = function () {
            console.log("🔊 Pregunta leída. Iniciando grabación...");
            setTimeout(() => {
                startRecording();
            }, 300);
        };
        //utterance.onend = function() {
            //startSpeechRecognition(); // Iniciar reconocimiento de voz después de hacer la pregunta
        //};
    }
}

// Iniciar la cámara automáticamente cuando se completen las preguntas
function startCamera(facingMode = "environment") {
    const video = document.getElementById('videoElement');
    const cameraContainer = document.getElementById('camera-container');
    const takePhotoButton = document.getElementById('take-photo');
    const startCameraButton = document.getElementById('start-camera');
    //const switchCameraButton = document.getElementById('switch-camera');

    // Detener cualquier stream anterior
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
    }

    navigator.mediaDevices.getUserMedia({
        video: { facingMode: { exact: facingMode } }
    }).then(function (stream) {
        currentStream = stream;
        video.srcObject = stream;
        video.style.display = 'block';
        cameraContainer.style.display = 'block';
        takePhotoButton.style.display = 'block';
        //switchCameraButton.style.display = 'block';
        startCameraButton.style.display = 'none';
    }).catch(function (error) {
        console.warn(`No se pudo abrir la cámara con modo: ${facingMode}`, error);
        // Fallback: intentar con la cámara predeterminada del dispositivo
        navigator.mediaDevices.getUserMedia({ video: true }).then(function (fallbackStream) {
            currentStream = fallbackStream;
            video.srcObject = fallbackStream;
            video.style.display = 'block';
            cameraContainer.style.display = 'block';
            takePhotoButton.style.display = 'block';
            startCameraButton.style.display = 'none';
        }).catch(function (fallbackError) {
            console.error("No se pudo acceder a ninguna cámara.", fallbackError);
            alert("No se pudo acceder a la cámara. Por favor, revisa los permisos del navegador.");
        });
    });
}

// Tomar la foto
function takePhoto() {
    const canvas = document.getElementById('photoCanvas');
    const videoElement = document.getElementById('videoElement');

    // Validar que el video esté transmitiendo
    if (videoElement.readyState !== 4) { // 4 = HAVE_ENOUGH_DATA
        alert('La cámara no está lista. Espere un momento.');
        return;
    }

    // Dibuja la imagen del video en el canvas
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    // Obtén la imagen en formato Base64
    const fotoBase64 = canvas.toDataURL('image/jpeg', 0.7);
    // Muestra la foto como miniatura para asegurarse de que se capturó correctamente
    const photoThumbnails = document.getElementById('photoThumbnails');
    photoThumbnails.innerHTML = `
        <div class="photo-thumbnail-wrapper">
            <img src="${fotoBase64}" class="thumbnail-image">
            <div class="photo-controls">
                <button id="accept-photo" class="photo-button">✅</button>
                <button id="retake-photo" class="photo-button">❌</button>
            </div>
        </div>
    `;
    // Ocultar cámara
    videoElement.style.display = 'none';

    // Agregar listeners a los botones recién insertados
    document.getElementById('accept-photo').addEventListener('click', function () {
        // No hacer nada más, simplemente se deja la miniatura
        console.log("Foto aceptada.");
    });

    document.getElementById('retake-photo').addEventListener('click', function () {
        // Mostrar cámara de nuevo
        videoElement.style.display = 'block';
        // Limpiar miniatura y base64
        document.getElementById('photoThumbnails').innerHTML = '';
        document.getElementById('base64-photo').value = '';
    });

    // Verificar formato correcto
    if (!fotoBase64.startsWith('data:image/jpeg;base64,')) {
        throw new Error('Formato de imagen no válido');
    }
    
    // Verificar longitud mínima
    if (fotoBase64.length < 100) {
        throw new Error('La imagen es demasiado pequeña');
    }

    // Guarda la imagen como Base64 en el input para enviarla
    document.getElementById('base64-photo').value = fotoBase64;

    // Mostrar los controles de aceptar/rechazar
    //document.getElementById('photoControls').style.display = 'block';

    // Ocultar la cámara
    document.getElementById('videoElement').style.display = 'none';
}
const foto = document.getElementById('base64-photo').value;
console.log(foto);


// Función para agregar la miniatura de la foto
function addPhotoThumbnail(photoSrc) {
    // Crear un contenedor para la miniatura
    const photoContainer = document.createElement('div');
    photoContainer.classList.add('photo-container');

    // Crear el elemento de imagen
    const img = document.createElement('img');
    img.src = photoSrc;
    img.classList.add('thumbnail');

    // Agregar el contenedor de la miniatura al área de miniaturas
    document.getElementById('photoThumbnails').appendChild(photoContainer);
}

document.getElementById('file-input').addEventListener('change', function (event) {
    const file = event.target.files[0];

    if (!file) return;

    const reader = new FileReader();

    reader.onload = function (e) {
        const base64 = e.target.result;

        // Insertar miniatura
        const photoThumbnails = document.getElementById('photoThumbnails');
        photoThumbnails.innerHTML = `
            <div class="photo-thumbnail-wrapper">
                <img src="${base64}" class="thumbnail-image">
                <div class="photo-controls">
                    <button id="accept-photo" class="photo-button">✅</button>
                    <button id="retake-photo" class="photo-button">❌</button>
                </div>
            </div>
        `;

        // Guardar en campo oculto
        document.getElementById('base64-photo').value = base64;

        // Ocultar cámara si estaba abierta
        document.getElementById('videoElement').style.display = 'none';

        // Agregar eventos a botones
        document.getElementById('accept-photo').addEventListener('click', function () {
            console.log("Foto aceptada desde archivo.");
        });

        document.getElementById('retake-photo').addEventListener('click', function () {
            document.getElementById('videoElement').style.display = 'block';
            document.getElementById('photoThumbnails').innerHTML = '';
            document.getElementById('base64-photo').value = '';
        });
    };

    reader.readAsDataURL(file); // Convierte el archivo a base64
});



// Cuando estés listo para enviar la imagen al backend:
function sendPhotoData() {
    const foto = document.getElementById('base64-photo').value;

    if (foto) {
        console.log(foto); // Verifica que el Base64 es correcto

        // Realiza la solicitud POST para enviar el Base64
        fetch('/guardar-registro', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                foto: foto,
                // Agrega otros datos si es necesario
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Registro guardado:', data);
        })
        .catch(error => {
            console.error('Error al guardar el registro:', error);
        });
    } else {
        console.error('No se encontró la foto Base64.');
    }
}

// Función para guardar el registro
function saveRecord() {
    // Obtener el proyecto relacionado
    const projectName = document.getElementById('project-name').value;
    const fotoBase64 = document.getElementById('base64-photo').value;
    // Mostrar el mensaje de éxito inmediatamente
    document.getElementById('successMessage').style.display = 'block';

    const respuestas = {
        disciplina : document.getElementById('question_0').value,
        lugar_obra: document.getElementById('question_1').value,
        especialidad: document.getElementById('question_2').value,
        actividades: document.getElementById('question_3').value,
        responsable: document.getElementById('question_4').value,
        estado: document.getElementById('question_5').value,
    };

    const canvas = document.getElementById('photoCanvas');
    const foto = canvas.toDataURL(); // Obtener la imagen en formato Base64
    const projectId = new URLSearchParams(window.location.search).get("project_id");

    // Hacer la solicitud al backend para guardar el registro
    //fetch('http://127.0.0.1:5000/guardar-registro', {
    fetch('/guardar-registro', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            respuestas: {
                ...respuestas,
                foto_base64: document.getElementById('base64-photo').value
            },
            project_id: projectId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Limpiar campos del formulario
            document.getElementById('question_0').value = '';
            document.getElementById('question_1').value = '';
            document.getElementById('question_2').value = '';
            document.getElementById('question_3').value = '';
            document.getElementById('question_4').value = '';
            document.getElementById('question_5').value = '';

            // Limpiar miniatura y botón de foto
            document.getElementById('photoThumbnails').innerHTML = '';
            document.getElementById('base64-photo').value = '';

            // Limpiar canvas de foto si aplica
            const canvas = document.getElementById('photoCanvas');
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Mostrar mensaje
            alert('¡Registro guardado exitosamente!');

            // Redirigir después de 1.5 segundos
            //setTimeout(() => {
                //window.location.href = '/registros';
            //}, 1500);
        } else {
            // Limpiar campos del formulario
            document.getElementById('question_0').value = '';
            document.getElementById('question_1').value = '';
            document.getElementById('question_2').value = '';
            document.getElementById('question_3').value = '';
            document.getElementById('question_4').value = '';
            document.getElementById('question_5').value = '';

            // Limpiar canvas de foto si aplica
            const canvas = document.getElementById('photoCanvas');
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            alert('¡Registro guardado exitosamente!');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error en la conexión con el servidor.');
    });
}



document.getElementById('successMessage').style.display = 'block';


// Empezar el proceso de preguntas en cuanto cargue la página
/*window.onload = function() {
    setTimeout(() => {
        askNextQuestion();
    }, 1000); // 1000 milisegundos = 1 segundo
};*/

document.getElementById('start-register-button').addEventListener('click', function () {
    console.log("Inicio de registro activado por el usuario");
    askNextQuestion();
});


// Abrir modal al presionar "Adjuntar plano"
//attachBtn.addEventListener("click", () => {
    //fileModal.style.display = "block";
//});

// Cerrar modal al presionar la "X"
//closeModal.addEventListener("click", () => {
    //fileModal.style.display = "none";
//});

function triggerFileInput() {
    document.getElementById('file-input').click();
}

document.getElementById('switch-camera').addEventListener('click', function () {
    // Alternar entre "user" y "environment"
    currentFacingMode = (currentFacingMode === "environment") ? "user" : "environment";
    startCamera(currentFacingMode);
});


