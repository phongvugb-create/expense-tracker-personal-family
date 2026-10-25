import { useState, useEffect, useMemo } from 'react';
import {
  X,
  ArrowRightLeft,
  AlertCircle,
  Calendar,
  FileText,
  Tag,
  Wallet,
  ArrowRight,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import type { Account } from '../types/account';
import type { Category } from '../types/category';
import type { TransferCreateRequest } from '../types/transfer';
import { transferService } from '../services/transferService';
import { getErrorMessage } from '../services/apiClient';
import { formatCurrency } from '../utils/accountUtils';
import { addDecimal, subtractDecimal } from '../utils/decimalUtils';

interface CreateTransferModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  accounts: Account[];
  categories: Category[];
  defaultFromAccountId?: string;
}

export function CreateTransferModal({
  isOpen,
  onClose,
  onSuccess,
  accounts,
  categories,
  defaultFromAccountId,
}: CreateTransferModalProps) {
  const [fromAccountId, setFromAccountId] = useState<string>('');
  const [toAccountId, setToAccountId] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [feeAmount, setFeeAmount] = useState<string>('0');
  const [feeCategoryId, setFeeCategoryId] = useState<string>('');
  const [occurredAt, setOccurredAt] = useState<string>(() => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  });
  const [note, setNote] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Lọc danh sách ví hoạt động (chưa lưu trữ)
  const activeAccounts = useMemo(() => {
    return accounts.filter((a) => !a.is_archived);
  }, [accounts]);

  // Khởi tạo ví nguồn và ví đích khi mở modal
  useEffect(() => {
    if (isOpen) {
      setError(null);
      if (defaultFromAccountId && activeAccounts.some((a) => a.id === defaultFromAccountId)) {
        setFromAccountId(defaultFromAccountId);
      } else if (activeAccounts.length > 0 && !fromAccountId) {
        setFromAccountId(activeAccounts[0].id);
      }
    }
  }, [isOpen, defaultFromAccountId, activeAccounts, fromAccountId]);

  // Tìm đối tượng ví nguồn đã chọn
  const fromAccount = useMemo(() => {
    return activeAccounts.find((a) => a.id === fromAccountId) || null;
  }, [activeAccounts, fromAccountId]);

  // Lọc danh sách ví đích tương thích:
  // 1. Khác ví nguồn (id != fromAccountId)
  // 2. Cùng currency với ví nguồn
  // 3. Cùng scope với ví nguồn (personal <-> personal; family <-> family có cùng family_id)
  const compatibleToAccounts = useMemo(() => {
    if (!fromAccount) return [];
    return activeAccounts.filter((acc) => {
      if (acc.id === fromAccount.id) return false;
      if (acc.currency !== fromAccount.currency) return false;
      if (acc.scope !== fromAccount.scope) return false;
      if (acc.scope === 'family' && acc.family_id !== fromAccount.family_id) return false;
      return true;
    });
  }, [activeAccounts, fromAccount]);

  // Đặt toAccountId mặc định khi danh sách ví đích tương thích thay đổi
  useEffect(() => {
    if (compatibleToAccounts.length > 0) {
      if (!compatibleToAccounts.some((a) => a.id === toAccountId)) {
        setToAccountId(compatibleToAccounts[0].id);
      }
    } else {
      setToAccountId('');
    }
  }, [compatibleToAccounts, toAccountId]);

  // Tìm đối tượng ví đích đã chọn
  const toAccount = useMemo(() => {
    return compatibleToAccounts.find((a) => a.id === toAccountId) || null;
  }, [compatibleToAccounts, toAccountId]);

  // Kiểm tra có phí chuyển tiền hay không
  const hasFee = useMemo(() => {
    const feeNum = Number(feeAmount);
    return !isNaN(feeNum) && feeNum > 0;
  }, [feeAmount]);

  // Lọc danh mục chi phí tương thích với ví nguồn:
  // 1. Phải là type='expense'
  // 2. Chưa lưu trữ
  // 3. Tương thích scope với ví nguồn (system dùng chung; personal cho ví cá nhân; family cho ví gia đình cùng family_id)
  const compatibleFeeCategories = useMemo(() => {
    if (!fromAccount) return [];
    return categories.filter((cat) => {
      if (cat.type !== 'expense') return false;
      if (cat.is_archived) return false;

      if (cat.scope === 'system') return true;
      if (cat.scope === 'personal') return fromAccount.scope === 'personal';
      if (cat.scope === 'family') {
        return (
          fromAccount.scope === 'family' &&
          Boolean(fromAccount.family_id) &&
          cat.family_id === fromAccount.family_id
        );
      }
      return false;
    });
  }, [categories, fromAccount]);

  // Đặt feeCategoryId mặc định khi có phí
  useEffect(() => {
    if (hasFee && compatibleFeeCategories.length > 0) {
      if (!compatibleFeeCategories.some((c) => c.id === feeCategoryId)) {
        // Ưu tiên danh mục có tên liên quan đến phí chuyển tiền nếu có
        const bestCat =
          compatibleFeeCategories.find((c) => c.name.toLowerCase().includes('phí')) ||
          compatibleFeeCategories[0];
        setFeeCategoryId(bestCat.id);
      }
    } else if (!hasFee) {
      setFeeCategoryId('');
    }
  }, [hasFee, compatibleFeeCategories, feeCategoryId]);

  // Tính số dư dự kiến (bảo toàn độ chính xác Decimal qua BigInt cents)
  const balancePreview = useMemo(() => {
    if (!fromAccount || !toAccount) return null;

    const cleanAmount = amount.trim();
    const cleanFee = feeAmount.trim() || '0';

    const numAmount = Number(cleanAmount);
    const numFee = Number(cleanFee);

    if (isNaN(numAmount) || numAmount <= 0) return null;
    if (isNaN(numFee) || numFee < 0) return null;

    // Tổng tiền trừ ở ví nguồn = amount + fee
    const totalDeduction = addDecimal(cleanAmount, cleanFee);
    const fromExpectedBalance = subtractDecimal(fromAccount.current_balance, totalDeduction);
    // Tiền cộng vào ví đích = amount
    const toExpectedBalance = addDecimal(toAccount.current_balance, cleanAmount);

    return {
      fromCurrent: fromAccount.current_balance,
      fromExpected: fromExpectedBalance,
      toCurrent: toAccount.current_balance,
      toExpected: toExpectedBalance,
      totalDeduction,
      currency: fromAccount.currency,
    };
  }, [fromAccount, toAccount, amount, feeAmount]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!fromAccountId) {
      setError('Vui lòng chọn ví nguồn.');
      return;
    }

    if (!toAccountId) {
      setError('Vui lòng chọn ví đích.');
      return;
    }

    if (fromAccountId === toAccountId) {
      setError('Ví nguồn và ví đích phải khác nhau.');
      return;
    }

    const cleanAmount = amount.trim();
    if (!cleanAmount) {
      setError('Vui lòng nhập số tiền chuyển.');
      return;
    }

    const num = Number(cleanAmount);
    if (isNaN(num) || num <= 0) {
      setError('Số tiền chuyển phải là số lớn hơn 0.');
      return;
    }

    const amountParts = cleanAmount.split('.');
    if (amountParts.length > 2 || (amountParts.length === 2 && amountParts[1].length > 2)) {
      setError('Số tiền chỉ được chứa tối đa 2 chữ số thập phân.');
      return;
    }

    const cleanFee = feeAmount.trim() || '0.00';
    const numFee = Number(cleanFee);
    if (isNaN(numFee) || numFee < 0) {
      setError('Phí chuyển tiền không hợp lệ (không được âm).');
      return;
    }

    const feeParts = cleanFee.split('.');
    if (feeParts.length > 2 || (feeParts.length === 2 && feeParts[1].length > 2)) {
      setError('Phí chuyển tiền chỉ được chứa tối đa 2 chữ số thập phân.');
      return;
    }

    if (numFee > 0 && !feeCategoryId) {
      setError('Vui lòng chọn danh mục chi phí khi có phát sinh phí chuyển tiền.');
      return;
    }

    if (!occurredAt) {
      setError('Vui lòng chọn thời gian phát sinh.');
      return;
    }

    const occurredDate = new Date(occurredAt);
    if (isNaN(occurredDate.getTime())) {
      setError('Thời gian phát sinh không hợp lệ.');
      return;
    }

    const payload: TransferCreateRequest = {
      from_account_id: fromAccountId,
      to_account_id: toAccountId,
      amount: cleanAmount,
      fee_amount: numFee > 0 ? cleanFee : '0.00',
      fee_category_id: numFee > 0 ? feeCategoryId : null,
      note: note.trim() || null,
      occurred_at: occurredDate.toISOString(),
    };

    try {
      setLoading(true);
      await transferService.createTransfer(payload);
      // Reset form
      setAmount('');
      setFeeAmount('0');
      setNote('');
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        zIndex: 50,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          animation: 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '12px',
                background: 'var(--secondary-soft)',
                color: 'var(--primary-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ArrowRightLeft size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                Chuyển tiền liên ví
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                Hạch toán kép bút toán kép tự động cập nhật số dư 2 ví
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-sub)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'var(--error-bg)',
              color: 'var(--error)',
              border: '1px solid var(--error-border)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.875rem',
              marginBottom: '20px',
            }}
          >
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Chọn Ví Nguồn & Ví Đích */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            {/* Ví Nguồn */}
            <div>
              <label
                htmlFor="tr-from-acc"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  marginBottom: '6px',
                }}
              >
                <Wallet size={15} color="var(--error)" />
                <span>Ví chuyển đi (Nguồn)</span>
              </label>
              <select
                id="tr-from-acc"
                value={fromAccountId}
                onChange={(e) => setFromAccountId(e.target.value)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.875rem',
                  outline: 'none',
                }}
              >
                {activeAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.scope === 'personal' ? 'Cá nhân' : 'Gia đình'})
                  </option>
                ))}
              </select>
              {fromAccount && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginTop: '4px' }}>
                  Số dư: <strong style={{ color: 'var(--text-main)' }}>{formatCurrency(fromAccount.current_balance, fromAccount.currency)}</strong>
                </div>
              )}
            </div>

            {/* Ví Đích */}
            <div>
              <label
                htmlFor="tr-to-acc"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  marginBottom: '6px',
                }}
              >
                <Wallet size={15} color="var(--success)" />
                <span>Ví nhận đến (Đích)</span>
              </label>
              {compatibleToAccounts.length === 0 ? (
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--warning)',
                    padding: '8px 10px',
                    background: 'rgba(245, 158, 11, 0.1)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid #FCE38E',
                  }}
                >
                  Không có ví đích cùng loại tiền tệ ({fromAccount?.currency}) và cùng phạm vi sở hữu.
                </div>
              ) : (
                <select
                  id="tr-to-acc"
                  value={toAccountId}
                  onChange={(e) => setToAccountId(e.target.value)}
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--bg-input-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--text-main)',
                    fontSize: '0.875rem',
                    outline: 'none',
                  }}
                >
                  {compatibleToAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.scope === 'personal' ? 'Cá nhân' : 'Gia đình'})
                    </option>
                  ))}
                </select>
              )}
              {toAccount && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginTop: '4px' }}>
                  Số dư: <strong style={{ color: 'var(--text-main)' }}>{formatCurrency(toAccount.current_balance, toAccount.currency)}</strong>
                </div>
              )}
            </div>
          </div>

          {/* Số Tiền Chuyển & Phí Chuyển Tiền */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            {/* Số Tiền Chuyển */}
            <div>
              <label
                htmlFor="tr-amount"
                style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
              >
                Số tiền chuyển ({fromAccount?.currency || 'VND'}) <span style={{ color: 'var(--error)' }}>*</span>
              </label>
              <input
                id="tr-amount"
                type="text"
                inputMode="decimal"
                placeholder="Ví dụ: 500000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={loading}
                required
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '1rem',
                  fontWeight: 600,
                  outline: 'none',
                }}
              />
            </div>

            {/* Phí Chuyển Tiền */}
            <div>
              <label
                htmlFor="tr-fee"
                style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
              >
                Phí chuyển tiền ({fromAccount?.currency || 'VND'})
              </label>
              <input
                id="tr-fee"
                type="text"
                inputMode="decimal"
                placeholder="Mặc định: 0"
                value={feeAmount}
                onChange={(e) => setFeeAmount(e.target.value)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '1rem',
                  fontWeight: 600,
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Chọn Danh Mục Phí (Chỉ hiện khi fee_amount > 0) */}
          {hasFee && (
            <div>
              <label
                htmlFor="tr-fee-cat"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  marginBottom: '6px',
                }}
              >
                <Tag size={15} color="#ec4899" />
                <span>Danh mục phí chuyển tiền</span> <span style={{ color: 'var(--error)' }}>*</span>
              </label>
              {compatibleFeeCategories.length === 0 ? (
                <div
                  style={{
                    fontSize: '0.8rem',
                    color: 'var(--error)',
                    padding: '8px 12px',
                    background: 'var(--error-bg)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--error-border)',
                  }}
                >
                  Không tìm thấy danh mục chi tiêu khả dụng để hạch toán phí chuyển tiền.
                </div>
              ) : (
                <select
                  id="tr-fee-cat"
                  value={feeCategoryId}
                  onChange={(e) => setFeeCategoryId(e.target.value)}
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--bg-input-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--text-main)',
                    fontSize: '0.875rem',
                    outline: 'none',
                  }}
                >
                  {compatibleFeeCategories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name} ({cat.scope === 'system' ? 'Hệ thống' : cat.scope === 'personal' ? 'Cá nhân' : 'Gia đình'})
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* Thời Gian Phát Sinh */}
          <div>
            <label
              htmlFor="tr-occurred-at"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.85rem',
                fontWeight: 600,
                marginBottom: '6px',
              }}
            >
              <Calendar size={15} color="var(--primary-500)" />
              <span>Thời gian chuyển tiền</span>
            </label>
            <input
              id="tr-occurred-at"
              type="datetime-local"
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
              disabled={loading}
              required
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.875rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Ghi Chú Tùy Chọn */}
          <div>
            <label
              htmlFor="tr-note"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.85rem',
                fontWeight: 600,
                marginBottom: '6px',
              }}
            >
              <FileText size={15} color="var(--text-sub)" />
              <span>Ghi chú (tùy chọn)</span>
            </label>
            <input
              id="tr-note"
              type="text"
              maxLength={500}
              placeholder="Ví dụ: Chuyển tiết kiệm, Thanh toán hộ..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={loading}
              style={{
                width: '100%',
                padding: '10px 12px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.875rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Xem Trước Tác Động Số Dư (Exact Decimal Balance Preview) */}
          {balancePreview && (
            <div
              style={{
                background: 'rgba(59, 130, 246, 0.06)',
                border: '1px solid #C4DDFC',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
              }}
            >
              <div
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  color: 'var(--primary-500)',
                  marginBottom: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <ArrowRightLeft size={14} />
                <span>XEM TRƯỚC TÁC ĐỘNG SỐ DƯ (DỰ KIẾN)</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.85rem' }}>
                {/* Ví Nguồn */}
                <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ color: 'var(--text-sub)', fontSize: '0.75rem', marginBottom: '2px' }}>
                    {fromAccount?.name}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--error)' }}>
                    <TrendingDown size={14} />
                    <span>-{formatCurrency(balancePreview.totalDeduction, balancePreview.currency)}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Sau chuyển: <strong>{formatCurrency(balancePreview.fromExpected, balancePreview.currency)}</strong>
                  </div>
                </div>

                {/* Ví Đích */}
                <div style={{ background: 'var(--bg-input)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ color: 'var(--text-sub)', fontSize: '0.75rem', marginBottom: '2px' }}>
                    {toAccount?.name}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--success)' }}>
                    <TrendingUp size={14} />
                    <span>+{formatCurrency(amount, balancePreview.currency)}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Sau chuyển: <strong>{formatCurrency(balancePreview.toExpected, balancePreview.currency)}</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '12px',
              marginTop: '12px',
              borderTop: '1px solid var(--border)',
              paddingTop: '16px',
            }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: '9px 18px',
                background: 'transparent',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-muted)',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={loading || !fromAccountId || !toAccountId || compatibleToAccounts.length === 0}
              style={{
                padding: '10px 22px',
                background: 'var(--primary-gradient)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: loading || !fromAccountId || !toAccountId || compatibleToAccounts.length === 0 ? 'not-allowed' : 'pointer',
                opacity: loading || !fromAccountId || !toAccountId || compatibleToAccounts.length === 0 ? 0.6 : 1,
                boxShadow: 'var(--shadow-button)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {loading ? (
                <span>Đang xử lý...</span>
              ) : (
                <>
                  <span>Xác Nhận Chuyển Tiền</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
