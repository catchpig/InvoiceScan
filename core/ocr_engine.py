import os

_CONFIDENCE_THRESHOLD = 0.5
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
        from rapidocr_onnxruntime import RapidOCR
        self._engine = RapidOCR()

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
        import cv2
        from PIL import Image, ImageEnhance, ImageFilter
        img = img.convert('RGB')

        # Standard pass: accurate for amounts and all non-name fields
        std = img.copy()
        if std.width < _UPSCALE_THRESHOLD:
            std = std.resize((std.width * 2, std.height * 2), Image.LANCZOS)
        std = ImageEnhance.Contrast(std).enhance(1.5)
        std = std.filter(ImageFilter.SHARPEN)
        result_std, _ = self._engine(np.array(std))
        texts_std = self._parse_ocr_result(result_std)

        # CLAHE pass: better character-level accuracy for company names.
        # Only prepend CLAHE texts that look like company name lines so that
        # amount-related patterns in the main text remain from the standard pass.
        arr = cv2.resize(np.array(img), (img.width * 4, img.height * 4),
                         interpolation=cv2.INTER_LANCZOS4)
        lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        cl = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l_ch)
        arr2 = cv2.cvtColor(cv2.merge((cl, a_ch, b_ch)), cv2.COLOR_LAB2RGB)
        result_hq, _ = self._engine(arr2)
        texts_hq = self._parse_ocr_result(result_hq)

        # Keep only HQ texts that are company-name-like (contain company keywords)
        hq_company = [t for t in texts_hq
                      if '贸易' in t or '有限' in t or '公司' in t or '企业' in t]

        # Prepend HQ company names so the parser's keyword-based search sees them first
        return hq_company + texts_std

    def _parse_ocr_result(self, result) -> list[str]:
        # RapidOCR 返回格式：[[bbox, text, score], ...] 或 None；score 为字符串
        if not result:
            return []
        return [
            text
            for (_bbox, text, score) in result
            if score is not None and float(score) >= _CONFIDENCE_THRESHOLD
        ]
