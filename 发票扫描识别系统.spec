# -*- mode: python ; coding: utf-8 -*-
import os
import importlib.util

# 自动定位 rapidocr_onnxruntime 包目录（兼容 venv 和系统 Python）
_rapid_spec = importlib.util.find_spec('rapidocr_onnxruntime')
_rapid_src = os.path.dirname(_rapid_spec.origin)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ui', 'ui'),
        ('core', 'core'),
        ('models', 'models'),
        ('poppler', 'poppler'),
        # RapidOCR 数据文件：ONNX 模型 + config.yaml（必须，否则识别失败）
        (_rapid_src, 'rapidocr_onnxruntime'),
    ],
    hiddenimports=[
        'rapidocr_onnxruntime',
        'rapidocr_onnxruntime.rapid_ocr_api',
        'rapidocr_onnxruntime.utils',
        'rapidocr_onnxruntime.ch_ppocr_v2_cls',
        'rapidocr_onnxruntime.ch_ppocr_v2_cls.text_cls',
        'rapidocr_onnxruntime.ch_ppocr_v3_det',
        'rapidocr_onnxruntime.ch_ppocr_v3_det.text_detect',
        'rapidocr_onnxruntime.ch_ppocr_v3_rec',
        'rapidocr_onnxruntime.ch_ppocr_v3_rec.text_recognize',
        'onnxruntime',
        'pdf2image',
        'PIL',
        'openpyxl',
        'cv2',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # easyocr 及其依赖链（项目未使用 easyocr，但 venv 中已安装）
        'easyocr',
        'torch', 'torchvision', 'torchaudio',
        'torch.distributed', 'torch.testing', 'torch.ao',
        # torch 的间接依赖
        'sympy', 'mpmath',
        'networkx',
        'ninja',
        # scikit-image 及其依赖链
        'skimage', 'scikit_image',
        'imageio', 'imageio_ffmpeg',
        'tifffile',
        'lazy_loader',
        # scipy（scikit-image 依赖，项目无需）
        'scipy',
        # easyocr 专属
        'python_bidi', 'bidi',
        # 数据分析/可视化（项目无需）
        'pandas', 'matplotlib', 'seaborn',
        # 测试框架（运行时无需）
        'pytest', 'pytest_cov', 'coverage',
        # tkinter（使用 PyQt6，无需 tk）
        'tkinter', '_tkinter',
    ],
    noarchive=False,
    optimize=0,
)
# 移除 cv2 视频 I/O 相关 DLL（发票扫描仅需图像处理，不需视频编解码）
# Windows 路径使用反斜杠，需同时兼容正斜杠
_cv2_video_prefixes = (
    'cv2\\opencv_videoio_ffmpeg',
    'cv2/opencv_videoio_ffmpeg',
    'cv2\\opencv_videoio_msmf',
    'cv2/opencv_videoio_msmf',
)
a.binaries = [
    x for x in a.binaries
    if not any(x[0].startswith(p) for p in _cv2_video_prefixes)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='发票扫描识别系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='发票扫描识别系统',
)
