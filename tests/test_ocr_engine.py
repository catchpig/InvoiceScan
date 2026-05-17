import os
import sys
import pytest
from unittest.mock import patch, MagicMock


def _make_engine_with_mock_ocr():
    """创建带 mock OCR 的引擎实例（绕过 paddleocr 导入）"""
    mock_ocr_instance = MagicMock()
    paddle_mock = MagicMock(return_value=mock_ocr_instance)
    with patch.dict('sys.modules', {'paddleocr': MagicMock(PaddleOCR=paddle_mock)}):
        from core.ocr_engine import OcrEngine
        engine = OcrEngine()
    engine._ocr = mock_ocr_instance
    return engine, mock_ocr_instance


def test_ocr_engine_calls_paddle_with_correct_args():
    mock_paddle = MagicMock()
    mock_paddle_module = MagicMock()
    mock_paddle_module.PaddleOCR = mock_paddle
    with patch.dict('sys.modules', {'paddleocr': mock_paddle_module}):
        # 强制重新导入
        if 'core.ocr_engine' in sys.modules:
            del sys.modules['core.ocr_engine']
        from core.ocr_engine import OcrEngine
        OcrEngine()
        mock_paddle.assert_called_once_with(use_angle_cls=True, lang='ch')


def test_parse_ocr_result_extracts_high_confidence_text():
    engine, _ = _make_engine_with_mock_ocr()
    result_data = [
        [
            [[[10, 10], [50, 10], [50, 20], [10, 20]], ("发票代码：0440000000", 0.99)],
            [[[10, 30], [50, 30], [50, 40], [10, 40]], ("发票号码：12345678", 0.98)],
        ]
    ]
    texts = engine._parse_ocr_result(result_data)
    assert isinstance(texts, list)
    assert "发票代码：0440000000" in texts
    assert "发票号码：12345678" in texts


def test_parse_ocr_result_filters_low_confidence():
    engine, _ = _make_engine_with_mock_ocr()
    result_data = [
        [
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("高置信度文本", 0.95)],
            [[[0, 0], [1, 0], [1, 1], [0, 1]], ("低置信度文本", 0.50)],
        ]
    ]
    texts = engine._parse_ocr_result(result_data)
    assert "高置信度文本" in texts
    assert "低置信度文本" not in texts


def test_parse_ocr_result_handles_empty():
    engine, _ = _make_engine_with_mock_ocr()
    assert engine._parse_ocr_result([]) == []
    assert engine._parse_ocr_result(None) == []


def test_extract_text_from_file_routes_pdf(tmp_path):
    dummy_pdf = tmp_path / "test.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 test")
    engine, _ = _make_engine_with_mock_ocr()

    with patch.object(engine, '_extract_from_pdf', return_value=["发票代码：0440000000"]) as mock_pdf:
        result = engine.extract_text_from_file(str(dummy_pdf))
        mock_pdf.assert_called_once_with(str(dummy_pdf))
    assert result == ["发票代码：0440000000"]


def test_extract_text_from_file_routes_png(tmp_path):
    dummy_png = tmp_path / "test.png"
    dummy_png.write_bytes(b"\x89PNG\r\n")
    engine, _ = _make_engine_with_mock_ocr()

    with patch.object(engine, 'extract_text_from_image', return_value=["发票号码：12345678"]) as mock_img:
        result = engine.extract_text_from_file(str(dummy_png))
        mock_img.assert_called_once_with(str(dummy_png))
        assert result == ["发票号码：12345678"]
