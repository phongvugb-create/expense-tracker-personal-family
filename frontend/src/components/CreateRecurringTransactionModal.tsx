import { useState, useEffect, useMemo } from 'react';
import {
  X,
  Repeat,
  Wallet,
  Tag,
  DollarSign,
  Calendar,
  AlertCircle,
  Clock,
  ArrowDownRight,
  ArrowUpRight,
  FileText,
} from 'lucide-react';
import type { Account } from '../types/account';
import type { Category } from '../types/category';
import type {
  RecurringTransaction,
  RecurringTransactionCreateRequest,
  RecurringTransactionType,
  RecurrenceFrequency,
} from '../types/recurringTransaction';
import { recurringTransactionService } from '../services/recurringTransactionService';
import { getErrorMessage } from '../services/apiClient';

interface CreateRecurringTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (rule: RecurringTransaction) => void;
  accounts: Account[];
  categories: Category[];
}

export function CreateRecurringTransactionModal({
  isOpen,
  onClose,
  onSuccess,
  accounts,
  categories,
}: CreateRecurringTransactionModalProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState<RecurringTransactionType>('expense');
  const [accountId, setAccountId] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [frequency, setFrequency] = useState<RecurrenceFrequency>('monthly');
  const [intervalValue, setIntervalValue] = useState('1');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [note, setNote] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lọc các ví khả dụng (chỉ các ví không lưu trữ)
  const availableAccounts = useMemo(() => {
    return accounts.filter((acc) => !acc.is_archived);
  }, [accounts]);

  // Ví được chọn hiện tại
  const selectedAccount = useMemo(() => {
    return availableAccounts.find((a) => a.id === accountId);
  }, [availableAccounts, accountId]);

  // Lọc danh mục theo loại (income / expense)
  const filteredCategories = useMemo(() => {
    return categories.filter((c) => c.type === type);
  }, [categories, type]);

  // Thiết lập giá trị khởi tạo khi mở modal
  useEffect(() => {
    if (isOpen) {
      const today = new Date().toISOString().split('T')[0];
      setName('');
      setType('expense');
      setAmount('');
      setFrequency('monthly');
      setIntervalValue('1');
      setStartDate(today);
      setEndDate('');
      setNote('');
      setError(null);

      if (availableAccounts.length > 0) {
        setAccountId(availableAccounts[0].id);
      }
    }
  }, [isOpen, availableAccounts]);

  // Tự động chọn category hợp lệ đầu tiên khi đổi type
  useEffect(() => {
    if (filteredCategories.length > 0) {
      const exists = filteredCategories.some((c) => c.id === categoryId);
      if (!exists) {
        setCategoryId(filteredCategories[0].id);
      }
    } else {
      setCategoryId('');
    }
  }, [type, filteredCategories, categoryId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Vui lòng nhập tên quy tắc');
      return;
    }

    if (!accountId) {
      setError('Vui lòng chọn ví tài khoản');
      return;
    }

    if (!categoryId) {
      setError('Vui lòng chọn danh mục hợp lệ');
      return;
    }

    const numAmount = parseFloat(amount.replace(/,/g, ''));
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Số tiền phải là số dương lớn hơn 0');
      return;
    }

    const numInterval = parseInt(intervalValue, 10);
    if (isNaN(numInterval) || numInterval < 1) {
      setError('Khoảng lặp phải là số nguyên dương (>= 1)');
      return;
    }

    if (!startDate) {
      setError('Vui lòng chọn ngày bắt đầu');
      return;
    }

    if (endDate && endDate < startDate) {
      setError('Ngày kết thúc không được trước ngày bắt đầu');
      return;
    }

    try {
      setLoading(true);
      const payload: RecurringTransactionCreateRequest = {
        name: name.trim(),
        type,
        account_id: accountId,
        category_id: categoryId,
        amount: numAmount.toString(),
        frequency,
        interval_value: numInterval,
        start_date: startDate,
        end_date: endDate ? endDate : null,
        note: note.trim() ? note.trim() : null,
        scope: selectedAccount?.scope || 'personal',
        family_id: selectedAccount?.family_id || null,
      };

      const newRule = await recurringTransactionService.createRecurringTransaction(payload);
      onSuccess(newRule);
      onClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-dialog">
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '18px 24px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--surface-muted)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: 'var(--primary-gradient)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-button)',
              }}
            >
              <Repeat size={18} color="#fff" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-0.01em' }}>
                Thêm Quy Tắc Thu / Chi Định Kỳ
              </h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                Tự động lên lịch các khoản thu chi lặp lại
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-sub)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form
          onSubmit={handleSubmit}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {error && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--error-bg)',
                border: '1px solid var(--error-border)',
                color: 'var(--danger)',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Loại giao dịch: Thu hoặc Chi */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '8px',
              }}
            >
              Loại Giao Dịch
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
                  border: type === 'expense' ? '1px solid #ef4444' : '1px solid var(--bg-input-border)',
                  background: type === 'expense' ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-input)',
                  color: type === 'expense' ? '#f87171' : 'var(--text-muted)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <ArrowDownRight size={16} />
                <span>Khoản Chi (Expense)</span>
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
                  border: type === 'income' ? '1px solid #10b981' : '1px solid var(--bg-input-border)',
                  background: type === 'income' ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-input)',
                  color: type === 'income' ? '#6ee7b7' : 'var(--text-muted)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <ArrowUpRight size={16} />
                <span>Khoản Thu (Income)</span>
              </button>
            </div>
          </div>

          {/* Tên quy tắc */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '8px',
              }}
            >
              Tên Quy Tắc *
            </label>
            <input
              type="text"
              placeholder="VD: Tiền thuê nhà hàng tháng, Nhận lương..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Ví và Danh mục */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                }}
              >
                <Wallet size={14} />
                <span>Ví Tài Khoản *</span>
              </label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                {availableAccounts.length === 0 && (
                  <option value="">Không có ví khả dụng</option>
                )}
                {availableAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.scope === 'family' ? 'Gia đình' : 'Cá nhân'}) - {acc.currency}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                }}
              >
                <Tag size={14} />
                <span>Danh Mục *</span>
              </label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                {filteredCategories.length === 0 && (
                  <option value="">Chưa có danh mục phù hợp</option>
                )}
                {filteredCategories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Số tiền */}
          <div>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '8px',
              }}
            >
              <DollarSign size={14} />
              <span>Số Tiền Mỗi Kỳ ({selectedAccount?.currency || 'VND'}) *</span>
            </label>
            <input
              type="number"
              min="0"
              step="any"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.95rem',
                fontWeight: 600,
                outline: 'none',
              }}
            />
          </div>

          {/* Chu kỳ lặp và Khoảng lặp */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                }}
              >
                <Clock size={14} />
                <span>Chu Kỳ Lặp</span>
              </label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value as RecurrenceFrequency)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="daily">Hàng Ngày</option>
                <option value="weekly">Hàng Tuần</option>
                <option value="monthly">Hàng Tháng</option>
                <option value="yearly">Hàng Năm</option>
              </select>
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                }}
              >
                Mỗi (Khoảng lặp)
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={intervalValue}
                  onChange={(e) => setIntervalValue(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '10px 14px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--bg-input-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--text-main)',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', minWidth: '40px' }}>
                  {frequency === 'daily' && 'ngày'}
                  {frequency === 'weekly' && 'tuần'}
                  {frequency === 'monthly' && 'tháng'}
                  {frequency === 'yearly' && 'năm'}
                </span>
              </div>
            </div>
          </div>

          {/* Ngày bắt đầu & Ngày kết thúc */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                }}
              >
                <Calendar size={14} />
                <span>Ngày Bắt Đầu *</span>
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '8px',
                }}
              >
                Ngày Kết Thúc (Tùy chọn)
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Ghi chú */}
          <div>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--text-muted)',
                marginBottom: '8px',
              }}
            >
              <FileText size={14} />
              <span>Ghi Chú (Tùy chọn)</span>
            </label>
            <textarea
              rows={2}
              placeholder="Ghi chú thêm về quy tắc..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
                resize: 'none',
              }}
            />
          </div>

          {/* Footer Actions */}
          <div
            style={{
              paddingTop: '16px',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '12px',
            }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: '9px 18px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
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
                padding: '9px 20px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-button)',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Đang tạo...' : 'Tạo Quy Tắc'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
