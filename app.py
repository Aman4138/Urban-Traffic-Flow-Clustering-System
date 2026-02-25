from flask import Flask, render_template, jsonify, request
import cv2
import numpy as np
import time
import os
import glob
from werkzeug.utils import secure_filename
import base64
import threading
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from io import BytesIO
from datetime import datetime
from collections import deque
app = Flask(__name__)
# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm', 'mp4v'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Create upload folder
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Global variables
video_capture = None
video_lock = threading.Lock()
current_video_source = "none"
current_video_path = None

# Store historical data (last 50 data points)
traffic_history = {
    'timestamps': deque(maxlen=50),
    'density': deque(maxlen=50),
    'vehicle_count': deque(maxlen=50),
    'cluster_level': deque(maxlen=50)
}

class TrafficAnalyzer:
    """Simple traffic analyzer"""
    
    @staticmethod
    def analyze_frame(frame):
        """Analyze frame and return density, count, level"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Blur
            blurred = cv2.GaussianBlur(gray, (15, 15), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 40, 120)
            
            # Find contours
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=2)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Count valid vehicles
            vehicle_count = 0
            total_area = 0
            min_area = 300
            max_area = 50000
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    vehicle_count += 1
                    total_area += area
            
            # Calculate density
            frame_area = frame.shape[0] * frame.shape[1]
            density = min(1.0, (total_area / (frame_area * 0.2)) * 0.6 + (vehicle_count / 12.0) * 0.4)
            
            # Determine level
            if density < 0.35:
                level = "low"
            elif density < 0.70:
                level = "medium"
            else:
                level = "high"
            
            return round(density, 3), vehicle_count, level
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return 0.0, 0, "low"
    
    @staticmethod
    def generate_summary(density, count, level):
        """Generate traffic summary"""
        emoji_map = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        emoji = emoji_map.get(level, "⚪")
        
        density_percent = int(density * 100)
        
        if count == 0:
            vehicle_text = "No vehicles detected"
        elif count <= 3:
            vehicle_text = f"{count} vehicle(s) - Very light"
        elif count <= 8:
            vehicle_text = f"{count} vehicles - Smooth flow"
        elif count <= 15:
            vehicle_text = f"{count} vehicles - Moderate"
        else:
            vehicle_text = f"{count} vehicles - Heavy"
        
        recommendations = {
            "low": "Short green signal recommended",
            "medium": "Balanced signal timing needed",
            "high": "Extended green signal required"
        }
        
        summary = f"""{emoji} Traffic: {level.upper()}

📊 Analysis:
• Density: {density_percent}%
• {vehicle_text}

💡 Recommendation:
{recommendations[level]}

