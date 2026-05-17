import os

_CONFIDENCE_THRESHOLD = 0.002
_PDF_DPI = 200
_UPSCALE_THRESHOLD = 1600  # 宽度低于此值时 2x 放大

# 自动发现项目本地的 poppler bin 目录（Windows 免安装）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_POPPLER_PATH: str | None = None
for _candidate in [
    os.path.join(_PROJECT_ROOT, 'poppler', 'poppler-24.08.0', 'Library', 'bin'),
    os.path.join(_PROJECT_ROOT, 'poppler', 'bin'),
]:
    if os.path.isfile(os.path.join(_candidate, 'pdftoppm.exe')):
        _POPPLER_PATH = _candidate
        break


class OcrEngine:
    def __init__(self):
        import easyocr
        self._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

    def extract_text_from_file(self, file_path: str) -> list[str]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self._extract_from_pdf(file_path)
        return self.extract_text_from_image(file_path)

    def _extract_from_pdf(self, pdf_path: str) -> list[str]:
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=_PDF_DPI, poppler_path=_POPPLER_PATH)
        texts = []
        for page in pages:
            page_texts = self._extract_from_pil_image(page)
            texts.extend(page_texts)
            combined = ' '.join(texts)
            if '发票代码' in combined and '发票号码' in combined:
                break
        return texts

    def extract_text_from_image(self, image_path: str) -> list[str]:
        from PIL import Image
        img = Image.open(image_path)
        return self._extract_from_pil_image(img)

    def _extract_from_pil_image(self, img) -> list[str]:
        import numpy as np
        from PIL import Image, ImageEnhance, ImageFilter
        img = img.convert('RGB')
        if img.width < _UPSCALE_THRESHOLD:
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)
        img_array = np.array(img)
        result = self._reader.readtext(img_array)
        return self._parse_ocr_result(result)

    def _parse_ocr_result(self, result) -> list[str]:
        # EasyOCR 返回格式：[(bbox, text, confidence), ...]
        if not result:
            return []
        return [
            text
            for (_bbox, text, confidence) in result
            if confidence >= _CONFIDENCE_THRESHOLD
        ]
