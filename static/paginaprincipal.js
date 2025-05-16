document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM fully loaded");

    const dropdownBtn = document.getElementById('dropdown-btn');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const deleteProjectBtn = document.getElementById('delete-project-btn');
    const confirmModal = document.getElementById('confirmModal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmNoBtn = document.getElementById('confirm-no');
    const currentProjectName = document.getElementById('current-project-name');

    // Obtener parámetros de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const projectName = urlParams.get('project');
    const projectId = urlParams.get('project_id');

    // 1. Configuración del menú desplegable
    if (dropdownBtn && dropdownMenu) {
        dropdownBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            dropdownMenu.classList.toggle('show');
        });

        document.addEventListener('click', function (event) {
            if (!dropdownMenu.contains(event.target)) {
                dropdownMenu.classList.remove('show');
            }
        });
    }

    // 2. Mostrar nombre del proyecto actual (si existe)
    if (currentProjectName && projectName) {
        currentProjectName.textContent = "Proyecto: " + decodeURIComponent(projectName);
    }

    // 3. Configuración de la eliminación de proyectos
    if (deleteProjectBtn && confirmModal && confirmYesBtn && confirmNoBtn) {
        // Mostrar modal de confirmación
        deleteProjectBtn.addEventListener('click', function() {
            if (projectId) {
                confirmModal.style.display = 'block';
            } else {
                alert('No hay proyecto seleccionado para eliminar');
            }
        });

        // Confirmar eliminación
        confirmYesBtn.addEventListener('click', async function() {
            confirmModal.style.display = 'none';
            await deleteProject(projectId);
        });

        // Cancelar eliminación
        confirmNoBtn.addEventListener('click', function() {
            confirmModal.style.display = 'none';
        });
    }

    // Función para eliminar proyecto (usando Fetch API)
    async function deleteProject(projectId) {
        if (!projectId) return;

        try {
            const response = await fetch('/delete_project', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ project_id: projectId })
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert(result.message);
                // Redirigir a la página de proyectos después de eliminar
                window.location.href = "{{ url_for('registros') }}";
            } else {
                alert('Error: ' + result.message);
            }
        } catch (error) {
            console.error('Error al eliminar proyecto:', error);
            alert('Error al conectar con el servidor');
        }
    }

    // 4. Actualizar enlace de bitácora con parámetro del proyecto
    const bitacoraBtn = document.getElementById('bitacora-btn');
    if (bitacoraBtn && projectName) {
        bitacoraBtn.href = `{{ url_for('index') }}?project=${encodeURIComponent(projectName)}`;
    }
});