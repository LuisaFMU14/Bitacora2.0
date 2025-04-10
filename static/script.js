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
            takePhotoButton.style.display = 'flex';  // Mostrar el botón "Tomar foto"
            startCameraButton.style.display = 'none'; // Ocultar el botón "Iniciar cámara"
        }).catch(function(error) {
            console.error("Error al acceder a la cámara: ", error);
            alert("No se puede acceder a la cámara. Asegúrate de que esté conectada y habilitada.");
        });
    } else {
        alert("No se puede acceder a la cámara.");
    }
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
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Obtén la imagen en formato Base64
    const fotoBase64 = canvas.toDataURL('image/jpeg', 0.7);
    // Muestra la foto como miniatura para asegurarse de que se capturó correctamente
    const photoThumbnails = document.getElementById('photoThumbnails');
    photoThumbnails.innerHTML = `<img src="${fotoBase64}" width="100px">`;

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
    // Obtener el proyecto relacionado
    const projectName = document.getElementById('project-name').value;
    // Obtener la foto en Base64
    const fotoBase64 = document.getElementById('base64-photo').value;
    // Mostrar el mensaje de éxito inmediatamente
    document.getElementById('successMessage').style.display = 'block';

    const respuestas = {
        //disciplina : document.getElementById('question_0').value,
        lugar: document.getElementById('question_1').value,
        especialidad: document.getElementById('question_2').value,
        descripcion: document.getElementById('question_3').value,
        responsable: document.getElementById('question_4').value,
        estado: document.getElementById('question_5').value,
    };

    const canvas = document.getElementById('photoCanvas');
    const foto = canvas.toDataURL(); // Obtener la imagen en formato Base64

    // Hacer la solicitud al backend para guardar el registro
    fetch('http://127.0.0.1:5000/guardar-registro', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            respuestas: respuestas,
            foto: foto
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            alert('Error al guardar el registro: ' + data.error);
        } else {
            // Aquí puedes mostrar un mensaje o redirigir al usuario
            alert('Registro guardado exitosamente!');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error en la conexión con el servidor.');
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