🚦 Status: Live monitoring
"""
        return summary

analyzer = TrafficAnalyzer()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_webcam():
    """Initialize webcam"""
    global video_capture, current_video_source
    
    with video_lock:
        # Release existing
        if video_capture is not None:
            try:
                video_capture.release()
            except:
                pass
            video_capture = None
        
        time.sleep(0.5)
        
        # Try different backends and indices
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        indices = [0, 1, 2]
        
        for backend in backends:
            for idx in indices:
                try:
                    print(f"Trying webcam {idx} with backend {backend}...")
                    cap = cv2.VideoCapture(idx, backend)
                    
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            video_capture = cap
                            current_video_source = "webcam"
                            print(f"✓ Webcam {idx} initialized!")
                            return True
                        else:
                            cap.release()
                except Exception as e:
                    print(f"Webcam {idx} error: {e}")
                    continue
        
        print("❌ No webcam found")
        return False

def init_video_file(filepath):
    """Initialize video file"""
    global video_capture, current_video_source, current_video_path
    
    with video_lock:
        # Release existing
        if video_capture is not None:
            try:
                video_capture.release()
            except:
                pass
            video_capture = None
        
        time.sleep(0.5)
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return False
        
        try:
            cap = cv2.VideoCapture(filepath)
            
            if not cap.isOpened():
                print("Cannot open video file")
                return False
            
            ret, test_frame = cap.read()
            if not ret or test_frame is None:
                cap.release()
                print("Cannot read video file")
                return False
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            video_capture = cap
            current_video_source = "file"
            current_video_path = filepath
            print(f"✓ Video file loaded")
            return True
            
        except Exception as e:
            print(f"Video file error: {e}")
            return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/upload_video", methods=["POST"])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({"status": "error", "message": "No video file provided"})
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"})
        
        if not allowed_file(file.filename):
            return jsonify({"status": "error", "message": "Invalid file type. Use: mp4, avi, mov, mkv"})
        
        # Delete old videos
        for old_file in glob.glob(os.path.join(UPLOAD_FOLDER, '*')):
            try:
                os.remove(old_file)
            except:
                pass
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        print(f"Video saved: {filepath}")
        
        # Initialize video
        if init_video_file(filepath):
            return jsonify({
                "status": "success",
                "message": "Video uploaded and loaded successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Video uploaded but cannot be processed"
            })
            
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/delete_video", methods=["POST"])
def delete_video():
    global video_capture, current_video_source, current_video_path
    
    try:
        with video_lock:
            if video_capture is not None:
                try:
                    video_capture.release()
                except:
                    pass
                video_capture = None
        
        # Delete files
        count = 0
        for video_file in glob.glob(os.path.join(UPLOAD_FOLDER, '*')):
            try:
                os.remove(video_file)
                count += 1
            except:
                pass
        
        current_video_source = "none"
        current_video_path = None
        
        return jsonify({
            "status": "success",
            "message": f"Deleted {count} file(s)"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/switch_source", methods=["POST"])
def switch_source():
    try:
        data = request.get_json()
        source = data.get("source", "webcam")
        
        if source == "webcam":
            if init_webcam():
                return jsonify({
                    "status": "success",
                    "message": "Webcam activated successfully"
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "Cannot access webcam. Please check if camera is connected and not used by another application."
                })
        
        return jsonify({"status": "error", "message": "Invalid source"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/traffic_snapshot", methods=["GET"])
def traffic_snapshot():
    global video_capture
    
    try:
        with video_lock:
            if video_capture is None or not video_capture.isOpened():
                return jsonify({
                    "status": "error",
                    "message": "No video source active"
                })
            
            # Read frame
            ret, frame = video_capture.read()
            
            # Loop video if ended
            if not ret and current_video_source == "file":
                video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = video_capture.read()
            
            if not ret or frame is None or frame.size == 0:
                return jsonify({
                    "status": "error",
                    "message": "Cannot read frame"
                })
        
        # Analyze frame
        frame_resized = cv2.resize(frame, (640, 360))
        density, count, level = analyzer.analyze_frame(frame_resized)
        
        # Store in history
        current_time = datetime.now().strftime("%H:%M:%S")
        traffic_history['timestamps'].append(current_time)
        traffic_history['density'].append(density)
        traffic_history['vehicle_count'].append(count)
        traffic_history['cluster_level'].append(0 if level == "low" else 1 if level == "medium" else 2)
        
        # Generate summary
        summary = analyzer.generate_summary(density, count, level)
        
        # Encode frame
        frame_preview = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', frame_preview, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            "status": "ok",
            "density_score": float(density),
            "bbox_count": int(count),
            "cluster_label": 0 if level == "low" else 1 if level == "medium" else 2,
            "cluster_level": level,
            "summary": summary,
            "video_source": current_video_source,
            "frame": frame_base64
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Processing error: {str(e)}"
        })

@app.route("/api/control_signal", methods=["POST"])
def control_signal():
    try:
        data = request.get_json()
        level = data.get("cluster_level", "medium")
        
        timing = {
            "low": (20, 40),
            "medium": (40, 30),
            "high": (60, 20)
        }
        
        green, red = timing.get(level, (40, 30))
        
        return jsonify({
            "green_time": green,
            "red_time": red,
            "note": f"Signal configured for {level} traffic"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/generate_graph", methods=["GET"])
def generate_graph():
    """Generate real-time traffic graph"""
    try:
        if len(traffic_history['timestamps']) < 2:
            return jsonify({
                "status": "error",
                "message": "Not enough data. Please wait for traffic analysis to collect data."
            })
        
        # Create figure with subplots
        fig = Figure(figsize=(12, 8))
        fig.patch.set_facecolor('#f8f9fa')
        
        # Subplot 1: Density Score Over Time
        ax1 = fig.add_subplot(311)
        ax1.plot(list(traffic_history['timestamps']), 
                list(traffic_history['density']), 
                color='#667eea', linewidth=2.5, marker='o', markersize=4)
        ax1.fill_between(range(len(traffic_history['density'])), 
                         list(traffic_history['density']), 
                         alpha=0.3, color='#667eea')
        ax1.set_title('Traffic Density Over Time', fontsize=14, fontweight='bold', color='#2d3748')
        ax1.set_ylabel('Density Score', fontsize=11, fontweight='bold')
        ax1.set_ylim(0, 1)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_facecolor('#ffffff')
        
        # Subplot 2: Vehicle Count Over Time
        ax2 = fig.add_subplot(312)
        ax2.bar(range(len(traffic_history['vehicle_count'])), 
               list(traffic_history['vehicle_count']), 
               color='#56ab2f', alpha=0.8, edgecolor='#2d5016', linewidth=1.5)
        ax2.set_title('Vehicle Count Over Time', fontsize=14, fontweight='bold', color='#2d3748')
        ax2.set_ylabel('Vehicle Count', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax2.set_facecolor('#ffffff')
        
        # Subplot 3: Traffic Level Over Time
        ax3 = fig.add_subplot(313)
        colors = ['#56ab2f' if x == 0 else '#ffaa00' if x == 1 else '#ee0979' 
                 for x in traffic_history['cluster_level']]
        ax3.scatter(range(len(traffic_history['cluster_level'])), 
                   list(traffic_history['cluster_level']), 
                   c=colors, s=100, alpha=0.7, edgecolors='black', linewidth=1.5)
        ax3.plot(range(len(traffic_history['cluster_level'])), 
                list(traffic_history['cluster_level']), 
                color='#764ba2', linewidth=2, alpha=0.5, linestyle='--')
        ax3.set_title('Traffic Level Classification', fontsize=14, fontweight='bold', color='#2d3748')
        ax3.set_ylabel('Traffic Level', fontsize=11, fontweight='bold')
        ax3.set_xlabel('Time Sequence', fontsize=11, fontweight='bold')
        ax3.set_yticks([0, 1, 2])
        ax3.set_yticklabels(['Low', 'Medium', 'High'])
        ax3.set_ylim(-0.5, 2.5)
        ax3.grid(True, alpha=0.3, linestyle='--')
        ax3.set_facecolor('#ffffff')
        
        # Adjust layout
        fig.tight_layout(pad=3.0)
        
        # Convert to base64
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        graph_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        
        return jsonify({
            "status": "success",
            "graph": graph_base64,
            "data_points": len(traffic_history['timestamps'])
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Graph generation error: {str(e)}"
        })

@app.route("/api/status", methods=["GET"])
def status():
    try:
        with video_lock:
            video_ok = video_capture is not None and video_capture.isOpened()
        
        return jsonify({
            "video_source": current_video_source,
            "video_ok": video_ok,
            "status": "ready" if video_ok else "no_source"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚦 URBAN TRAFFIC FLOW CLUSTERING SYSTEM")
    print("="*70)
    print("🌐 Starting server at: http://127.0.0.1:5000/")
    print("="*70 + "\n")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        if video_capture is not None:
            try:
                video_capture.release()
            except:
                pass
        print("✓ Cleanup complete!")
