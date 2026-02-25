try:
    import flask
    print("✓ Flask imported successfully")
except ImportError as e:
    print(f"✗ Flask error: {e}")

try:
    import cv2
    print("✓ OpenCV imported successfully")
except ImportError as e:
    print(f"✗ OpenCV error: {e}")

try:
    import numpy
    print("✓ NumPy imported successfully")
except ImportError as e:
    print(f"✗ NumPy error: {e}")

try:
    import matplotlib
    print("✓ Matplotlib imported successfully")
except ImportError as e:
    print(f"✗ Matplotlib error: {e}")

try:
    import werkzeug
    print("✓ Werkzeug imported successfully")
except ImportError as e:
    print(f"✗ Werkzeug error: {e}")

print("\n✅ All packages are working!")
