/**
 * Tiện ích tính toán số học bảo toàn độ chính xác Decimal (2 chữ số thập phân)
 * mà không gặp lỗi làm tròn IEEE 754 float của JavaScript.
 */

/**
 * Chuyển đổi chuỗi Decimal sang số nguyên đơn vị cent (nhân 100)
 */
export function decimalToCents(valStr: string | number | null | undefined): bigint {
  if (valStr === null || valStr === undefined || valStr === '') {
    return 0n;
  }
  const clean = String(valStr).trim();
  if (!clean || isNaN(Number(clean))) return 0n;

  const isNeg = clean.startsWith('-');
  const unsigned = isNeg ? clean.slice(1) : clean;
  const parts = unsigned.split('.');

  const integerPart = BigInt(parts[0] || '0');
  let fractionPart = 0n;

  if (parts.length > 1) {
    const fracStr = parts[1].padEnd(2, '0').slice(0, 2);
    fractionPart = BigInt(fracStr);
  }

  const totalCents = integerPart * 100n + fractionPart;
  return isNeg ? -totalCents : totalCents;
}

/**
 * Chuyển đổi số nguyên cents sang chuỗi Decimal (chia 100)
 */
export function centsToDecimal(cents: bigint): string {
  const isNeg = cents < 0n;
  const absCents = isNeg ? -cents : cents;
  const integerPart = absCents / 100n;
  const fractionPart = absCents % 100n;
  const fractionStr = fractionPart.toString().padStart(2, '0');
  return `${isNeg ? '-' : ''}${integerPart}.${fractionStr}`;
}

/**
 * Cộng 2 chuỗi Decimal
 */
export function addDecimal(a: string, b: string): string {
  return centsToDecimal(decimalToCents(a) + decimalToCents(b));
}

/**
 * Trừ 2 chuỗi Decimal
 */
export function subtractDecimal(a: string, b: string): string {
  return centsToDecimal(decimalToCents(a) - decimalToCents(b));
}
