# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
PDF to Podcast Audio Generator - A Python CLI tool that converts PDF documents or text files into podcast-style audio narrations using Google's Generative AI (Gemini) API.

## Common Commands

### Setup & Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.template .env
# Edit .env to add GENAI_API_KEY

# Install FFmpeg (required for audio processing)
# macOS: brew install ffmpeg
# Ubuntu/Debian: sudo apt-get install ffmpeg
```

### Running the Application
```bash
# Run all phases at once
python main.py all --pdf document.pdf

# Run individual phases
python main.py input --pdf document.pdf --start 10 --end 20
python main.py split --infile output/input_text.txt
python main.py script --indir output/chunks
python main.py synthesize --indir output/scripts

# With custom options
python main.py all --pdf document.pdf --voice "Aoede" --voice-style "calm" --chunk-size 2000
```

### Testing

Since there are no formal test files yet, testing should be done manually with short texts to minimize API costs.

#### Phase 1: Input Phase Testing
```bash
# Test with text file
python main.py input --text test/input/test_short.txt --output-dir test/output
# Check output: cat test/output/input_text.txt

# Test with PDF (if available)
python main.py input --pdf sample.pdf --start 1 --end 2 --output-dir test/output
```

#### Phase 2: Split Phase Testing
```bash
# Use pre-created test_long.txt (contains ~1000 characters with 4 chapters)
python main.py input --text test/input/test_long.txt --output-dir test/output
python main.py split --infile test/output/input_text.txt --chunk-size 250 --output-dir test/output/chunks
# Check outputs: ls -la test/output/chunks/
```

#### Phase 3: Script Phase Testing
```bash
# Test script generation from chunks
python main.py script --indir test/output/chunks --output-dir test/output/scripts --style "親しみやすく"
# Review generated scripts: cat test/output/scripts/script_*.txt
```

#### Phase 4: Synthesize Phase Testing
```bash
# Test audio synthesis with pre-created short scripts (uses API credits but faster)
python main.py synthesize --indir test/input/scripts --output-dir test/output/audio --voice "Aoede" --voice-style "calm"
# Check audio files: ls -la test/output/audio/
# Play audio: afplay test/output/audio/output_1.mp3  # macOS
```

#### Full Pipeline Test
```bash
# Complete test with minimal content
python main.py all --text test/input/test_minimal.txt
# Note: This will use default output directory
```

## Architecture

### Phase-Based Processing Pipeline
The application follows a 4-phase pipeline, each phase can be run independently:

1. **InputPhase** (`src/phases/input_phase.py`)
   - Extracts text from PDF or reads text files
   - Handles page range selection for PDFs
   - Output: `output/input_text.txt`

2. **SplitPhase** (`src/phases/split_phase.py`)
   - Splits long content into manageable chunks using Gemini API
   - Uses LLM to find natural breaking points (chapters, sections)
   - Target: ~4 minutes of audio per chunk
   - Output: `output/chunks/chunk_*.txt`

3. **ScriptPhase** (`src/phases/script_phase.py`)
   - Converts each text chunk into conversational podcast script
   - Uses Gemini API to rewrite in spoken Japanese style
   - Maintains content fidelity while making it natural for speech
   - Output: `output/scripts/script_*.txt`

4. **SynthesizePhase** (`src/phases/synthesize_phase.py`)
   - Generates audio from scripts using Gemini TTS API
   - Handles voice selection and style customization
   - Converts to MP3 format using FFmpeg
   - Output: `output/audio/output_*.mp3`

### Key Components

- **CLI Framework**: Click-based CLI in `src/cli.py`
- **Configuration**: Environment-based config in `src/utils/config.py`
- **Logging**: Centralized logging setup in `src/utils/logger.py`
- **API Integration**: Google Generative AI (Gemini) for LLM and TTS

### Directory Structure
```
output/
├── input_text.txt       # Extracted text
├── chunks/              # Split text chunks
│   └── chunk_*.txt
├── scripts/             # Generated scripts
│   └── script_*.txt
└── audio/               # Final audio files
    └── output_*.mp3
```

## Environment Variables
Required in `.env`:
- `GENAI_API_KEY`: Google Generative AI API key (required)
- `MODEL_SPLIT`: Gemini model for text splitting
- `MODEL_SCRIPT`: Gemini model for script generation
- `MODEL_TTS`: Gemini model for text-to-speech
- `VOICE_NAME`: Default TTS voice
- `VOICE_STYLE`: Default voice style/characteristics

## Development Notes

- All phases are designed to be idempotent and resumable
- Intermediate outputs are saved to allow debugging and manual intervention
- API usage should be tested with short texts to minimize costs
- The application supports Japanese text natively
- Error handling includes detailed logging for troubleshooting

## 応答のルール
- 常に日本語で応答してください。コード部分はそのままにしてください。

## **MUST** 思考のルール
- 思考する際は英語で考えてください

## ユーザーへの確認をお願いする時
MANDATORY: ALWAYS ALERT ON ASKING USER FOR CONFIRMATION
Use `afplay /System/Library/Sounds/Hero.aiff` to ring a bell.

## テスト方法

- API Keyを設定してあるので、各フェーズのテストは実コマンドを用いて行える
- 料金がかかるので短めのテキストで行うこと。タイム・アウトしたらユーザーにテストを依頼すること

## タスクの遂行方法

適用条件: 実装を依頼された時。単なる質問事項の場合適用されない。

### 基本フロー

- PRD の各項目を「Plan → Imp → Debug → Review → Doc」サイクルで処理する  
- irreversible / high-risk 操作（削除・本番 DB 変更・外部 API 決定）は必ず停止する

#### Phase1 Plan

- PRDを受け取ったら、PRDを確認し、不明点がないか確認する
- その後、PRD の各項目を Planに落とし込む
  - Planは `.docs/todo/YYYYMMDDhhmm_${タスクの概要}.md` に保存
- ユーザーにPlanの確認を行い、承認されるまで次のフェーズには移行しない

#### Phase2 Imp

- Planをもとに実装する

#### Phase3 Debug

- 指定のテストがあればテストを行う
- 指定がなければ関連のテストを探してテストを行う
- 関連のテストがなければ停止して、なんのテストを行うべきかユーザーに確認する
- テストが通ったらフォーマッタをかける
- lintチェックを行い、エラーがあればImpに戻り、修正する

#### Phase4 Review

- これまでのやり取りの中でPRDの変更があったら。最新のPRDに更新する
- subagentを起動し、PRDを伝え、レビューしてもらう
- レビュー指摘があればImpに戻る

#### Phase5 Doc

- 基本設計書を`.docs/design/YYYYMMDD_${タスクの概要}.md` に保存
- ユーザーからのフィードバックを待つ。フィードバックがあれば適宜前のフェーズに戻ること
