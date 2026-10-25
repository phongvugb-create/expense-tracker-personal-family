import { useState, useEffect, useMemo } from 'react';
import { X, ArrowDownRight, ArrowUpRight, AlertCircle, Calendar, FileText, Tag, Wallet } from 'lucide-react';
import type { Account } from '../types/account';
import type { Category, CategoryType } from '../types/category';
import type { TransactionCreateRequest } from '../types/transaction';
import { transactionService } from '../services/transactionService';
import { getErrorMessage } from '../services/apiClient';

interface CreateTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  accounts: Account[];
  categories: Category[];
  defaultAccountId?: string;
  defaultType?: CategoryType;
}

export function CreateTransactionModal({
  isOpen,
  onClose,
  onSuccess,
  accounts,
  categories,
  defaultAccountId,
  defaultType = 'expense',
}: CreateTransactionModalProps) {
  const [type, setType] = useState<CategoryType>(defaultType);
  const [accountId, setAccountId] = useState<string>(defaultAccountId || '');
  const [categoryId, setCategoryId] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [occurredAt, setOccurredAt] = useState<string>(() => {
    // Định dạng YYYY-MM-DDTHH:mm cho input datetime-local
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  });
  const [note, setNote] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Lọc các ví đang hoạt động (không bị lưu trữ)
  const activeAccounts = useMemo(() => {
    return accounts.filter((a) => !a.is_archived);
  }, [accounts]);

  // Cập nhật selected account mặc định nếu chưa chọn
  useEffect(() => {
    if (isOpen) {
      if (defaultAccountId && activeAccounts.some((a) => a.id === defaultAccountId)) {
        setAccountId(defaultAccountId);
      } else if (activeAccounts.length > 0 && !accountId) {
        setAccountId(activeAccounts[0].id);
      }
      setType(defaultType);
      setError(null);
    }
  }, [isOpen, defaultAccountId, defaultType, activeAccounts, accountId]);

  // Lấy đối tượng ví đã chọn để kiểm tra scope
  const selectedAccount = useMemo(() => {
    return activeAccounts.find((a) => a.id === accountId);
  }, [activeAccounts, accountId]);

  // Lọc danh mục hợp lệ: cùng type và tương thích với scope của ví
  const compatibleCategories = useMemo(() => {
    return categories.filter((cat) => {
      // Bắt buộc cùng loại thu/chi
      if (cat.type !== type) return false;
      if (cat.is_archived) return false;

      // Danh mục hệ thống dùng được cho mọi ví
      if (cat.scope === 'system') return true;

      // Danh mục cá nhân chỉ dùng cho ví cá nhân
      if (cat.scope === 'personal') {
        return selectedAccount?.scope === 'personal';
      }

      // Danh mục gia đình chỉ dùng cho ví thuộc cùng nhóm gia đình
      if (cat.scope === 'family') {
        return (
          selectedAccount?.scope === 'family' &&
          Boolean(selectedAccount.family_id) &&
          cat.family_id === selectedAccount.family_id
        );
      }

      return false;
    });
  }, [categories, type, selectedAccount]);

  // Đặt categoryId mặc định khi danh sách danh mục tương thích thay đổi
  useEffect(() => {
    if (compatibleCategories.length > 0) {
      if (!compatibleCategories.some((c) => c.id === categoryId)) {
        setCategoryId(compatibleCategories[0].id);
      }
    } else {
      setCategoryId('');
    }
  }, [compatibleCategories, categoryId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!accountId) {
      setError('Vui lòng chọn ví thực hiện giao dịch.');
      return;
    }

    if (!categoryId) {
      setError('Vui lòng chọn danh mục thu/chi phù hợp.');
      return;
    }

    // Validate amount string (chuỗi Decimal chuẩn)
    const cleanAmount = amount.trim();
    if (!cleanAmount) {
      setError('Vui lòng nhập số tiền.');
      return;
    }

    const num = Number(cleanAmount);
    if (isNaN(num) || num <= 0) {
      setError('Số tiền giao dịch phải là một số lớn hơn 0.');
      return;
    }

    // Kiểm tra tối đa 2 chữ số thập phân
    const parts = cleanAmount.split('.');
    if (parts.length > 2 || (parts.length === 2 && parts[1].length > 2)) {
      setError('Số tiền chỉ được chứa tối đa 2 chữ số thập phân.');
      return;
    }

    if (!occurredAt) {
      setError('Vui lòng chọn thời gian phát sinh giao dịch.');
      return;
    }

    // Chuẩn hóa occurred_at sang ISO 8601 UTC
    const occurredDate = new Date(occurredAt);
    if (isNaN(occurredDate.getTime())) {
      setError('Thời gian phát sinh không hợp lệ.');
      return;
    }

    const payload: TransactionCreateRequest = {
      account_id: accountId,
      category_id: categoryId,
      type,
      amount: cleanAmount,
      note: note.trim() || null,
      occurred_at: occurredDate.toISOString(),
    };

    try {
      setLoading(true);
      await transactionService.createTransaction(payload);
      // Reset form
      setAmount('');
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
          maxWidth: '540px',
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
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background:
                  type === 'income'
                    ? 'rgba(16, 185, 129, 0.15)'
                    : 'rgba(239, 68, 68, 0.15)',
                color: type === 'income' ? 'var(--success)' : 'var(--error)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {type === 'income' ? <ArrowDownRight size={22} /> : <ArrowUpRight size={22} />}
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                {type === 'income' ? 'Thêm khoản thu nhập' : 'Thêm khoản chi tiêu'}
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                Ghi chép giao dịch và tự động cập nhật số dư ví
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
          {/* Chọn Loại Giao Dịch: Thu nhập / Chi tiêu */}
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
              Loại giao dịch
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setType('expense')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px',
                  borderRadius: 'var(--radius-md)',
                  border:
                    type === 'expense'
                      ? '2px solid var(--error)'
                      : '1px solid rgba(255, 255, 255, 0.1)',
                  background:
                    type === 'expense'
                      ? 'rgba(239, 68, 68, 0.12)'
                      : 'var(--bg-input)',
                  color: type === 'expense' ? 'var(--error)' : 'var(--text-sub)',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <ArrowUpRight size={18} />
                <span>Khoản Chi Tiêu</span>
              </button>

              <button
                type="button"
                onClick={() => setType('income')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px',
                  borderRadius: 'var(--radius-md)',
                  border:
                    type === 'income'
                      ? '2px solid var(--success)'
                      : '1px solid rgba(255, 255, 255, 0.1)',
                  background:
                    type === 'income'
                      ? 'rgba(16, 185, 129, 0.12)'
                      : 'var(--bg-input)',
                  color: type === 'income' ? 'var(--success)' : 'var(--text-sub)',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <ArrowDownRight size={18} />
                <span>Khoản Thu Nhập</span>
              </button>
            </div>
          </div>

          {/* Chọn Ví Tài Chính */}
          <div>
            <label
              htmlFor="tx-account"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <Wallet size={15} color="var(--primary-500)" />
              <span>Ví tài khoản</span>
            </label>
            {activeAccounts.length === 0 ? (
              <div
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--error)',
                  padding: '10px',
                  background: 'var(--error-bg)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--error-border)',
                }}
              >
                Chưa có ví đang hoạt động. Vui lòng tạo ví tại trang Quản lý ví trước.
              </div>
            ) : (
              <select
                id="tx-account"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '11px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.9rem',
                  outline: 'none',
                }}
              >
                {activeAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.scope === 'personal' ? 'Cá nhân' : 'Gia đình'}) — Số dư: {acc.current_balance} {acc.currency}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Chọn Danh Mục */}
          <div>
            <label
              htmlFor="tx-category"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <Tag size={15} color="#ec4899" />
              <span>Danh mục {type === 'income' ? 'thu nhập' : 'chi tiêu'}</span>
            </label>
            {compatibleCategories.length === 0 ? (
              <div
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--warning)',
                  padding: '10px',
                  background: 'rgba(245, 158, 11, 0.1)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid #FCE38E',
                }}
              >
                Không có danh mục {type === 'income' ? 'thu nhập' : 'chi tiêu'} phù hợp cho ví này.
              </div>
            ) : (
              <select
                id="tx-category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '11px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.9rem',
                  outline: 'none',
                }}
              >
                {compatibleCategories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name} ({cat.scope === 'system' ? 'Hệ thống' : cat.scope === 'personal' ? 'Cá nhân' : 'Gia đình'})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Số Tiền */}
          <div>
            <label
              htmlFor="tx-amount"
              style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              Số tiền ({selectedAccount?.currency || 'VND'}) <span style={{ color: 'var(--error)' }}>*</span>
            </label>
            <input
              id="tx-amount"
              type="text"
              inputMode="decimal"
              placeholder="Ví dụ: 150000 hoặc 25000.50"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={loading}
              required
              style={{
                width: '100%',
                padding: '11px 14px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '1rem',
                fontWeight: 600,
                outline: 'none',
              }}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginTop: '4px', display: 'block' }}>
              Nhập chuỗi số nguyên hoặc thập phân (tối đa 2 chữ số lẻ), ví dụ: 500000
            </span>
          </div>

          {/* Thời Gian Phát Sinh */}
          <div>
            <label
              htmlFor="tx-occurred-at"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <Calendar size={15} color="var(--primary-500)" />
              <span>Thời gian phát sinh</span>
            </label>
            <input
              id="tx-occurred-at"
              type="datetime-local"
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
              disabled={loading}
              required
              style={{
                width: '100%',
                padding: '11px 14px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Ghi Chú Tùy Chọn */}
          <div>
            <label
              htmlFor="tx-note"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <FileText size={15} color="var(--text-sub)" />
              <span>Ghi chú (tùy chọn)</span>
            </label>
            <input
              id="tx-note"
              type="text"
              maxLength={255}
              placeholder="Ví dụ: Mua sắm cuối tuần, Tiền thưởng dự án..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={loading}
              style={{
                width: '100%',
                padding: '11px 14px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Actions */}
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
                padding: '10px 18px',
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
              disabled={loading || activeAccounts.length === 0 || compatibleCategories.length === 0}
              style={{
                padding: '10px 22px',
                background:
                  type === 'income'
                    ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                    : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading || activeAccounts.length === 0 || compatibleCategories.length === 0 ? 0.6 : 1,
                boxShadow: 'var(--shadow-button)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              {loading ? (
                <span>Đang xử lý...</span>
              ) : (
                <span>Lưu Giao Dịch</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
