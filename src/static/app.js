// Plant Monitoring Dashboard JavaScript
// Polls API every 5 seconds for updates

// Configuration
const API_BASE_URL = '';  // Same origin
const POLL_INTERVAL_MS = 5000;  // 5 seconds
const STALE_DATA_THRESHOLD_MS = 5 * 60 * 1000;  // 5 minutes

// State
let lastUpdateTime = null;
let pollTimer = null;
let envHistoryChart = null;

/**
 * Fetch plant data from API
 */
async function fetchPlants() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/plants`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data.plants || [];
    } catch (error) {
        console.error('Failed to fetch plants:', error);
        showError(`Failed to load plant data: ${error.message}`);
        return null;
    }
}

/**
 * Fetch latest environmental reading from API
 */
async function fetchEnvironmentalData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/environmental/latest`);

        if (response.status === 204) {
            // No environmental data available
            return null;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch environmental data:', error);
        return null;
    }
}

/**
 * Fetch environmental history (last 60 minutes) from API
 */
async function fetchEnvironmentalHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/environmental/history`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data.readings || [];
    } catch (error) {
        console.error('Failed to fetch environmental history:', error);
        return [];
    }
}

/**
 * Render plant cards
 */
function renderPlantCards(plants) {
    const grid = document.getElementById('plants-grid');

    if (!plants || plants.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1 / -1; text-align: center; color: #7f8c8d;">No plants configured yet.</p>';
        return;
    }

    grid.innerHTML = plants.map((plant, index) => {
        const moisture = plant.current_moisture_level;
        const threshold = plant.acceptable_moisture_level;
        const needsWatering = plant.needs_watering;

        // Determine status class
        let statusClass = 'no-data';
        let statusText = 'No Data';
        let moistureDisplay = '--';

        if (moisture !== null && moisture !== undefined) {
            if (needsWatering) {
                statusClass = 'warning';
                statusText = 'Needs Watering';
            } else {
                statusClass = 'ok';
                statusText = 'OK';
            }
            moistureDisplay = `${moisture.toFixed(1)}%`;
        }

        // Plant image or placeholder
        const imagePath = plant.image_path;
        const imageHtml = imagePath
            ? `<img src="/images/${imagePath}" alt="${plant.plant_name}" class="plant-image">`
            : `<div class="plant-image placeholder">🌿</div>`;

        return `
            <div class="plant-card ${statusClass}">
                ${imageHtml}
                <div class="plant-info">
                    <div class="plant-name">${plant.plant_name}</div>
                    <div class="plant-details">
                        <div>Channel: ${plant.sensor_channel}</div>
                        <div>Threshold: ${threshold}%</div>
                    </div>
                    <div class="moisture-display">
                        <div class="moisture-label">Current Moisture</div>
                        <div class="moisture-value ${statusClass}">${moistureDisplay}</div>
                        <span class="status-indicator ${statusClass}">${statusText}</span>
                    </div>
                    <div class="plant-actions">
                        <button class="btn btn-secondary" onclick='openEditModal(${JSON.stringify(plant)})'>Edit</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Render environmental panel
 */
function renderEnvironmentalPanel(envData) {
    const tempEl = document.getElementById('env-temperature');
    const humidityEl = document.getElementById('env-humidity');
    const pressureEl = document.getElementById('env-pressure');
    const gasEl = document.getElementById('env-gas');
    const statusEl = document.getElementById('env-status');

    if (!envData) {
        // No environmental data available
        tempEl.textContent = '--';
        humidityEl.textContent = '--';
        pressureEl.textContent = '--';
        gasEl.textContent = '--';
        statusEl.textContent = 'Sensor Unavailable';
        return;
    }

    // Update values with 2 decimal places
    tempEl.textContent = envData.temperature !== null
        ? envData.temperature.toFixed(2)
        : '--';
    humidityEl.textContent = envData.humidity !== null
        ? envData.humidity.toFixed(2)
        : '--';
    pressureEl.textContent = envData.pressure !== null
        ? envData.pressure.toFixed(2)
        : '--';
    gasEl.textContent = envData.gas_resistance !== null
        ? Math.round(envData.gas_resistance).toLocaleString()
        : '--';

    statusEl.textContent = '';  // Clear status when data available
}

/**
 * Initialize Chart.js time-series graph
 */
