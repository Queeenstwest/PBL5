from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_cors import CORS
import paho.mqtt.client as mqtt
import sqlite3
import os
import requests
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)

# Create directory for storing images
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ESP32 Webcam server URL
# Sử dụng URL với tham số chất lượng cao hơn (nếu ESP32-CAM hỗ trợ)
ESP32_WEBCAM_URL = "http://192.168.141.171/capture?quality=10&resolution=UXGA"
# UXGA = 1600x1200, chất lượng: giá trị thấp hơn = chất lượng cao hơn (10-63)

# Khởi tạo SQLite


def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (timestamp TEXT, temperature REAL, humidity REAL, light REAL, moisture INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leaf_images
                 (timestamp TEXT, image TEXT)''')
    conn.commit()
    conn.close()


# Cấu hình MQTT
latest_data = {"temperature": 0, "humidity": 0, "light": 0, "moisture": 0}
client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with code", rc)
    client.subscribe("sensor/dht11")
    client.subscribe("sensor/bh1750")
    client.subscribe("sensor/mh_soil")
    client.subscribe("image/leaf")


def on_message(client, userdata, msg):
    global latest_data
    if msg.topic == "sensor/dht11":
        data = msg.payload.decode()
        try:
            temp = float(data.split("temp:")[1].split("C")[0])
            hum = float(data.split("humidity:")[1].split("%")[0])
            latest_data["temperature"] = temp
            latest_data["humidity"] = hum
            print(
                f"Received DHT11 data: Temperature={temp}°C, Humidity={hum}%")
        except Exception as e:
            print(f"Error parsing DHT11 data: {data}, Error: {e}")
    elif msg.topic == "sensor/bh1750":
        data = msg.payload.decode()
        try:
            # Handle both formats: "light:100lux" and "light:100,lux"
            if "," in data:
                light = float(data.split("light:")[1].split(",")[0])
            else:
                light = float(data.split("light:")[1].split("lux")[0])
            latest_data["light"] = light
            print(f"Received light data: {light} lux")
        except Exception as e:
            print(f"Error parsing BH1750 data: {data}, Error: {e}")
    elif msg.topic == "sensor/mh_soil":
        data = msg.payload.decode()
        try:
            moisture = int(data.split("moisture:")[1])
            latest_data["moisture"] = moisture
            print(f"Received soil moisture data: {moisture}")
        except Exception as e:
            print(f"Error parsing soil moisture data: {data}, Error: {e}")
    elif msg.topic == "image/leaf":
        image = msg.payload.decode()
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO leaf_images (timestamp, image) VALUES (datetime('now'), ?)", (image,))
        conn.commit()
        conn.close()

    # Lưu tất cả dữ liệu vào SQLite
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO sensor_data (timestamp, temperature, humidity, light, moisture) VALUES (datetime('now'), ?, ?, ?, ?)",
              (latest_data["temperature"], latest_data["humidity"], latest_data["light"], latest_data["moisture"]))
    conn.commit()
    conn.close()


client.on_connect = on_connect
client.on_message = on_message

try:
    # Thay đổi địa chỉ IP này thành IP mới của Raspberry Pi
    RASPBERRY_PI_IP = "192.168.141.250"  # Cập nhật IP này sau khi kiểm tra
    client.connect(RASPBERRY_PI_IP, 1883, 60)
    client.loop_start()
    print(f"Connected to MQTT broker at {RASPBERRY_PI_IP}")
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")
    print("Application will continue, but MQTT functionality may not work")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def get_data():
    return latest_data


@app.route("/api/debug")
def get_debug():
    # Return information useful for debugging
    debug_info = {
        "mqtt_connected": client.is_connected(),
        "latest_data": latest_data,
        "upload_folder_exists": os.path.exists(UPLOAD_FOLDER),
        "image_count": len([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.jpg')]) if os.path.exists(UPLOAD_FOLDER) else 0
    }
    return jsonify(debug_info)


@app.route("/api/leaf")
def get_leaf():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM leaf_images ORDER BY timestamp DESC LIMIT 1")
    data = c.fetchone()
    conn.close()
    return {"timestamp": data[0], "image": data[1]} if data else {"timestamp": "", "image": ""}


@app.route("/api/take_photo")
def take_photo():
    client.publish("camera/control", "Take Photo")
    return {"status": "success"}


@app.route('/capture-image')
def capture_image():
    try:
        # Lấy các tham số từ request
        # Mặc định UXGA (1600x1200)
        resolution = request.args.get('resolution', 'UXGA')
        # Mặc định chất lượng 10 (cao nhất)
        quality = request.args.get('quality', '10')

        # Xây dựng URL với các tham số
        camera_url = f"http://192.168.141.171/capture?resolution={resolution}&quality={quality}"

        # Send request to get image from ESP32 camera
        print(f"Requesting ESP32 camera image with URL: {camera_url}")
        response = requests.get(camera_url, timeout=10)

        if response.status_code == 200:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"esp32cam_{timestamp}.jpg"
            image_path = os.path.join(
                app.config['UPLOAD_FOLDER'], image_filename)

            # Save image to directory
            with open(image_path, 'wb') as f:
                f.write(response.content)

            return jsonify({
                "status": "success",
                "message": "Image captured and saved successfully",
                "filename": image_filename,
                "url": f"/images/{image_filename}"
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to capture image: HTTP {response.status_code}"
            }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error capturing image: {str(e)}"
        }), 500


@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/latest-image')
def get_latest_image():
    try:
        # Get all files in the uploads directory
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        # Filter for jpg files only
        image_files = [f for f in files if f.endswith('.jpg')]

        if not image_files:
            return jsonify({"status": "error", "message": "No images found"})

        # Sort by creation time, get the newest file
        latest_image = sorted(image_files, key=lambda x: os.path.getmtime(
            os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)[0]

        return jsonify({
            "status": "success",
            "filename": latest_image,
            "url": f"/images/{latest_image}",
            "timestamp": os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], latest_image))
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error getting latest image: {str(e)}"
        })


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
