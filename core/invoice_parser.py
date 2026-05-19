import re
import logging
from decimal import Decimal, InvalidOperation
from models.invoice import Invoice, InvoiceStatus

_INVOICE_TYPES = [
    "增值税专用发票", "增值税普通发票",
    "增值税电子专用发票", "增值税电子普通发票",
    "电子发票（增值税专用发票）", "电子发票（普通发票）",
    "电子发票", "普通发票",
]

_RE_CODE        = re.compile(r'发票代码[：:]\s*(\d{10,12})')
_RE_NUMBER      = re.compile(r'(?:发票号码|岌采号[玛码罚])[：:]\s*[_]?\s*(\d{7,20})')
_RE_NUMBER_LONG = re.compile(r'(?<!\d)(\d{20})(?!\d)')
_RE_DATE        = re.compile(r'开.{0,2}日期[：:]?\s*(\d{4})年?(\d{1,2})[月](\d{1,2})[日月0]?')
_RE_TAX_ID      = re.compile(r'(?:纳税人识别号|统一社会信用代码)[：:]\s*([A-Za-z0-9]{15,20})')
_RE_TAX_RATE         = re.compile(r'税率\s*[：:]?\s*(\d+%|免税|零税率)')
_RE_TAX_RATE_LINE    = re.compile(r'(?:^|\n)(\d{1,2}%)(?:\n|$)', re.MULTILINE)
_RE_TOTAL_LOWER = re.compile(r'[（(](?:小写|小召|小弓)[）)]\s*[¥￥4]?\s*([\d,]+\.?\d*)')
_RE_AMOUNT      = re.compile(r'[¥￥]\s*([\d,]+\.?\d*)')
_RE_TAX_AMOUNT  = re.compile(r'税额\s*\n\s*[¥￥]\s*([\d,]+\.?\d*)')
_RE_SUBTOTAL    = re.compile(r'合计\s*\n\s*[¥￥]\s*([\d,]+\.?\d*)')
# 从 OCR 输出的 "合\n计\n{金额}\n{税额}" 行结构中提取税额
_RE_TAX_IN_TOTAL_ROW = re.compile(r'合\n计\n[\d,.]+\n([\d,.]+)')
_RE_ISSUER      = re.compile(r'(?:开票|开采)[柔]?人[：:]\s*(.+)')

_REQUIRED_FIELDS = ['invoice_number', 'invoice_date', 'buyer_name', 'seller_name']


