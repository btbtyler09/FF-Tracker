// Fantasy Football Tracker JavaScript

// Global state

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Restore expanded state for team details
    setTimeout(restoreExpandedState, 100); // Small delay to ensure DOM is ready
    
    console.log('Fantasy Football Tracker initialized');
}








function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${getNotificationIcon(type)}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Add styles for notification
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        max-width: 400px;
        z-index: 1000;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        overflow: hidden;
        animation: slideIn 0.3s ease-out;
    `;
    
    // Add notification-specific styling
    const colors = {
        success: '#d4edda',
        error: '#f8d7da',
        warning: '#fff3cd',
        info: '#cce7ff'
    };
    
    const borderColors = {
        success: '#27ae60',
        error: '#e74c3c',
        warning: '#f39c12',
        info: '#3498db'
    };
    
    notification.style.background = colors[type] || colors.info;
    notification.style.borderLeft = `4px solid ${borderColors[type] || borderColors.info}`;
    
    // Add content styling
    const content = notification.querySelector('.notification-content');
    content.style.cssText = `
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
    `;
    
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        margin-left: auto;
        opacity: 0.7;
        padding: 0;
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    // Add CSS animation
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in forwards';
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    return icons[type] || icons.info;
}

// Utility function to handle API errors gracefully
async function fetchWithErrorHandling(url, options = {}) {
    try {
        const response = await fetch(url, {
            timeout: 30000, // 30 second timeout
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Fetch error for ${url}:`, error);
        throw error;
    }
}

// Handle navigation highlighting
function updateNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Table sorting functionality (if needed later)
function sortTable(table, column, direction = 'asc') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const sortedRows = rows.sort((a, b) => {
        const aVal = a.children[column].textContent.trim();
        const bVal = b.children[column].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aVal.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bVal.replace(/[^\d.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        } else {
            return direction === 'asc' 
                ? aVal.localeCompare(bVal)
                : bVal.localeCompare(aVal);
        }
    });
    
    // Clear tbody and add sorted rows
    tbody.innerHTML = '';
    sortedRows.forEach(row => tbody.appendChild(row));
}

// Team Details Expand/Collapse Functionality
function toggleTeamDetails(button) {
    const row = button.closest('tr');
    const managerId = row.getAttribute('data-manager-id');
    const detailsRow = document.querySelector(`.team-details-row[data-manager-id="${managerId}"]`);
    const expandIcon = button.querySelector('.expand-icon');
    
    if (detailsRow.style.display === 'none' || detailsRow.style.display === '') {
        // Expand
        detailsRow.style.display = 'table-row';
        button.classList.add('expanded');
        expandIcon.style.transform = 'rotate(180deg)';
        
        // Store state
        const expandedRows = getExpandedRows();
        expandedRows.add(managerId);
        localStorage.setItem('expandedRows', JSON.stringify([...expandedRows]));
    } else {
        // Collapse
        detailsRow.style.display = 'none';
        button.classList.remove('expanded');
        expandIcon.style.transform = 'rotate(0deg)';
        
        // Store state
        const expandedRows = getExpandedRows();
        expandedRows.delete(managerId);
        localStorage.setItem('expandedRows', JSON.stringify([...expandedRows]));
    }
}

// Manager Name Click to Toggle Team Details
function toggleTeamDetailsByManager(managerId) {
    const row = document.querySelector(`.standing-row[data-manager-id="${managerId}"]`);
    if (row) {
        const button = row.querySelector('.expand-btn');
        if (button) {
            toggleTeamDetails(button);
        }
    }
}



function getExpandedRows() {
    const stored = localStorage.getItem('expandedRows');
    return new Set(stored ? JSON.parse(stored) : []);
}


function restoreExpandedState() {
    const expandedRows = getExpandedRows();
    expandedRows.forEach(managerId => {
        const row = document.querySelector(`.standing-row[data-manager-id="${managerId}"]`);
        if (row) {
            const button = row.querySelector('.expand-btn');
            if (button) {
                toggleTeamDetails(button);
            }
        }
    });
}

// Export functions for use in templates
window.showNotification = showNotification;
window.toggleTeamDetails = toggleTeamDetails;
window.toggleTeamDetailsByManager = toggleTeamDetailsByManager;


// Service worker registration (for future PWA features)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Uncomment when you add a service worker
        // navigator.serviceWorker.register('/sw.js')
        //     .then(function(registration) {
        //         console.log('SW registered: ', registration);
        //     })
        //     .catch(function(registrationError) {
        //         console.log('SW registration failed: ', registrationError);
        //     });
    });
}