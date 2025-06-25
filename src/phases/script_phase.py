import os
from typing import List
import google.generativeai as genai
from ..utils import setup_logger, Config

logger = setup_logger(__name__)

class ScriptPhase:
    def __init__(self, config: Config, output_dir: str = "output/scripts"):
        self.config = config
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        genai.configure(api_key=config.genai_api_key)
        self.model = genai.GenerativeModel(config.model_script)
    
    def process(self, chunk_files: List[str], style: str = "親しみやすく") -> List[str]:
        logger.info(f"Processing {len(chunk_files)} chunks for script generation")
        
        output_paths = []
        
        for i, chunk_file in enumerate(chunk_files, 1):
            if not os.path.exists(chunk_file):
                logger.warning(f"Chunk file not found: {chunk_file}")
                continue
            
            with open(chunk_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            script = self._generate_script(text, style)
            
            output_path = os.path.join(self.output_dir, f"script_{i}.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(script)
            
            output_paths.append(output_path)
            logger.info(f"Generated script {i}: {len(script)} characters")
        
        return output_paths
    
    def _generate_script(self, text: str, style: str) -> str:
        prompt = f"""以下のテキストを、ポッドキャストで一人が話すための台本に書き直してください。

要件:
1. 簡潔に：元のテキストの2-3倍以内の長さに収める
2. 元の内容に忠実に：創作や装飾的な要素を追加しない
3. 話し言葉で自然に：「です・ます」調で聞きやすく
4. トーンは「{style}」に
5. 導入と締めは最小限に（1-2文程度）
6. 冗長な繋ぎ言葉（「さて」「えーと」など）は控えめに

注意:
- ポッドキャスト名などを創作しない
- 過度な挨拶や感嘆詞を避ける
- 元のテキストの構成を尊重する

テキスト:
{text}

台本:"""
        
        try:
            response = self.model.generate_content(prompt)
            script = response.text.strip()
            
            script = self._post_process_script(script)
            
            return script
        
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return self._fallback_script(text)
    
    def _post_process_script(self, script: str) -> str:
        script = script.replace('。。', '。')
        script = script.replace('、、', '、')
        
        lines = script.split('\n')
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('*'):
                processed_lines.append(line)
        
        return '\n\n'.join(processed_lines)
    
    def _fallback_script(self, text: str) -> str:
        logger.warning("Using fallback script generation")
        
        paragraphs = text.split('\n\n')
        script_parts = []
        
        script_parts.append("皆さん、こんにちは。今回は次の内容についてお話しします。")
        
        for para in paragraphs:
            para = para.strip()
            if para:
                sentences = para.replace('。', '。\n').split('\n')
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        if len(sentence) > 100:
                            mid = len(sentence) // 2
                            split_point = sentence.find('、', mid - 20, mid + 20)
                            if split_point > 0:
                                script_parts.append(sentence[:split_point + 1])
                                script_parts.append(sentence[split_point + 1:])
                            else:
                                script_parts.append(sentence)
                        else:
                            script_parts.append(sentence)
        
        script_parts.append("\n以上が今回の内容でした。ありがとうございました。")
        
        return '\n\n'.join(script_parts)