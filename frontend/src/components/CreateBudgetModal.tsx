import { useState, useEffect, useMemo } from 'react';
import {
  X,
  PieChart,
  Layers,
  Users,
  Tag,
  DollarSign,
  Calendar,
  AlertCircle,
  Percent,
} from 'lucide-react';
import type { Category } from '../types/category';
import type { Family } from '../types/family';
import type { Budget, BudgetCreateRequest, BudgetScope } from '../types/budget';
import { budgetService } from '../services/budgetService';
import { getErrorMessage } from '../services/apiClient';

interface CreateBudgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (budget: Budget) => void;
  categories: Category[];
  families: Family[];
}

export function CreateBudgetModal({
  isOpen,
  onClose,
  onSuccess,
  categories,
  families,
}: CreateBudgetModalProps) {
  const [name, setName] = useState('');
  const [scope, setScope] = useState<BudgetScope>('personal');
  const [familyId, setFamilyId] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [amountLimit, setAmountLimit] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [warningThreshold, setWarningThreshold] = useState('80');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lọc các gia đình mà user có quyền owner hoặc editor
  const writableFamilies = useMemo(() => {
    return families.filter((f) => f.my_role === 'owner' || f.my_role === 'editor');
  }, [families]);

  // Khởi tạo ngày mặc định: ngày đầu tháng và cuối tháng hiện tại
  useEffect(() => {
    if (isOpen) {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth();

      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);

      const toISO = (d: Date) => d.toISOString().split('T')[0];

      setPeriodStart(toISO(firstDay));
      setPeriodEnd(toISO(lastDay));
      setAmountLimit('');
      setName('');
      setWarningThreshold('80');
      setError(null);
    }
  }, [isOpen]);

  // Tự động chọn family đầu tiên nếu chuyển sang scope family
  useEffect(() => {
    if (scope === 'family' && writableFamilies.length > 0 && !familyId) {
      setFamilyId(writableFamilies[0].id);
    }
  }, [scope, writableFamilies, familyId]);

  // Lọc danh mục hợp lệ theo scope và family đã chọn
  const compatibleCategories = useMemo(() => {
    return categories.filter((cat) => {
      // Chỉ lấy danh mục loại expense và chưa bị lưu trữ
      if (cat.type !== 'expense' || cat.is_archived) return false;

      if (scope === 'personal') {
        return cat.scope === 'system' || cat.scope === 'personal';
      } else {
        return (
          cat.scope === 'system' ||
          (cat.scope === 'family' && familyId && cat.family_id === familyId)
        );
      }
    });
  }, [categories, scope, familyId]);

  // Tự động chọn danh mục đầu tiên khi danh sách compatible categories thay đổi
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

    if (!categoryId) {
      setError('Vui lòng chọn danh mục chi tiêu hợp lệ.');
      return;
    }

    if (scope === 'family' && !familyId) {
      setError('Vui lòng chọn nhóm gia đình cho ngân sách.');
      return;
    }

    try {
      setLoading(true);
      const payload: BudgetCreateRequest = {
        name: name.trim() || undefined,
        scope,
        category_id: categoryId,
        amount_limit: numLimit.toFixed(2),
        period_start: periodStart,
        period_end: periodEnd,
        warning_threshold: numThreshold.toFixed(2),
        ...(scope === 'family' ? { family_id: familyId } : {}),
      };

      const newBudget = await budgetService.createBudget(payload);
      onSuccess(newBudget);
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
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Tạo Ngân Sách Mới</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)', margin: 0 }}>
                Thiết lập hạn mức chi tiêu định kỳ và ngưỡng cảnh báo
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

          {/* Scope selection */}
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
              <Layers size={14} style={{ display: 'inline', marginRight: '6px' }} />
              Phạm vi ngân sách
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                onClick={() => setScope('personal')}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background:
                    scope === 'personal' ? 'rgba(59, 130, 246, 0.2)' : 'var(--surface-muted)',
                  border: `1px solid ${
                    scope === 'personal' ? 'var(--primary-500)' : 'var(--border)'
                  }`,
                  color: scope === 'personal' ? 'var(--primary)' : 'var(--text-sub)',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Cá nhân
              </button>
              <button
                type="button"
                onClick={() => setScope('family')}
                style={{
                  flex: 1,
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  background:
                    scope === 'family' ? 'rgba(99, 102, 241, 0.2)' : 'var(--surface-muted)',
                  border: `1px solid ${
                    scope === 'family' ? 'rgba(99, 102, 241, 0.6)' : 'var(--border)'
                  }`,
                  color: scope === 'family' ? 'var(--secondary)' : 'var(--text-sub)',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Gia đình
              </button>
            </div>
          </div>

          {/* Family dropdown (nếu scope family) */}
          {scope === 'family' && (
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
                <Users size={14} style={{ display: 'inline', marginRight: '6px' }} />
                Chọn nhóm gia đình *
              </label>
              {writableFamilies.length > 0 ? (
                <select
                  value={familyId}
                  onChange={(e) => setFamilyId(e.target.value)}
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
                  {writableFamilies.map((fam) => (
                    <option key={fam.id} value={fam.id}>
                      {fam.name} ({fam.my_role === 'owner' ? 'Trưởng nhóm' : 'Biên tập viên'})
                    </option>
                  ))}
                </select>
              ) : (
                <div
                  style={{
                    padding: '10px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid #F5BAC2',
                    color: 'var(--danger)',
                    fontSize: '0.85rem',
                  }}
                >
                  Bạn không có quyền quản trị hoặc tạo ngân sách trong nhóm gia đình nào (yêu cầu vai
                  trò Owner hoặc Editor).
                </div>
              )}
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
              Tên ngân sách (tùy chọn)
            </label>
            <input
              type="text"
              placeholder="Ví dụ: Ăn uống gia đình tháng 10, Tiền xăng xe..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
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

          {/* Category Selection */}
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
            {compatibleCategories.length > 0 ? (
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
            ) : (
              <div
                style={{
                  padding: '10px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid #F5BAC2',
                  color: 'var(--danger)',
                  fontSize: '0.85rem',
                }}
              >
                Không tìm thấy danh mục chi tiêu khả dụng cho phạm vi này.
              </div>
            )}
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
              placeholder="Nhập số tiền hạn mức (VD: 5000000)"
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

          {/* Warning threshold */}
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
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                color: 'var(--text-sub)',
                marginTop: '4px',
              }}
            >
              <span>10% (Sớm)</span>
              <span>80% (Khuyến nghị)</span>
              <span>100% (Khi cạn tiền)</span>
            </div>
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
              disabled={loading || (scope === 'family' && writableFamilies.length === 0)}
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
              {loading ? 'Đang tạo...' : 'Xác nhận tạo ngân sách'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
