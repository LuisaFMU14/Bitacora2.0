document.addEventListener('DOMContentLoaded2', function () {
    const dropdownBtn = document.getElementById('dropdown-btn2');
    const dropdownMenu = document.getElementById('dropdown-menu2');

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
});
