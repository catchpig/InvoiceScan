from decimal import Decimal
from core.invoice_parser import InvoiceParser
from models.invoice import InvoiceStatus

# 模拟真实增值税专用发票 OCR 输出
SAMPLE_TEXTS = [
    "增值税专用发票",
    "发票代码：044001900111",
    "发票号码：12345678",
    "开票日期：2024年03月15日",
    "购买方名称：深圳XX科技有限公司",
    "纳税人识别号：914403001234567890",
    "地址、电话：广东省深圳市南山区XX路100号",
    "销售方名称：广州YY贸易有限公司",
    "纳税人识别号：914401011234567891",
    "*信息技术服务*软件开发服务",
    "1",
    "次",
    "¥1000.00",
    "合计",
    "¥1000.00",
    "税率",
    "13%",
    "税额",
    "¥130.00",
    "价税合计（大写）壹仟壹佰叁拾元整",
    "（小写）¥1130.00",
    "开票人：张三",
]


def test_parse_invoice_code():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").invoice_code == "044001900111"


def test_parse_invoice_number():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").invoice_number == "12345678"


def test_parse_invoice_date():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").invoice_date == "2024-03-15"


def test_parse_buyer_name():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").buyer_name == "深圳XX科技有限公司"


def test_parse_buyer_tax_id():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").buyer_tax_id == "914403001234567890"


def test_parse_seller_name():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").seller_name == "广州YY贸易有限公司"


def test_parse_seller_tax_id():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").seller_tax_id == "914401011234567891"


def test_parse_total_amount():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").total_amount == Decimal("1130.00")


def test_parse_tax_rate():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").tax_rate == "13%"


def test_parse_tax_amount():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").tax_amount == Decimal("130.00")


def test_parse_invoice_type():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").invoice_type == "增值税专用发票"


def test_parse_issuer():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").issuer == "张三"


def test_parse_source_file():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "invoice_001.pdf").source_file == "invoice_001.pdf"


def test_parse_status_success():
    assert InvoiceParser().parse(SAMPLE_TEXTS, "test.pdf").status == InvoiceStatus.SUCCESS


def test_parse_status_review_on_amount_mismatch():
    texts = [t.replace("（小写）¥1130.00", "（小写）¥1200.00") for t in SAMPLE_TEXTS]
    assert InvoiceParser().parse(texts, "test.pdf").status == InvoiceStatus.REVIEW


def test_parse_empty_texts_returns_failed():
    inv = InvoiceParser().parse([], "empty.pdf")
    assert inv.status == InvoiceStatus.FAILED
    assert inv.error_message != ""


def test_parse_missing_number_returns_review():
    texts = [t for t in SAMPLE_TEXTS if "发票号码" not in t]
    assert InvoiceParser().parse(texts, "test.pdf").status == InvoiceStatus.REVIEW


# OCR 将"电子发票（普通发票）"截断为"电子发"时，仍能识别出正确类型
ETICKET_TEXTS = [
    '名称：成都天投中油能源有限公司',
    '成都天投中油能源有限公司海昌加油站028-68224969;',
    '电子发',                                    # OCR 截断，缺少"票（普通发票）"
    '发票号码：26512000000859495336',
    '成品油',
    '国家税务总局',
    '开票日期：2026年03月05日',
    '四川省税务局',
    '购买方信息',
    '名称：李涛',
    '销售方信息',
    '名称：成都天投中油能源有限公司',
    '统一社会信用代码/纳税人识别号：9151010033204312X9',
    '*汽油*92号车用汽油',
    '13%',
    '¥176.99',
    '¥23.01',
    '（小写）¥200.00',
    '开票人：方利香',
]


def test_parse_invoice_type_ocr_truncated_to_电子发():
    # OCR 将发票类型截断为"电子发"时，解析器仍应返回正确类型
    inv = InvoiceParser().parse(ETICKET_TEXTS, "发票pdf.pdf")
    assert inv.invoice_type == "电子发票（普通发票）"


