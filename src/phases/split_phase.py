import json
import os
from typing import Dict, List

import google.generativeai as genai

from ..utils import Config, setup_logger

logger = setup_logger(__name__)

class SplitPhase:
    def __init__(self, config: Config, output_dir: str = "output/chunks"):
        self.config = config
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        genai.configure(api_key=config.genai_api_key)
        self.model = genai.GenerativeModel(config.model_split)
    
    def process(self, input_file: str, target_minutes: int = 5) -> List[str]:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        logger.info(f"Processing file for content splitting: {input_file}")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 約300文字/分で判定
        if len(text) < 600:  # 2分未満のテキストは分割不要
            logger.info("Text is short enough, no splitting needed")
            output_path = os.path.join(self.output_dir, "chunk_1.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            return [output_path]
        
        # 新しい分割メソッドを使用
        chunk_data = self._split_content_v2(text, target_minutes)
        
        if not chunk_data:
            raise RuntimeError("Failed to split content")
        
        chunks = [item.get('text', '') for item in chunk_data if item.get('text')]
        
        output_paths = []
        for i, chunk in enumerate(chunks, 1):
            output_path = os.path.join(self.output_dir, f"chunk_{i}.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(chunk)
            output_paths.append(output_path)
            
            # 推定読み上げ時間を計算（日本語の場合、約300文字/分）
            estimated_minutes = len(chunk) / 300
            logger.info(f"Created chunk {i}: {len(chunk)} characters (約{estimated_minutes:.1f}分)")
            
            # メタデータも保存
            if i <= len(chunk_data):
                meta_path = os.path.join(self.output_dir, f"chunk_{i}_meta.json")
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "id": i,
                        "title": chunk_data[i-1].get('title', f'チャンク{i}'),
                        "char_count": len(chunk),
                        "estimated_minutes": estimated_minutes
                    }, f, ensure_ascii=False, indent=2)
        
        return output_paths
    
    def _split_content(self, text: str, target_size: int) -> List[str]:
        # 全体のchunk数を推定
        text_length = len(text)
        estimated_chunks = max(2, int(text_length / target_size))
        
        # より詳細なログ
        logger.info(f"Text length: {text_length} characters")
        logger.info(f"Target chunk size: {target_size} characters")
        logger.info(f"Estimated chunks: {estimated_chunks}")
        
        prompt = f"""以下のテキストを読んで、すべての自然な区切りを特定してください。

分割対象:
1. 章の開始（例：「第1章」「Chapter 1」など）
2. 大きな節の区切り（例：「1.1」「■」など）
3. 明確な話題の転換点
4. その他の自然な区切り

出力形式:
JSONフォーマットで、以下の形式で出力してください:
{{
  "splits": [
    {{
      "marker_text": "分割位置の直前の文（正確な文字列、30-50文字程度）",
      "split_type": "章の開始" / "節の区切り" / "話題の転換" / "その他"
    }}
  ]
}}

重要な指示: 
- すべての自然な区切りを漏れなく特定してください
- marker_textは分割位置の「直前」の文を正確にコピーしてください
- 省略記号（...）は絶対に使わないでください
- 文字数は気にせず、内容的に自然な位置をすべて挙げてください

テキスト全文:
{text}"""
        
        try:
            response = self.model.generate_content(prompt)
            logger.debug(f"Gemini response (first 500 chars): {response.text[:500]}")
            split_info = self._parse_split_response(response.text)
            
            if not split_info or not split_info.get('splits'):
                logger.warning("Failed to get split information, falling back to simple split")
                return self._simple_split(text, target_size)
            
            logger.info(f"Gemini returned {len(split_info.get('splits', []))} split points")
            
            return self._apply_splits(text, split_info['splits'])
        
        except Exception as e:
            logger.error(f"Error during content splitting: {e}")
            return self._simple_split(text, target_size)
    
    def _parse_split_response(self, response_text: str) -> Dict:
        try:
            # JSONブロックを抽出（```json...```形式に対応）
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                if json_end > json_start:
                    json_text = response_text[json_start:json_end].strip()
                else:
                    json_text = response_text[json_start:].strip()
            else:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                else:
                    return {}
            
            parsed = json.loads(json_text)
            logger.debug(f"Parsed JSON: {json.dumps(parsed, ensure_ascii=False)[:500]}")
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:1000]}")
            return {}
    
    def _apply_splits(self, text: str, splits: List[Dict]) -> List[str]:
        chunks = []
        last_pos = 0
        
        for i, split in enumerate(splits):
            marker = split.get('marker_text', '')
            if marker in text[last_pos:]:
                # marker_textの終了位置で分割（marker自体は前のチャンクに含める）
                split_pos = text.find(marker, last_pos) + len(marker)
                chunk = text[last_pos:split_pos].strip()
                if chunk:  # 空でないチャンクのみ追加
                    chunks.append(chunk)
                    logger.info(f"Created chunk {i+1}: {len(chunk)} chars")
                    logger.debug(f"Split after: '{marker[:50]}...' - Type: {split.get('split_type', 'N/A')}")
                last_pos = split_pos
            else:
                logger.warning(f"Marker not found: '{marker[:50]}...'")
        
        # 最後の残りの部分を追加
        if last_pos < len(text):
            remaining = text[last_pos:].strip()
            if remaining:
                chunks.append(remaining)
                logger.debug(f"Final chunk: {len(remaining)} chars")
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[str], min_size: int = 1000) -> List[str]:
        """小さいチャンクを次のチャンクとマージする"""
        if not chunks:
            return chunks
        
        logger.info(f"Merging small chunks (min size: {min_size} chars)")
        logger.info(f"Initial chunk count: {len(chunks)}")
        
        merged_chunks = []
        current_chunk = chunks[0]
        
        for next_chunk in chunks[1:]:
            if len(current_chunk) < min_size:
                # 現在のチャンクが小さい場合は次のチャンクとマージ
                current_chunk = current_chunk + "\n\n" + next_chunk
                logger.debug(f"Merged chunk: {len(current_chunk)} chars")
            else:
                # 現在のチャンクが十分大きい場合は保存して次へ
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk
        
        # 最後のチャンクを処理
        if current_chunk:
            if len(current_chunk) < min_size and merged_chunks:
                # 最後のチャンクが小さい場合は前のチャンクとマージ
                merged_chunks[-1] = merged_chunks[-1] + "\n\n" + current_chunk
                logger.debug(f"Merged last chunk with previous: {len(merged_chunks[-1])} chars")
            else:
                merged_chunks.append(current_chunk)
        
        logger.info(f"Final chunk count: {len(merged_chunks)}")
        return merged_chunks
    
    def _split_content_v2(self, text: str, target_minutes: int = 5) -> List[Dict]:
        """新しい分割メソッド：Geminiに直接chunk分割を依頼"""
        # 日本語の読み上げ速度を基準に文字数を計算（約300文字/分）
        chars_per_minute = 300
        target_chars = target_minutes * chars_per_minute
        
        # 全体の文字数から適切なchunk数を計算
        text_length = len(text)
        estimated_chunks = max(1, int(text_length / target_chars))
        
        logger.info(f"Text length: {text_length} characters")
        logger.info(f"Target minutes per chunk: {target_minutes}")
        logger.info(f"Target chars per chunk: {target_chars}")
        logger.info(f"Estimated number of chunks: {estimated_chunks}")
        
        prompt = f"""あなたは編集者兼ポッドキャスト脚本家です。
以下の全文テキストを、論理的にまとまりのある「節」単位で切り分けてください。

### 必須ルール
1. 各チャンクは **600〜1200字** に収めること。
2. 出力は **JSON配列**。各要素は下記キーを持つこと。  
   - "id": 連番（1,2,3…）  
   - "title": チャンク小見出し（15字以内）  
   - "text": チャンク本文（規定文字数内）  
3. 最後に `summary_quality` キーで "OK" もしくは "NEEDS REVIEW" を返すこと。  

### 目標
- チャンクは **音声化したとき約{target_minutes}分**で聴ける長さにする。
- 途中で話題が途切れないよう、自然な分割点を選ぶ。
- 全体を約{estimated_chunks}個のチャンクに分割することを目標とする。

### 注意事項
- 章や節の区切りを優先的に利用する
- 段落の途中では絶対に分割しない
- 文の途中では絶対に分割しない
- 各チャンクが独立して理解できるようにする

### 出力形式
{{
  "chunks": [
    {{
      "id": 1,
      "title": "はじめに",
      "text": "ここに600-1200字の本文..."
    }},
    {{
      "id": 2,
      "title": "基本概念",
      "text": "ここに600-1200字の本文..."
    }}
  ],
  "summary_quality": "OK"
}}

### テキスト全文
{text}"""
        
        try:
            response = self.model.generate_content(prompt)
            logger.debug(f"Gemini response (first 500 chars): {response.text[:500]}")
            
            result = self._parse_split_response(response.text)
            
            if not result or not result.get('chunks'):
                logger.warning("Failed to get chunks from Gemini")
                return []
            
            chunks = result.get('chunks', [])
            quality = result.get('summary_quality', 'UNKNOWN')
            
            logger.info(f"Gemini returned {len(chunks)} chunks with quality: {quality}")
            
            # 各チャンクの文字数をログ出力
            for chunk in chunks:
                logger.debug(f"Chunk {chunk.get('id')}: '{chunk.get('title')}' - {len(chunk.get('text', ''))} chars")
            
            return chunks
        
        except Exception as e:
            logger.error(f"Error in _split_content_v2: {e}")
            return []
    
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