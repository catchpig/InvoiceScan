import os
import logging
import threading

_CONFIDENCE_THRESHOLD = 0.5
_PDF_DPI = 200
_UPSCALE_THRESHOLD = 1600  # 宽度低于此值时 2x 放大

_thread_local = threading.local()

# 限制同时执行 OCR 推理的线程数；3 并发文件时最多 2 个同时推理，
# 第 3 个在前序完成后立即接续，CPU 峰值从 ~100% 降到 ~70%。
_ocr_semaphore = threading.Semaphore(2)

_ort_patched = False
_ort_patch_lock = threading.Lock()


def _patch_ort_thread_limits(max_threads: int = 2) -> None:
    """给 rapidocr_onnxruntime 的 InferenceSession 创建注入线程上限。

    rapidocr_onnxruntime.utils.OrtInferSession 没有设置 intra_op_num_threads，
    默认 onnxruntime 会占满所有 CPU 核。通过替换 utils 模块中的 InferenceSession
    引用，在 sess_options 传入前注入线程限制。
    """
    global _ort_patched
    with _ort_patch_lock:
        if _ort_patched:
            return
        try:
            import rapidocr_onnxruntime.utils as _rr_utils
            _orig_IS = _rr_utils.InferenceSession

            def _limited_IS(model_path, sess_options=None, providers=None, **kw):
                if sess_options is not None:
                    try:
                        sess_options.intra_op_num_threads = max_threads
                        sess_options.inter_op_num_threads = 1
                    except Exception:
                        pass
                return _orig_IS(model_path,
                                sess_options=sess_options,
                                providers=providers, **kw)

            _rr_utils.InferenceSession = _limited_IS
            _ort_patched = True
            logging.debug("ORT thread limit patched: intra_op=%d", max_threads)
        except Exception as e:
            logging.warning("ORT thread patch failed: %s", e)

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

logging.debug("poppler path: %s", _POPPLER_PATH)


