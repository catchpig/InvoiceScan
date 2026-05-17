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
