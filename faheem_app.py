from fastapi.middleware.cors import CORSMiddleware
from faheem_speech import create_speech_router
import faheem_engine
from faheem_orchestrator import create_chat_router
from fastapi import FastAPI
from faheem_report_tools import create_report_tools_router

if not hasattr(faheem_engine, "app"):
    raise RuntimeError("faheem_engine.py must expose a FastAPI instance named 'app'.")

if not callable(getattr(faheem_engine, "analyze_text", None)):
    raise RuntimeError("faheem_engine.py must expose a callable function named 'analyze_text'.")

app = faheem_engine.app

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

chat_router = create_chat_router(faheem_engine.analyze_text)
app.include_router(chat_router)
speech_router = create_speech_router()
app.include_router(speech_router)
app.include_router(create_report_tools_router())


@app.get("/health")
async def health():
    return {"status": "ok", "service": "FAHEEM AI"}
