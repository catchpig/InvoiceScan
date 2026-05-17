import os
import tempfile

_CONFIDENCE_THRESHOLD = 0.80
_PDF_DPI = 200


class OcrEngine:
    def __init__(self):
        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(use_angle_cls=True, lang='ch')

    def extract_text_from_file(self, file_path: str) -> list[str]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self._extract_from_pdf(file_path)
        return self.extract_text_from_image(file_path)

    def _extract_from_pdf(self, pdf_path: str) -> list[str]:
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=_PDF_DPI)
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
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
            img.save(tmp_path)
        try:
            result = self._ocr.ocr(tmp_path, cls=True)
            return self._parse_ocr_result(result)
        finally:
            os.unlink(tmp_path)

    def _parse_ocr_result(self, result) -> list[str]:
        if not result:
            return []
        texts = []
        for page in result:
            if not page:
                continue
            for line in page:
                text_info = line[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) == 2:
                    text, confidence = text_info
                else:
                    text = str(text_info)
                    confidence = 1.0
                if confidence >= _CONFIDENCE_THRESHOLD:
                    texts.append(text)
        return texts
