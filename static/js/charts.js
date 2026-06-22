// Visualization and Dashboard Controller using Chart.js

// Configure global Chart.js defaults for Dark Portal theme
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';
    Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.plugins.tooltip.backgroundColor = '#0e1322';
    Chart.defaults.plugins.tooltip.titleColor = '#f1f5f9';
    Chart.defaults.plugins.tooltip.bodyColor = '#f1f5f9';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
}

// Color definitions for consistency
const AQI_COLORS = {
    "Good": "rgba(16, 185, 129, 0.85)",
    "Satisfactory": "rgba(52, 211, 153, 0.85)",
    "Moderate": "rgba(245, 158, 11, 0.85)",
    "Poor": "rgba(249, 115, 22, 0.85)",
    "Very Poor": "rgba(239, 68, 68, 0.85)",
    "Severe": "rgba(153, 27, 27, 0.85)"
};

const GAUGES_BORDER_COLORS = {
    "Good": "#10b981",
    "Satisfactory": "#34d399",
    "Moderate": "#f59e0b",
    "Poor": "#f97316",
    "Very Poor": "#ef4444",
    "Severe": "#991b1b"
};

// Global chart references to allow destroying before recreating
let charts = {};

// ==========================================
// 1. DATA PREPROCESSING & EDA DASHBOARD
// ==========================================
async function loadDashboardData() {
    try {
        const metricsResponse = await fetch('/api/metrics');
        const metricsResult = await metricsResponse.json();
        
        if (metricsResult.status === 'not_trained') {
            document.getElementById('not-trained-alert').classList.remove('d-none');
            document.getElementById('dashboard-content').classList.add('d-none');
            return;
        }
        
        document.getElementById('not-trained-alert').classList.add('d-none');
        document.getElementById('dashboard-content').classList.remove('d-none');
        
        const summary = metricsResult.data.preprocessing_summary;
        
        // Populate Preprocessing Summary Cards
        document.getElementById('val-raw-rows').textContent = summary.raw_rows.toLocaleString();
        document.getElementById('val-clean-rows').textContent = summary.preprocessed_rows.toLocaleString();
        document.getElementById('val-duplicates').textContent = summary.duplicates_removed.toLocaleString();
        document.getElementById('val-split').textContent = `${summary.train_shape[0].toLocaleString()} / ${summary.test_shape[0].toLocaleString()}`;
        

        
        // Fetch and load EDA Charts
        const edaResponse = await fetch('/api/eda');
        const edaResult = await edaResponse.json();
        
        if (edaResult.status === 'success') {
            renderEDADashboards(edaResult);
        }
        
    } catch (error) {
        console.error("Error loading dashboard data:", error);
    }
}