class InvoiceParser:
    def parse(self, texts: list[str], source_file: str) -> Invoice:
        logging.debug("Parser.parse: %d OCR texts for %s", len(texts), source_file)
        if not texts:
            logging.warning("Parser.parse: no OCR texts for %s", source_file)
            return Invoice(
                source_file=source_file,
                status=InvoiceStatus.FAILED,
                error_message="OCR 未返回任何文本",
            )

        full_text = '\n'.join(texts)
        full_text = self._normalize_text(full_text)
        invoice = Invoice(source_file=source_file)

        invoice.invoice_type   = self._find_invoice_type(texts)
        invoice.invoice_code   = self._search(full_text, _RE_CODE, 1)
        invoice.invoice_number = self._extract_invoice_number(full_text)
        invoice.invoice_date   = self._extract_date(full_text)
        invoice.buyer_name, invoice.buyer_tax_id   = self._extract_party(full_text, "购买方", 0)
        invoice.seller_name, invoice.seller_tax_id = self._extract_party(full_text, "销售方", 1)
        invoice.tax_rate = self._search(full_text, _RE_TAX_RATE, 1)
        if not invoice.tax_rate:
            invoice.tax_rate = self._search(full_text, _RE_TAX_RATE_LINE, 1)
        invoice.total_amount   = self._extract_total(full_text)
        invoice.tax_amount, invoice.subtotal = self._extract_sub_amounts(full_text)
        if invoice.total_amount and invoice.tax_amount and not invoice.subtotal:
            invoice.subtotal = invoice.total_amount - invoice.tax_amount
        # 税额 OCR 轻微误读时（与 total−subtotal 相差 ≤2%），以精确计算值修正
        if invoice.total_amount and invoice.subtotal and invoice.tax_amount:
            expected_tax = invoice.total_amount - invoice.subtotal
            if abs(invoice.tax_amount - expected_tax) <= invoice.total_amount * Decimal("0.02"):
                invoice.tax_amount = expected_tax
        issuer_raw             = self._search(full_text, _RE_ISSUER, 1)
        invoice.issuer         = issuer_raw.strip()

        invoice.status = self._determine_status(invoice)

        logging.info(
            "Parsed %s: status=%s type=%s code=%s number=%s date=%s",
            source_file, invoice.status, invoice.invoice_type,
            invoice.invoice_code, invoice.invoice_number, invoice.invoice_date,
        )
        logging.debug(
            "  buyer=%r tax_id=%r | seller=%r tax_id=%r",
            invoice.buyer_name, invoice.buyer_tax_id,
            invoice.seller_name, invoice.seller_tax_id,
        )
        logging.debug(
            "  tax_rate=%s total=%s tax=%s subtotal=%s issuer=%r",
            invoice.tax_rate, invoice.total_amount,
            invoice.tax_amount, invoice.subtotal, invoice.issuer,
        )
        return invoice

    def _normalize_text(self, text: str) -> str:
        # 修正年份：?026年 → 2026年（OCR 将 '2' 误读为 '?'）
        text = re.sub(r'[？?]0(\d{2})年', r'20\1年', text)
        # 修正日期中被丢失的十位数字：月.3日 → 月13日（'1' 被误读为 '.'）
        text = re.sub(r'(\d{1,2}月)\.(\d)日', r'\g<1>1\2日', text)
        # 修正 ¥ 被 RapidOCR 误读为 Y、X 或 ?（非字母/数字前缀，避免误替换税号末位字母）
        text = re.sub(r'(?<![A-Za-z0-9])Y(\d)', r'¥\1', text)
        text = re.sub(r'(?<![A-Za-z0-9])X(\d)', r'¥\1', text)
        text = re.sub(r'(?<![A-Za-z0-9])[?？](\d)', r'¥\1', text)
        # 修正小数点后的空格："327. 44" → "327.44"
        text = re.sub(r'(\d)\. (\d)', r'\1.\2', text)
        # 修正 OCR 将小数点误读为冒号：如"327: 44" → "327.44"（仅数字间的 ASCII 冒号）
        text = re.sub(r'(\d+)\s*:\s*(\d+)', r'\1.\2', text)
        # 修正 ¥ 金额中小数点被误读为空格、数字 4 被误读为 M：如"¥327 M4" → "¥327.44"
        text = re.sub(r'([¥￥]\d+)\s+[Mm](\d)', r'\1.4\2', text)
        # 修正"有限公司"中"有"字被误读为"在"：在限公司 → 有限公司
        text = re.sub(r'在限公司', '有限公司', text)
        # 修正"广"字被误读为"厂"（常见于地名：广汉、广州、广东等）
        text = re.sub(r'厂([汉州东南])', r'广\1', text)
        # 修正 OCR 在税号/编号内插入的空格：如"MA6 6M6" → "MA66M6"
        text = re.sub(r'(?<=[A-Za-z0-9]) +(?=[A-Za-z0-9])', '', text)
        # 修正 Unicode 乘号 × 被误识别为 ASCII X（常见于税号末位）
        text = re.sub(r'(?<=[A-Za-z0-9])×(?=[A-Za-z0-9])', 'X', text)
        return text

    def _find_invoice_type(self, texts: list[str]) -> str:
        matched = ""
        for text in texts:
            for t in _INVOICE_TYPES:
                if t in text:
                    matched = t
                    break
            if matched:
                break

        # 全电发票补全：匹配到通用"电子发票"时根据上下文精化为子类型
        # OCR 常将"电子发票（普通发票）"丢失"普通"两字，或截断为"电子发"
        if matched in ("电子发票", ""):
            combined = '\n'.join(texts)
            if '电子发' in combined:   # 涵盖完整"电子发票"和截断"电子发"两种情况
                if '专用' in combined:
                    return '电子发票（增值税专用发票）'
                return '电子发票（普通发票）'

        return matched

    def _search(self, text: str, pattern: re.Pattern, group: int) -> str:
        m = pattern.search(text)
        return m.group(group) if m else ""

    def _extract_invoice_number(self, text: str) -> str:
        m = _RE_NUMBER.search(text)
        if m:
            return m.group(1)
        # 回退：查找 20 位连续数字（新版全电发票号码格式）
        m = _RE_NUMBER_LONG.search(text)
        return m.group(1) if m else ""

    def _extract_date(self, text: str) -> str:
        m = _RE_DATE.search(text)
        if not m:
            return ""
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    def _extract_party(self, text: str, party: str, tax_index: int) -> tuple[str, str]:
        name_pat = re.compile(rf'{party}名称[：:]\s*([^\n]+)')
        m = name_pat.search(text)
        if m:
            name = m.group(1).strip()
            logging.debug("  %s name (direct): %r", party, name)
        else:
            # 次选：在"购买方信息"或"销售方信息" section 内查找紧随的名称行
            # re.DOTALL 让 .{0,200}? 能跨行匹配，[^\n]+ 限制捕获到行尾
            section_pat = re.compile(rf'{party}信息.{{0,200}}?名.{{0,3}}?[：:]\s*([^\n]+)', re.DOTALL)
            m = section_pat.search(text)
            if m:
                name = re.sub(r'[：:]', '', m.group(1)).strip()
                logging.debug("  %s name (section): %r", party, name)
            else:
                # 第三回退：按出现顺序使用 "名称：" 匹配（购买方=第0个，销售方=第1个）
                all_names = re.findall(r'名.{0,3}?[：:]\s*([^\n]+)', text)
                party_idx = 0 if '购买' in party else 1
                raw = all_names[party_idx].strip() if len(all_names) > party_idx else ""
                name = re.sub(r'[：:]', '', raw).strip()
                logging.debug("  %s name (fallback idx=%d, all=%s): %r",
                              party, party_idx, all_names, name)

                # 第四回退：旧版纸质发票 OCR 将"名称："识别为"称："（丢失"名"字）
                # 在对应方标签（"购买方"/"销售方"）前若干字符内查找最后一个"称：XXX"行
                if not name:
                    label_key = '购买方' if '购买' in party else '销售方'
                    label_pos = text.rfind(label_key)
                    if label_pos != -1:
                        before = text[max(0, label_pos - 400): label_pos]
                        matches = re.findall(r'称[：:]\s*([^\n]+)', before)
                        if matches:
                            name = matches[-1].strip()
                            logging.debug("  %s name (label fallback): %r", party, name)

                # 第五回退：旧版发票无"购买方"标签时，用空税号行作锚点（仅用于购买方）
                # 空 "纳税人识别号：\n" 行紧随购买方名称，可作为定位锚
                if not name and '购买' in party:
                    empty_id_m = re.search(r'纳税人识别号[：:]\s*\n', text)
                    if empty_id_m:
                        before_id = text[:empty_id_m.start()]
                        matches = re.findall(r'称[：:]\s*([^\n]+)', before_id)
                        if matches:
                            name = matches[-1].strip()
                            logging.debug("  %s name (empty-id fallback): %r", party, name)

        # 税号：优先从对应方的 section 内查找，避免买方无税号时索引偏移
        # 兼容"购买方信息"（全电发票）和"购买方"（旧版纸质发票）两种格式
        if '购买' in party:
            sec_m = re.search(r'购.{0,2}方(?:信息)?([\s\S]*?)(?:销.{0,2}方|$)', text)
        else:
            sec_m = re.search(r'销.{0,2}方(?:信息)?([\s\S]*)', text)
        if sec_m:
            ids_in_sec = _RE_TAX_ID.findall(sec_m.group(1))
            tax_id = ids_in_sec[0] if ids_in_sec else ""
            logging.debug("  %s tax_id (section): %r (found=%s)", party, tax_id, ids_in_sec)
        else:
            # 无方标签时：若存在空"纳税人识别号：\n"行，购买方税号视为空
            if '购买' in party and re.search(r'纳税人识别号[：:]\s*\n', text):
                tax_id = ""
                logging.debug("  %s tax_id (empty-line inferred): ''", party)
            else:
                tax_ids = _RE_TAX_ID.findall(text)
                tax_id = tax_ids[tax_index] if len(tax_ids) > tax_index else ""
                logging.debug("  %s tax_id (fallback idx=%d, all=%s): %r",
                              party, tax_index, tax_ids, tax_id)
        return name, tax_id

    def _extract_total(self, text: str) -> Decimal:
        m = _RE_TOTAL_LOWER.search(text)
        if m:
            return self._to_decimal(m.group(1))
        amounts = _RE_AMOUNT.findall(text)
        return self._to_decimal(amounts[-1]) if amounts else Decimal("0")

    def _extract_sub_amounts(self, text: str) -> tuple[Decimal, Decimal]:
        # 优先：带 ¥ 标签的精确提取
        tax_m = _RE_TAX_AMOUNT.search(text)
        if tax_m:
            tax = self._to_decimal(tax_m.group(1))
            sub_m = _RE_SUBTOTAL.search(text)
            subtotal = self._to_decimal(sub_m.group(1)) if sub_m else Decimal("0")
            return tax, subtotal

        # 次选：从 "合\n计\n{小计}\n{税额}" 行结构提取税额（OCR 无 ¥ 时）
        tax_m = _RE_TAX_IN_TOTAL_ROW.search(text)
        if tax_m:
            return self._to_decimal(tax_m.group(1)), Decimal("0")

        # 最后回退：从所有 ¥ 金额中智能配对找出小计与税额
        amounts = _RE_AMOUNT.findall(text)
        total_m = _RE_TOTAL_LOWER.search(text)
        total_str = total_m.group(1) if total_m else ""
        filtered = [a for a in amounts if a != total_str]
        if len(filtered) >= 2:
            total_dec = self._to_decimal(total_str) if total_str else Decimal("0")
            if total_dec > Decimal("0"):
                candidates = [self._to_decimal(a) for a in filtered]
                best_tax, best_sub = Decimal("0"), Decimal("0")
                best_diff = None
                for i in range(len(candidates)):
                    for j in range(i + 1, len(candidates)):
                        diff = abs(candidates[i] + candidates[j] - total_dec)
                        if best_diff is None or diff < best_diff:
                            best_diff = diff
                            a, b = candidates[i], candidates[j]
                            best_tax, best_sub = (a, b) if a <= b else (b, a)
                if best_diff is not None and best_diff <= total_dec * Decimal("0.02"):
                    return best_tax, best_sub
            return self._to_decimal(filtered[-1]), self._to_decimal(filtered[-2])
        return Decimal("0"), Decimal("0")

    def _to_decimal(self, value: str) -> Decimal:
        try:
            return Decimal(value.replace(',', ''))
        except InvalidOperation:
            return Decimal("0")

    def _determine_status(self, invoice: Invoice) -> str:
        missing = [f for f in _REQUIRED_FIELDS if not getattr(invoice, f)]
        if missing:
            logging.info("  status=REVIEW: missing fields %s", missing)
            return InvoiceStatus.REVIEW

        if invoice.subtotal and invoice.tax_amount:
            expected = invoice.subtotal + invoice.tax_amount
            if abs(expected - invoice.total_amount) > Decimal("0.01"):
                logging.info(
                    "  status=REVIEW: amount mismatch subtotal(%s)+tax(%s)=%s != total(%s)",
                    invoice.subtotal, invoice.tax_amount, expected, invoice.total_amount,
                )
                return InvoiceStatus.REVIEW

        return InvoiceStatus.SUCCESS
