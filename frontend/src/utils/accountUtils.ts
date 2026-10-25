/**
 * Định dạng số tiền tiền tệ hiển thị trên giao diện người dùng
 * Giữ nguyên giá trị thập phân chính xác từ chuỗi Decimal của PostgreSQL
 */
export function formatCurrency(amountStr: string | number, currency: string = 'VND'): string {
  if (amountStr === undefined || amountStr === null || amountStr === '') {
    return '0 ₫';
  }

  const rawStr = String(amountStr).trim();
  const num = Number(rawStr);

  // Nếu là VND thì hiển thị định dạng chuẩn Việt Nam kèm ký hiệu ₫
  if (currency.toUpperCase() === 'VND') {
    if (isNaN(num)) return `${rawStr} ₫`;
    // Format số nguyên hoặc 2 chữ số thập phân nếu có số lẻ
    const parts = rawStr.split('.');
    const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    if (parts.length > 1 && parts[1] !== '00' && parts[1] !== '') {
      return `${integerPart},${parts[1]} ₫`;
    }
    return `${integerPart} ₫`;
  }

  // Tiền tệ khác (USD, EUR,...)
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `${rawStr} ${currency}`;
  }
}

/**
 * Nhãn hiển thị loại ví tiếng Việt
 */
export const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  cash: 'Tiền mặt',
  bank: 'Tài khoản ngân hàng',
  e_wallet: 'Ví điện tử',
  credit_card: 'Thẻ tín dụng',
  other: 'Khác',
};

/**
 * Nhãn phạm vi ví tiếng Việt
 */
export const ACCOUNT_SCOPE_LABELS: Record<string, string> = {
  personal: 'Ví cá nhân',
  family: 'Ví gia đình',
};
