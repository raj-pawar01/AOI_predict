// Main JavaScript for AQI Predictor Page and Form Syncing

// Sync range sliders and number input fields
function syncInputs(sliderId, numberId) {
    const slider = document.getElementById(sliderId);
    const numberInput = document.getElementById(numberId);
    
    if (!slider || !numberInput) return;
    
    slider.addEventListener('input', function() {
        numberInput.value = this.value;
    });
    
    numberInput.addEventListener('input', function() {
        // Enforce boundaries
        let val = parseFloat(this.value);
        const min = parseFloat(this.min);
        const max = parseFloat(this.max);
        
        if (isNaN(val)) val = min;
        if (val < min) val = min;
        if (val > max) val = max;
        
        this.value = val;
        slider.value = val;
    });
}

// Check if models are trained and update page visibility
async function checkModelAvailability() {
    try {
        const response = await fetch('/api/metrics');
        const result = await response.json();
        
        const alertDiv = document.getElementById('not-trained-alert');
        const contentDiv = document.getElementById('predictor-content');
        
        if (result.status === 'not_trained') {
            if (alertDiv) alertDiv.classList.remove('d-none');
            if (contentDiv) contentDiv.classList.add('d-none');
            return false;
        } else {
            if (alertDiv) alertDiv.classList.add('d-none');
            if (contentDiv) contentDiv.classList.remove('d-none');
            return true;
        }
    } catch (error) {
        console.error("Error checking model status:", error);
        return false;
    }
}

// Animate the circular AQI gauge
function updateAQIGauge(aqi, category) {
    const gauge = document.getElementById('gauge-progress');
    const aqiNum = document.getElementById('result-aqi');
    const badge = document.getElementById('result-category');
    
    if (!gauge || !aqiNum || !badge) return;
    
    // Animate AQI number count-up
    let current = 0;
    const target = parseFloat(aqi);
    const duration = 800; // ms
    const stepTime = Math.max(10, Math.floor(duration / (target || 1)));
    
    if (target === 0) {
        aqiNum.textContent = "0";
    } else {
        const timer = setInterval(() => {
            current += Math.ceil(target / 25);
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            aqiNum.textContent = Math.round(current);
        }, stepTime);
    }
    
    // Update Badge text and class
    badge.textContent = category;
    badge.className = "aqi-badge px-4 py-2 fs-5"; // Reset class
    
    // Add specific category class
    const catClassMap = {
        "Good": "aqi-badge-good",
        "Satisfactory": "aqi-badge-satisfactory",
        "Moderate": "aqi-badge-moderate",
        "Poor": "aqi-badge-poor",
        "Very Poor": "aqi-badge-verypoor",
        "Severe": "aqi-badge-severe"
    };
    badge.classList.add(catClassMap[category] || "bg-secondary");
    
    // Update Gauge Color ring and Progress stroke
    const gaugeColors = {
        "Good": "#2d6a4f",
        "Satisfactory": "#52b788",
        "Moderate": "#f7b731",
        "Poor": "#fd9644",
        "Very Poor": "#eb3b5a",
        "Severe": "#8b0000"
    };
    
    const targetColor = gaugeColors[category] || "var(--primary)";
    gauge.style.stroke = targetColor;
    
    // Dash Offset Calculation (max AQI is 500)
    // Circumference = 2 * PI * r = 2 * 3.14159 * 44 = 276.46
    const circumference = 276;
    const cleanAqi = Math.min(500, Math.max(0, target));
    const offset = circumference - (cleanAqi / 500) * circumference;
    
    gauge.style.strokeDashoffset = offset;
}

// Set up Predictor Page
async function initPredictorPage() {
    const isTrained = await checkModelAvailability();
    if (!isTrained) return;
    
    // Sync all range and numeric input pairs
    syncInputs('range-pm25', 'num-pm25');
    syncInputs('range-pm10', 'num-pm10');
    syncInputs('range-no2', 'num-no2');
    syncInputs('range-so2', 'num-so2');
    syncInputs('range-co', 'num-co');
    syncInputs('range-o3', 'num-o3');
    
    const form = document.getElementById('prediction-form');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Disable submit button during call
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Calculating...';
        
        // Gather values
        const payload = {
            model: document.getElementById('select-model').value,
            pm25: document.getElementById('num-pm25').value,
            pm10: document.getElementById('num-pm10').value,
            no2: document.getElementById('num-no2').value,
            so2: document.getElementById('num-so2').value,
            co: document.getElementById('num-co').value,
            o3: document.getElementById('num-o3').value
        };
        
        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // Hide placeholder, show active results
                document.getElementById('result-placeholder').classList.add('d-none');
                const activeDiv = document.getElementById('result-active');
                activeDiv.classList.remove('d-none');
                
                // Trigger gauge animation
                updateAQIGauge(result.aqi, result.category);
                
                // Update confidence level
                document.getElementById('result-confidence').textContent = result.confidence + '%';
                const confBar = document.getElementById('progress-confidence');
                confBar.style.width = result.confidence + '%';
                
                // Update recommendation box
                const recBox = document.getElementById('result-recommendation-box');
                recBox.className = `alert text-start d-flex align-items-start gap-3 p-3 mx-2 alert-${result.alert_class}`;
                
                const recIcon = document.getElementById('result-rec-icon');
                recIcon.className = `bi ${result.icon}`;
                
                document.getElementById('result-recommendation-text').textContent = result.recommendation;
                document.getElementById('result-model-used').textContent = result.model;
                
                // Scroll result card into view on small screens
                document.getElementById('result-card').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                alert("Prediction Error: " + (result.message || "Unknown error occurred"));
            }
        } catch (error) {
            console.error("Error making prediction:", error);
            alert("Connection error: Unable to reach prediction service.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}