function initializeEnvironmentalChart() {
    const ctx = document.getElementById('env-history-chart');
    if (!ctx) return;

    envHistoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    yAxisID: 'y-temp',
                    tension: 0.3
                },
                {
                    label: 'Humidity (%)',
                    data: [],
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    yAxisID: 'y-humidity',
                    tension: 0.3
                },
                {
                    label: 'Pressure (hPa)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    yAxisID: 'y-pressure',
                    tension: 0.3,
                    hidden: true  // Hidden by default due to different scale
                },
                {
                    label: 'Gas Resistance (kΩ)',
                    data: [],
                    borderColor: 'rgb(255, 205, 86)',
                    backgroundColor: 'rgba(255, 205, 86, 0.1)',
                    yAxisID: 'y-gas',
                    tension: 0.3,
                    hidden: true  // Hidden by default due to different scale
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(2);
                            }
                            return label;
                        },
                        title: function(context) {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleTimeString();
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Time'
                    }
                },
                'y-temp': {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temperature (°C)'
                    }
                },
                'y-humidity': {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Humidity (%)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                'y-pressure': {
                    type: 'linear',
                    display: false,
                    position: 'left'
                },
                'y-gas': {
                    type: 'linear',
                    display: false,
                    position: 'right'
                }
            }
        }
    });

    console.log('Environmental history chart initialized');
}

/**
 * Update environmental history chart with new data
 */
async function updateEnvironmentalChart() {
    const readings = await fetchEnvironmentalHistory();

    const noDataEl = document.getElementById('graph-no-data');
    const canvasEl = document.getElementById('env-history-chart');

    if (!readings || readings.length === 0) {
        // Show "no data" message
        if (noDataEl) noDataEl.style.display = 'flex';
        if (canvasEl) canvasEl.style.display = 'none';
        return;
    }

    // Hide "no data" message, show chart
    if (noDataEl) noDataEl.style.display = 'none';
    if (canvasEl) canvasEl.style.display = 'block';

    if (!envHistoryChart) {
        initializeEnvironmentalChart();
    }

    // Convert readings to Chart.js format
    const tempData = [];
    const humidityData = [];
    const pressureData = [];
    const gasData = [];

    readings.forEach(reading => {
        const timestamp = new Date(reading.timestamp);

        if (reading.temperature !== null) {
            tempData.push({ x: timestamp, y: reading.temperature });
        }
        if (reading.humidity !== null) {
            humidityData.push({ x: timestamp, y: reading.humidity });
        }
        if (reading.pressure !== null) {
            pressureData.push({ x: timestamp, y: reading.pressure });
        }
        if (reading.gas_resistance !== null) {
            // Convert to kΩ for better readability
            gasData.push({ x: timestamp, y: reading.gas_resistance / 1000 });
        }
    });

    // Update chart datasets
    envHistoryChart.data.datasets[0].data = tempData;
    envHistoryChart.data.datasets[1].data = humidityData;
    envHistoryChart.data.datasets[2].data = pressureData;
    envHistoryChart.data.datasets[3].data = gasData;

    envHistoryChart.update('none');  // Update without animation for smoother polling

    console.log(`Updated environmental chart with ${readings.length} readings`);
}

/**
 * Update last updated timestamp
 */
function updateLastUpdatedTime() {
    const timeEl = document.getElementById('last-updated-time');
    if (lastUpdateTime) {
        timeEl.textContent = lastUpdateTime.toLocaleTimeString();
    }
}

/**
 * Check for stale data and show warning
 */
function checkStaleData() {
    const warningEl = document.getElementById('stale-warning');

    if (!lastUpdateTime) {
        warningEl.style.display = 'none';
        return;
    }

    const timeSinceUpdate = Date.now() - lastUpdateTime.getTime();

    if (timeSinceUpdate > STALE_DATA_THRESHOLD_MS) {
        warningEl.style.display = 'block';
    } else {
        warningEl.style.display = 'none';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorEl = document.getElementById('error-message');
    errorEl.textContent = message;
    errorEl.style.display = 'block';

    // Auto-hide after 10 seconds
    setTimeout(() => {
        errorEl.style.display = 'none';
    }, 10000);
}

/**
 * Main update function - fetches and renders all data
 */
async function updateDashboard() {
    console.log('Updating dashboard...');

    // Fetch plant and environmental data in parallel
    const [plants, envData] = await Promise.all([
        fetchPlants(),
        fetchEnvironmentalData()
    ]);

    // Render data
    if (plants !== null) {
        renderPlantCards(plants);
    }

    renderEnvironmentalPanel(envData);

    // Update environmental history chart
    await updateEnvironmentalChart();

    // Update timestamp
    lastUpdateTime = new Date();
    updateLastUpdatedTime();
    checkStaleData();
}

/**
 * Start polling loop
 */
function startPolling() {
    // Initial update
    updateDashboard();

    // Poll every 5 seconds
    pollTimer = setInterval(updateDashboard, POLL_INTERVAL_MS);

    console.log(`Polling started (every ${POLL_INTERVAL_MS / 1000}s)`);
}

/**
 * Stop polling (cleanup)
 */
function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
        console.log('Polling stopped');
    }
}

/**
 * Show modal
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Hide modal
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Show form error
 */
