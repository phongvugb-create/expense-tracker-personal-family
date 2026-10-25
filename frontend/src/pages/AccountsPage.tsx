import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  WalletCards,
  Plus,
  ArrowLeft,
  RefreshCw,
  Archive,
  RotateCcw,
  Edit,
  ShieldCheck,
  AlertTriangle,
  FolderLock,
  Layers,
  Search,
  Users,
  ReceiptText,
  ArrowLeftRight,
  PieChart,
} from 'lucide-react';
import type { Account, AccountScope } from '../types/account';
import { accountService } from '../services/accountService';
import { getErrorMessage } from '../services/apiClient';
import {
  formatCurrency,
  ACCOUNT_TYPE_LABELS,
  ACCOUNT_SCOPE_LABELS,
} from '../utils/accountUtils';
import { CreateAccountModal } from '../components/CreateAccountModal';
import { EditAccountModal } from '../components/EditAccountModal';

type FilterTab = 'all' | 'personal' | 'family' | 'archived';

export function AccountsPage() {
  const navigate = useNavigate();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Filter state
  const [currentTab, setCurrentTab] = useState<FilterTab>('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);

  // Archive Confirm Modal
  const [accountToArchive, setAccountToArchive] = useState<Account | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);

  /**
   * Tải danh sách ví từ API backend
   */
  const fetchAccounts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let scopeParam: AccountScope | undefined;
      let includeArchived = false;

      if (currentTab === 'personal') {
        scopeParam = 'personal';
      } else if (currentTab === 'family') {
        scopeParam = 'family';
      } else if (currentTab === 'archived') {
        includeArchived = true;
      }

      const data = await accountService.getAccounts({
        scope: scopeParam,
        include_archived: includeArchived,
      });

      if (currentTab === 'archived') {
        setAccounts(data.filter((acc) => acc.is_archived));
      } else {
        setAccounts(data);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [currentTab]);

  useEffect(() => {
    void fetchAccounts();
  }, [fetchAccounts]);

  // Flash message tự động ẩn sau 4 giây
  useEffect(() => {
    if (actionMessage) {
      const timer = setTimeout(() => {
        setActionMessage(null);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [actionMessage]);

  /**
   * Xử lý lưu trữ ví
   */
  const handleConfirmArchive = async () => {
    if (!accountToArchive) return;
    try {
      setArchiveLoading(true);
      await accountService.archiveAccount(accountToArchive.id);
      setActionMessage({
        type: 'success',
        text: `Đã lưu trữ ví "${accountToArchive.name}" thành công. Giao dịch vẫn được bảo lưu an toàn.`,
      });
      setAccountToArchive(null);
      await fetchAccounts();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setArchiveLoading(false);
    }
  };

  /**
   * Xử lý khôi phục ví
   */
  const handleRestore = async (account: Account) => {
    try {
      setLoading(true);
      await accountService.restoreAccount(account.id);
      setActionMessage({
        type: 'success',
        text: `Đã khôi phục ví "${account.name}" về trạng thái hoạt động.`,
      });
      await fetchAccounts();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
      setLoading(false);
    }
  };

  // Tính toán số liệu thống kê tổng quan (không cộng gộp khác currency)
  const stats = useMemo(() => {
    const active = accounts.filter((a) => !a.is_archived);
    const personalCount = active.filter((a) => a.scope === 'personal').length;
    const familyCount = active.filter((a) => a.scope === 'family').length;

    // Tổng số dư nhóm theo từng loại tiền tệ
    const balancesByCurrency: Record<string, number> = {};
    active.forEach((acc) => {
      const curr = acc.currency.toUpperCase();
      const val = Number(acc.current_balance) || 0;
      balancesByCurrency[curr] = (balancesByCurrency[curr] || 0) + val;
    });

    return {
      activeCount: active.length,
      personalCount,
      familyCount,
      balancesByCurrency,
    };
  }, [accounts]);

  // Lọc tìm kiếm theo tên
  const filteredAccounts = useMemo(() => {
    if (!searchTerm.trim()) return accounts;
    const term = searchTerm.toLowerCase();
    return accounts.filter((acc) => acc.name.toLowerCase().includes(term));
  }, [accounts, searchTerm]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)' }}>
      {/* Top Navbar */}
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
            maxWidth: '1200px',
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
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
                <WalletCards size={20} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.15rem' }}>Quản lý ví tài chính</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Ví cá nhân & ví dùng chung gia đình
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              id="accounts-budgets-nav-btn"
              onClick={() => navigate('/budgets')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--warning-soft)',
                border: '1px solid #FCE38E',
                color: 'var(--warning)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <PieChart size={16} />
              <span>Ngân sách</span>
            </button>

            <button
              id="accounts-transfers-nav-btn"
              onClick={() => navigate('/transfers')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--secondary-soft)',
                border: '1px solid #C4DDFC',
                color: 'var(--secondary)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <ArrowLeftRight size={16} />
              <span>Chuyển tiền</span>
            </button>

            <button
              id="accounts-transactions-nav-btn"
              onClick={() => navigate('/transactions')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--income-soft)',
                border: '1px solid #BCE2CE',
                color: '#6ee7b7',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <ReceiptText size={16} />
              <span>Sổ giao dịch</span>
            </button>

            <button
              id="accounts-families-nav-btn"
              onClick={() => navigate('/families')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(99, 102, 241, 0.12)',
                border: '1px solid rgba(99, 102, 241, 0.25)',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <Users size={16} />
              <span>Nhóm gia đình</span>
            </button>

            <button
              id="refresh-accounts-btn"
              onClick={fetchAccounts}
              disabled={loading}
              title="Tải lại danh sách"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '38px',
                height: '38px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>

            <button
              id="open-create-account-btn"
              onClick={() => setIsCreateOpen(true)}
              className="btn-primary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '9px 18px',
                fontSize: '0.875rem',
              }}
            >
              <Plus size={16} />
              <span>Tạo ví mới</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
        {/* Flash Message Banner */}
        {actionMessage && (
          <div
            style={{
              padding: '14px 20px',
              borderRadius: 'var(--radius-md)',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              fontSize: '0.9rem',
              fontWeight: 500,
              background:
                actionMessage.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
              border: `1px solid ${
                actionMessage.type === 'success' ? 'var(--success-border)' : 'var(--error-border)'
              }`,
              color: actionMessage.type === 'success' ? 'var(--success)' : 'var(--danger)',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <ShieldCheck size={18} />
            <span>{actionMessage.text}</span>
          </div>
        )}

        {/* Overview Stats Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '18px',
            marginBottom: '32px',
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
            }}
          >
            <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '8px' }}>
              TỔNG SỐ VÍ HOẠT ĐỘNG
            </div>
            <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-main)' }}>
              {stats.activeCount} <span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-sub)' }}>ví</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              {stats.personalCount} cá nhân • {stats.familyCount} gia đình
            </div>
          </div>

          {/* Hiển thị số dư theo từng loại tiền tệ */}
          {Object.entries(stats.balancesByCurrency).length > 0 ? (
            Object.entries(stats.balancesByCurrency).map(([curr, total]) => (
              <div
                key={curr}
                style={{
                  background:
                    'linear-gradient(135deg, rgba(40, 107, 87, 0.08) 0%, rgba(255, 255, 255, 0.95) 100%)',
                  border: '1px solid #C4DDFC',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                }}
              >
                <div style={{ fontSize: '0.8rem', color: 'var(--secondary)', fontWeight: 600, marginBottom: '8px' }}>
                  TỔNG SỐ DƯ HIỆN TẠI ({curr})
                </div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#60a5fa' }}>
                  {formatCurrency(total, curr)}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginTop: '6px' }}>
                  Tính toán theo thời gian thực từ PostgreSQL
                </div>
              </div>
            ))
          ) : (
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '20px',
              }}
            >
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '8px' }}>
                TỔNG SỐ DƯ HIỆN TẠI
              </div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-muted)' }}>
                0 ₫
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginTop: '6px' }}>
                Chưa có ví tài chính nào
              </div>
            </div>
          )}
        </div>

        {/* Filter Controls & Search */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            marginBottom: '24px',
          }}
        >
          {/* Tabs */}
          <div
            style={{
              display: 'inline-flex',
              padding: '4px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface-muted)',
              border: '1px solid var(--border)',
            }}
          >
            {(
              [
                { id: 'all', label: 'Tất cả ví' },
                { id: 'personal', label: 'Ví cá nhân' },
                { id: 'family', label: 'Ví gia đình' },
                { id: 'archived', label: 'Đã lưu trữ' },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                id={`filter-tab-${tab.id}`}
                onClick={() => setCurrentTab(tab.id)}
                style={{
                  padding: '7px 16px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  background: currentTab === tab.id ? 'var(--primary-500)' : 'transparent',
                  color: currentTab === tab.id ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.2s',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search box */}
          <div style={{ position: 'relative', minWidth: '240px' }}>
            <Search
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
              type="text"
              placeholder="Tìm kiếm theo tên ví..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{
                paddingLeft: '36px',
                paddingTop: '8px',
                paddingBottom: '8px',
                fontSize: '0.85rem',
                borderRadius: 'var(--radius-md)',
              }}
            />
          </div>
        </div>

        {/* Account List Area */}
        {loading ? (
          /* Loading State Skeleton */
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: '20px',
            }}
          >
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                style={{
                  height: '180px',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-lg)',
                  animation: 'pulse 1.5s infinite',
                }}
              />
            ))}
          </div>
        ) : error ? (
          /* Error State */
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--error-border)',
              borderRadius: 'var(--radius-lg)',
              padding: '48px 24px',
              textAlign: 'center',
            }}
          >
            <AlertTriangle size={40} color="var(--error)" style={{ marginBottom: '12px' }} />
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '8px' }}>
              Không thể tải danh sách ví
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '20px' }}>
              {error}
            </p>
            <button onClick={fetchAccounts} className="btn-primary" style={{ padding: '8px 20px' }}>
              Thử tải lại
            </button>
          </div>
        ) : filteredAccounts.length === 0 ? (
          /* Empty State */
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px dashed var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '60px 24px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                background: 'rgba(59, 130, 246, 0.1)',
                color: 'var(--primary-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <FolderLock size={28} />
            </div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px' }}>
              {currentTab === 'archived'
                ? 'Không có ví nào đang lưu trữ'
                : searchTerm
                ? 'Không tìm thấy ví phù hợp'
                : 'Chưa có ví tài khoản nào'}
            </h3>
            <p
              style={{
                color: 'var(--text-muted)',
                fontSize: '0.9rem',
                maxWidth: '440px',
                margin: '0 auto 24px',
                lineHeight: 1.5,
              }}
            >
              {currentTab === 'archived'
                ? 'Các ví bị lưu trữ sẽ xuất hiện tại đây khi bạn tạm ẩn chúng.'
                : searchTerm
                ? 'Vui lòng kiểm tra lại từ khóa tìm kiếm.'
                : 'Hãy bắt đầu quản lý tài chính bằng cách tạo ví tiền mặt, tài khoản ngân hàng hoặc ví dùng chung cho gia đình.'}
            </p>
            {currentTab !== 'archived' && !searchTerm && (
              <button
                onClick={() => setIsCreateOpen(true)}
                className="btn-primary"
                style={{ padding: '10px 22px' }}
              >
                + Tạo ví đầu tiên
              </button>
            )}
          </div>
        ) : (
          /* Cards Grid */
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
              gap: '20px',
            }}
          >
            {filteredAccounts.map((account) => {
              const isPersonal = account.scope === 'personal';
              return (
                <div
                  key={account.id}
                  style={{
                    background: 'var(--bg-card)',
                    border: account.is_archived
                      ? '1px solid var(--border)'
                      : isPersonal
                      ? '1px solid rgba(59, 130, 246, 0.2)'
                      : '1px solid rgba(99, 102, 241, 0.25)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    position: 'relative',
                    transition: 'all 0.2s ease',
                    opacity: account.is_archived ? 0.75 : 1,
                  }}
                >
                  {/* Card Header */}
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        marginBottom: '12px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span
                          style={{
                            fontSize: '0.725rem',
                            fontWeight: 700,
                            padding: '3px 10px',
                            borderRadius: 'var(--radius-full)',
                            background: isPersonal
                              ? 'rgba(59, 130, 246, 0.15)'
                              : 'rgba(99, 102, 241, 0.15)',
                            color: isPersonal ? 'var(--primary)' : 'var(--secondary)',
                            border: `1px solid ${
                              isPersonal ? 'rgba(59, 130, 246, 0.3)' : 'rgba(99, 102, 241, 0.3)'
                            }`,
                          }}
                        >
                          {ACCOUNT_SCOPE_LABELS[account.scope] || account.scope}
                        </span>

                        <span
                          style={{
                            fontSize: '0.725rem',
                            color: 'var(--text-sub)',
                            background: 'var(--surface-muted)',
                            padding: '3px 8px',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          {ACCOUNT_TYPE_LABELS[account.account_type] || account.account_type}
                        </span>
                      </div>

                      {account.is_archived && (
                        <span
                          style={{
                            fontSize: '0.7rem',
                            padding: '2px 8px',
                            borderRadius: 'var(--radius-full)',
                            background: 'var(--expense-soft)',
                            color: 'var(--danger)',
                            fontWeight: 600,
                          }}
                        >
                          Đã lưu trữ
                        </span>
                      )}
                    </div>

                    <h3
                      style={{
                        fontSize: '1.25rem',
                        fontWeight: 700,
                        marginBottom: '16px',
                        color: 'var(--text-main)',
                      }}
                    >
                      {account.name}
                    </h3>

                    {/* Balance Info */}
                    <div
                      style={{
                        background: 'var(--surface-muted)',
                        padding: '14px 16px',
                        borderRadius: 'var(--radius-md)',
                        marginBottom: '18px',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-sub)',
                          marginBottom: '4px',
                        }}
                      >
                        SỐ DƯ KHẢ DỤNG
                      </div>
                      <div
                        style={{
                          fontSize: '1.5rem',
                          fontWeight: 800,
                          color: Number(account.current_balance) < 0 ? 'var(--expense)' : 'var(--income)',
                          letterSpacing: '-0.02em',
                        }}
                      >
                        {formatCurrency(account.current_balance, account.currency)}
                      </div>
                      <div
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-sub)',
                          marginTop: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <span>Khởi tạo ban đầu:</span>
                        <span style={{ color: 'var(--text-muted)' }}>
                          {formatCurrency(account.initial_balance, account.currency)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Card Actions Footer */}
                  <div
                    style={{
                      borderTop: '1px solid var(--border)',
                      paddingTop: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-sub)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <Layers size={13} />
                      <span>{account.currency}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {!account.is_archived ? (
                        <>
                          <button
                            title="Chỉnh sửa ví"
                            onClick={() => {
                              setSelectedAccount(account);
                              setIsEditOpen(true);
                            }}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 12px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'var(--surface-muted)',
                              border: '1px solid var(--border)',
                              color: 'var(--text-muted)',
                              fontSize: '0.8rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            <Edit size={14} />
                            <span>Sửa</span>
                          </button>

                          <button
                            title="Lưu trữ ví"
                            onClick={() => setAccountToArchive(account)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 12px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'rgba(239, 68, 68, 0.08)',
                              border: '1px solid rgba(239, 68, 68, 0.2)',
                              color: 'var(--danger)',
                              fontSize: '0.8rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            <Archive size={14} />
                            <span>Lưu trữ</span>
                          </button>
                        </>
                      ) : (
                        <button
                          title="Khôi phục ví về hoạt động"
                          onClick={() => handleRestore(account)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '6px 14px',
                            borderRadius: 'var(--radius-sm)',
                            background: 'var(--income-soft)',
                            border: '1px solid #BCE2CE',
                            color: 'var(--success)',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          <RotateCcw size={14} />
                          <span>Khôi phục</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Modal tạo ví mới */}
      <CreateAccountModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Đã tạo ví tài khoản mới thành công!',
          });
          fetchAccounts();
        }}
      />

      {/* Modal chỉnh sửa ví */}
      <EditAccountModal
        account={selectedAccount}
        isOpen={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setSelectedAccount(null);
        }}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Đã cập nhật thông tin ví thành công!',
          });
          fetchAccounts();
        }}
      />

      {/* Modal xác nhận Archive */}
      {accountToArchive && (
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
            zIndex: 60,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !archiveLoading) setAccountToArchive(null);
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid #F5BAC2',
              borderRadius: 'var(--radius-lg)',
              maxWidth: '440px',
              width: '100%',
              padding: '24px',
              boxShadow: 'var(--shadow-card)',
              animation: 'fadeIn 0.2s ease',
            }}
          >
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: 'var(--expense-soft)',
                color: 'var(--error)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
              }}
            >
              <Archive size={22} />
            </div>

            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px' }}>
              Xác nhận lưu trữ ví?
            </h3>

            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '20px' }}>
              Bạn đang yêu cầu lưu trữ ví <strong>"{accountToArchive.name}"</strong>. Ví này sẽ được ẩn khỏi danh sách sử dụng hàng ngày, nhưng toàn bộ lịch sử giao dịch và số dư vẫn được lưu trữ nguyên vẹn và có thể khôi phục bất cứ lúc nào.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setAccountToArchive(null)}
                disabled={archiveLoading}
                style={{
                  padding: '9px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Hủy
              </button>

              <button
                type="button"
                id="confirm-archive-btn"
                onClick={handleConfirmArchive}
                disabled={archiveLoading}
                style={{
                  padding: '9px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--error)',
                  border: 'none',
                  color: '#fff',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {archiveLoading ? 'Đang lưu trữ...' : 'Đồng ý lưu trữ'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
