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
    excludes=[],
    noarchive=False,
    optimize=0,
)
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
