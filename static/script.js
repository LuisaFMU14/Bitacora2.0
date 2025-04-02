// Variables globales
let currentQuestionIndex = 0;
const questions = [
    "¿Cuál es la disciplina?",
    "¿Cuál es el lugar de la obra?",
    "¿Cuál es la especialidad?",
    "Describe las actividades realizadas.",
    "¿Quién es el responsable?",
    "¿Cuál es el estado de la actividad?"
];
const responses = [];

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

        utterance.onend = function() {
            startSpeechRecognition(); // Iniciar reconocimiento de voz después de hacer la pregunta
        };
    }
}

// Iniciar la cámara automáticamente cuando se completen las preguntas
function startCamera() {
    const video = document.getElementById('videoElement');
    const cameraContainer = document.getElementById('camera-container');
    const takePhotoButton = document.getElementById('take-photo');
    const startCameraButton = document.getElementById('start-camera');

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true }).then(function(stream) {
            video.srcObject = stream;
            cameraContainer.style.display = 'block';  // Mostrar la cámara
            takePhotoButton.style.display = 'block';  // Mostrar el botón "Tomar foto"
            startCameraButton.style.display = 'none'; // Ocultar el botón "Iniciar cámara"
        });
    } else {
        alert("No se puede acceder a la cámara.");
    }
}

// Tomar la foto
function takePhoto() {
    const canvas = document.getElementById('photoCanvas');
    const videoElement = document.getElementById('videoElement');

    // Dibuja la imagen del video en el canvas
    canvas.width = videoElement.videoWidth;
    canvas.height = videoElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    // Obtén la imagen en formato Base64
    const fotoBase64 = canvas.toDataURL('image/png');
    // Muestra la foto como miniatura para asegurarse de que se capturó correctamente
    const photoThumbnails = document.getElementById('photoThumbnails');
    photoThumbnails.innerHTML = `<img src="${fotoBase64}" width="100px">`;

    // Guarda la imagen como Base64 en el input para enviarla
    document.getElementById('base64-photo').value = fotoBase64;
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
    // 1. Validar que el canvas está inicializado
    const canvas = document.getElementById('photoCanvas');
    if (!canvas) {
        showError('No se encontró el elemento canvas');
        return;
    }

    // 2. Obtener la imagen en Base64 con validación
    let fotoBase64;
    try {
        fotoBase64 = canvas.toDataURL('image/jpeg', 0.7);
        
        // Validar formato de la cadena Base64
        if (typeof fotoBase64 !== 'string' || !fotoBase64.includes(',')) {
            throw new Error('Formato de imagen no válido');
        }
    } catch (error) {
        showError('Error al procesar la foto: ' + error.message);
        return;
    }

    // 3. Extraer solo la parte Base64 (con validación)
    const fotoParts = fotoBase64.split(',');
    if (fotoParts.length < 2) {
        showError('La foto no tiene el formato esperado');
        return;
    }
    const pureBase64 = fotoParts[1];

    // 4. Preparar datos del formulario
    const formData = {
        respuestas: {
            disciplina: getValue('question_0'),
            lugar: getValue('question_1'),
            especialidad: getValue('question_2'),
            descripcion: getValue('question_3'),
            responsable: getValue('question_4'),
            estado: getValue('question_5')
        },
        foto: pureBase64
    };

    // 5. Validar campos obligatorios
    if (!validateForm(formData)) return;

    // 6. Enviar datos (FETCH con manejo de errores mejorado)
    sendDataToServer(formData);
}

// ----- Funciones auxiliares ----- //

function getValue(elementId) {
    const element = document.getElementById(elementId);
    return element ? element.value.trim() : '';
}

function validateForm(formData) {
    const requiredFields = ['disciplina', 'lugar', 'especialidad', 'descripcion'];
    const missingFields = requiredFields.filter(field => !formData.respuestas[field]);
    
    if (missingFields.length > 0) {
        showError(`Faltan campos requeridos: ${missingFields.join(', ')}`);
        return false;
    }
    
    if (!formData.foto) {
        showError('Debe capturar una foto válida');
        return false;
    }
    
    return true;
}

function sendDataToServer(formData) {
    const submitBtn = document.getElementById('save-record');
    const originalText = submitBtn.textContent;
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Enviando...';

    fetch('/guardar-registro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    })
    .then(handleResponse)
    .then(handleSuccess)
    .catch(handleError)
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    });
}

function handleResponse(response) {
    if (!response.ok) {
        return response.json().then(errData => {
            throw new Error(errData.error || `Error ${response.status}`);
        });
    }
    return response.json();
}

function handleSuccess(data) {
    if (data.error) throw new Error(data.error);
    
    const successMsg = document.getElementById('successMessage');
    successMsg.textContent = '✅ Registro guardado correctamente';
    successMsg.style.display = 'block';
    successMsg.style.color = 'green';
    
    setTimeout(() => {
        successMsg.style.display = 'none';
    }, 3000);
}

function handleError(error) {
    console.error('Error:', error);
    showError(error.message || 'Error al guardar el registro');
}

function showError(message) {
    const errorMsg = document.getElementById('successMessage');
    errorMsg.textContent = `❌ ${message}`;
    errorMsg.style.display = 'block';
    errorMsg.style.color = 'red';
}



document.getElementById('successMessage').style.display = 'block';


// Empezar el proceso de preguntas en cuanto cargue la página
window.onload = function() {
    askNextQuestion();
};


 // Abrir modal al presionar "Adjuntar plano"
 attachBtn.addEventListener("click", () => {
    fileModal.style.display = "block";
});

// Cerrar modal al presionar la "X"
closeModal.addEventListener("click", () => {
    fileModal.style.display = "none";
});

function triggerFileInput() {
    document.getElementById('file-input').click();
}

