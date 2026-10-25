import { useState, useEffect, useMemo } from 'react';
import {
  X,
  PieChart,
  Tag,
  DollarSign,
  Calendar,
  AlertCircle,
  Percent,
} from 'lucide-react';
import type { Category } from '../types/category';
import type { Budget, BudgetUpdateRequest } from '../types/budget';
import { budgetService } from '../services/budgetService';
import { getErrorMessage } from '../services/apiClient';

interface EditBudgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (budget: Budget) => void;
  budget: Budget | null;
  categories: Category[];
}

export function EditBudgetModal({
  isOpen,
  onClose,
  onSuccess,
  budget,
  categories,
}: EditBudgetModalProps) {
  const [name, setName] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [amountLimit, setAmountLimit] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [warningThreshold, setWarningThreshold] = useState('80');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Điền dữ liệu ban đầu khi modal mở
  useEffect(() => {
    if (isOpen && budget) {
      setName(budget.name || '');
      setCategoryId(budget.category_id);
      setAmountLimit(budget.amount_limit);
      setPeriodStart(budget.period_start);
      setPeriodEnd(budget.period_end);
      setWarningThreshold(String(Math.round(Number(budget.warning_threshold))));
      setError(null);
    }
  }, [isOpen, budget]);

  // Lọc danh mục hợp lệ theo scope của ngân sách đang chỉnh sửa
  const compatibleCategories = useMemo(() => {
    if (!budget) return [];
    return categories.filter((cat) => {
      if (cat.type !== 'expense' || cat.is_archived) return false;

      if (budget.scope === 'personal') {
        return cat.scope === 'system' || cat.scope === 'personal';
      } else {
        return (
          cat.scope === 'system' ||
          (cat.scope === 'family' && budget.family_id && cat.family_id === budget.family_id)
        );
      }
    });
  }, [categories, budget]);

  if (!isOpen || !budget) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    const cleanAmount = amountLimit.trim();
    if (!cleanAmount) {
      setError('Vui lòng nhập hạn mức ngân sách.');
      return;
    }
    const numLimit = Number(cleanAmount);
    if (isNaN(numLimit) || numLimit <= 0) {
      setError('Hạn mức ngân sách phải là số lớn hơn 0.');
      return;
    }

    if (!periodStart || !periodEnd) {
      setError('Vui lòng chọn ngày bắt đầu và kết thúc kỳ ngân sách.');
      return;
    }
    if (periodEnd < periodStart) {
      setError('Ngày kết thúc kỳ ngân sách không được trước ngày bắt đầu.');
      return;
    }

    const numThreshold = Number(warningThreshold);
    if (isNaN(numThreshold) || numThreshold <= 0 || numThreshold > 100) {
      setError('Ngưỡng cảnh báo phải nằm trong khoảng từ 1% đến 100%.');
      return;
    }

    try {
      setLoading(true);
      const payload: BudgetUpdateRequest = {
        name: name.trim() || undefined,
        category_id: categoryId,
        amount_limit: numLimit.toFixed(2),
        period_start: periodStart,
        period_end: periodEnd,
        warning_threshold: numThreshold.toFixed(2),
      };

      const updatedBudget = await budgetService.updateBudget(budget.id, payload);
      onSuccess(updatedBudget);
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
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: '16px',
      }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '540px',
          boxShadow: 'var(--shadow-modal)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '18px 24px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--surface-muted)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'var(--secondary-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary-500)',
              }}
            >
              <PieChart size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Chỉnh Sửa Ngân Sách</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)', margin: 0 }}>
                Cập nhật hạn mức, kỳ ngân sách hoặc danh mục
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
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '24px' }}>
          {error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--error-bg)',
                border: '1px solid var(--error-border)',
                color: 'var(--error)',
                fontSize: '0.875rem',
                marginBottom: '18px',
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Budget Name */}
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: 'var(--text-main)',
                marginBottom: '6px',
              }}
            >
              Tên gợi nhớ ngân sách
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              placeholder="Tên gợi nhớ..."
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
            />
          </div>

          {/* Category */}
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: 'var(--text-main)',
                marginBottom: '6px',
              }}
            >
              <Tag size={14} style={{ display: 'inline', marginRight: '6px' }} />
              Danh mục chi tiêu *
            </label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
              required
            >
              {compatibleCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name} ({cat.scope === 'system' ? 'Hệ thống' : cat.scope === 'family' ? 'Gia đình' : 'Cá nhân'})
                </option>
              ))}
            </select>
          </div>

          {/* Amount Limit */}
          <div style={{ marginBottom: '16px' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.85rem',
                fontWeight: 600,
                color: 'var(--text-main)',
                marginBottom: '6px',
              }}
            >
              <DollarSign size={14} style={{ display: 'inline', marginRight: '6px' }} />
              Hạn mức ngân sách (VND) *
            </label>
            <input
              type="number"
              step="any"
              min="1"
              value={amountLimit}
              onChange={(e) => setAmountLimit(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                outline: 'none',
              }}
              required
            />
          </div>

          {/* Date range */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: 'var(--text-main)',
                  marginBottom: '6px',
                }}
              >
                <Calendar size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Ngày bắt đầu *
              </label>
              <input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
                required
              />
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: 'var(--text-main)',
                  marginBottom: '6px',
                }}
              >
                <Calendar size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Ngày kết thúc *
              </label>
              <input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
                required
              />
            </div>
          </div>

          {/* Warning Threshold */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label
                style={{
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  color: 'var(--text-main)',
                }}
              >
                <Percent size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Ngưỡng cảnh báo chi tiêu (%)
              </label>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f59e0b' }}>
                {warningThreshold}%
              </span>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              step="5"
              value={warningThreshold}
              onChange={(e) => setWarningThreshold(e.target.value)}
              style={{
                width: '100%',
                cursor: 'pointer',
              }}
            />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: '10px 18px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
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
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#fff',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1,
                boxShadow: 'var(--shadow-button)',
              }}
            >
              {loading ? 'Đang lưu...' : 'Lưu thay đổi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
