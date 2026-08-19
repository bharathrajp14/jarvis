# api/routes/voice.py — Voice STT & TTS Endpoints
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(tags=["Voice"])


class VoiceTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-ChristopherNeural"


@router.post("/api/voice/stt")
async def voice_stt_endpoint(file: UploadFile = File(...)):
    """Convert uploaded audio file to text using speech-to-text engine."""
    try:
        from brjarvis.core.paths import paths
        temp_dir = paths.TEMP_ROOT / "audio_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        audio_path = temp_dir / (file.filename or "recording.wav")
        audio_bytes = await file.read()
        audio_path.write_bytes(audio_bytes)

        from brjarvis.voice.stt import SpeechToTextEngine
        stt_engine = SpeechToTextEngine()
        text = stt_engine.transcribe(str(audio_path))
        return {"status": "success", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT Error: {e}")


@router.post("/api/voice/tts")
async def voice_tts_endpoint(req: VoiceTTSRequest):
    """Synthesize speech audio from text using text-to-speech engine."""
    try:
        from brjarvis.voice.tts import TextToSpeechEngine
        tts_engine = TextToSpeechEngine()
        audio_path = tts_engine.speak_to_file(req.text)
        if audio_path and Path(audio_path).exists():
            return FileResponse(audio_path, media_type="audio/mpeg", filename="speech.mp3")
        return {"status": "success", "message": "Synthesized", "text": req.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS Error: {e}")