def test_parse_seller_tax_id_with_letter_x():
    # 税号末位含字母 X（如 9151010033204312X9）不应被 normalize 误替换为 ¥
    inv = InvoiceParser().parse(ETICKET_TEXTS, "发票pdf.pdf")
    assert inv.seller_tax_id == "9151010033204312X9"


# ── 全电普通发票 OCR 常见误读修复测试 ────────────────────────────────────────

def test_parse_date_piao_dropped():
    """OCR 丢失"票"字，将"开票日期"读为"开日期"时仍能解析出日期"""
    texts = [
        "电子发票(普通发票)",
        "发票号码：26517000000159325620",
        "开日期：2026年02月13日",
        "名称：个人",
        "名称：测试科技有限公司",
    ]
    inv = InvoiceParser().parse(texts, "t.jpg")
    assert inv.invoice_date == "2026-02-13"


def test_parse_date_ri_misread_as_yue():
    """OCR 将日期末尾的"日"误读为"月"，如"2026年02月13月"，仍能解析出日期"""
    texts = [
        "发票号码：26517000000159325620",
        "开票日期：2026年02月13月",
        "名称：个人",
        "名称：测试科技有限公司",
    ]
    inv = InvoiceParser().parse(texts, "t.jpg")
    assert inv.invoice_date == "2026-02-13"


def test_parse_colon_as_decimal_in_amounts():
    """OCR 将小数点误读为冒号，如"X327: 44"应解析为 ¥327.44，并使发票状态为 SUCCESS"""
    texts = [
        "电子发票(普通发票)",
        "发票号码：26517000000159325620",
        "开票日期：2026年02月13日",
        "名称：个人",
        "名称：测试科技有限公司",
        "X327: 44",
        "Y42: 56",
        "(小写) ¥370.00",
    ]
    inv = InvoiceParser().parse(texts, "t.jpg")
    assert inv.total_amount == Decimal("370.00")
    assert inv.subtotal == Decimal("327.44")
    assert inv.tax_amount == Decimal("42.56")
    assert inv.status == InvoiceStatus.SUCCESS


def test_parse_smart_amount_pairing_with_corrupted_row():
    """
    当第二行合计因 OCR 噪点出现错误金额（如"Y12: 56"混入），
    应通过最优配对找到正确的小计与税额，使发票状态为 SUCCESS。
    """
    texts = [
        "电子发票(普通发票)",
        "发票号码：26517000000159325620",
        "开票日期：2026年02月13日",
        "名称：个人",
        "名称：测试科技有限公司",
        "X327: 44",   # 正确小计（冒号为小数点误读）
        "Y42: 56",    # 正确税额
        "7327 4",     # 合计行重复，无 ¥ 前缀，不影响提取
        "Y12: 56",    # 噪点："Y42.56" 被错读为 "Y12.56"
        "(小写) ¥370.00",
    ]
    inv = InvoiceParser().parse(texts, "t.jpg")
    assert inv.total_amount == Decimal("370.00")
    assert inv.status == InvoiceStatus.SUCCESS


# ── 全电普通发票方信息标题误读 + 税号含空格 ─────────────────────────────────

_SECTION_MISREAD_TEXTS = [
    '购方信息',                                                    # "购买方信息"被OCR截断
    '销货方信息',                                                   # "售"被OCR误读为"货"
    '名称：个人',
    '名称：成都某贸易有限公司',
    '优一社全信用代码/纳税人识别号',                                  # 无税号的买方行
    '统一社会估用代码/纳税人识别号： 91510681MA6 6M6MO21',            # 税号含空格
    '发票号码：26517000000159325620',
    '开票日期：2026年02月13日',
    '13%',
    '(小写) ¥370.00',
]


def test_parse_seller_tax_id_section_misread_and_space():
    """购买/销售方 section 标题被 OCR 误读，且税号含 OCR 插入空格，仍能正确提取销售方税号"""
    inv = InvoiceParser().parse(_SECTION_MISREAD_TEXTS, 't.pdf')
    assert inv.seller_tax_id == '91510681MA66M6MO21'


