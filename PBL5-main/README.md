# Hệ Thống Giám Sát Nhà Kính Thông Minh

Ứng dụng web Flask để giám sát mô hình nhà kính thông minh, thu thập dữ liệu từ cảm biến DHT11 kết nối với Raspberry Pi 3B thông qua MQTT.

## Cài đặt

1. Cài đặt các gói cần thiết:
   ```
   pip install -r requirements.txt
   ```

2. Đảm bảo Mosquitto MQTT broker đang chạy trên Raspberry Pi của bạn.

3. Cấu hình Raspberry Pi để xuất bản dữ liệu cảm biến đến MQTT broker với định dạng:
   ```
   Temperature:{nhiệt_độ}C Humidity:{độ_ẩm}%
   ```
   
   Ví dụ:
   ```
   Temperature:27.0C Humidity:86.0%
   ```

4. Chạy ứng dụng Flask:
   ```
   python app.py
   ```

5. Mở trình duyệt web và điều hướng đến:
   ```
   http://localhost:5000
   ```

## Cấu trúc MQTT Topic

Ứng dụng đăng ký đến topic `sensor/dht11`. Raspberry Pi sẽ xuất bản dữ liệu với định dạng:
```
Temperature:{nhiệt_độ}C Humidity:{độ_ẩm}%
```

## Tính năng

- Hiển thị dữ liệu cảm biến theo thời gian thực
- Tự động làm mới mỗi 5 giây
- Tùy chọn làm mới thủ công
- Thiết kế đáp ứng sử dụng Bootstrap

setup:
chỉnh mosquitto.conf để allow anonymous (done)
login lần đầu: admin@192.168.244.251 pass 123
source myenv/bin/activate (chạy khi vào được pi os từ laptop) 


bước chạy:
bật điểm truy cập wifi
connect laptop với wifi 
vào terminal gọi ssh admin@192.168.244.251 (ssh admin@raspberrypi.local)
pass 123
truy cập VNC để vào giao diện pi (admin, pass 123)
mở terminal, gọi lệnh source myenv/bin/activate để vào môi trường ảo
chạy python3 dht11_mqtt.py
ở laptop chạy python app.py

