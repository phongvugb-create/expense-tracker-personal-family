import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, RefreshCw, CheckCheck, ExternalLink, Calendar, AlertTriangle, AlertCircle, Sparkles } from 'lucide-react';
import { notificationService } from '../services/notificationService';
import type { NotificationItem } from '../types/notification';

export function NotificationBell() {
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [recentNotifications, setRecentNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Lấy unread count định kỳ hoặc khi mở trang
  const fetchUnreadCount = useCallback(async () => {
    try {
      const count = await notificationService.getUnreadCount();
      setUnreadCount(count);
    } catch {
      // Ignored
    }
  }, []);

  useEffect(() => {
    void fetchUnreadCount();
    // Đồng bộ unread count mỗi 60 giây và khi có event notification-sync
    const interval = setInterval(fetchUnreadCount, 60000);
    const handleSyncEvent = () => {
      void fetchUnreadCount();
    };
    window.addEventListener('notification-sync', handleSyncEvent);
    return () => {
      clearInterval(interval);
      window.removeEventListener('notification-sync', handleSyncEvent);
    };
  }, [fetchUnreadCount]);

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Khi click mở chuông: đồng bộ và tải danh sách thông báo mới nhất
  const handleToggle = async () => {
    if (!isOpen) {
      setIsOpen(true);
      setLoading(true);
      try {
        await notificationService.syncNotifications();
        const [items, count] = await Promise.all([
          notificationService.getNotifications({ limit: 5 }),
          notificationService.getUnreadCount(),
        ]);
        setRecentNotifications(items);
        setUnreadCount(count);
      } catch (err) {
        console.error('Lỗi tải thông báo:', err);
      } finally {
        setLoading(false);
      }
    } else {
      setIsOpen(false);
    }
  };

  const handleMarkAllRead = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationService.markAllAsRead();
      setUnreadCount(0);
      setRecentNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
    } catch (err) {
      console.error('Lỗi mark all read:', err);
    }
  };

  const handleNotificationClick = (item: NotificationItem) => {
    // Nếu chưa đọc thì đánh dấu đọc
    if (!item.read_at) {
      void notificationService.markAsRead(item.id);
      setUnreadCount((prev) => Math.max(0, prev - 1));
      setRecentNotifications((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, read_at: new Date().toISOString() } : n))
      );
    }
    setIsOpen(false);

    // Whitelist điều hướng nội bộ an toàn
    const allowedPrefixes = ['/recurring-transactions', '/budgets', '/transactions', '/accounts', '/reports', '/dashboard'];
    if (item.action_url && allowedPrefixes.some((p) => item.action_url?.startsWith(p))) {
      navigate(item.action_url);
    } else {
      navigate('/notifications');
    }
  };

  const getIconForType = (type: string) => {
    switch (type) {
      case 'recurring_overdue':
        return <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />;
      case 'recurring_due_today':
        return <Calendar className="w-4 h-4 text-amber-500 shrink-0" />;
      case 'recurring_due_soon':
        return <Calendar className="w-4 h-4 text-indigo-500 shrink-0" />;
      case 'budget_exceeded':
        return <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />;
      case 'budget_warning':
        return <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />;
      default:
        return <Sparkles className="w-4 h-4 text-slate-400 shrink-0" />;
    }
  };

  return (
    <div
      ref={dropdownRef}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
      }}
    >
      {/* Chuông thông báo */}
      <button
        id="navbar-notification-bell-btn"
        onClick={handleToggle}
        title="Trung tâm thông báo"
        style={{
          position: 'relative',
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: isOpen ? 'rgba(59, 130, 246, 0.15)' : 'var(--surface-muted)',
          border: isOpen ? '1px solid rgba(59, 130, 246, 0.35)' : '1px solid rgba(255, 255, 255, 0.1)',
          color: isOpen ? 'var(--primary)' : 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
        }}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              minWidth: '18px',
              height: '18px',
              padding: '0 5px',
              borderRadius: '9999px',
              background: '#ef4444',
              color: '#ffffff',
              fontSize: '0.65rem',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(239, 68, 68, 0.6)',
              lineHeight: 1,
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Popup */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 10px)',
            right: 0,
            width: '360px',
            maxWidth: 'calc(100vw - 32px)',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 16px 40px -8px rgba(36, 53, 44, 0.14), 0 0 0 1px var(--border)',
            backdropFilter: 'blur(20px)',
            zIndex: 100,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 16px',
              borderBottom: '1px solid var(--border)',
              background: 'var(--surface-muted)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                Thông báo
              </span>
              {unreadCount > 0 && (
                <span
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--danger-soft)',
                    color: 'var(--danger)',
                    border: '1px solid #F5BAC2',
                  }}
                >
                  {unreadCount} mới
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: 'var(--primary-500)',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '2px 6px',
                  borderRadius: '4px',
                }}
              >
                <CheckCheck size={14} />
                <span>Đọc tất cả</span>
              </button>
            )}
          </div>

          {/* List Content */}
          <div
            style={{
              maxHeight: '340px',
              overflowY: 'auto',
            }}
          >
            {loading ? (
              <div
                style={{
                  padding: '32px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  color: 'var(--text-muted)',
                }}
              >
                <RefreshCw size={20} className="spinner" style={{ color: 'var(--primary-500)' }} />
                <span style={{ fontSize: '0.8rem' }}>Đang đồng bộ thông báo...</span>
              </div>
            ) : recentNotifications.length === 0 ? (
              <div
                style={{
                  padding: '36px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                }}
              >
                <Bell size={28} style={{ color: 'var(--border)' }} />
                <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  Không có thông báo mới
                </p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Bạn đã cập nhật hết các nhắc nhở tài chính.
                </p>
              </div>
            ) : (
              recentNotifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleNotificationClick(item)}
                  style={{
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    cursor: 'pointer',
                    transition: 'background 0.2s',
                    borderBottom: '1px solid var(--border)',
                    background: !item.read_at ? 'rgba(59, 130, 246, 0.08)' : 'transparent',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = !item.read_at
                      ? 'rgba(59, 130, 246, 0.14)'
                      : 'var(--surface-muted)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = !item.read_at
                      ? 'rgba(59, 130, 246, 0.08)'
                      : 'transparent';
                  }}
                >
                  <div style={{ marginTop: '2px', flexShrink: 0 }}>{getIconForType(item.type)}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: '0.85rem',
                        fontWeight: !item.read_at ? 700 : 500,
                        color: !item.read_at ? 'var(--text-main)' : 'var(--text-muted)',
                        marginBottom: '3px',
                        lineHeight: 1.35,
                      }}
                    >
                      {item.title}
                    </p>
                    <p
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-sub)',
                        lineHeight: 1.4,
                        marginBottom: '4px',
                        wordBreak: 'break-word',
                      }}
                    >
                      {item.message}
                    </p>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-sub)', opacity: 0.8 }}>
                      {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer View All */}
          <div
            style={{
              padding: '10px 16px',
              borderTop: '1px solid var(--border)',
              background: 'rgba(0, 0, 0, 0.25)',
              textAlign: 'center',
            }}
          >
            <button
              onClick={() => {
                setIsOpen(false);
                navigate('/notifications');
              }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                color: 'var(--primary-500)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: '6px 0',
              }}
            >
              <span>Xem tất cả thông báo</span>
              <ExternalLink size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
