document.addEventListener('DOMContentLoaded', function () {
    const dropdownBtn2 = document.getElementById('dropdown-btn2');
    const dropdownMenu2 = document.getElementById('dropdown-menu2');

    // Alternar el menú desplegable al hacer clic en el botón
    dropdownBtn2.addEventListener('click', function (event) {
        event.stopPropagation(); // Evitar que el clic cierre el menú
        dropdownMenu.classList.toggle('show');
    });

    // Cerrar el menú al hacer clic fuera de él
    document.addEventListener('click', function (event) {
        if (!dropdownMenu2.contains(event.target)) {
            dropdownMenu2.classList.remove('show');
        }
    });
});
