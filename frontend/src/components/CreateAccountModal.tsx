import { useState, useEffect } from 'react';
import { X, Wallet, ShieldAlert, Users, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AccountCreateRequest, AccountScope, AccountType } from '../types/account';
import type { Family } from '../types/family';
import { accountService } from '../services/accountService';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';

interface CreateAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateAccountModal({ isOpen, onClose, onSuccess }: CreateAccountModalProps) {
  const [name, setName] = useState('');
  const [scope, setScope] = useState<AccountScope>('personal');
  const [accountType, setAccountType] = useState<AccountType>('cash');
  const [currency, setCurrency] = useState('VND');
  const [initialBalance, setInitialBalance] = useState('0');
  const [familyId, setFamilyId] = useState('');

  const [families, setFamilies] = useState<Family[]>([]);
  const [loadingFamilies, setLoadingFamilies] = useState(false);
  const [familyError, setFamilyError] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Khi modal mở và scope là family, tải danh sách nhóm gia đình thực tế từ backend
  useEffect(() => {
    if (isOpen && scope === 'family') {
      const fetchFamilies = async () => {
        try {
          setLoadingFamilies(true);
          setFamilyError(null);
          const data = await familyService.getFamilies();
          // Lọc các nhóm mà user có quyền quản trị tạo ví (owner hoặc editor)
          setFamilies(data);
          // Tự động chọn nhóm đầu tiên nếu có nhóm phù hợp
          const validFamilies = data.filter((f) => f.my_role === 'owner' || f.my_role === 'editor');
          if (validFamilies.length > 0 && !familyId) {
            setFamilyId(validFamilies[0].id);
          }
        } catch (err: unknown) {
          setFamilyError(getErrorMessage(err));
        } finally {
          setLoadingFamilies(false);
        }
      };
      void fetchFamilies();
    }
  }, [isOpen, scope, familyId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Vui lòng nhập tên ví.');
      return;
    }

    if (scope === 'family') {
      if (!familyId.trim()) {
        setError('Vui lòng chọn một nhóm gia đình mà bạn có quyền quản trị (Owner hoặc Editor).');
        return;
      }
      const selected = families.find((f) => f.id === familyId);
      if (selected && selected.my_role === 'viewer') {
        setError('Bạn chỉ có vai trò Viewer trong nhóm này nên không có quyền tạo ví gia đình.');
        return;
      }
    }

    // Validate decimal balance
    const cleanBalance = initialBalance.trim() || '0';
    if (isNaN(Number(cleanBalance))) {
      setError('Số dư ban đầu không hợp lệ (phải là số thập phân hoặc số nguyên).');
      return;
    }

    const payload: AccountCreateRequest = {
      name: name.trim(),
      scope,
      account_type: accountType,
      currency: currency.trim().toUpperCase() || 'VND',
      initial_balance: cleanBalance,
      family_id: scope === 'family' ? familyId.trim() : null,
    };

    try {
      setLoading(true);
      await accountService.createAccount(payload);
      // Reset form
      setName('');
      setScope('personal');
      setAccountType('cash');
      setCurrency('VND');
      setInitialBalance('0');
      setFamilyId('');
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
          maxWidth: '520px',
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
            borderBottom: '1px solid var(--border)',
            paddingBottom: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'var(--secondary-soft)',
                color: 'var(--primary-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Wallet size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Tạo ví tài khoản mới</h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                Thiết lập ví cá nhân hoặc ví dùng chung cho gia đình
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
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
              alignItems: 'flex-start',
              gap: '10px',
              padding: '12px 16px',
              background: 'var(--error-bg)',
              border: '1px solid var(--error-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--danger)',
              fontSize: '0.875rem',
              marginBottom: '20px',
            }}
          >
            <ShieldAlert size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>{error}</div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Tên ví */}
          <div className="form-group">
            <label className="form-label" htmlFor="create-account-name">
              Tên ví <span style={{ color: 'var(--error)' }}>*</span>
            </label>
            <input
              id="create-account-name"
              type="text"
              className="form-input"
              placeholder="VD: Tiền mặt hàng ngày, Techcombank, Ví MoMo..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              maxLength={100}
              required
            />
          </div>

          {/* Scope: Cá nhân vs Gia đình */}
          <div className="form-group">
            <label className="form-label">Phạm vi sở hữu ví</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <button
                type="button"
                onClick={() => setScope('personal')}
                style={{
                  padding: '10px',
                  borderRadius: 'var(--radius-md)',
                  background:
                    scope === 'personal'
                      ? 'rgba(59, 130, 246, 0.18)'
                      : 'var(--surface-muted)',
                  border: `1px solid ${
                    scope === 'personal' ? 'var(--primary-500)' : 'var(--border)'
                  }`,
                  color: scope === 'personal' ? 'var(--primary)' : 'var(--text-muted)',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <span>Ví cá nhân</span>
              </button>

              <button
                type="button"
                onClick={() => setScope('family')}
                style={{
                  padding: '10px',
                  borderRadius: 'var(--radius-md)',
                  background:
                    scope === 'family'
                      ? 'rgba(99, 102, 241, 0.18)'
                      : 'var(--surface-muted)',
                  border: `1px solid ${
                    scope === 'family' ? '#818cf8' : 'var(--border)'
                  }`,
                  color: scope === 'family' ? 'var(--secondary)' : 'var(--text-muted)',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                }}
              >
                <span>Ví gia đình</span>
              </button>
            </div>
          </div>

          {/* Nếu chọn ví gia đình, yêu cầu chọn nhóm gia đình từ dropdown */}
          {scope === 'family' && (
            <div
              className="form-group"
              style={{
                background: 'rgba(99, 102, 241, 0.06)',
                padding: '14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label className="form-label" htmlFor="create-account-family-id" style={{ marginBottom: 0 }}>
                  Chọn nhóm gia đình <span style={{ color: 'var(--error)' }}>*</span>
                </label>
                <Link
                  to="/families"
                  target="_blank"
                  style={{
                    fontSize: '0.75rem',
                    color: '#818cf8',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    textDecoration: 'none',
                  }}
                >
                  <Users size={12} />
                  <span>Quản lý gia đình</span>
                  <ExternalLink size={10} />
                </Link>
              </div>

              {loadingFamilies ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--text-sub)', padding: '8px 0' }}>
                  Đang tải danh sách nhóm gia đình từ máy chủ...
                </div>
              ) : familyError ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--danger)', padding: '6px 0' }}>
                  Lỗi: {familyError}
                </div>
              ) : families.length === 0 ? (
                <div style={{ fontSize: '0.85rem', color: 'var(--warning)', padding: '6px 0', lineHeight: 1.5 }}>
                  Bạn chưa tham gia nhóm gia đình nào. Hãy{' '}
                  <Link to="/families" style={{ color: '#818cf8', fontWeight: 600 }}>
                    tạo nhóm mới
                  </Link>{' '}
                  hoặc chấp nhận lời mời trước khi tạo ví gia đình.
                </div>
              ) : (
                <>
                  <select
                    id="create-account-family-id"
                    className="form-input"
                    value={familyId}
                    onChange={(e) => setFamilyId(e.target.value)}
                    disabled={loading}
                    required
                  >
                    <option value="">-- Chọn nhóm gia đình --</option>
                    {families.map((fam) => {
                      const canManage = fam.my_role === 'owner' || fam.my_role === 'editor';
                      const roleLabel =
                        fam.my_role === 'owner'
                          ? 'Chủ sở hữu'
                          : fam.my_role === 'editor'
                          ? 'Biên tập viên'
                          : 'Người xem';
                      return (
                        <option key={fam.id} value={fam.id} disabled={!canManage}>
                          {fam.name} ({roleLabel}){canManage ? '' : ' - Không có quyền tạo ví'}
                        </option>
                      );
                    })}
                  </select>
                  <div
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-sub)',
                      marginTop: '6px',
                      lineHeight: 1.4,
                    }}
                  >
                    Dữ liệu được tải trực tiếp từ cơ sở dữ liệu PostgreSQL. Bạn cần có quyền <strong>Owner</strong> hoặc <strong>Editor</strong> trong nhóm để tạo ví dùng chung.
                  </div>
                </>
              )}
            </div>
          )}

          {/* Loại ví & Tiền tệ */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="create-account-type">
                Loại tài chính
              </label>
              <select
                id="create-account-type"
                className="form-input"
                value={accountType}
                onChange={(e) => setAccountType(e.target.value as AccountType)}
                disabled={loading}
              >
                <option value="cash">Tiền mặt</option>
                <option value="bank">Tài khoản ngân hàng</option>
                <option value="e_wallet">Ví điện tử</option>
                <option value="credit_card">Thẻ tín dụng</option>
                <option value="other">Khác</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="create-account-currency">
                Loại tiền tệ
              </label>
              <input
                id="create-account-currency"
                type="text"
                className="form-input"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                disabled={loading}
                maxLength={3}
                placeholder="VND"
                required
              />
            </div>
          </div>

          {/* Số dư ban đầu */}
          <div className="form-group">
            <label className="form-label" htmlFor="create-account-initial-balance">
              Số dư ban đầu ({currency})
            </label>
            <input
              id="create-account-initial-balance"
              type="text"
              inputMode="decimal"
              className="form-input"
              value={initialBalance}
              onChange={(e) => setInitialBalance(e.target.value)}
              disabled={loading}
              placeholder="0"
            />
            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginTop: '4px' }}>
              Số dư khởi tạo này sẽ làm mốc bắt đầu cho các báo cáo thu chi sau này.
            </div>
          </div>

          {/* Actions */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '12px',
              marginTop: '24px',
            }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: '10px 18px',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Hủy
            </button>

            <button
              id="submit-create-account-btn"
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ padding: '10px 22px' }}
            >
              {loading ? 'Đang tạo ví...' : 'Tạo ví mới'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
