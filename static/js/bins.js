/**
 * SmartWasteX Smart Bin Real-Time Telemetry Client
 * ==================================================
 * Periodically polls the REST API for physical sensor updates and
 * renders live capacity changes, sensor diagnostics, and overflow alerts.
 */

document.addEventListener('DOMContentLoaded', () => {
    function updateBinCardUI(binId, bin, alertInfo) {
        const fillText = document.getElementById(`fill-text-${binId}`);
        const fillBar = document.getElementById(`fill-bar-${binId}`);
        const statusBadge = document.getElementById(`status-badge-${binId}`);
        const weightText = document.getElementById(`weight-${binId}`);
        const tempText = document.getElementById(`temp-${binId}`);
        const battText = document.getElementById(`battery-${binId}`);
        const estText = document.getElementById(`estimate-${binId}`);
        const updatedText = document.getElementById(`updated-${binId}`);

        if (!bin.has_sensor_data) {
            if (fillText) fillText.innerHTML = '<span class="text-muted fs-6 fst-italic">Awaiting sensor data</span>';
            if (weightText) weightText.innerHTML = '<span class="text-muted small">Awaiting data</span>';
            if (tempText) tempText.innerHTML = '<span class="text-muted small">Awaiting data</span>';
            if (battText) battText.innerHTML = '<span class="text-muted small">Awaiting data</span>';
            if (estText) estText.innerHTML = '<span class="fst-italic">Awaiting sensor data</span>';
            if (updatedText) updatedText.innerHTML = 'Last Update: <strong>Awaiting sensor data</strong>';
            if (statusBadge) {
                statusBadge.className = 'badge bg-secondary-subtle text-secondary border px-3 py-2 fs-6';
                statusBadge.textContent = 'Awaiting sensor data';
            }
            if (fillBar) {
                fillBar.style.width = '0%';
                fillBar.className = 'progress-bar bg-secondary';
            }
            return;
        }

        // Update Fill Level Badge & Text
        if (fillText) fillText.textContent = `${bin.fill_percentage}%`;
        if (weightText) weightText.textContent = `${bin.weight_kg} kg`;
        if (tempText) tempText.textContent = `${bin.temperature_c} °C`;
        if (battText) battText.textContent = `${bin.battery_level}%`;
        if (updatedText) updatedText.innerHTML = `Last Update: <strong>${bin.last_updated}</strong>`;

        if (estText) {
            if (bin.fill_percentage >= 100) {
                estText.innerHTML = '<span class="text-danger fw-bold">Collection urgently required now!</span>';
            } else if (bin.hours_to_full && bin.hours_to_full > 0) {
                estText.innerHTML = `Service interval: ~<strong>${bin.hours_to_full} hrs</strong>`;
            } else {
                estText.textContent = 'Collection recommended';
            }
        }

        if (fillBar) {
            fillBar.style.width = `${Math.min(100, bin.fill_percentage)}%`;
            fillBar.className = 'progress-bar';
            if (bin.fill_percentage >= 100) {
                fillBar.classList.add('bg-danger', 'progress-bar-striped', 'progress-bar-animated');
            } else if (bin.fill_percentage >= 85) {
                fillBar.classList.add('bg-danger');
            } else if (bin.fill_percentage >= 70) {
                fillBar.classList.add('bg-warning');
            } else {
                fillBar.classList.add('bg-success');
            }
        }

        if (statusBadge) {
            statusBadge.className = 'badge px-3 py-2 fs-6';
            statusBadge.textContent = bin.status;
            if (bin.status === 'OVERFLOW') {
                statusBadge.classList.add('badge-eco-overflow');
            } else if (bin.status === 'HIGH') {
                statusBadge.classList.add('badge-eco-high');
            } else if (bin.status === 'WARNING') {
                statusBadge.classList.add('badge-eco-warning');
            } else {
                statusBadge.classList.add('badge-eco-normal');
            }
        }

        // Display Overflow Alert Banner dynamically if triggered
        if (alertInfo && alertInfo.triggered) {
            const alertContainer = document.getElementById('liveAlertContainer');
            if (alertContainer) {
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${alertInfo.priority === 'URGENT' ? 'danger' : 'warning'} alert-dismissible fade show shadow-sm`;
                alertDiv.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="bi ${alertInfo.priority === 'URGENT' ? 'bi-exclamation-octagon-fill' : 'bi-exclamation-triangle-fill'} fs-4 me-3 text-danger"></i>
                        <div>
                            <strong>${alertInfo.priority === 'URGENT' ? 'CRITICAL OVERFLOW ALERT' : 'CAPACITY WARNING'}</strong>:
                            ${alertInfo.message}
                            <span class="badge bg-dark ms-2">Automated Ticket Created</span>
                        </div>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                alertContainer.prepend(alertDiv);
            }
        }
    }

    // Live polling: Fetch /api/bins every 5 seconds so dashboard reflects physical hardware telemetry
    setInterval(async () => {
        try {
            const res = await fetch('/api/bins');
            if (res.ok) {
                const bins = await res.json();
                bins.forEach(b => {
                    updateBinCardUI(b.id, b);
                });
            }
        } catch (e) {
            // Silently ignore temporary network disconnects
        }
    }, 5000);
});
