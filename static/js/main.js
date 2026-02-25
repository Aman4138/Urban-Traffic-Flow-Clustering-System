let currentClusterLevel = "medium";
let monitoringInterval = null;
let consecutiveErrors = 0;

// Update traffic signal
function updateTrafficSignal(level) {
    const redLight = document.getElementById("red-light");
    const yellowLight = document.getElementById("yellow-light");
    const greenLight = document.getElementById("green-light");
    const signalStatus = document.getElementById("signal-status");
    
    // Reset
    redLight.className = "signal-light";
    yellowLight.className = "signal-light";
    greenLight.className = "signal-light";
    
    // Activate
    if (level === "high") {
        redLight.className = "signal-light red-on";
        signalStatus.textContent = "🔴 Heavy Traffic";
    } else if (level === "medium") {
        yellowLight.className = "signal-light yellow-on";
        signalStatus.textContent = "🟡 Moderate Traffic";
    } else {
        greenLight.className = "signal-light green-on";
        signalStatus.textContent = "🟢 Light Traffic";
    }
}

// Show message
function showMessage(message, type = "info") {
    const statusDiv = document.getElementById("upload-status");
    statusDiv.style.display = "block";
    statusDiv.className = `alert alert-${type}`;
    statusDiv.textContent = message;
    
    if (type === "success") {
        setTimeout(() => {
            statusDiv.style.display = "none";
        }, 3000);
    }
}

// Fetch snapshot
async function fetchSnapshot() {
    try {
        const res = await fetch("/api/traffic_snapshot");
        const data = await res.json();

        const statusBadge = document.getElementById("status-badge");
        
        if (data.status !== "ok") {
            consecutiveErrors++;
            
            if (consecutiveErrors > 3) {
                statusBadge.textContent = "Error";
                statusBadge.className = "badge bg-danger";
            }
            
            document.getElementById("no-video-msg").style.display = "block";
            document.getElementById("video-preview").style.display = "none";
            return;
        }

        // Reset error counter
        consecutiveErrors = 0;

        // Update status
        statusBadge.textContent = "🟢 Live";
        statusBadge.className = "badge bg-success";

        // Get data
        const density = data.density_score || 0;
        const count = data.bbox_count || 0;
        const level = data.cluster_level || "medium";
        const summary = data.summary || "";

        currentClusterLevel = level;

        // Update metrics
        document.getElementById("density-score").textContent = density.toFixed(2);
        document.getElementById("vehicle-count").textContent = count;
        document.getElementById("cluster-level").textContent = level.toUpperCase();

        // Update progress bar
        const bar = document.getElementById("density-bar");
        const percent = Math.round(density * 100);
        bar.style.width = percent + "%";
        bar.textContent = percent + "%";

        if (level === "low") {
            bar.className = "progress-bar bg-success progress-bar-striped progress-bar-animated";
        } else if (level === "medium") {
            bar.className = "progress-bar bg-warning progress-bar-striped progress-bar-animated";
        } else {
            bar.className = "progress-bar bg-danger progress-bar-striped progress-bar-animated";
        }

        // Update summary
        document.getElementById("summary-box").textContent = summary;
        
        // Update video
        if (data.frame) {
            const videoPreview = document.getElementById("video-preview");
            videoPreview.src = "data:image/jpeg;base64," + data.frame;
            videoPreview.style.display = "block";
            document.getElementById("no-video-msg").style.display = "none";
        }
        
        // Update signal
        updateTrafficSignal(level);
        
        // Update source
        const sourceMap = {
            "webcam": "Webcam",
            "file": "Video File",
            "none": "None"
        };
        document.getElementById("current-source").textContent = sourceMap[data.video_source] || "None";
        
        // Hide error message if showing
        const errorDiv = document.getElementById("upload-status");
        if (errorDiv.classList.contains("alert-danger")) {
            errorDiv.style.display = "none";
        }
        
    } catch (err) {
        console.error("Fetch error:", err);
        consecutiveErrors++;
    }
}