function showFormError(errorElementId, message) {
    const errorEl = document.getElementById(errorElementId);
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }
}

/**
 * Hide form error
 */
function hideFormError(errorElementId) {
    const errorEl = document.getElementById(errorElementId);
    if (errorEl) {
        errorEl.style.display = 'none';
    }
}

/**
 * Create new plant via API
 */
async function createPlant(plantName, sensorChannel, moistureThreshold) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/plants`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                plant_name: plantName,
                sensor_channel: sensorChannel,
                acceptable_moisture_level: moistureThreshold
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Failed to create plant:', error);
        throw error;
    }
}

/**
 * Update plant via API
 */
async function updatePlant(plantId, updates) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/plants/${plantId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        if (response.status === 204) {
            return {};
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Failed to update plant:', error);
        throw error;
    }
}

/**
 * Delete plant via API
 */
async function deletePlant(plantId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/plants/${plantId}`, {
            method: 'DELETE'
        });

        if (response.status === 204) {
            return;
        }

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || `HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Failed to delete plant:', error);
        throw error;
    }
}

/**
 * Setup add plant form handlers
 */
function setupAddPlantForm() {
    const addBtn = document.getElementById('add-plant-btn');
    const modal = document.getElementById('add-plant-modal');
    const closeBtn = document.getElementById('add-modal-close');
    const cancelBtn = document.getElementById('add-cancel-btn');
    const form = document.getElementById('add-plant-form');

    // Open modal
    addBtn?.addEventListener('click', () => {
        // Reset form
        form?.reset();
        hideFormError('add-form-error');
        showModal('add-plant-modal');
    });

    // Close modal
    closeBtn?.addEventListener('click', () => hideModal('add-plant-modal'));
    cancelBtn?.addEventListener('click', () => hideModal('add-plant-modal'));
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) hideModal('add-plant-modal');
    });

    // Submit form
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideFormError('add-form-error');

        const plantName = document.getElementById('add-plant-name').value.trim();
        const sensorChannel = parseInt(document.getElementById('add-sensor-channel').value);
        const moistureThreshold = parseInt(document.getElementById('add-moisture-threshold').value);

        // Client-side validation
        if (!plantName) {
            showFormError('add-form-error', 'Plant name is required');
            return;
        }

        if (sensorChannel < 0 || sensorChannel > 3) {
            showFormError('add-form-error', 'Sensor channel must be between 0 and 3');
            return;
        }

        if (moistureThreshold < 0 || moistureThreshold > 100) {
            showFormError('add-form-error', 'Moisture threshold must be between 0 and 100');
            return;
        }

        try {
            await createPlant(plantName, sensorChannel, moistureThreshold);
            hideModal('add-plant-modal');
            // Trigger immediate dashboard update
            await updateDashboard();
            showError(`Plant "${plantName}" created successfully!`);
        } catch (error) {
            showFormError('add-form-error', error.message);
        }
    });
}

/**
 * Setup edit plant form handlers
 */
function setupEditPlantForm() {
    const modal = document.getElementById('edit-plant-modal');
    const closeBtn = document.getElementById('edit-modal-close');
    const cancelBtn = document.getElementById('edit-cancel-btn');
    const deleteBtn = document.getElementById('delete-plant-btn');
    const form = document.getElementById('edit-plant-form');

    // Close modal
    closeBtn?.addEventListener('click', () => hideModal('edit-plant-modal'));
    cancelBtn?.addEventListener('click', () => hideModal('edit-plant-modal'));
    modal?.addEventListener('click', (e) => {
        if (e.target === modal) hideModal('edit-plant-modal');
    });

    // Submit form
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideFormError('edit-form-error');

        const plantId = document.getElementById('edit-plant-id').value;
        const plantName = document.getElementById('edit-plant-name').value.trim();
        const sensorChannel = parseInt(document.getElementById('edit-sensor-channel').value);
        const moistureThreshold = parseInt(document.getElementById('edit-moisture-threshold').value);

        // Client-side validation
        if (!plantName) {
            showFormError('edit-form-error', 'Plant name is required');
            return;
        }

        if (sensorChannel < 0 || sensorChannel > 3) {
            showFormError('edit-form-error', 'Sensor channel must be between 0 and 3');
            return;
        }

        if (moistureThreshold < 0 || moistureThreshold > 100) {
            showFormError('edit-form-error', 'Moisture threshold must be between 0 and 100');
            return;
        }

        try {
            // Update plant details
            await updatePlant(plantId, {
                plant_name: plantName,
                sensor_channel: sensorChannel,
                acceptable_moisture_level: moistureThreshold
            });

            // Upload image if selected
            const imageFile = window.getCurrentImageFile ? window.getCurrentImageFile() : null;
            if (imageFile) {
                await uploadPlantImage(plantId, imageFile);
            }

            hideModal('edit-plant-modal');
            await updateDashboard();
            showError(`Plant "${plantName}" updated successfully!`);
        } catch (error) {
            showFormError('edit-form-error', error.message);
        }
    });

    // Delete plant
    deleteBtn?.addEventListener('click', async () => {
        const plantId = document.getElementById('edit-plant-id').value;
        const plantName = document.getElementById('edit-plant-name').value;

        if (!confirm(`Are you sure you want to delete "${plantName}"? This action cannot be undone.`)) {
            return;
        }

        try {
            await deletePlant(plantId);
            hideModal('edit-plant-modal');
            await updateDashboard();
            showError(`Plant "${plantName}" deleted successfully!`);
        } catch (error) {
            showFormError('edit-form-error', error.message);
        }
    });
}

/**
 * Upload plant image
 */
async function uploadPlantImage(plantId, imageFile) {
    try {
        const formData = new FormData();
        formData.append('image', imageFile);

        const response = await fetch(`${API_BASE_URL}/api/plants/${plantId}/image`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Failed to upload image:', error);
        throw error;
    }
}

/**
 * Delete plant image
 */
async function deletePlantImage(plantId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/plants/${plantId}/image`, {
            method: 'DELETE'
        });

        if (response.status !== 204 && !response.ok) {
            const data = await response.json();
            throw new Error(data.error || `HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Failed to delete image:', error);
        throw error;
    }
}

/**
 * Setup image upload handlers for edit modal
 */
function setupImageUploadHandlers() {
    const uploadBtn = document.getElementById('upload-image-btn');
    const removeBtn = document.getElementById('remove-image-btn');
    const fileInput = document.getElementById('edit-image-input');
    const preview = document.getElementById('edit-image-preview');

    let currentImageFile = null;
    let hasExistingImage = false;

    // Upload button click -> trigger file input
    uploadBtn?.addEventListener('click', () => {
        fileInput?.click();
    });

    // File selected -> show preview
    fileInput?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Client-side validation
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            showFormError('edit-form-error', 'Invalid file format. Accepted: JPEG, PNG, GIF, WebP');
            return;
        }

        const maxSize = 10 * 1024 * 1024; // 10 MB
        if (file.size > maxSize) {
            showFormError('edit-form-error', 'File size exceeds 10 MB limit');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (event) => {
            preview.innerHTML = `<img src="${event.target.result}" alt="Preview">`;
            removeBtn.style.display = 'inline-block';
        };
        reader.readAsDataURL(file);

        currentImageFile = file;
        hideFormError('edit-form-error');
    });

    // Remove button click -> clear preview
    removeBtn?.addEventListener('click', async () => {
        const plantId = document.getElementById('edit-plant-id').value;

        if (hasExistingImage) {
            // Delete from server
            if (!confirm('Are you sure you want to remove this image?')) {
                return;
            }

            try {
                await deletePlantImage(plantId);
                hasExistingImage = false;
            } catch (error) {
                showFormError('edit-form-error', error.message);
                return;
            }
        }

        // Clear preview
        preview.innerHTML = '<div class="image-placeholder">🌿</div>';
        removeBtn.style.display = 'none';
        currentImageFile = null;
        fileInput.value = '';
        hideFormError('edit-form-error');
    });

    // Store functions for use in form submit
    window.getCurrentImageFile = () => currentImageFile;
    window.setHasExistingImage = (value) => { hasExistingImage = value; };
    window.setImagePreview = (imagePath) => {
        if (imagePath) {
            preview.innerHTML = `<img src="/images/${imagePath}" alt="Plant image">`;
            removeBtn.style.display = 'inline-block';
            hasExistingImage = true;
        } else {
            preview.innerHTML = '<div class="image-placeholder">🌿</div>';
            removeBtn.style.display = 'none';
            hasExistingImage = false;
        }
        currentImageFile = null;
        fileInput.value = '';
    };
}

/**
 * Open edit modal for a plant
 */
function openEditModal(plant) {
    // Pre-fill form
    document.getElementById('edit-plant-id').value = plant.plant_name;
    document.getElementById('edit-plant-name').value = plant.plant_name;
    document.getElementById('edit-sensor-channel').value = plant.sensor_channel;
    document.getElementById('edit-moisture-threshold').value = plant.acceptable_moisture_level;

    // Set image preview
    if (window.setImagePreview) {
        window.setImagePreview(plant.image_path);
    }

    hideFormError('edit-form-error');
    showModal('edit-plant-modal');
}

// Start dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Plant Monitoring Dashboard loaded');
    setupAddPlantForm();
    setupEditPlantForm();
    setupImageUploadHandlers();
    startPolling();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopPolling();
});
