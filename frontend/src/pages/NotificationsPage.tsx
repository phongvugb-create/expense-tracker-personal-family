import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  ArrowLeft,
  RefreshCw,
  CheckCheck,
  Archive,
  Calendar,
  AlertTriangle,
  AlertCircle,
  Sparkles,
  ExternalLink,
  Search,
} from 'lucide-react';
import { notificationService } from '../services/notificationService';
import { getErrorMessage } from '../services/apiClient';
import type { NotificationItem, NotificationType } from '../types/notification';

export function NotificationsPage() {
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Filters
  const [filterType, setFilterType] = useState<string>('all');
  const [filterReadStatus, setFilterReadStatus] = useState<string>('all'); // all, unread, read
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Tự động tắt alert sau 4s
  useEffect(() => {
    if (actionMessage) {
      const timer = setTimeout(() => setActionMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [actionMessage]);

  // Tải danh sách thông báo
  const fetchNotifications = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      setError(null);
      const params: Parameters<typeof notificationService.getNotifications>[0] = {
        include_archived: includeArchived,
      };

      if (filterReadStatus === 'unread') {
        params.unread_only = true;
      }
      if (filterType !== 'all') {
        params.type = filterType as NotificationType;
      }

      const data = await notificationService.getNotifications(params);
      setNotifications(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      if (isInitial) setLoading(false);
    }
  }, [filterType, filterReadStatus, includeArchived]);

  // Đồng bộ với server và tải lại
  const handleSync = async () => {
    try {
      setSyncing(true);
      const syncRes = await notificationService.syncNotifications();
      setActionMessage({
        type: 'success',
        text: `Đồng bộ hoàn tất: Tạo mới ${syncRes.created_count}, Cập nhật ${syncRes.updated_count}.`,
      });
      window.dispatchEvent(new Event('notification-sync'));
      await fetchNotifications();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    void fetchNotifications(true);
  }, [fetchNotifications]);

  // Đánh dấu đã đọc
  const handleMarkAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
      window.dispatchEvent(new Event('notification-sync'));
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    }
  };

  // Đánh dấu tất cả đã đọc
  const handleMarkAllRead = async () => {
    try {
      const res = await notificationService.markAllAsRead();
      setActionMessage({
        type: 'success',
        text: `Đã đánh dấu ${res.marked_count} thông báo là đã đọc.`,
      });
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
      window.dispatchEvent(new Event('notification-sync'));
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    }
  };

  // Lưu trữ thông báo
  const handleArchive = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationService.archiveNotification(id);
      setActionMessage({
        type: 'success',
        text: 'Đã lưu trữ thông báo.',
      });
      if (!includeArchived) {
        setNotifications((prev) => prev.filter((n) => n.id !== id));
      } else {
        setNotifications((prev) =>
          prev.map((n) => (n.id === id ? { ...n, archived_at: new Date().toISOString() } : n))
        );
      }
      window.dispatchEvent(new Event('notification-sync'));
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    }
  };

  // Điều hướng an toàn khi click thông báo
  const handleItemClick = (item: NotificationItem) => {
    if (!item.read_at) {
      void notificationService.markAsRead(item.id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, read_at: new Date().toISOString() } : n))
      );
    }

    const allowedPrefixes = ['/recurring-transactions', '/budgets', '/transactions', '/accounts', '/reports', '/dashboard'];
    if (item.action_url && allowedPrefixes.some((p) => item.action_url?.startsWith(p))) {
      navigate(item.action_url);
    }
  };

  // Lọc theo search term
  const filteredNotifications = useMemo(() => {
    return notifications.filter((item) => {
      if (filterReadStatus === 'read' && !item.read_at) return false;
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchTitle = item.title.toLowerCase().includes(term);
        const matchMsg = item.message.toLowerCase().includes(term);
        if (!matchTitle && !matchMsg) return false;
      }
      return true;
    });
  }, [notifications, filterReadStatus, searchTerm]);

  const getIconForType = (type: string) => {
    switch (type) {
      case 'recurring_overdue':
        return <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />;
      case 'recurring_due_today':
        return <Calendar className="w-5 h-5 text-amber-500 shrink-0" />;
      case 'recurring_due_soon':
        return <Calendar className="w-5 h-5 text-indigo-500 shrink-0" />;
      case 'budget_exceeded':
        return <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />;
      case 'budget_warning':
        return <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />;
      default:
        return <Sparkles className="w-5 h-5 text-slate-400 shrink-0" />;
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', color: 'var(--text-main)', paddingBottom: '60px' }}>
      {/* Sticky Header */}
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
            maxWidth: '1000px',
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <button
              onClick={() => navigate('/dashboard')}
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
                transition: 'all 0.2s',
              }}
              title="Quay lại Dashboard"
            >
              <ArrowLeft size={16} />
              <span>Dashboard</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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
                <Bell size={20} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.15rem', letterSpacing: '-0.02em' }}>
                  Trung Tâm Thông Báo
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Nhắc nhở hạn thu chi định kỳ và cảnh báo ngân sách tài chính
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={handleSync}
              disabled={syncing}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
                fontSize: '0.85rem',
                cursor: 'pointer',
                opacity: syncing ? 0.6 : 1,
              }}
              title="Đồng bộ nguồn thông báo"
            >
              <RefreshCw size={15} className={syncing ? 'spinner' : ''} />
              <span>{syncing ? 'Đang đồng bộ...' : 'Đồng Bộ'}</span>
            </button>

            <button
              onClick={handleMarkAllRead}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-button)',
              }}
            >
              <CheckCheck size={16} />
              <span>Đọc Tất Cả</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main
        style={{
          maxWidth: '1000px',
          margin: '0 auto',
          padding: '24px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}
      >
        {/* Action Message Alert */}
        {actionMessage && (
          <div
            style={{
              padding: '14px 18px',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '0.9rem',
              background: actionMessage.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
              border:
                actionMessage.type === 'success'
                  ? '1px solid var(--success-border)'
                  : '1px solid var(--error-border)',
              color: actionMessage.type === 'success' ? 'var(--income)' : 'var(--danger)',
            }}
          >
            <CheckCheck size={18} style={{ flexShrink: 0 }} />
            <span style={{ fontWeight: 500 }}>{actionMessage.text}</span>
          </div>
        )}

        {/* Filters Bar */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '16px 20px',
            boxShadow: 'var(--shadow-card)',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '12px',
              alignItems: 'center',
            }}
          >
            {/* Search */}
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-sub)' }} />
              <input
                type="text"
                placeholder="Tìm kiếm nội dung..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px 9px 36px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>

            {/* Trạng thái đọc */}
            <div>
              <select
                value={filterReadStatus}
                onChange={(e) => setFilterReadStatus(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="all">Tất cả (Đã đọc & Chưa đọc)</option>
                <option value="unread">Chỉ chưa đọc</option>
                <option value="read">Đã đọc</option>
              </select>
            </div>

            {/* Loại thông báo */}
            <div>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="all">Tất cả loại thông báo</option>
                <option value="recurring_overdue">Khoản định kỳ quá hạn</option>
                <option value="recurring_due_today">Khoản định kỳ đến hạn hôm nay</option>
                <option value="recurring_due_soon">Khoản định kỳ sắp đến hạn</option>
                <option value="budget_exceeded">Ngân sách vượt hạn mức</option>
                <option value="budget_warning">Cảnh báo chạm ngưỡng ngân sách</option>
              </select>
            </div>

            {/* Tùy chọn lưu trữ */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="checkbox"
                id="include_archived_check"
                checked={includeArchived}
                onChange={(e) => setIncludeArchived(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--primary-500)', cursor: 'pointer' }}
              />
              <label
                htmlFor="include_archived_check"
                style={{ fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer', userSelect: 'none' }}
              >
                Hiện thông báo đã lưu trữ
              </label>
            </div>
          </div>
        </div>

        {/* Notifications List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {loading ? (
            <div
              style={{
                padding: '60px 0',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                color: 'var(--text-muted)',
              }}
            >
              <RefreshCw size={28} className="spinner" style={{ color: 'var(--primary-500)' }} />
              <p style={{ fontSize: '0.9rem' }}>Đang tải thông báo...</p>
            </div>
          ) : error ? (
            <div
              style={{
                padding: '40px 20px',
                background: 'var(--error-bg)',
                border: '1px solid var(--error-border)',
                borderRadius: 'var(--radius-lg)',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <AlertCircle size={32} style={{ color: '#ef4444' }} />
              <p style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--danger)' }}>{error}</p>
              <button
                onClick={() => fetchNotifications(true)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: '#ef4444',
                  border: 'none',
                  color: '#fff',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Thử lại
              </button>
            </div>
          ) : filteredNotifications.length === 0 ? (
            <div
              style={{
                padding: '60px 20px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '12px',
                  background: 'var(--surface-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                <Bell size={24} />
              </div>
              <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Không có thông báo nào phù hợp
              </p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-sub)', maxWidth: '400px' }}>
                Bạn đã hoàn thành hết các nhắc nhở tài chính hoặc bộ lọc hiện tại không có kết quả.
              </p>
            </div>
          ) : (
            filteredNotifications.map((item) => (
              <div
                key={item.id}
                onClick={() => handleItemClick(item)}
                style={{
                  background: !item.read_at ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-card)',
                  border: !item.read_at ? '1px solid rgba(59, 130, 246, 0.35)' : '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 20px',
                  boxShadow: 'var(--shadow-card)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '16px',
                  cursor: 'pointer',
                  opacity: item.archived_at ? 0.6 : 1,
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = !item.read_at
                    ? 'rgba(59, 130, 246, 0.35)'
                    : 'var(--border)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      padding: '10px',
                      borderRadius: '10px',
                      background: 'var(--surface-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {getIconForType(item.type)}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                      <h3
                        style={{
                          fontSize: '0.95rem',
                          fontWeight: !item.read_at ? 700 : 600,
                          color: !item.read_at ? 'var(--text-main)' : 'var(--text-muted)',
                        }}
                      >
                        {item.title}
                      </h3>
                      {!item.read_at && (
                        <span
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: '#3b82f6',
                            display: 'inline-block',
                          }}
                        />
                      )}
                      {item.archived_at && (
                        <span
                          style={{
                            fontSize: '0.7rem',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: 'var(--border)',
                            color: 'var(--text-sub)',
                          }}
                        >
                          Đã lưu trữ
                        </span>
                      )}
                    </div>
                    <p
                      style={{
                        fontSize: '0.85rem',
                        color: 'var(--text-muted)',
                        lineHeight: 1.5,
                        marginBottom: '8px',
                      }}
                    >
                      {item.message}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                      <span>
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                      {item.action_url && (
                        <span
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            color: 'var(--primary-500)',
                            fontWeight: 600,
                          }}
                        >
                          <span>Xem chi tiết</span>
                          <ExternalLink size={12} />
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions Button */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                  {!item.read_at && (
                    <button
                      onClick={(e) => handleMarkAsRead(item.id, e)}
                      title="Đánh dấu đã đọc"
                      style={{
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--secondary-soft)',
                        border: '1px solid #C4DDFC',
                        color: 'var(--secondary)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <CheckCheck size={14} />
                      <span>Đã đọc</span>
                    </button>
                  )}
                  {!item.archived_at && (
                    <button
                      onClick={(e) => handleArchive(item.id, e)}
                      title="Lưu trữ thông báo"
                      style={{
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--surface-muted)',
                        border: '1px solid var(--border)',
                        color: 'var(--text-sub)',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <Archive size={14} />
                      <span>Lưu trữ</span>
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