function renderEDADashboards(data) {
    // 1. AQI Distribution Doughnut Chart
    const aqiDistCanvas = document.getElementById('chart-aqi-dist');
    if (aqiDistCanvas) {
        const labels = Object.keys(data.aqi_distribution);
        const values = Object.values(data.aqi_distribution);
        const bgColors = labels.map(label => AQI_COLORS[label] || "rgba(100, 100, 100, 0.8)");
        
        if (charts['aqi-dist']) charts['aqi-dist'].destroy();
        charts['aqi-dist'] = new Chart(aqiDistCanvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: bgColors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, font: { family: 'Plus Jakarta Sans' } }
                    }
                }
            }
        });
    }
    
    // 2. Pollutant Average Concentrations Bar Chart
    const pollutantCanvas = document.getElementById('chart-pollutant-avgs');
    if (pollutantCanvas) {
        const labels = Object.keys(data.pollutant_averages);
        const values = Object.values(data.pollutant_averages);
        
        if (charts['pollutant-avgs']) charts['pollutant-avgs'].destroy();
        charts['pollutant-avgs'] = new Chart(pollutantCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Mean Concentration',
                    data: values,
                    backgroundColor: 'rgba(90, 82, 229, 0.75)',
                    borderColor: 'rgba(90, 82, 229, 1)',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Concentration (μg/m³ or mg/m³ for CO)' }
                    }
                }
            }
        });
    }
    
    // 3. PM2.5 and PM10 Trends ( Jalgaon Monthly )
    const pmTrendsCanvas = document.getElementById('chart-pm-trends');
    if (pmTrendsCanvas) {
        if (charts['pm-trends']) charts['pm-trends'].destroy();
        charts['pm-trends'] = new Chart(pmTrendsCanvas, {
            type: 'line',
            data: {
                labels: data.trends.months,
                datasets: [
                    {
                        label: 'PM2.5 Average',
                        data: data.trends.pm25,
                        borderColor: 'rgba(235, 59, 90, 0.9)',
                        backgroundColor: 'rgba(235, 59, 90, 0.1)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2.5
                    },
                    {
                        label: 'PM10 Average',
                        data: data.trends.pm10,
                        borderColor: 'rgba(16, 185, 129, 0.9)',
                        backgroundColor: 'rgba(16, 185, 129, 0.05)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2.5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Concentration (μg/m³)' }
                    }
                }
            }
        });
    }
    
    // 4. Time Series Chart ( Last 120 Hours )
    const tsCanvas = document.getElementById('chart-aqi-time-series');
    if (tsCanvas) {
        // Formating short dates for chart labels
        const shortLabels = data.time_series.timestamps.map(t => {
            const dt = new Date(t);
            return dt.toLocaleDateString('en-IN', {day:'numeric', month:'short'}) + ' ' + dt.toLocaleTimeString('en-IN', {hour: '2-digit', minute:'2-digit'});
        });
        
        if (charts['time-series']) charts['time-series'].destroy();
        charts['time-series'] = new Chart(tsCanvas, {
            type: 'line',
            data: {
                labels: shortLabels,
                datasets: [
                    {
                        label: 'AQI Value',
                        data: data.time_series.aqi,
                        borderColor: 'var(--primary)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: 'rgba(90, 82, 229, 0.1)',
                        tension: 0.2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { maxTicksLimit: 12 } },
                    y: { beginAtZero: true, title: { display: true, text: 'AQI' } }
                }
            }
        });
    }
    
    // 5. Feature Importance Horizontal Bar Chart
    const importanceCanvas = document.getElementById('chart-feature-importance');
    if (importanceCanvas) {
        const labels = Object.keys(data.feature_importance);
        const values = Object.values(data.feature_importance);
        
        if (charts['importance']) charts['importance'].destroy();
        charts['importance'] = new Chart(importanceCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: 'rgba(16, 185, 129, 0.85)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 1.5,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, title: { display: true, text: 'Relative Importance Score' } }
                }
            }
        });
    }
    
    // 6. Build Correlation Heatmap Table Matrix
    const heatmapContainer = document.getElementById('correlation-heatmap-container');
    if (heatmapContainer) {
        const cols = data.correlation_matrix.columns;
        const matrix = data.correlation_matrix.matrix;
        
        let html = '<div class="table-responsive"><table class="w-100" style="border-collapse: separate; border-spacing: 4px;">';
        
        // Header row
        html += '<tr><td></td>';
        cols.forEach(col => {
            html += `<td class="text-center font-weight-bold py-1" style="font-size:0.8rem; font-weight:700; width:60px; color:var(--text-secondary)">${col}</td>`;
        });
        html += '</tr>';
        
        // Matrix Rows
        for (let r = 0; r < matrix.length; r++) {
            html += `<tr><td class="text-end font-weight-bold pe-2" style="font-size:0.8rem; font-weight:700; color:var(--text-secondary)">${cols[r]}</td>`;
            for (let c = 0; c < matrix[r].length; c++) {
                const val = matrix[r][c];
                // Scale color based on correlation strength (positive is indigo, negative is rose red)
                const opacity = Math.abs(val).toFixed(2);
                const color = val >= 0 ? `rgba(90, 82, 229, ${opacity})` : `rgba(239, 68, 68, ${opacity})`;
                const textColor = Math.abs(val) > 0.45 ? '#ffffff' : '#94a3b8';
                
                html += `<td class="text-center py-2 px-1 rounded" style="background-color: ${color}; color: ${textColor}; font-weight:700; font-size:0.85rem;" title="Correlation between ${cols[r]} and ${cols[c]}: ${val.toFixed(3)}">
                    ${val.toFixed(2)}
                </td>`;
            }
            html += '</tr>';
        }
        html += '</table></div>';
        heatmapContainer.innerHTML = html;
    }
}

// ==========================================
// 2. MODEL EVALUATION & COMPARISON
// ==========================================
let trainPollInterval = null;

