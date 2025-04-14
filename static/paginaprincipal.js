document.addEventListener('DOMContentLoaded', function () {
    const dropdownBtn = document.getElementById('dropdown-btn');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const deleteProjectBtn = document.getElementById('delete-project-btn');
    const confirmModal = document.getElementById('confirmModal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmNoBtn = document.getElementById('confirm-no');

    // Obtener el parámetro del proyecto de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const projectName = urlParams.get('project');

    // Alternar el menú desplegable al hacer clic en el botón
    dropdownBtn.addEventListener('click', function (event) {
        event.stopPropagation(); // Evitar que el clic cierre el menú
        dropdownMenu.classList.toggle('show');
    });

    // Cerrar el menú al hacer clic fuera de él
    document.addEventListener('click', function (event) {
        if (!dropdownMenu.contains(event.target)) {
            dropdownMenu.classList.remove('show');
        }
    });

    // Verificar si los elementos existen antes de agregar eventos
    if (deleteProjectBtn) {
        deleteProjectBtn.addEventListener('click', function() {
            if (confirmModal) {
                confirmModal.style.display = 'block';
            }
        });
    }

    if (confirmYesBtn) {
        confirmYesBtn.addEventListener('click', function() {
            if (projectName) {
                // Redirigir a la ruta de eliminación con el nombre del proyecto
                window.location.href = '/delete_project?project=' + encodeURIComponent(projectName);
            }
            if (confirmModal) {
                confirmModal.style.display = 'none';
            }
        });
    }

    if (confirmNoBtn) {
        confirmNoBtn.addEventListener('click', function() {
            if (confirmModal) {
                confirmModal.style.display = 'none';
            }
        });
    }
});
