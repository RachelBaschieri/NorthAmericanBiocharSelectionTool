// script.js

document.addEventListener('DOMContentLoaded', () => {
    // Select the element with the class 'clickable-heading'
    const heading = document.querySelector('.heading');

    // Add a click event listener to the heading
    heading.addEventListener('click', () => {
        // Toggle a class that adds the effect
        heading.classList.toggle('highlight');
    });
});