async function loadComparisonData() {
    try {
        const response = await fetch('/api/metrics');
        const result = await response.json();
        
        // Register Retrain button listener
        const retrainBtn = document.getElementById('btn-retrain');
        if (retrainBtn) {
            retrainBtn.onclick = startRetraining;
        }
        
        // Check if retraining is currently running (in case of page reload)
        checkCurrentRetrainStatus();
        
        if (result.status === 'not_trained') {
            document.getElementById('not-trained-alert').classList.remove('d-none');
            document.getElementById('comparison-content').classList.add('d-none');
            return;
        }
        
        document.getElementById('not-trained-alert').classList.add('d-none');
        document.getElementById('comparison-content').classList.remove('d-none');
        
        // Process model scores
        const metrics = result.data.metrics;
        
        // Convert to sorted array by R2 score
        const modelsArray = Object.entries(metrics).map(([name, scores]) => ({
            name: name,
            ...scores
        })).sort((a, b) => b.R2 - a.R2);
        
        // Highlight Best Model (Prioritized to Artificial Neural Network by user preference)
        const bestModel = modelsArray.find(m => m.name === 'Artificial Neural Network') || modelsArray[0];
        document.getElementById('best-model-name').textContent = bestModel.name;
        document.getElementById('best-model-r2').textContent = bestModel.R2.toFixed(4);
        document.getElementById('best-model-rmse-badge').textContent = `RMSE: ${bestModel.RMSE.toFixed(3)}`;
        
        // Render comparison charts
        renderModelComparisonCharts(modelsArray);
        
        // Render ranking table
        const rankingBody = document.getElementById('ranking-table-body');
        rankingBody.innerHTML = '';
        modelsArray.forEach((model, index) => {
            const isBest = model.name === 'Artificial Neural Network';
            const rowClass = isBest ? 'highlight-best' : '';
            const badgeClass = isBest ? 'badge bg-success' : 'badge bg-light text-dark border';
            
            const row = `<tr class="${rowClass}">
                <td class="font-weight-bold">${index + 1}</td>
                <td class="font-weight-bold">
                    ${model.name} ${isBest ? '<i class="bi bi-patch-check-fill text-success ms-1" title="Best Performing Model"></i>' : ''}
                </td>
                <td>${model.MAE.toFixed(3)}</td>
                <td>${model.MSE.toFixed(2)}</td>
                <td>${model.RMSE.toFixed(3)}</td>
                <td><span class="${badgeClass}">${model.R2.toFixed(4)}</span></td>
            </tr>`;
            rankingBody.innerHTML += row;
        });
        
    } catch (error) {
        console.error("Error loading comparison data:", error);
    }
}

function renderModelComparisonCharts(models) {
    const names = models.map(m => m.name);
    const r2s = models.map(m => m.R2);
    const rmses = models.map(m => m.RMSE);
    const maes = models.map(m => m.MAE);
    
    // Bar chart colors (highlighting the Artificial Neural Network in green, others in indigo)
    const backgroundColors = models.map((m) => m.name === 'Artificial Neural Network' ? 'rgba(16, 185, 129, 0.85)' : 'rgba(90, 82, 229, 0.75)');
    const borderColors = models.map((m) => m.name === 'Artificial Neural Network' ? 'rgba(16, 185, 129, 1)' : 'rgba(90, 82, 229, 1)');
    
    // 1. R2 Score Comparison Chart
    const r2Canvas = document.getElementById('chart-r2-compare');
    if (r2Canvas) {
        if (charts['r2-compare']) charts['r2-compare'].destroy();
        charts['r2-compare'] = new Chart(r2Canvas, {
            type: 'bar',
            data: {
                labels: names,
                datasets: [{
                    label: 'R² (R-Squared) Coefficient',
                    data: r2s,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 1.5,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: { display: true, text: 'R² Coefficient' }
                    }
                }
            }
        });
    }
    
    // 2. Error Score Comparison Chart (RMSE & MAE)
    const errorCanvas = document.getElementById('chart-error-compare');
    if (errorCanvas) {
        if (charts['error-compare']) charts['error-compare'].destroy();
        charts['error-compare'] = new Chart(errorCanvas, {
            type: 'bar',
            data: {
                labels: names,
                datasets: [
                    {
                        label: 'Root Mean Squared Error (RMSE)',
                        data: rmses,
                        backgroundColor: 'rgba(235, 59, 90, 0.8)',
                        borderColor: 'rgba(235, 59, 90, 1)',
                        borderWidth: 1.5,
                        borderRadius: 4
                    },
                    {
                        label: 'Mean Absolute Error (MAE)',
                        data: maes,
                        backgroundColor: 'rgba(253, 150, 68, 0.8)',
                        borderColor: 'rgba(253, 150, 68, 1)',
                        borderWidth: 1.5,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Error Magnitude' }
                    }
                }
            }
        });
    }
}

