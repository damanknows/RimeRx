"""
RimeRx Main Entrypoint Wrapper
Re-exports FastAPI application instance 'app' from app.main
"""
import sys, os
from app.main import app, text_to_phonemes, analyze_word_errors
from app.config import PORT, HOST

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
