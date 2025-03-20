// State management
const state = {
    query: '',
    cameraFilter: '',
    dateStart: '',
    dateEnd: '',
    limit: 20,
    offset: 0,
    results: [],
    camerasData: [],
    statsData: {}
};

// DOM elements
const searchForm = document.getElementById('searchForm');
const searchQuery = document.getElementById('searchQuery');
const cameraFilter = document.getElementById('cameraFilter');
const dateStart = document.getElementById('dateStart');
const dateEnd = document.getElementById('dateEnd');
const resetButton = document.getElementById('resetFilters');
const resultsContainer = document.getElementById('results');
const loadingIndicator = document.getElementById('loading');
const paginationContainer = document.getElementById('pagination');
const statsContainer = document.getElementById('stats');

// Modal elements
const imageModal = document.getElementById('imageModal');
const modalClose = document.querySelector('.close');
const modalTitle = document.getElementById('modalTitle');
const modalImage = document.getElementById('modalImage');
const modalFilename = document.getElementById('modalFilename');
const modalDate = document.getElementById('modalDate');
const modalCamera = document.getElementById('modalCamera');
const modalDimensions = document.getElementById('modalDimensions');
const modalFormat = document.getElementById('modalFormat');
const modalLocation = document.getElementById('modalLocation');
const modalExif = document.getElementById('modalExif');
const modalDescription = document.getElementById('modalDescription');

// Modal tabs
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');

