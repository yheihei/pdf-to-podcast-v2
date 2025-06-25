# PDF to Podcast Audio Generator

PDF/テキストファイルからポッドキャスト風の音声ファイルを生成するツール

## セットアップ

1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

2. 環境設定
```bash
cp .env.template .env
# .envファイルを編集してGENAI_API_KEYを設定
```

3. FFmpegのインストール（音声変換用）
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

## 使い方

本ツールは4つのフェーズ（入力→分割→脚本生成→音声合成）で構成されており、各フェーズは独立して実行可能です。途中から再開したり、特定のフェーズのみ実行することができます。

各コマンドの詳細なオプションは `--help` で確認できます：
```bash
python main.py --help
python main.py all --help
python main.py input --help
python main.py split --help
python main.py script --help
python main.py synthesize --help
```

### 全フェーズを一度に実行
```bash
# PDFファイル全体を処理
python main.py all --pdf document.pdf

# PDFの特定ページ範囲を指定
python main.py all --pdf document.pdf --start 10 --end 20

# テキストファイルから処理
python main.py all --text input.txt
```

### 各フェーズを個別に実行

1. 入力処理
```bash
python main.py input --pdf document.pdf
```

2. コンテンツ分割
```bash
python main.py split --infile output/input_text.txt
```

3. 脚本生成
```bash
python main.py script --indir output/chunks
```

4. 音声合成
```bash
python main.py synthesize --indir output/scripts
```

## 出力ファイル

- `output/input_text.txt` - 抽出されたテキスト
- `output/chunks/chunk_*.txt` - 分割されたテキスト
- `output/scripts/script_*.txt` - 生成された脚本
- `output/audio/{番号}_{タイトル}.mp3` - 生成された音声ファイル（タイトルは脚本内容から自動生成）
