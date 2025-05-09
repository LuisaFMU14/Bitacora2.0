document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM fully loaded");

    // Elementos existentes
    const dropdownBtn = document.getElementById('dropdown-btn');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const deleteProjectBtn = document.getElementById('delete-project-btn');
    const confirmModal = document.getElementById('confirmModal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmNoBtn = document.getElementById('confirm-no');

    // Nuevos elementos para el modal de compartir
    const shareBtn = document.getElementById('share-project-btn');
    const shareModal = document.getElementById('shareModal');
    const closeShareModal = document.querySelector('.close-share-modal');
    const shareForm = document.getElementById('shareForm');

    // Verificar si los elementos existen
    console.log("deleteProjectBtn exists:", !!deleteProjectBtn);
    console.log("confirmModal exists:", !!confirmModal);
    console.log("shareModal exists:", !!shareModal);

    // Obtener el parámetro del proyecto de la URL
    const urlParams = new URLSearchParams(window.location.search);
    const projectName = urlParams.get('project');
    console.log("Project name from URL:", projectName);

    // --- Funcionalidad existente ---
    // Menú desplegable
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

    // Modal de confirmación de eliminación
    if (deleteProjectBtn && confirmModal) {
        deleteProjectBtn.addEventListener('click', function() {
            confirmModal.style.display = 'block';
        });
    }

    if (confirmYesBtn && confirmNoBtn) {
        confirmYesBtn.addEventListener('click', function() {
            if (projectName) {
                window.location.href = '/delete_project?project=' + encodeURIComponent(projectName);
            }
            confirmModal.style.display = 'none';
        });

        confirmNoBtn.addEventListener('click', function() {
            confirmModal.style.display = 'none';
        });
    }

    // --- Nueva funcionalidad: Modal para compartir proyecto ---
    if (shareBtn && shareModal && closeShareModal && shareForm) {
        // Mostrar modal al hacer clic
        shareBtn.addEventListener('click', function(event) {
            event.stopPropagation();
            shareModal.style.display = 'flex';
        });

        // Cerrar modal
        closeShareModal.addEventListener('click', function() {
            shareModal.style.display = 'none';
        });

        // Cerrar al hacer clic fuera
        window.addEventListener('click', function(event) {
            if (event.target === shareModal) {
                shareModal.style.display = 'none';
            }
        });

        // Manejar envío del formulario (sin acción real)
        shareForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = document.getElementById('share-email').value;
            console.log(`Invitación demo para: ${email}`);
            // Aquí iría la lógica real de envío
            shareModal.style.display = 'none';
            
            // Muestra feedback visual (opcional)
            alert(`Demo: Invitación enviada a ${email}`);
        });
    } else {
        console.warn("Algunos elementos del modal de compartir no existen");
    }

    // Cerrar todos los modales al presionar Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (confirmModal) confirmModal.style.display = 'none';
            if (shareModal) shareModal.style.display = 'none';
        }
    });
});