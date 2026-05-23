"""Whisper 转录实现。"""

from typing import Dict, List

from .transcriber import Transcriber


class WhisperTranscriber(Transcriber):
    """使用 OpenAI Whisper 将音频转录为带时间戳的文字稿。

    首次调用会自动下载模型（tiny 约 40MB）。
    """

    def __init__(self, model_name: str = 'tiny'):
        self._model_name = model_name

    def transcribe(self, audio_path: str) -> List[Dict]:
        import whisper
        model = whisper.load_model(self._model_name)
        result = model.transcribe(audio_path, language='zh')
        return [
            {
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'].strip(),
            }
            for seg in result.get('segments', [])
        ]