// Background retraining polling control
async function startRetraining() {
    const retrainBtn = document.getElementById('btn-retrain');
    if (!retrainBtn) return;
    
    retrainBtn.disabled = true;
    
    try {
        const response = await fetch('/api/train', { method: 'POST' });
        const result = await response.json();
        
        if (result.status === 'started') {
            document.getElementById('training-section').classList.remove('d-none');
            pollRetrainingLogs();
        } else {
            alert("Retraining failed to start: " + result.message);
            retrainBtn.disabled = false;
        }
    } catch (e) {
        console.error(e);
        alert("Server connection failed.");
        retrainBtn.disabled = false;
    }
}

async function checkCurrentRetrainStatus() {
    try {
        const response = await fetch('/api/train-status');
        const result = await response.json();
        
        if (result.status === 'training') {
            document.getElementById('training-section').classList.remove('d-none');
            const retrainBtn = document.getElementById('btn-retrain');
            if (retrainBtn) retrainBtn.disabled = true;
            pollRetrainingLogs();
        }
    } catch (e) {
        console.error(e);
    }
}

function pollRetrainingLogs() {
    if (trainPollInterval) clearInterval(trainPollInterval);
    
    const term = document.getElementById('terminal-logs');
    
    trainPollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/train-status');
            const result = await response.json();
            
            if (term) {
                term.textContent = result.logs;
                // Auto-scroll to bottom of console
                term.scrollTop = term.scrollHeight;
            }
            
            if (result.status === 'idle') {
                // Done training
                clearInterval(trainPollInterval);
                document.getElementById('training-status-badge').className = "badge bg-success";
                document.getElementById('training-status-badge').innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Completed';
                
                const retrainBtn = document.getElementById('btn-retrain');
                if (retrainBtn) retrainBtn.disabled = false;
                
                // Wait 3 seconds, hide console, reload data
                setTimeout(() => {
                    document.getElementById('training-section').classList.add('d-none');
                    loadComparisonData();
                }, 3000);
            }
        } catch (e) {
            console.error("Error polling logs:", e);
        }
    }, 1500);
}

// ==========================================
// 3. LSTM TIME SERIES FORECASTING
// ==========================================
async function initForecastPage() {
    const citySelector = document.getElementById('select-forecast-city');
    if (!citySelector) return;
    
    citySelector.onchange = function() {
        loadForecastData(this.value);
    };
    
    // Load initial city forecast
    loadForecastData(citySelector.value);
}

