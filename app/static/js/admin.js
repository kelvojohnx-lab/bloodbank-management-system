document.addEventListener('DOMContentLoaded', function() {
    // Highlight active menu item
    const currentPath = window.location.pathname;
    const menuLinks = document.querySelectorAll('.menu-link');
    
    menuLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // You can add more interactive functionality here
    // For example:
    // - Fetching real-time data updates
    // - Handling form submissions
    // - Implementing search/filter for tables
    // - Adding modal dialogs for actions
});