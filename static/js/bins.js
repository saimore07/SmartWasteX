/**
 * SmartWasteX Smart Bin Telemetry Simulation Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    window.simulateBin = async function(binId, action, buttonEl) {
        if (!buttonEl) return;
        const originalHtml = buttonEl.innerHTML;
        buttonEl.disabled = true;
        buttonEl.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span>`;

        try {
            const response = await fetch(`/api/bins/${binId}/simulate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ action: action })
            });

            const data = await response.json();
            if (data.success && data.bin) {
                updateBinCardUI(binId, data.bin, data.alert);
            } else {
                alert(data.error || 'Failed to update telemetry');
            }
        } catch (err) {
            console.error('Simulation error:', err);
            // Fallback to submitting parent form if available
            const form = buttonEl.closest('form');
            if (form) form.submit();
        } finally {
            buttonEl.disabled = false;
            buttonEl.innerHTML = originalHtml;
        }
    };

    function updateBinCardUI(binId, bin, alertInfo) {
        // Update Fill Level Badge & Text
        const fillText = document.getElementById(`fill-text-${binId}`);
        const fillBar = document.getElementById(`fill-bar-${binId}`);
        const statusBadge = document.getElementById(`status-badge-${binId}`);
        const weightText = document.getElementById(`weight-${binId}`);
        const tempText = document.getElementById(`temp-${binId}`);
        const battText = document.getElementById(`battery-${binId}`);
        const estText = document.getElementById(`estimate-${binId}`);
        const cardEl = document.getElementById(`bin-card-${binId}`);

        if (fillText) fillText.textContent = `${bin.fill_percentage}%`;
        if (weightText) weightText.textContent = `${bin.weight_kg} kg`;
        if (tempText) tempText.textContent = `${bin.temperature_c} °C`;
        if (battText) battText.textContent = `${bin.battery_level}%`;
        if (estText) {
            estText.textContent = bin.hours_to_full > 0 
                ? `Collection recommended in ~${bin.hours_to_full} hrs` 
                : 'Collection urgently required now!';
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
            statusBadge.className = 'badge';
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
                        <i class="bi ${alertInfo.priority === 'URGENT' ? 'bi-exclamation-octagon-fill' : 'bi-exclamation-triangle-fill'} fs-4 me-3"></i>
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

    // Lightweight live polling: Fetch /api/bins every 3 seconds so judges see simulator updates in real time
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
            // Silently ignore temporary network jitter during live presentations
        }
    }, 3000);
});
