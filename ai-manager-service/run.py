import uvicorn

if __name__ == "__main__":
    print("Демо-версия: http://localhost:8000", flush=True)
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )