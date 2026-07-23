#!/bin/bash

# Hàm dọn dẹp để tắt toàn bộ các tiến trình chạy ngầm khi nhấn Ctrl+C hoặc thoát
cleanup() {
    echo -e "\n\n[Hệ thống] Đang dừng tất cả các dịch vụ (Backend & Frontend)..."
    # Tắt tiến trình backend và frontend nếu đang chạy
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit 0
}

# Đăng ký sự kiện tắt tiến trình
trap cleanup SIGINT SIGTERM EXIT

echo "[Hệ thống] Khởi động ứng dụng..."

# 1. Khởi động Backend
echo "[Hệ thống] Đang khởi động Backend FastAPI (Port: 8000)..."
cd back-end || exit 1

# Kích hoạt môi trường ảo nếu có
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Chạy backend ở chế độ nền
python main.py &
BACKEND_PID=$!

# Quay trở lại thư mục gốc
cd ..

# Đợi 1 giây để backend khởi động trước khi bật frontend
sleep 1

# 2. Khởi động Frontend
echo "[Hệ thống] Đang khởi động Frontend Next.js (Port: 3000)..."
cd front-end || exit 1

# Chạy frontend ở chế độ nền
npm run dev &
FRONTEND_PID=$!

# Quay trở lại thư mục gốc
cd ..

echo -e "\n[Hệ thống] Các dịch vụ đã được kích hoạt thành công!"
echo "----------------------------------------"
echo "👉 Frontend (Next.js): http://localhost:3000"
echo "👉 Backend (FastAPI):  http://localhost:8000"
echo "----------------------------------------"
echo "Nhấn [Ctrl+C] để dừng chạy tất cả các dịch vụ cùng một lúc."

# Giữ script chạy để lắng nghe Ctrl+C
wait $BACKEND_PID $FRONTEND_PID
