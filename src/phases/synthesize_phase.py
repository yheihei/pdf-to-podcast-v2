import os
import wave
import struct
import time
import re
from typing import List
import google.generativeai as genai
from google.genai import Client, types
from pydub import AudioSegment
from ..utils import setup_logger, Config

logger = setup_logger(__name__)

class SynthesizePhase:
    def __init__(self, config: Config, output_dir: str = "output/audio"):
        self.config = config
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize new client for audio generation
        self.client = Client(api_key=config.genai_api_key)
        self.model_name = config.model_tts
        
        # Initialize generative model for title generation
        genai.configure(api_key=config.genai_api_key)
        self.text_model = genai.GenerativeModel(config.model_script)
    
    def process(self, script_files: List[str], voice_name: str = None, 
                voice_style: str = None) -> List[str]:
        logger.info(f"Processing {len(script_files)} scripts for audio synthesis")
        
        voice_name = voice_name or self.config.voice_name
        voice_style = voice_style or self.config.voice_style
        
        output_paths = []
        
        for i, script_file in enumerate(script_files, 1):
            if not os.path.exists(script_file):
                logger.warning(f"Script file not found: {script_file}")
                continue
            
            with open(script_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            audio_path = self._synthesize_audio(text, i, voice_name, voice_style)
            if audio_path:
                output_paths.append(audio_path)
                logger.info(f"Generated audio {i}: {audio_path}")
        
        return output_paths
    
    def _synthesize_audio(self, text: str, index: int, voice_name: str, 
                         voice_style: str) -> str:
        try:
            # Generate title from script content
            title = self._generate_title(text)
            sanitized_title = self._sanitize_filename(title)
            logger.info(f"Generated title: {title} -> {sanitized_title}")
            
            logger.info(f"Synthesizing audio with voice: {voice_name}, style: {voice_style}")
            
            # Prepare the content with style instruction if provided
            if voice_style and voice_style.strip():
                content = f"{voice_style}: {text}"
            else:
                content = text
            
            # Retry mechanism for API calls
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"Attempt {attempt + 1} of {max_attempts} for TTS generation")
                    
                    # Call Gemini API with TTS configuration using new client
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=content,
                        config=types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_name
                                    )
                                )
                            ),
                        )
                    )
                    
                    # Extract audio data from response
                    if response.candidates and response.candidates[0].content.parts:
                        audio_data = response.candidates[0].content.parts[0].inline_data.data
                        
                        # Save as WAV first
                        wav_path = os.path.join(self.output_dir, f"{index}_{sanitized_title}.wav")
                        self._save_audio_as_wav(audio_data, wav_path)
                        
                        # Convert to MP3
                        mp3_path = os.path.join(self.output_dir, f"{index}_{sanitized_title}.mp3")
                        self._convert_to_mp3(wav_path, mp3_path, title)
                        
                        # Remove temporary WAV file
                        if os.path.exists(mp3_path):
                            os.remove(wav_path)
                        
                        logger.info(f"Successfully generated audio file: {mp3_path}")
                        return mp3_path
                    else:
                        logger.error("No audio data in API response")
                        
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(1)  # Wait before retry
                    else:
                        raise e
            
        except Exception as e:
            logger.error(f"Error generating audio with Gemini API: {e}")
            logger.info("Falling back to placeholder audio")
            
            # Fallback to placeholder audio
            mp3_path = os.path.join(self.output_dir, f"{index}_{sanitized_title}.mp3")
            silent_audio = AudioSegment.silent(duration=1000)
            silent_audio = silent_audio.set_channels(1)
            silent_audio = silent_audio.set_frame_rate(44100)
            silent_audio.export(mp3_path, format="mp3", bitrate="128k", 
                              tags={
                                  'title': title,
                                  'artist': 'PDF to Podcast Generator',
                                  'album': 'Generated Content',
                                  'comment': f'Voice: {voice_name}, Style: {voice_style[:50] if voice_style else "default"}...'
                              })
            
            return mp3_path
    
    def _save_audio_as_wav(self, audio_data: bytes, output_path: str):
        # Gemini returns 24kHz 16-bit PCM mono audio
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(24000)  # 24kHz
            wf.writeframes(audio_data)
    
    def _convert_to_mp3(self, wav_path: str, mp3_path: str, title: str = "Podcast Audio"):
        try:
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3", bitrate="128k",
                        tags={
                            'title': title,
                            'artist': 'PDF to Podcast Generator',
                            'album': 'Generated Content',
                            'genre': 'Podcast'
                        })
            logger.debug(f"Converted to MP3: {mp3_path}")
        except Exception as e:
            logger.error(f"Error converting to MP3: {e}")
            # If conversion fails, keep the WAV file
            os.rename(wav_path, mp3_path.replace('.mp3', '.wav'))
    
    def _generate_title(self, text: str) -> str:
        """Generate a concise title from the script content"""
        try:
            prompt = f"""以下のスクリプトの内容を要約して、簡潔なタイトルを生成してください。

要件:
1. 最大20文字以内
2. スクリプトの主要なトピックを反映
3. ファイル名として使用可能（特殊文字を使わない）
4. 日本語または英語
5. タイトルのみを返す（説明文は不要）

スクリプト（最初の500文字）:
{text[:500]}

タイトル:"""
            
            response = self.text_model.generate_content(prompt)
            title = response.text.strip()
            
            # Remove quotes if present
            title = title.strip('"').strip("'").strip('「').strip('」')
            
            # Limit length
            if len(title) > 20:
                title = title[:20]
            
            return title
        
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return "untitled"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for filesystem"""
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        # Limit length
        if len(filename) > 50:
            filename = filename[:50]
        # Ensure it's not empty
        if not filename:
            filename = "untitled"
        return filename