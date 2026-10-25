import { useState, useEffect, useMemo } from 'react';
import { X, ArrowDownRight, ArrowUpRight, AlertCircle, Calendar, FileText, Tag, Wallet } from 'lucide-react';
import type { Account } from '../types/account';
import type { Category, CategoryType } from '../types/category';
import type { Transaction, TransactionUpdateRequest } from '../types/transaction';
import { transactionService } from '../services/transactionService';
import { getErrorMessage } from '../services/apiClient';

interface EditTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  transaction: Transaction | null;
  accounts: Account[];
  categories: Category[];
}

export function EditTransactionModal({
  isOpen,
  onClose,
  onSuccess,
  transaction,
  accounts,
  categories,
}: EditTransactionModalProps) {
  const [type, setType] = useState<CategoryType>('expense');
  const [categoryId, setCategoryId] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [occurredAt, setOccurredAt] = useState<string>('');
  const [note, setNote] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Tìm thông tin ví của giao dịch
  const currentAccount = useMemo(() => {
    if (!transaction) return null;
    return accounts.find((a) => a.id === transaction.account_id);
  }, [accounts, transaction]);

  // Load transaction data vào form khi mở modal
  useEffect(() => {
    if (isOpen && transaction) {
      setType(transaction.type);
      setCategoryId(transaction.category_id);
      setAmount(transaction.amount);
      setNote(transaction.note || '');

      // Format occurred_at sang định dạng YYYY-MM-DDTHH:mm
      try {
        const d = new Date(transaction.occurred_at);
        if (!isNaN(d.getTime())) {
          d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
          setOccurredAt(d.toISOString().slice(0, 16));
        } else {
          setOccurredAt('');
        }
      } catch {
        setOccurredAt('');
      }
      setError(null);
    }
  }, [isOpen, transaction]);

  // Lọc danh mục hợp lệ theo loại và ví
  const compatibleCategories = useMemo(() => {
    return categories.filter((cat) => {
      if (cat.type !== type) return false;
      if (cat.is_archived) return false;

      if (cat.scope === 'system') return true;

      if (cat.scope === 'personal') {
        return currentAccount?.scope === 'personal';
      }

      if (cat.scope === 'family') {
        return (
          currentAccount?.scope === 'family' &&
          Boolean(currentAccount.family_id) &&
          cat.family_id === currentAccount.family_id
        );
      }

      return false;
    });
  }, [categories, type, currentAccount]);

  // Nếu type đổi khiến categoryId không còn hợp lệ, reset về danh mục hợp lệ đầu tiên
  useEffect(() => {
    if (compatibleCategories.length > 0) {
      if (!compatibleCategories.some((c) => c.id === categoryId)) {
        setCategoryId(compatibleCategories[0].id);
      }
    } else {
      setCategoryId('');
    }
  }, [compatibleCategories, categoryId]);

  if (!isOpen || !transaction) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!categoryId) {
      setError('Vui lòng chọn danh mục thu/chi phù hợp.');
      return;
    }

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

    const parts = cleanAmount.split('.');
    if (parts.length > 2 || (parts.length === 2 && parts[1].length > 2)) {
      setError('Số tiền chỉ được chứa tối đa 2 chữ số thập phân.');
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

    // Backend PATCH /transactions/{id} KHÔNG cho đổi account_id hoặc user_id
    const payload: TransactionUpdateRequest = {
      type,
      category_id: categoryId,
      amount: cleanAmount,
      note: note.trim() || null,
      occurred_at: occurredDate.toISOString(),
    };

    try {
      setLoading(true);
      await transactionService.updateTransaction(transaction.id, payload);
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
                Chỉnh sửa giao dịch
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                Cập nhật thông tin giao dịch và đồng bộ lại số dư ví
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
          {/* Thông tin ví gắn liền (Cố định, không cho sửa theo API contract) */}
          <div
            style={{
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid #C4DDFC',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wallet size={16} color="var(--primary-500)" />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>VÍ TÀI CHÍNH (CỐ ĐỊNH)</div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                  {transaction.account_name || currentAccount?.name || 'Ví tài chính'}
                </div>
              </div>
            </div>
            <span
              style={{
                fontSize: '0.75rem',
                color: 'var(--primary-500)',
                background: 'var(--secondary-soft)',
                padding: '3px 8px',
                borderRadius: 'var(--radius-full)',
                fontWeight: 600,
              }}
            >
              {currentAccount?.currency || 'VND'}
            </span>
          </div>

          {/* Chọn Loại Giao Dịch */}
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

          {/* Chọn Danh Mục */}
          <div>
            <label
              htmlFor="edit-tx-category"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <Tag size={15} color="#ec4899" />
              <span>Danh mục {type === 'income' ? 'thu nhập' : 'chi tiêu'}</span>
            </label>
            <select
              id="edit-tx-category"
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
          </div>

          {/* Số Tiền */}
          <div>
            <label
              htmlFor="edit-tx-amount"
              style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              Số tiền ({currentAccount?.currency || 'VND'}) <span style={{ color: 'var(--error)' }}>*</span>
            </label>
            <input
              id="edit-tx-amount"
              type="text"
              inputMode="decimal"
              placeholder="Ví dụ: 150000"
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
          </div>

          {/* Thời Gian Phát Sinh */}
          <div>
            <label
              htmlFor="edit-tx-occurred-at"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <Calendar size={15} color="var(--primary-500)" />
              <span>Thời gian phát sinh</span>
            </label>
            <input
              id="edit-tx-occurred-at"
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
              htmlFor="edit-tx-note"
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}
            >
              <FileText size={15} color="var(--text-sub)" />
              <span>Ghi chú (tùy chọn)</span>
            </label>
            <input
              id="edit-tx-note"
              type="text"
              maxLength={255}
              placeholder="Ghi chú giao dịch..."
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
              disabled={loading}
              style={{
                padding: '10px 22px',
                background: 'var(--primary-gradient)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
                boxShadow: 'var(--shadow-button)',
              }}
            >
              {loading ? 'Đang lưu...' : 'Lưu Thay Đổi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
