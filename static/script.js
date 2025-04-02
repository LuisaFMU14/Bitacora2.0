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
    // 1. Validar que el canvas contiene una imagen
    const canvas = document.getElementById('photoCanvas');
    if (!canvas || canvas.width === 0 || canvas.height === 0) {
        alert('Por favor capture una foto válida antes de guardar');
        return;
    }

    // 2. Obtener y validar la imagen
    let fotoBase64;
    try {
        fotoBase64 = canvas.toDataURL('image/jpeg', 0.7); // Calidad del 70%
        if (!fotoBase64.startsWith('data:image/jpeg;base64,') || fotoBase64.length < 100) {
            throw new Error('La foto capturada no es válida');
        }
    } catch (error) {
        alert('Error al procesar la foto: ' + error.message);
        return;
    }

    // 3. Preparar datos del formulario
    const formData = {
        respuestas: {
            disciplina: document.getElementById('question_0').value.trim(),
            lugar: document.getElementById('question_1').value.trim(),
            especialidad: document.getElementById('question_2').value.trim(),
            descripcion: document.getElementById('question_3').value.trim(),
            responsable: document.getElementById('question_4').value.trim(),
            estado: document.getElementById('question_5').value.trim()
        },
        foto: fotoBase64.split(',')[1] // Extraer solo el Base64 (sin el prefijo)
    };

    // 4. Validar campos obligatorios
    const camposRequeridos = [
        'disciplina', 'lugar', 'especialidad', 
        'descripcion', 'responsable', 'estado'
    ];
    
    const camposFaltantes = camposRequeridos.filter(campo => !formData.respuestas[campo]);
    if (camposFaltantes.length > 0) {
        alert(`Faltan campos requeridos: ${camposFaltantes.join(', ')}`);
        return;
    }

    // 5. Configurar el botón durante el envío
    const submitBtn = document.getElementById('save-record');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Guardando...';

    // 6. Enviar datos al servidor (FETCH COMPLETO)
    fetch('/guardar-registro', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            // Si el servidor devuelve un error HTTP (ej. 400, 500)
            return response.json().then(errData => {
                throw new Error(errData.error || `Error HTTP ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Éxito - mostrar feedback visual
        const successMsg = document.getElementById('successMessage');
        successMsg.textContent = '✅ Registro guardado correctamente';
        successMsg.style.display = 'block';
        successMsg.style.color = 'green';
        
        // Opcional: Resetear el formulario después de 2 segundos
        setTimeout(() => {
            successMsg.style.display = 'none';
            // document.getElementById('project-form').reset(); // Si quieres limpiar el form
        }, 3000);
    })
    .catch(error => {
        console.error('Error en saveRecord:', error);
        
        // Mostrar error específico
        const errorMsg = document.getElementById('successMessage');
        errorMsg.textContent = `❌ Error: ${error.message || 'Error al guardar'}`;
        errorMsg.style.display = 'block';
        errorMsg.style.color = 'red';
    })
    .finally(() => {
        // Restaurar el botón a su estado original
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    });
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