// Configure signal
async function configureSignal() {
    try {
        const res = await fetch("/api/control_signal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cluster_level: currentClusterLevel })
        });
        
        const data = await res.json();

        document.getElementById("green-time").textContent = data.green_time;
        document.getElementById("red-time").textContent = data.red_time;
        document.getElementById("signal-note").textContent = data.note;
        document.getElementById("signal-info").style.display = "block";
        
        const btn = document.getElementById("update-signal");
        const originalText = btn.textContent;
        btn.textContent = "✓ Configured!";
        btn.className = "btn btn-success btn-lg";
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.className = "btn btn-primary btn-lg";
        }, 2000);
        
    } catch (err) {
        console.error("Signal error:", err);
        showMessage("Failed to configure signal", "danger");
    }
}

// Show graph modal
async function showGraph() {
    const modal = new bootstrap.Modal(document.getElementById('graphModal'));
    modal.show();
    
    // Load graph
    await loadGraph();
}

// Load graph
async function loadGraph() {
    const loadingDiv = document.getElementById("graph-loading");
    const graphImg = document.getElementById("traffic-graph");
    const errorDiv = document.getElementById("graph-error");
    
    // Show loading
    loadingDiv.style.display = "block";
    graphImg.style.display = "none";
    errorDiv.style.display = "none";
    
    try {
        const res = await fetch("/api/generate_graph");
        const data = await res.json();
        
        if (data.status === "success") {
            graphImg.src = "data:image/png;base64," + data.graph;
            graphImg.style.display = "block";
            loadingDiv.style.display = "none";
        } else {
            errorDiv.textContent = data.message || "Failed to generate graph";
            errorDiv.style.display = "block";
            loadingDiv.style.display = "none";
        }
    } catch (err) {
        console.error("Graph error:", err);
        errorDiv.textContent = "Error loading graph: " + err.message;
        errorDiv.style.display = "block";
        loadingDiv.style.display = "none";
    }
}

// Refresh graph
async function refreshGraph() {
    await loadGraph();
}

// Upload video
async function handleVideoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    showMessage("⏳ Uploading video...", "info");

    const formData = new FormData();
    formData.append("video", file);

    try {
        const res = await fetch("/api/upload_video", {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        if (data.status === "success") {
            showMessage("✓ " + data.message, "success");
            consecutiveErrors = 0;
        } else {
            showMessage("✗ " + data.message, "danger");
        }
    } catch (err) {
        console.error("Upload error:", err);
        showMessage("✗ Upload failed: " + err.message, "danger");
    }
}

// Delete video
async function deleteVideo() {
    showMessage("Deleting video...", "info");

    try {
        const res = await fetch("/api/delete_video", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        const data = await res.json();

        if (data.status === "success") {
            showMessage("✓ " + data.message, "success");
            document.getElementById("current-source").textContent = "None";
            document.getElementById("no-video-msg").style.display = "block";
            document.getElementById("video-preview").style.display = "none";
            document.getElementById("status-badge").textContent = "No Source";
            document.getElementById("status-badge").className = "badge bg-secondary";
        } else {
            showMessage("✗ " + data.message, "danger");
        }
    } catch (err) {
        console.error("Delete error:", err);
        showMessage("✗ Delete failed", "danger");
    }
}

// Switch to webcam
async function switchToWebcam() {
    showMessage("Activating webcam...", "info");

    try {
        const res = await fetch("/api/switch_source", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: "webcam" })
        });

        const data = await res.json();

        if (data.status === "success") {
            showMessage("✓ " + data.message, "success");
            consecutiveErrors = 0;
        } else {
            showMessage("✗ " + data.message, "danger");
        }
    } catch (err) {
        console.error("Webcam error:", err);
        showMessage("✗ Webcam activation failed", "danger");
    }
}

// Start monitoring
function startMonitoring() {
    if (monitoringInterval) {
        clearInterval(monitoringInterval);
    }
    monitoringInterval = setInterval(fetchSnapshot, 500);
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    console.log("🚦 Traffic system initialized");
    
    // Start monitoring
    startMonitoring();
    
    // Event listeners
    document.getElementById("update-signal").addEventListener("click", configureSignal);
    document.getElementById("video-upload").addEventListener("change", handleVideoUpload);
    document.getElementById("use-webcam-btn").addEventListener("click", switchToWebcam);
    document.getElementById("delete-video-btn").addEventListener("click", deleteVideo);
    
    // Graph button listeners
    document.getElementById("show-graph-btn").addEventListener("click", showGraph);
    document.getElementById("refresh-graph-btn").addEventListener("click", refreshGraph);
});
