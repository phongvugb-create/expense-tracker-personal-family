import { useState, useEffect, useMemo } from 'react';
import {
  X,
  Repeat,
  Tag,
  DollarSign,
  Calendar,
  AlertCircle,
  Clock,
  FileText,
} from 'lucide-react';
import type { Category } from '../types/category';
import type {
  RecurringTransaction,
  RecurringTransactionUpdateRequest,
  RecurrenceFrequency,
} from '../types/recurringTransaction';
import { recurringTransactionService } from '../services/recurringTransactionService';
import { getErrorMessage } from '../services/apiClient';

interface EditRecurringTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updated: RecurringTransaction) => void;
  rule: RecurringTransaction | null;
  categories: Category[];
}

export function EditRecurringTransactionModal({
  isOpen,
  onClose,
  onSuccess,
  rule,
  categories,
}: EditRecurringTransactionModalProps) {
  const [name, setName] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [amount, setAmount] = useState('');
  const [frequency, setFrequency] = useState<RecurrenceFrequency>('monthly');
  const [intervalValue, setIntervalValue] = useState('1');
  const [endDate, setEndDate] = useState('');
  const [note, setNote] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lọc danh mục tương thích với rule.type
  const filteredCategories = useMemo(() => {
    if (!rule) return [];
    return categories.filter((c) => c.type === rule.type);
  }, [categories, rule]);

  useEffect(() => {
    if (isOpen && rule) {
      setName(rule.name);
      setCategoryId(rule.category_id);
      setAmount(rule.amount);
      setFrequency(rule.frequency);
      setIntervalValue(rule.interval_value.toString());
      setEndDate(rule.end_date || '');
      setNote(rule.note || '');
      setIsActive(rule.is_active);
      setError(null);
    }
  }, [isOpen, rule]);

  if (!isOpen || !rule) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Vui lòng nhập tên quy tắc');
      return;
    }

    if (!categoryId) {
      setError('Vui lòng chọn danh mục');
      return;
    }

    const numAmount = parseFloat(amount.replace(/,/g, ''));
    if (isNaN(numAmount) || numAmount <= 0) {
      setError('Số tiền phải lớn hơn 0');
      return;
    }

    const numInterval = parseInt(intervalValue, 10);
    if (isNaN(numInterval) || numInterval < 1) {
      setError('Khoảng lặp phải là số nguyên dương (>= 1)');
      return;
    }

    if (endDate && endDate < rule.start_date) {
      setError('Ngày kết thúc không được trước ngày bắt đầu');
      return;
    }

    try {
      setLoading(true);
      const payload: RecurringTransactionUpdateRequest = {
        name: name.trim(),
        category_id: categoryId,
        amount: numAmount.toString(),
        frequency,
        interval_value: numInterval,
        end_date: endDate ? endDate : null,
        note: note.trim() ? note.trim() : null,
        is_active: isActive,
      };

      const updated = await recurringTransactionService.updateRecurringTransaction(rule.id, payload);
      onSuccess(updated);
      onClose();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !rule) return null;

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
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 14px rgba(245, 158, 11, 0.35)',
              }}
            >
              <Repeat size={18} color="#fff" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, letterSpacing: '-0.01em' }}>
                Chỉnh Sửa Quy Tắc Định Kỳ
              </h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                {rule.type === 'expense' ? 'Khoản chi' : 'Khoản thu'} • {rule.account_name} ({rule.currency})
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

          {/* Danh mục */}
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
              {filteredCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
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
              <span>Số Tiền Mỗi Kỳ ({rule.currency}) *</span>
            </label>
            <input
              type="number"
              min="0"
              step="any"
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

          {/* Chu kỳ lặp & khoảng lặp */}
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
                Khoảng Lặp
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={intervalValue}
                onChange={(e) => setIntervalValue(e.target.value)}
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

          {/* Ngày kết thúc */}
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
              <span>Ngày Kết Thúc (Tùy chọn)</span>
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
              <span>Ghi Chú</span>
            </label>
            <textarea
              rows={2}
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

          {/* Trạng thái hoạt động */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingTop: '4px' }}>
            <input
              type="checkbox"
              id="is_active_toggle"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              style={{ width: '16px', height: '16px', accentColor: 'var(--primary-500)', cursor: 'pointer' }}
            />
            <label htmlFor="is_active_toggle" style={{ fontSize: '0.85rem', color: 'var(--text-main)', cursor: 'pointer' }}>
              Quy tắc đang hoạt động (Bỏ chọn để tạm dừng)
            </label>
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
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 4px 14px rgba(245, 158, 11, 0.35)',
                opacity: loading ? 0.7 : 1,
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