def test_parse_date_kaimi_riqi():
    """OCR 将"开票日期"误读为"开米日期"且无冒号和年份分隔符时，仍能解析出日期"""
    texts = [
        '发票号码：26517000000159325620',
        '开米日期202602月13日',
        '名称：个人',
        '名称：成都某贸易有限公司',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.invoice_date == '2026-02-13'


def test_parse_total_amount_xiao_gong():
    """OCR 将"（小写）"读为"(小弓)"时，仍能提取到价税合计并达到 SUCCESS 状态"""
    texts = [
        '发票号码：26517000000159325620',
        '开票日期：2026年02月13日',
        '名称：个人',
        '名称：成都某贸易有限公司',
        '¥327.44',
        '¥42.56',
        '(小弓)370.00',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.total_amount == Decimal('370.00')
    assert inv.status == InvoiceStatus.SUCCESS


# ── ¥ 金额中小数点被误读为空格，首位小数被误读为 M ───────────────────────────

def test_parse_subtotal_m_as_decimal():
    """OCR 将 '¥327.44' 误读为 '¥327 M4'（小数点→空格，数字4→M），仍能正确解析"""
    texts = [
        '电子发票(普通发票)',
        '发票号码：26517000000159325620',
        '开票日期：2026年02月13日',
        '名称：个人',
        '名称：成都某贸易有限公司',
        '¥327 M4',
        '¥42.56',
        '(小写) ¥370.00',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.subtotal == Decimal('327.44')
    assert inv.tax_amount == Decimal('42.56')
    assert inv.status == InvoiceStatus.SUCCESS


# ── 公司名称中常见 OCR 误读修复 ───────────────────────────────────────────────

def test_parse_company_you_xian_misread():
    """OCR 将'有限公司'前的'有'字误读为'在'（'在限公司'），仍能正确提取公司名称"""
    texts = [
        '发票号码：26517000000159325620',
        '开票日期：2026年02月13日',
        '名称：个人',
        '名称：京东广汉信成贸易在限公司',
        '(小写) ¥370.00',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.seller_name == '京东广汉信成贸易有限公司'


def test_parse_company_guang_misread_as_chang():
    """OCR 将公司名称中'广'字误读为'厂'（广汉→厂汉），仍能正确提取公司名称"""
    texts = [
        '发票号码：26517000000159325620',
        '开票日期：2026年02月13日',
        '名称：个人',
        '名称：京东厂汉信成贸易有限公司',
        '(小写) ¥370.00',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.seller_name == '京东广汉信成贸易有限公司'


def test_parse_tax_amount_reconciled_from_total():
    """税额 OCR 读数与 total-subtotal 相差 ≤2% 时，应修正为精确值并达到 SUCCESS 状态"""
    texts = [
        '电子发票(普通发票)',
        '发票号码：26517000000159325620',
        '开票日期：2026年02月13日',
        '名称：个人',
        '名称：成都某贸易有限公司',
        '¥327.44',
        '¥42.86',       # 应为 42.56，OCR 将 '5' 误读为 '8'
        '(小写) ¥370.00',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.subtotal == Decimal('327.44')
    assert inv.tax_amount == Decimal('42.56')   # 370.00 - 327.44 = 42.56
    assert inv.status == InvoiceStatus.SUCCESS


def test_parse_company_combined_ocr_errors():
    """模拟发票.jpg 实际 OCR 输出：CLAHE 前置行 + 标准行同时含多个误读"""
    texts = [
        '林家家广汉信成政易有限公司',            # CLAHE pass 前置行（'广'正确但有噪点）
        '名称：个人',
        '名称：京东厂汉信成贸易在限公司',         # standard pass：'广'→'厂', '有'→'在'
        '发票号码：26517000000159325620',
        '开票日期：2026年02月13日',
        '¥327 M4',                              # ¥327.44 误读
        '¥42.56',
        '(小写) ¥370.00',
    ]
    inv = InvoiceParser().parse(texts, 't.jpg')
    assert inv.seller_name == '京东广汉信成贸易有限公司'
    assert inv.subtotal == Decimal('327.44')
    assert inv.tax_amount == Decimal('42.56')
    assert inv.status == InvoiceStatus.SUCCESS
