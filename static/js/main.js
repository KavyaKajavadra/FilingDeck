document.addEventListener("DOMContentLoaded", () => {
    // Initialize AOS (Scroll Animations)
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            easing: 'ease-out-cubic',
            once: true,
            offset: 50,
        });
    }
});
