from backend.main import app

# Root entrypoint for Vercel deployment and local Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
