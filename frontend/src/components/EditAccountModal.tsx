import { useState } from 'react';
import { X, Edit3, ShieldAlert } from 'lucide-react';
import type { Account, AccountType } from '../types/account';
import { accountService } from '../services/accountService';
import { getErrorMessage } from '../services/apiClient';

interface EditAccountModalProps {
  account: Account | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function EditAccountModal({ account, isOpen, onClose, onSuccess }: EditAccountModalProps) {
  const [name, setName] = useState(account?.name || '');
  const [accountType, setAccountType] = useState<AccountType>(account?.account_type || 'cash');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync state khi modal mở với account mới
  if (account && account.name !== name && !loading && !error && name === '') {
    setName(account.name);
    setAccountType(account.account_type);
  }

  if (!isOpen || !account) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Tên ví không được để trống.');
      return;
    }

    try {
      setLoading(true);
      await accountService.updateAccount(account.id, {
        name: name.trim(),
        account_type: accountType,
      });
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
          maxWidth: '480px',
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
                background: 'var(--warning-soft)',
                color: 'var(--warning)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Edit3 size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Chỉnh sửa ví</h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                Cập nhật thông tin nhận diện tài khoản
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
            <label className="form-label" htmlFor="edit-account-name">
              Tên ví <span style={{ color: 'var(--error)' }}>*</span>
            </label>
            <input
              id="edit-account-name"
              type="text"
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              maxLength={100}
              required
            />
          </div>

          {/* Phân loại tài chính */}
          <div className="form-group">
            <label className="form-label" htmlFor="edit-account-type">
              Loại tài chính
            </label>
            <select
              id="edit-account-type"
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

          {/* Các trường cố định không cho phép sửa trực tiếp */}
          <div
            style={{
              background: 'var(--surface-muted)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border)',
              fontSize: '0.8rem',
              color: 'var(--text-sub)',
              lineHeight: 1.5,
              marginBottom: '20px',
            }}
          >
            <div>
              Phạm vi: <strong>{account.scope === 'personal' ? 'Cá nhân' : 'Gia đình'}</strong>
            </div>
            <div>
              Tiền tệ: <strong>{account.currency}</strong> (cố định theo lịch sử hạch toán)
            </div>
            <div>
              Số dư ban đầu: <strong>{account.initial_balance} {account.currency}</strong>
            </div>
          </div>

          {/* Actions */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '12px',
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
              id="submit-edit-account-btn"
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ padding: '10px 22px' }}
            >
              {loading ? 'Đang lưu...' : 'Lưu thay đổi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
