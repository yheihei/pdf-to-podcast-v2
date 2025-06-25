import os
import json
from typing import List, Dict
import google.generativeai as genai
from ..utils import setup_logger, Config

logger = setup_logger(__name__)

class SplitPhase:
    def __init__(self, config: Config, output_dir: str = "output/chunks"):
        self.config = config
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        genai.configure(api_key=config.genai_api_key)
        self.model = genai.GenerativeModel(config.model_split)
    
    def process(self, input_file: str, target_chunk_size: int = 1400) -> List[str]:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        logger.info(f"Processing file for content splitting: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if len(text) < target_chunk_size * 1.5:
            logger.info("Text is short enough, no splitting needed")
            output_path = os.path.join(self.output_dir, "chunk_1.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return [output_path]
        
        chunks = self._split_content(text, target_chunk_size)
        
        output_paths = []
        for i, chunk in enumerate(chunks, 1):
            output_path = os.path.join(self.output_dir, f"chunk_{i}.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(chunk)
            output_paths.append(output_path)
            logger.info(f"Created chunk {i}: {len(chunk)} characters")
        
        return output_paths
    
    def _split_content(self, text: str, target_size: int) -> List[str]:
        prompt = f"""以下のテキストを、自然な区切りで分割してください。

要件:
1. 各部分は約{target_size}文字（音声で約4分程度）になるようにしてください
2. 章、節、トピックの変わり目など、内容的に自然な位置で分割してください
3. 文の途中で切らないでください
4. 各分割箇所を示す際は、その位置の前後の文章を含めて明確に示してください

出力形式:
JSONフォーマットで、以下の形式で出力してください:
{{
  "splits": [
    {{
      "split_position": 1,
      "marker_text": "分割位置の前後20文字程度のテキスト",
      "reason": "分割理由"
    }}
  ]
}}

テキスト:
{text[:3000]}...

(注: テキストが長い場合は最初の3000文字のみ表示しています。実際の分割は全体を考慮して行ってください)"""
        
        try:
            response = self.model.generate_content(prompt)
            split_info = self._parse_split_response(response.text)
            
            if not split_info or not split_info.get('splits'):
                logger.warning("Failed to get split information, falling back to simple split")
                return self._simple_split(text, target_size)
            
            return self._apply_splits(text, split_info['splits'])
        
        except Exception as e:
            logger.error(f"Error during content splitting: {e}")
            return self._simple_split(text, target_size)
    
    def _parse_split_response(self, response_text: str) -> Dict:
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
        except:
            pass
        return {}
    
    def _apply_splits(self, text: str, splits: List[Dict]) -> List[str]:
        chunks = []
        last_pos = 0
        
        for split in splits:
            marker = split.get('marker_text', '')
            if marker in text[last_pos:]:
                split_pos = text.find(marker, last_pos) + len(marker)
                chunks.append(text[last_pos:split_pos].strip())
                last_pos = split_pos
                logger.debug(f"Split at: {marker} - Reason: {split.get('reason', 'N/A')}")
        
        if last_pos < len(text):
            chunks.append(text[last_pos:].strip())
        
        return [chunk for chunk in chunks if chunk]
    
    def _simple_split(self, text: str, target_size: int) -> List[str]:
        logger.info("Using simple splitting method")
        
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            para_size = len(paragraph)
            
            if current_size + para_size > target_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_size = para_size
            else:
                current_chunk.append(paragraph)
                current_size += para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks