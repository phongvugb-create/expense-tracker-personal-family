import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, ShieldAlert, ArrowLeft, CheckCircle2, Users } from 'lucide-react';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';

export function AcceptInvitationPage() {
  const navigate = useNavigate();
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<{
    display_name: string;
    role: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanToken = token.trim();
    if (!cleanToken) {
      setError('Vui lòng nhập mã token lời mời.');
      return;
    }

    try {
      setLoading(true);
      const member = await familyService.acceptInvitation({ token: cleanToken });
      setSuccessResult({
        display_name: member.display_name,
        role: member.role === 'editor' ? 'Biên tập viên' : 'Người xem',
      });
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)' }}>
      {/* Header */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(12px)',
          position: 'sticky',
          top: 0,
          zIndex: 40,
        }}
      >
        <div
          style={{
            maxWidth: '800px',
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <button
            onClick={() => navigate('/families')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface-muted)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            <ArrowLeft size={16} />
            <span>Danh sách gia đình</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={18} color="#818cf8" />
            <span style={{ fontSize: '0.9rem', fontWeight: 700 }}>Không Gian Gia Đình</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '580px', margin: '48px auto', padding: '0 24px' }}>
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '36px',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          {/* Title Area */}
          <div style={{ textAlign: 'center', marginBottom: '28px' }}>
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '16px',
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#818cf8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <KeyRound size={26} />
            </div>
            <h1 style={{ fontSize: '1.45rem', fontWeight: 800, marginBottom: '8px' }}>
              Chấp nhận lời mời gia đình
            </h1>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.875rem', lineHeight: 1.5, margin: 0 }}>
              Nhập mã token bảo mật do chủ nhóm hoặc biên tập viên chia sẻ để gia nhập không gian quản lý chi tiêu chung.
            </p>
          </div>

          {/* Success State */}
          {successResult ? (
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  background: 'var(--income-soft)',
                  border: '1px solid #BCE2CE',
                  borderRadius: 'var(--radius-md)',
                  padding: '24px',
                  marginBottom: '28px',
                }}
              >
                <CheckCircle2 size={40} color="var(--success)" style={{ margin: '0 auto 12px' }} />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--income)', marginBottom: '6px' }}>
                  Gia nhập thành công!
                </h3>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
                  Bạn đã tham gia nhóm gia đình với vai trò <strong>{successResult.role}</strong>. Bây giờ bạn có thể xem các ví dùng chung hoặc khởi tạo ví mới theo quyền hạn.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                <button
                  onClick={() => navigate('/families')}
                  className="btn-primary"
                  style={{ padding: '10px 24px' }}
                >
                  Xem danh sách gia đình
                </button>
                <button
                  onClick={() => navigate('/accounts')}
                  style={{
                    padding: '10px 20px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--surface-muted)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Quản lý ví
                </button>
              </div>
            </div>
          ) : (
            <>
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
                <div className="form-group">
                  <label className="form-label" htmlFor="invitation-token-input">
                    Mã token lời mời <span style={{ color: 'var(--error)' }}>*</span>
                  </label>
                  <input
                    id="invitation-token-input"
                    type="text"
                    className="form-input"
                    placeholder="Dán mã token (VD: sX8f...)"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    disabled={loading}
                    autoComplete="off"
                    required
                  />
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginTop: '6px', lineHeight: 1.4 }}>
                    Lưu ý: Địa chỉ email của tài khoản đang đăng nhập hiện tại phải trùng khớp hoàn toàn với email mà người mời đã đăng ký.
                  </div>
                </div>

                <button
                  id="submit-accept-invitation-btn"
                  type="submit"
                  disabled={loading}
                  className="btn-primary"
                  style={{ width: '100%', padding: '12px', marginTop: '12px', fontSize: '0.95rem' }}
                >
                  {loading ? 'Đang xác thực mã...' : 'Xác nhận gia nhập nhóm'}
                </button>
              </form>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
