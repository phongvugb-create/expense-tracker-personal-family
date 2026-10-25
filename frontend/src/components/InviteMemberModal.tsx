import { useState, useEffect } from 'react';
import { X, Mail, ShieldAlert, Copy, Check, Clock, UserPlus } from 'lucide-react';
import type { FamilyInvitation } from '../types/family';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';

interface InviteMemberModalProps {
  familyId: string;
  familyName: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function InviteMemberModal({
  familyId,
  familyName,
  isOpen,
  onClose,
  onSuccess,
}: InviteMemberModalProps) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'editor' | 'viewer'>('editor');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lưu trữ kết quả tạo thành công để hiển thị token copy
  const [createdInvitation, setCreatedInvitation] = useState<FamilyInvitation | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setEmail('');
      setRole('editor');
      setError(null);
      setCreatedInvitation(null);
      setCopied(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError('Vui lòng nhập địa chỉ email người được mời.');
      return;
    }

    try {
      setLoading(true);
      const invitation = await familyService.createInvitation(familyId, {
        invited_email: email.trim(),
        role,
      });
      setCreatedInvitation(invitation);
      onSuccess();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCopyToken = () => {
    if (createdInvitation?.invitation_token) {
      void navigator.clipboard.writeText(createdInvitation.invitation_token);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
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
          maxWidth: '500px',
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
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#818cf8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <UserPlus size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Mời thành viên mới</h2>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                Tham gia nhóm: <strong>{familyName}</strong>
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

        {/* Success Alert with Dev Token */}
        {createdInvitation ? (
          <div>
            <div
              style={{
                background: 'var(--income-soft)',
                border: '1px solid #BCE2CE',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                marginBottom: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--success)', fontWeight: 600, fontSize: '0.95rem', marginBottom: '8px' }}>
                <Check size={18} />
                <span>Đã phát hành lời mời thành công!</span>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
                Hệ thống đã ghi nhận lời mời cho email <strong>{createdInvitation.invited_email}</strong> với vai trò{' '}
                <strong>{createdInvitation.role === 'editor' ? 'Biên tập viên' : 'Người xem'}</strong>.
              </p>
            </div>

            {/* Chế độ Demo / Dev: Hiển thị Token */}
            {createdInvitation.invitation_token ? (
              <div
                style={{
                  background: 'rgba(99, 102, 241, 0.08)',
                  border: '1px solid rgba(99, 102, 241, 0.25)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                  marginBottom: '20px',
                }}
              >
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                  MÃ TOKEN LỜI MỜI (MÔI TRƯỜNG DEMO / PHÁT TRIỂN)
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '10px', lineHeight: 1.4 }}>
                  Do chưa cấu hình dịch vụ gửi email SMTP thực tế, bạn có thể sao chép mã token bên dưới và chia sẻ cho người được mời để họ nhập tại mục <strong>&quot;Chấp nhận lời mời&quot;</strong>.
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    background: 'rgba(0, 0, 0, 0.4)',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <code
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '0.8rem',
                      color: 'var(--secondary)',
                      wordBreak: 'break-all',
                      flex: 1,
                    }}
                  >
                    {createdInvitation.invitation_token}
                  </code>
                  <button
                    onClick={handleCopyToken}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '6px 12px',
                      borderRadius: 'var(--radius-sm)',
                      background: copied ? 'var(--success-bg)' : 'rgba(59, 130, 246, 0.2)',
                      border: `1px solid ${copied ? 'var(--success-border)' : 'rgba(59, 130, 246, 0.4)'}`,
                      color: copied ? 'var(--success)' : '#93c5fd',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      flexShrink: 0,
                    }}
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '10px', fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  <Clock size={12} />
                  <span>
                    Hạn hiệu lực: {new Date(createdInvitation.expires_at).toLocaleString('vi-VN')}
                  </span>
                </div>
              </div>
            ) : (
              <div
                style={{
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px',
                  marginBottom: '20px',
                  fontSize: '0.85rem',
                  color: 'var(--text-muted)',
                  lineHeight: 1.5,
                }}
              >
                Hệ thống đang chạy chế độ sản xuất bảo mật (không trả mã token thô). Hiện tại dịch vụ gửi email tự động (SMTP) chưa được cấu hình trong hệ thống, do đó email kích hoạt chưa được gửi tự động.
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={onClose}
                className="btn-primary"
                style={{ padding: '8px 20px', fontSize: '0.875rem' }}
              >
                Hoàn tất
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="invite-email">
                Địa chỉ email người nhận <span style={{ color: 'var(--error)' }}>*</span>
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={16}
                  style={{
                    position: 'absolute',
                    left: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-sub)',
                  }}
                />
                <input
                  id="invite-email"
                  type="email"
                  className="form-input"
                  style={{ paddingLeft: '38px' }}
                  placeholder="vidu@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginTop: '6px' }}>
                Người nhận cần có tài khoản đã đăng ký trên hệ thống với địa chỉ email này để chấp nhận lời mời.
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Vai trò đề xuất</label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => setRole('editor')}
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-md)',
                    background:
                      role === 'editor'
                        ? 'rgba(59, 130, 246, 0.18)'
                        : 'var(--surface-muted)',
                    border: `1px solid ${
                      role === 'editor' ? 'var(--primary-500)' : 'var(--border)'
                    }`,
                    color: role === 'editor' ? 'var(--primary)' : 'var(--text-muted)',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: '2px' }}>Biên tập viên (Editor)</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 400 }}>
                    Được quyền tạo ví gia đình, ghi thu chi và mời thành viên khác.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setRole('viewer')}
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-md)',
                    background:
                      role === 'viewer'
                        ? 'rgba(99, 102, 241, 0.18)'
                        : 'var(--surface-muted)',
                    border: `1px solid ${
                      role === 'viewer' ? '#818cf8' : 'var(--border)'
                    }`,
                    color: role === 'viewer' ? 'var(--secondary)' : 'var(--text-muted)',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: '2px' }}>Người xem (Viewer)</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 400 }}>
                    Chỉ có quyền xem thông tin chi tiêu và số dư, không được sửa đổi.
                  </div>
                </button>
              </div>
            </div>

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
                id="submit-create-invitation-btn"
                type="submit"
                disabled={loading}
                className="btn-primary"
                style={{ padding: '10px 22px' }}
              >
                {loading ? 'Đang gửi lời mời...' : 'Tạo lời mời'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
