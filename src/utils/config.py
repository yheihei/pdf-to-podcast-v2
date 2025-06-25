import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

@dataclass
class Config:
    genai_api_key: str
    model_split: str
    model_script: str
    model_tts: str
    voice_name: str
    voice_style: str
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'Config':
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        return cls(
            genai_api_key=os.getenv('GENAI_API_KEY', ''),
            model_split=os.getenv('MODEL_SPLIT', 'gemini-2.0-flash-exp'),
            model_script=os.getenv('MODEL_SCRIPT', 'gemini-2.0-flash-exp'),
            model_tts=os.getenv('MODEL_TTS', 'gemini-2.0-flash-exp'),
            voice_name=os.getenv('VOICE_NAME', 'Aoede'),
            voice_style=os.getenv('VOICE_STYLE', 'calm')
        )
    
    def validate(self) -> None:
        if not self.genai_api_key:
            raise ValueError("GENAI_API_KEY is required")