/**
 * SmartWasteX Main Client Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 6000);
    });

    // 2. Demo Login Helper
    window.fillCredentials = function(email, password) {
        const emailInput = document.getElementById('email');
        const passInput = document.getElementById('password');
        if (emailInput && passInput) {
            emailInput.value = email;
            passInput.value = password;
            // Highlight feedback
            emailInput.classList.add('is-valid');
            passInput.classList.add('is-valid');
        }
    };

    // 3. Image Upload Preview & Dropzone
    const fileInput = document.getElementById('wasteImageInput');
    const previewContainer = document.getElementById('imagePreviewContainer');
    const previewImg = document.getElementById('imagePreview');
    const dropzone = document.getElementById('uploadDropzone');

    if (fileInput && previewImg) {
        fileInput.addEventListener('change', function(e) {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(evt) {
                    previewImg.src = evt.target.result;
                    if (previewContainer) previewContainer.classList.remove('d-none');
                };
                reader.readAsDataURL(file);
            }
        });
    }

    if (dropzone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.remove('dragover');
            });
        });

        dropzone.addEventListener('drop', (e) => {
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                const event = new Event('change');
                fileInput.dispatchEvent(event);
            }
        });
    }

    // 4. Sample Item Quick Selector
    window.selectSample = function(sampleKey) {
        const sampleField = document.getElementById('sampleItemField');
        const previewContainer = document.getElementById('imagePreviewContainer');
        const previewImg = document.getElementById('imagePreview');
        const scanForm = document.getElementById('wasteScanForm');

        if (sampleField) {
            sampleField.value = sampleKey;
            if (previewImg && previewContainer) {
                previewImg.src = `/static/uploads/samples/${sampleKey}.jpg`;
                previewContainer.classList.remove('d-none');
            }
            // Auto submit or highlight
            if (scanForm) {
                const submitBtn = document.getElementById('scanSubmitBtn');
                if (submitBtn) {
                    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Classifying ${sampleKey.replace('_', ' ')}...`;
                    submitBtn.disabled = true;
                }
                scanForm.submit();
            }
        }
    };
});
