from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.search_controller import router as api_router

app = FastAPI(title="Welcome API")

# Cấu hình CORS để front-end có thể gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Có thể giới hạn lại thành ["http://localhost:3000"] ở môi trường production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký router từ controller
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