class OcrEngine:
    def __init__(self):
        logging.debug("OcrEngine.__init__: patching ORT + importing RapidOCR")
        _patch_ort_thread_limits(max_threads=2)
        from rapidocr_onnxruntime import RapidOCR
        self._engine = RapidOCR()
        logging.debug("OcrEngine.__init__: done")

    @staticmethod
    def get_thread_local() -> "OcrEngine":
        """每个工作线程只初始化一次引擎，避免重复加载 ONNX 模型。"""
        if not hasattr(_thread_local, 'engine'):
            _thread_local.engine = OcrEngine()
        return _thread_local.engine

    def extract_text_from_file(self, file_path: str,
                               progress_callback=None) -> list[str]:
        """Extract text from an image or PDF file.

        Args:
            file_path: Path to the file.
            progress_callback: Optional callable(percent: int) receiving
                progress updates from 0 to 100 for this single file.
        """
        ext = os.path.splitext(file_path)[1].lower()
        logging.info("OCR extract: %s (type=%s)", os.path.basename(file_path), ext)
        with _ocr_semaphore:
            if ext == '.pdf':
                return self._extract_from_pdf(file_path, progress_callback)
            return self.extract_text_from_image(file_path, progress_callback)

    def _extract_from_pdf(self, pdf_path: str,
                          progress_callback=None) -> list[str]:
        from pdf2image import convert_from_path
        logging.debug("PDF convert: dpi=%d, poppler=%s", _PDF_DPI, _POPPLER_PATH)
        if progress_callback:
            progress_callback(5)
        pages = convert_from_path(pdf_path, dpi=_PDF_DPI, poppler_path=_POPPLER_PATH)
        logging.info("PDF pages: %d", len(pages))
        if progress_callback:
            progress_callback(10)
        texts = []
        total_pages = len(pages)
        for idx, page in enumerate(pages):
            logging.debug("PDF page %d: size=%dx%d", idx, page.width, page.height)

            def _page_progress(pct: int):
                if progress_callback:
                    page_base = int((idx / total_pages) * 80) + 10
                    page_range = 80 // total_pages
                    progress_callback(min(page_base + int(pct / 100 * page_range), 95))

            page_texts = self._extract_from_pil_image(page, _page_progress)
            texts.extend(page_texts)
            combined = ' '.join(texts)
            if '发票代码' in combined and '发票号码' in combined:
                logging.debug("PDF: key fields found on page %d, stopping early", idx)
                break
        if progress_callback:
            progress_callback(100)
        return texts

    def extract_text_from_image(self, image_path: str,
                                progress_callback=None) -> list[str]:
        from PIL import Image
        if progress_callback:
            progress_callback(5)
        img = Image.open(image_path)
        logging.debug("Image opened: size=%dx%d, mode=%s", img.width, img.height, img.mode)
        if progress_callback:
            progress_callback(10)
        result = self._extract_from_pil_image(img, progress_callback)
        if progress_callback:
            progress_callback(100)
        return result

    def _extract_from_pil_image(self, img, progress_callback=None) -> list[str]:
        import numpy as np
        import cv2
        from PIL import Image, ImageEnhance, ImageFilter
        img = img.convert('RGB')

        # Standard pass: accurate for amounts and all non-name fields
        std = img.copy()
        if std.width < _UPSCALE_THRESHOLD:
            std = std.resize((std.width * 2, std.height * 2), Image.LANCZOS)
            logging.debug("Standard pass: upscaled to %dx%d", std.width, std.height)
        std = ImageEnhance.Contrast(std).enhance(1.5)
        std = std.filter(ImageFilter.SHARPEN)
        if progress_callback:
            progress_callback(20)
        result_std, _ = self._engine(np.array(std))
        texts_std = self._parse_ocr_result(result_std, "standard")
        logging.debug("Standard pass: %d texts extracted", len(texts_std))
        if progress_callback:
            progress_callback(55)

        # CLAHE pass: better character-level accuracy for company names.
        # Only prepend CLAHE texts that look like company name lines so that
        # amount-related patterns in the main text remain from the standard pass.
        # 使用 2x 放大（而非 4x），在识别质量和 CPU 占用之间取得平衡。
        arr = cv2.resize(np.array(img), (img.width * 2, img.height * 2),
                         interpolation=cv2.INTER_LANCZOS4)
        lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        cl = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l_ch)
        arr2 = cv2.cvtColor(cv2.merge((cl, a_ch, b_ch)), cv2.COLOR_LAB2RGB)
        if progress_callback:
            progress_callback(70)
        result_hq, _ = self._engine(arr2)
        texts_hq = self._parse_ocr_result(result_hq, "CLAHE")
        logging.debug("CLAHE pass: %d texts extracted", len(texts_hq))
        if progress_callback:
            progress_callback(90)

        # Keep only HQ texts that are company-name-like (contain company keywords)
        hq_company = [t for t in texts_hq
                      if '贸易' in t or '有限' in t or '公司' in t or '企业' in t]
        logging.debug("CLAHE company texts (%d): %s", len(hq_company), hq_company)

        combined = hq_company + texts_std
        logging.debug("Final text list (%d items): %s", len(combined), combined)
        return combined

    def _parse_ocr_result(self, result, pass_name: str = "") -> list[str]:
        # RapidOCR 返回格式：[[bbox, text, score], ...] 或 None；score 为字符串
        if not result:
            logging.debug("OCR %s pass: no result", pass_name)
            return []
        kept = []
        dropped = []
        for (_bbox, text, score) in result:
            if score is not None and float(score) >= _CONFIDENCE_THRESHOLD:
                kept.append(text)
            else:
                dropped.append((text, score))
        if dropped:
            logging.debug("OCR %s pass: dropped %d low-confidence items: %s",
                          pass_name, len(dropped), dropped)
        return kept
