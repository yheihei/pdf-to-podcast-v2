# Gemini API音声生成機能実装計画

作成日: 2025年6月25日 14:10

## 目的
PDF to Podcast v2の音声合成フェーズ（SynthesizePhase）を、Gemini APIの音声生成機能を使用して実装する。

## 実装内容

### 1. 必要なインポートと設定の追加
- google.genai.typesの追加インポート
- GenerateContentConfigとSpeechConfigの設定

### 2. _synthesize_audio メソッドの更新
現在のプレースホルダー実装を以下の機能で置き換える：
- Gemini TTS APIの呼び出し
- 音声データの取得と保存
- WAVからMP3への変換

### 3. 音声設定パラメータ
- モデル: `gemini-2.5-pro-preview-tts`（既に.envで設定済み）
- 音声名: .envのVOICE_NAMEパラメータを使用（デフォルト: Kore）
- 音声スタイル: .envのVOICE_STYLEパラメータを使用

### 4. エラーハンドリング
- API呼び出しのリトライ機能（最大3回）
- 失敗時のフォールバック処理

### 5. 音声ファイル処理
- 24kHz 16-bit PCM モノラルWAV形式で受信
- pydubを使用してMP3に変換
- メタデータの追加

## 実装手順

1. **synthesize_phase.py の更新**
   - 必要なインポートの追加
   - _synthesize_audioメソッドの書き換え
   - WAV保存とMP3変換の実装

2. **設定の確認**
   - .envファイルの設定値確認
   - デフォルト値の設定

3. **テスト**
   - 短いテキストでの動作確認
   - 長文テキストでの処理確認
   - エラーケースのテスト

## 技術的な考慮事項

- APIレスポンスのデータ構造: `response.candidates[0].content.parts[0].inline_data.data`
- 音声フォーマット: 24kHz, 16-bit PCM, モノラル
- トークン制限: 32,000トークン以内
- 再試行間隔: 1秒

## 期待される成果

- 実際の音声ファイル（MP3）の生成
- 自然な日本語の読み上げ
- 設定可能な音声スタイル