async function loadForecastData(cityName) {
    try {
        const response = await fetch(`/api/forecast-data?city=${cityName}`);
        const result = await response.json();
        
        if (result.status === 'error') {
            document.getElementById('not-trained-alert').classList.remove('d-none');
            document.getElementById('forecast-content').classList.add('d-none');
            return;
        }
        
        document.getElementById('not-trained-alert').classList.add('d-none');
        document.getElementById('forecast-content').classList.remove('d-none');
        
        // Calculate and set metrics cards
        const h6Avg = Math.round(result.forecast.h6.reduce((a, b) => a + b, 0) / 6);
        const h12Avg = Math.round(result.forecast.h12.reduce((a, b) => a + b, 0) / 12);
        const h24Avg = Math.round(result.forecast.h24.reduce((a, b) => a + b, 0) / 24);
        
        const getCat = (aqi) => {
            if (aqi <= 50) return {name: "Good", class: "bg-success text-white"};
            else if (aqi <= 100) return {name: "Satisfactory", class: "bg-info text-dark"};
            else if (aqi <= 200) return {name: "Moderate", class: "bg-warning text-dark"};
            else if (aqi <= 300) return {name: "Poor", class: "bg-warning text-dark"};
            else if (aqi <= 400) return {name: "Very Poor", class: "bg-danger text-white"};
            else return {name: "Severe", class: "bg-danger text-white"};
        };
        
        const cat6 = getCat(h6Avg);
        const cat12 = getCat(h12Avg);
        const cat24 = getCat(h24Avg);
        
        document.getElementById('forecast-avg-6').textContent = h6Avg;
        document.getElementById('forecast-cat-6').textContent = cat6.name;
        document.getElementById('forecast-cat-6').className = `badge ${cat6.class} border`;
        
        document.getElementById('forecast-avg-12').textContent = h12Avg;
        document.getElementById('forecast-cat-12').textContent = cat12.name;
        document.getElementById('forecast-cat-12').className = `badge ${cat12.class} border`;
        
        document.getElementById('forecast-avg-24').textContent = h24Avg;
        document.getElementById('forecast-cat-24').textContent = cat24.name;
        document.getElementById('forecast-cat-24').className = `badge ${cat24.class} border`;
        
        // Render Combined History & Forecast Line Plot
        renderForecastPlot(result);
        
        // Populate Forecast Table Details
        const tblBody = document.getElementById('forecast-table-body');
        tblBody.innerHTML = '';
        for (let i = 0; i < result.forecast.values.length; i++) {
            const time = result.forecast.timestamps[i];
            const val = result.forecast.values[i];
            const cat = getCat(val).name;
            const textClass = `text-${cat.toLowerCase().replace(" ", "")}`;
            
            const row = `<tr>
                <td>Hour +${i+1}</td>
                <td>${time}</td>
                <td class="font-weight-bold fs-6">${val}</td>
                <td><span class="font-weight-bold ${textClass}">${cat}</span></td>
            </tr>`;
            tblBody.innerHTML += row;
        }
        
    } catch (e) {
        console.error(e);
    }
}

function renderForecastPlot(data) {
    const forecastCanvas = document.getElementById('chart-aqi-forecast');
    if (!forecastCanvas) return;
    
    // X-axis timestamps: 24 historical + 24 future
    const historyTimes = data.history.timestamps.map(t => new Date(t).toLocaleTimeString('en-IN', {hour: '2-digit', minute:'2-digit'}));
    const forecastTimes = data.forecast.timestamps.map(t => new Date(t).toLocaleTimeString('en-IN', {hour: '2-digit', minute:'2-digit'}));
    const combinedLabels = historyTimes.concat(forecastTimes);
    
    // Combine datasets. Pad historical with nulls during forecasting, and pad forecasting with nulls during history
    // We want a tiny overlap at the boundary index so the lines connect!
    const historyData = data.history.values.concat(Array(24).fill(null));
    
    const forecastData = Array(23).fill(null)
                         .concat([data.history.values[data.history.values.length-1]]) // Connect point
                         .concat(data.forecast.values);
                         
    if (charts['forecast-plot']) charts['forecast-plot'].destroy();
    charts['forecast-plot'] = new Chart(forecastCanvas, {
        type: 'line',
        data: {
            labels: combinedLabels,
            datasets: [
                {
                    label: 'Historical AQI (Actual)',
                    data: historyData,
                    borderColor: 'rgba(90, 82, 229, 0.95)',
                    backgroundColor: 'rgba(90, 82, 229, 0.1)',
                    borderWidth: 3,
                    pointRadius: 2,
                    fill: true,
                    tension: 0.15
                },
                {
                    label: 'LSTM Predicted Forecast',
                    data: forecastData,
                    borderColor: 'rgba(249, 115, 22, 0.95)',
                    backgroundColor: 'transparent',
                    borderWidth: 3,
                    borderDash: [6, 4],
                    pointRadius: 3,
                    pointBackgroundColor: 'rgba(249, 115, 22, 1)',
                    tension: 0.2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                x: {
                    ticks: { maxTicksLimit: 14 }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'AQI Value' }
                }
            }
        }
    });
}

