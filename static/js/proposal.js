const statusConfig = {
    'draft':   { label: 'Brouillons', color: 'gray' },
    'waiting': { label: 'En attente', color: 'blue' },
    'nego':    { label: 'En cours',   color: 'orange' },
    'won':     { label: 'Terminés',   color: 'green' }
};


// DÉBUT DU DRAG
function drag(ev) {
    ev.dataTransfer.setData("text", ev.target.id);
    ev.dataTransfer.effectAllowed = "move"; 
    
    setTimeout(() => {
        ev.target.classList.add('dragging');
    }, 0);
}

// FIN DU DRAG
function dragEnd(ev) {
    ev.target.classList.remove('dragging');
    document.querySelectorAll('.status-column').forEach(col => col.style.background = "");
}

// SURVOL
function allowDrop(ev) {
    ev.preventDefault();
    
    const column = ev.target.closest('.status-column');
    if (!column) return;

    column.style.background = "#f9fafb";

    const container = column.querySelector('.column-content');
    const draggingCard = document.querySelector('.dragging');

    if (!draggingCard) return;

    const newStatusKey = column.getAttribute('data-status-key');
    updateCardVisuals(draggingCard, newStatusKey);

    const afterElement = getDragAfterElement(container, ev.clientY);
    if (afterElement == null) {
        container.appendChild(draggingCard);
    } else {
        container.insertBefore(draggingCard, afterElement);
    }
}

// DROP
function drop(ev) {
    ev.preventDefault();
    
    const card = document.querySelector('.dragging');
    if (!card) return;

    card.classList.remove('dragging'); 
    document.querySelectorAll('.status-column').forEach(col => col.style.background = "");

    let targetColumn = card.closest('.status-column'); 

    if (targetColumn) {
        let newStatus = targetColumn.getAttribute('data-status-key');
        let projectId = card.getAttribute('data-project-id');

        updateCardVisuals(card, newStatus);

        updateStatusInDb(projectId, newStatus);

        updateCounters();
    }
}

// CALCUL DE POSITION
function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.status-card:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// --- UPDATE VISUEL DU BADGE ---
function updateCardVisuals(card, statusKey) {
    const badge = card.querySelector('.status-badge');
    const config = statusConfig[statusKey];

    if (badge && config) {
        if (badge.innerText !== config.label) {
            badge.className = `status-badge ${config.color}`;
            badge.innerText = config.label;
        }
    }
}

// UPDATE BACKEND
function updateStatusInDb(projectId, status) {
    fetch(UPDATE_URL, { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, new_status: status }),
    }).catch(err => console.error(err));
}

// UPDATE COMPTEURS
function updateCounters() {
    document.querySelectorAll('.status-column').forEach(col => {
        let count = col.querySelectorAll('.status-card').length;
        let statusKey = col.getAttribute('data-status-key');
        let counterElement = document.getElementById('count-' + statusKey);
        if(counterElement) counterElement.innerText = count;
    });
}