// Initialize the application
function init() {
    // Load initial data
    loadCameras();
    loadStats();
    
    // Initial search without query
    search();
    
    // Event listeners
    searchForm.addEventListener('submit', event => {
        event.preventDefault();
        state.query = searchQuery.value;
        state.offset = 0; // Reset pagination
        search();
    });
    
    cameraFilter.addEventListener('change', () => {
        state.cameraFilter = cameraFilter.value;
        state.offset = 0;
        search();
    });
    
    dateStart.addEventListener('change', () => {
        state.dateStart = dateStart.value;
        state.offset = 0;
        search();
    });
    
    dateEnd.addEventListener('change', () => {
        state.dateEnd = dateEnd.value;
        state.offset = 0;
        search();
    });
    
    resetButton.addEventListener('click', () => {
        state.query = '';
        state.cameraFilter = '';
        state.dateStart = '';
        state.dateEnd = '';
        state.offset = 0;
        
        // Reset form elements
        searchQuery.value = '';
        cameraFilter.value = '';
        dateStart.value = '';
        dateEnd.value = '';
        
        search();
    });
    
    // Modal events
    modalClose.addEventListener('click', () => {
        imageModal.style.display = 'none';
    });
    
    window.addEventListener('click', event => {
        if (event.target === imageModal) {
            imageModal.style.display = 'none';
        }
    });
    
    // Tab navigation
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Deactivate all tabs
            tabButtons.forEach(tab => tab.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Activate selected tab
            button.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// API functions
async function search() {
    loadingIndicator.style.display = 'block';
    resultsContainer.innerHTML = '';
    
    // Build query parameters
    const params = new URLSearchParams();
    if (state.query) params.append('q', state.query);
    if (state.cameraFilter) {
        const [make, model] = state.cameraFilter.split('|');
        if (make) params.append('camera_make', make);
        if (model) params.append('camera_model', model);
    }
    if (state.dateStart) params.append('date_start', `${state.dateStart}T00:00:00`);
    if (state.dateEnd) params.append('date_end', `${state.dateEnd}T23:59:59`);
    params.append('limit', state.limit);
    params.append('offset', state.offset);
    
    try {
        const response = await fetch(`/api/search?${params.toString()}`);
        const data = await response.json();
        
        state.results = data.results;
        displayResults(data.results);
        displayPagination(data.total);
    } catch (error) {
        console.error('Error searching:', error);
        resultsContainer.innerHTML = '<p>Error loading results. Please try again.</p>';
    } finally {
        loadingIndicator.style.display = 'none';
    }
}

async function loadCameras() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        state.camerasData = data.cameras;
        
        // Clear existing options
        cameraFilter.innerHTML = '<option value="">All Cameras</option>';
        
        // Add camera options
        data.cameras.forEach(camera => {
            const option = document.createElement('option');
            option.value = `${camera.make}|${camera.model}`;
            option.textContent = `${camera.make} ${camera.model} (${camera.count})`;
            cameraFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading cameras:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        state.statsData = data;
        
        // Display stats
        const statsHTML = `
            <div class="stats-section">
                <h3>Overview</h3>
                <p>Total Images: ${data.stats.total_images}</p>
                <p>Images with GPS Data: ${data.stats.with_gps}</p>
                <p>Images with AI Descriptions: ${data.stats.with_description}</p>
            </div>
            
            <div class="stats-section">
                <h3>Image Formats</h3>
                <ul>
                    ${data.stats.formats.map(format => 
                        `<li>${format.format || 'Unknown'}: ${format.count}</li>`
                    ).join('')}
                </ul>
            </div>
            
            <div class="stats-section">
                <h3>Date Range</h3>
                <p>${data.stats.date_range.min ? data.stats.date_range.min.split('T')[0] : 'Unknown'} to 
                   ${data.stats.date_range.max ? data.stats.date_range.max.split('T')[0] : 'Unknown'}</p>
            </div>
        `;
        
        statsContainer.innerHTML = statsHTML;
    } catch (error) {
        console.error('Error loading stats:', error);
        statsContainer.innerHTML = '<p>Error loading statistics. Please try again.</p>';
    }
}

async function viewImage(imageId) {
    try {
        const response = await fetch(`/api/image/${imageId}`);
        const imageData = await response.json();
        
        // Set modal content
        modalTitle.textContent = imageData.filename;
        modalImage.src = `/image/${imageId}`;
        modalFilename.textContent = imageData.filename;
        modalDate.textContent = imageData.capture_date ? new Date(imageData.capture_date).toLocaleString() : 'Unknown';
        modalCamera.textContent = `${imageData.camera_make || ''} ${imageData.camera_model || ''}`.trim() || 'Unknown';
        modalDimensions.textContent = `${imageData.width} × ${imageData.height}`;
        modalFormat.textContent = imageData.format || 'Unknown';
        
        // Handle location
        if (imageData.gps_lat && imageData.gps_lon) {
            modalLocation.textContent = `${imageData.gps_lat.toFixed(6)}, ${imageData.gps_lon.toFixed(6)}`;
            // Here you could add a map visualization
        } else {
            modalLocation.textContent = 'No location data';
        }
        
        // Handle EXIF data
        if (imageData.exif) {
            modalExif.textContent = JSON.stringify(imageData.exif, null, 2);
        } else {
            modalExif.textContent = 'No EXIF data available';
        }
        
        // Handle description
        if (imageData.description) {
            modalDescription.textContent = imageData.description;
        } else {
            modalDescription.textContent = 'No AI description available';
        }
        
        // Show modal
        imageModal.style.display = 'block';
    } catch (error) {
        console.error('Error loading image details:', error);
        alert('Error loading image details. Please try again.');
    }
}

// Display functions
function displayResults(results) {
    if (results.length === 0) {
        resultsContainer.innerHTML = '<p>No images found matching your search criteria.</p>';
        return;
    }
    
    const html = results.map(image => `
        <div class="image-card" data-id="${image.id}">
            <img src="${image.thumbnail || '/static/placeholder.jpg'}" alt="${image.filename}">
            <div class="details">
                <p>${image.filename}</p>
                <p>${image.capture_date ? new Date(image.capture_date).toLocaleDateString() : 'Unknown date'}</p>
                <p>${image.camera_make || ''} ${image.camera_model || ''}</p>
            </div>
        </div>
    `).join('');
    
    resultsContainer.innerHTML = html;
    
    // Add click event to cards
    document.querySelectorAll('.image-card').forEach(card => {
        card.addEventListener('click', () => {
            const imageId = card.getAttribute('data-id');
            viewImage(imageId);
        });
    });
}

function displayPagination(total) {
    const totalPages = Math.ceil(total / state.limit);
    const currentPage = Math.floor(state.offset / state.limit) + 1;
    
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }
    
    const paginationHTML = `
        <button ${currentPage === 1 ? 'disabled' : ''} id="prevPage">Previous</button>
        <span>Page ${currentPage} of ${totalPages}</span>
        <button ${currentPage === totalPages ? 'disabled' : ''} id="nextPage">Next</button>
    `;
    
    paginationContainer.innerHTML = paginationHTML;
    
    // Add event listeners
    const prevButton = document.getElementById('prevPage');
    const nextButton = document.getElementById('nextPage');
    
    if (prevButton) {
        prevButton.addEventListener('click', () => {
            state.offset = Math.max(0, state.offset - state.limit);
            search();
        });
    }
    
    if (nextButton) {
        nextButton.addEventListener('click', () => {
            state.offset = state.offset + state.limit;
            search();
        });
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', init);