// ==========================================
// 4. CITY AQI COMPARISON DASHBOARD
// ==========================================
async function initCityPage() {
    try {
        const response = await fetch('/api/city-data');
        const result = await response.json();
        
        if (result.status === 'error') {
            document.getElementById('not-trained-alert').classList.remove('d-none');
            document.getElementById('city-content').classList.add('d-none');
            return;
        }
        
        document.getElementById('not-trained-alert').classList.add('d-none');
        document.getElementById('city-content').classList.remove('d-none');
        
        const cities = result.cities;
        
        // Convert to sorted array by current AQI (cleanest to most polluted)
        const cityArray = Object.entries(cities).map(([name, data]) => ({
            name: name,
            ...data
        })).sort((a, b) => a.current.aqi - b.current.aqi);
        
        // Populate rankings list UI
        const rankingList = document.getElementById('city-ranking-list');
        rankingList.innerHTML = '';
        
        const catClassMap = {
            "Good": "aqi-badge-good",
            "Satisfactory": "aqi-badge-satisfactory",
            "Moderate": "aqi-badge-moderate text-dark",
            "Poor": "aqi-badge-poor",
            "Very Poor": "aqi-badge-verypoor",
            "Severe": "aqi-badge-severe"
        };
        
        cityArray.forEach((city, index) => {
            const badgeClass = catClassMap[city.current.category] || "bg-secondary";
            
            const item = `<li class="list-group-item d-flex justify-content-between align-items-center py-3 px-4">
                <div class="d-flex align-items-center">
                    <span class="fs-4 font-weight-bold text-muted me-3" style="width: 25px;">#${index + 1}</span>
                    <div>
                        <h5 class="mb-0 text-primary-dark">${city.name}</h5>
                        <small class="text-muted">Last update: ${city.current.time}</small>
                    </div>
                </div>
                <div class="text-end">
                    <div class="fs-3 font-weight-bold mb-1 text-dark" style="line-height: 1;">${city.current.aqi}</div>
                    <span class="badge ${badgeClass}" style="font-size:0.75rem;">${city.current.category}</span>
                </div>
            </li>`;
            rankingList.innerHTML += item;
        });
        
        // Render comparison charts
        renderCityComparisonCharts(cityArray);
        
    } catch (e) {
        console.error(e);
    }
}

function renderCityComparisonCharts(cities) {
    const names = cities.map(c => c.name);
    const pm25s = cities.map(c => c.current.pm25);
    const pm10s = cities.map(c => c.current.pm10);
    
    // 1. Particulate Matter side-by-side bar chart
    const pmCanvas = document.getElementById('chart-city-pollutants');
    if (pmCanvas) {
        if (charts['city-pollutants']) charts['city-pollutants'].destroy();
        charts['city-pollutants'] = new Chart(pmCanvas, {
            type: 'bar',
            data: {
                labels: names,
                datasets: [
                    {
                        label: 'PM2.5 (Fine)',
                        data: pm25s,
                        backgroundColor: 'rgba(244, 63, 94, 0.85)',
                        borderColor: 'rgba(244, 63, 94, 1)',
                        borderWidth: 1.5,
                        borderRadius: 4
                    },
                    {
                        label: 'PM10 (Coarse)',
                        data: pm10s,
                        backgroundColor: 'rgba(90, 82, 229, 0.85)',
                        borderColor: 'rgba(90, 82, 229, 1)',
                        borderWidth: 1.5,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Concentration (μg/m³)' } }
                }
            }
        });
    }
    
    // 2. 7-Day Multi-City Historical Trends line chart
    const trendsCanvas = document.getElementById('chart-city-history');
    if (trendsCanvas) {
        // Assume all cities have same historical dates (index 0 dates)
        const dates = cities[0].historical.dates.map(d => {
            const dt = new Date(d);
            return dt.toLocaleDateString('en-IN', {day:'numeric', month:'short'});
        });
        
        const cityColors = [
            '#5A52E5', // Jalgaon
            '#10B981', // Mumbai
            '#F59E0B', // Bengaluru
            '#EC4899', // Chennai
            '#EF4444', // Kolkata
            '#8B5CF6'  // Hyderabad
        ];
        
        const datasets = cities.map((city, idx) => ({
            label: city.name,
            data: city.historical.aqi,
            borderColor: cityColors[idx % cityColors.length],
            backgroundColor: 'transparent',
            borderWidth: 2.5,
            pointRadius: 3,
            tension: 0.2
        }));
        
        if (charts['city-history']) charts['city-history'].destroy();
        charts['city-history'] = new Chart(trendsCanvas, {
            type: 'line',
            data: {
                labels: dates,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { boxWidth: 12 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Daily Average AQI' }
                    }
                }
            }
        });
    }
}
