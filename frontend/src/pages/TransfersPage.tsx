import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowRightLeft,
  Plus,
  ArrowLeft,
  RefreshCw,
  Eye,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  X,
  CreditCard,
  ReceiptText,
  Ban,
  CheckCircle,
} from 'lucide-react';
import type { Account } from '../types/account';
import type { Category } from '../types/category';
import type { Transfer } from '../types/transfer';
import { accountService } from '../services/accountService';
import { categoryService } from '../services/categoryService';
import { transferService } from '../services/transferService';
import { getErrorMessage } from '../services/apiClient';
import { formatCurrency } from '../utils/accountUtils';
import { CreateTransferModal } from '../components/CreateTransferModal';
import { TransferDetailModal } from '../components/TransferDetailModal';

const PAGE_SIZE = 15;

export function TransfersPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Danh sách ví và danh mục phục vụ chọn lựa & bộ lọc
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Dữ liệu danh sách chuyển tiền
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Bộ lọc
  const [filterAccountId, setFilterAccountId] = useState<string>(() => {
    return searchParams.get('account_id') || '';
  });
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');
  const [includeVoided, setIncludeVoided] = useState<boolean>(false);

  // Phân trang
  const [offset, setOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [selectedTransfer, setSelectedTransfer] = useState<Transfer | null>(null);

  // Modal xác nhận Void
  const [transferToVoid, setTransferToVoid] = useState<Transfer | null>(null);
  const [voidLoading, setVoidLoading] = useState(false);

  /**
   * Tải danh sách ví và danh mục ban đầu
   */
  const loadFilterOptions = useCallback(async () => {
    try {
      const [accs, cats] = await Promise.all([
        accountService.getAccounts(),
        categoryService.getCategories({ type: 'expense' }),
      ]);
      setAccounts(accs);
      setCategories(cats);
    } catch (err: unknown) {
      console.error('Lỗi khi tải ví hoặc danh mục:', err);
    }
  }, []);

  useEffect(() => {
    void loadFilterOptions();
  }, [loadFilterOptions]);

  /**
   * Tải danh sách chuyển tiền từ Backend API
   */
  const fetchTransfers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (filterDateFrom && filterDateTo && filterDateFrom > filterDateTo) {
        setError('Ngày bắt đầu không được lớn hơn ngày kết thúc.');
        setLoading(false);
        return;
      }

      const params = {
        ...(filterAccountId ? { account_id: filterAccountId } : {}),
        ...(filterDateFrom ? { date_from: new Date(filterDateFrom).toISOString() } : {}),
        ...(filterDateTo
          ? {
              date_to: new Date(`${filterDateTo}T23:59:59.999Z`).toISOString(),
            }
          : {}),
        include_voided: includeVoided,
        limit: PAGE_SIZE + 1,
        offset,
      };

      const data = await transferService.getTransfers(params);

      if (data.length > PAGE_SIZE) {
        setHasMore(true);
        setTransfers(data.slice(0, PAGE_SIZE));
      } else {
        setHasMore(false);
        setTransfers(data);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filterAccountId, filterDateFrom, filterDateTo, includeVoided, offset]);

  useEffect(() => {
    void fetchTransfers();
  }, [fetchTransfers]);

  const handleFilterChange = (updater: () => void) => {
    updater();
    setOffset(0);
  };

  /**
   * Xác nhận hủy hiệu lực (void) chuyển tiền
   */
  const handleConfirmVoid = async () => {
    if (!transferToVoid) return;
    try {
      setVoidLoading(true);
      await transferService.voidTransfer(transferToVoid.id);
      setActionMessage({
        type: 'success',
        text: 'Đã hủy hiệu lực chuyển tiền thành công! Số dư 2 ví đã được tự động hoàn nguyên.',
      });
      setTransferToVoid(null);
      if (isDetailOpen) setIsDetailOpen(false);
      void fetchTransfers();
      void loadFilterOptions();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setVoidLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', paddingBottom: '60px' }}>
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
                background: 'transparent',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                cursor: 'pointer',
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
                <ArrowRightLeft size={20} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em' }}>
                  Chuyển Tiền Liên Ví
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Hạch toán kép bút toán kép và hoàn nguyên số dư
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => navigate('/accounts')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                padding: '9px 16px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <CreditCard size={16} color="var(--primary-500)" />
              <span>Quản lý Ví</span>
            </button>

            <button
              onClick={() => navigate('/transactions')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                padding: '9px 16px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <ReceiptText size={16} color="var(--success)" />
              <span>Sổ giao dịch</span>
            </button>

            <button
              onClick={() => setIsCreateOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#fff',
                padding: '9px 18px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-button)',
              }}
            >
              <Plus size={18} />
              <span>Chuyển Tiền Mới</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
        {/* Toast Action Message */}
        {actionMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background:
                actionMessage.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
              color: actionMessage.type === 'success' ? 'var(--success)' : 'var(--error)',
              border: `1px solid ${
                actionMessage.type === 'success'
                  ? 'var(--success-border)'
                  : 'var(--error-border)'
              }`,
              borderRadius: 'var(--radius-md)',
              padding: '12px 18px',
              marginBottom: '24px',
              fontSize: '0.9rem',
              fontWeight: 500,
            }}
          >
            <span>{actionMessage.text}</span>
            <button
              onClick={() => setActionMessage(null)}
              style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Thanh Bộ Lọc */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            marginBottom: '24px',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '14px',
              alignItems: 'flex-end',
            }}
          >
            {/* Lọc Theo Ví */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '6px' }}>
                Ví liên quan (Nguồn hoặc Đích)
              </label>
              <select
                value={filterAccountId}
                onChange={(e) => handleFilterChange(() => setFilterAccountId(e.target.value))}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.875rem',
                  outline: 'none',
                }}
              >
                <option value="">Tất cả các ví</option>
                {accounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.scope === 'personal' ? 'Cá nhân' : 'Gia đình'})
                  </option>
                ))}
              </select>
            </div>

            {/* Từ Ngày */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '6px' }}>
                Từ ngày
              </label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => handleFilterChange(() => setFilterDateFrom(e.target.value))}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.875rem',
                  outline: 'none',
                }}
              />
            </div>

            {/* Đến Ngày */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '6px' }}>
                Đến ngày
              </label>
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => handleFilterChange(() => setFilterDateTo(e.target.value))}
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--bg-input-border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-main)',
                  fontSize: '0.875rem',
                  outline: 'none',
                }}
              />
            </div>

            {/* Checkbox bao gồm Voided */}
            <div style={{ display: 'flex', alignItems: 'center', height: '40px' }}>
              <label
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '0.85rem',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={includeVoided}
                  onChange={(e) => handleFilterChange(() => setIncludeVoided(e.target.checked))}
                  style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                />
                <span>Bao gồm chuyển tiền đã hủy (void)</span>
              </label>
            </div>

            {/* Buttons */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => {
                  setFilterAccountId('');
                  setFilterDateFrom('');
                  setFilterDateTo('');
                  setIncludeVoided(false);
                  setOffset(0);
                }}
                style={{
                  padding: '9px 14px',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-muted)',
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                Đặt lại
              </button>

              <button
                type="button"
                onClick={() => void fetchTransfers()}
                style={{
                  padding: '9px 14px',
                  background: 'var(--secondary-soft)',
                  border: '1px solid #C4DDFC',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--primary-500)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <RefreshCw size={15} />
                <span>Tải lại</span>
              </button>
            </div>
          </div>
        </div>

        {/* Danh Sách Chuyển Tiền */}
        {loading ? (
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '60px',
              textAlign: 'center',
              color: 'var(--text-sub)',
            }}
          >
            <RefreshCw size={30} className="animate-spin" style={{ margin: '0 auto 12px' }} />
            <div>Đang tải lịch sử chuyển tiền từ PostgreSQL...</div>
          </div>
        ) : error ? (
          <div
            style={{
              background: 'var(--error-bg)',
              border: '1px solid var(--error-border)',
              borderRadius: 'var(--radius-lg)',
              padding: '30px',
              textAlign: 'center',
              color: 'var(--error)',
            }}
          >
            <AlertTriangle size={32} style={{ margin: '0 auto 12px' }} />
            <div style={{ fontWeight: 600, marginBottom: '8px' }}>Không thể tải lịch sử chuyển tiền</div>
            <div style={{ fontSize: '0.875rem', marginBottom: '16px' }}>{error}</div>
            <button
              onClick={() => void fetchTransfers()}
              style={{
                padding: '8px 18px',
                background: 'var(--error)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Thử lại
            </button>
          </div>
        ) : transfers.length === 0 ? (
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '60px 24px',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '20px',
                background: 'var(--surface-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                color: 'var(--text-sub)',
              }}
            >
              <ArrowRightLeft size={32} />
            </div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px' }}>
              Chưa có giao dịch chuyển tiền nào
            </h3>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.9rem', maxWidth: '440px', margin: '0 auto 20px' }}>
              Bạn chưa thực hiện lượt chuyển khoản nào hoặc không có bản ghi phù hợp với bộ lọc hiện tại.
            </p>
            <button
              onClick={() => setIsCreateOpen(true)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#fff',
                padding: '10px 20px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-button)',
              }}
            >
              <Plus size={18} />
              <span>Tạo chuyển tiền đầu tiên</span>
            </button>
          </div>
        ) : (
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              overflow: 'hidden',
            }}
          >
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: '1px solid var(--border)',
                      background: 'var(--surface-muted)',
                    }}
                  >
                    <th style={{ padding: '14px 20px', fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                      THỜI GIAN
                    </th>
                    <th style={{ padding: '14px 20px', fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                      VÍ NGUỒN ➔ VÍ ĐÍCH
                    </th>
                    <th style={{ padding: '14px 20px', fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                      GHI CHÚ
                    </th>
                    <th style={{ padding: '14px 20px', fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                      TRẠNG THÁI
                    </th>
                    <th
                      style={{
                        padding: '14px 20px',
                        fontSize: '0.75rem',
                        color: 'var(--text-sub)',
                        fontWeight: 600,
                        textAlign: 'right',
                      }}
                    >
                      SỐ TIỀN & PHÍ
                    </th>
                    <th
                      style={{
                        padding: '14px 20px',
                        fontSize: '0.75rem',
                        color: 'var(--text-sub)',
                        fontWeight: 600,
                        textAlign: 'center',
                      }}
                    >
                      THAO TÁC
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {transfers.map((tr) => {
                    const curr = tr.currency || 'VND';
                    return (
                      <tr
                        key={tr.id}
                        style={{
                          borderBottom: '1px solid var(--border)',
                          transition: 'background 0.15s ease',
                          opacity: tr.is_voided ? 0.65 : 1,
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'var(--surface-muted)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'transparent';
                        }}
                      >
                        {/* Thời gian */}
                        <td style={{ padding: '16px 20px', fontSize: '0.85rem' }}>
                          <div style={{ fontWeight: 600 }}>
                            {new Date(tr.occurred_at).toLocaleDateString('vi-VN')}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                            {new Date(tr.occurred_at).toLocaleTimeString('vi-VN', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                        </td>

                        {/* Tuyến chuyển tiền */}
                        <td style={{ padding: '16px 20px', fontSize: '0.85rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                              {tr.from_account_name || 'Ví nguồn'}
                            </span>
                            <span style={{ color: 'var(--primary-500)', fontSize: '0.8rem' }}>➔</span>
                            <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                              {tr.to_account_name || 'Ví đích'}
                            </span>
                          </div>
                          {tr.creator_name && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                              Bởi: {tr.creator_name}
                            </div>
                          )}
                        </td>

                        {/* Ghi chú */}
                        <td style={{ padding: '16px 20px', fontSize: '0.85rem' }}>
                          {tr.note ? (
                            <div
                              style={{
                                maxWidth: '280px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {tr.note}
                            </div>
                          ) : (
                            <span style={{ color: 'var(--text-sub)', fontStyle: 'italic', fontSize: '0.75rem' }}>
                              Không có ghi chú
                            </span>
                          )}
                        </td>

                        {/* Trạng thái */}
                        <td style={{ padding: '16px 20px' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              padding: '3px 8px',
                              borderRadius: 'var(--radius-full)',
                              background: tr.is_voided ? 'var(--error-bg)' : 'var(--success-bg)',
                              color: tr.is_voided ? 'var(--error)' : 'var(--success)',
                              border: `1px solid ${
                                tr.is_voided ? 'var(--error-border)' : 'var(--success-border)'
                              }`,
                            }}
                          >
                            {tr.is_voided ? <Ban size={12} /> : <CheckCircle size={12} />}
                            <span>{tr.is_voided ? 'Đã hủy (Void)' : 'Hoàn tất'}</span>
                          </span>
                        </td>

                        {/* Số tiền & Phí */}
                        <td style={{ padding: '16px 20px', textAlign: 'right' }}>
                          <div
                            style={{
                              fontWeight: 700,
                              fontSize: '0.95rem',
                              color: tr.is_voided ? 'var(--text-sub)' : 'var(--primary-500)',
                              textDecoration: tr.is_voided ? 'line-through' : 'none',
                            }}
                          >
                            {formatCurrency(tr.amount, curr)}
                          </div>
                          {Number(tr.fee_amount) > 0 && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                              Phí: {formatCurrency(tr.fee_amount, curr)}
                            </div>
                          )}
                        </td>

                        {/* Thao tác */}
                        <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <button
                              title="Xem chi tiết"
                              onClick={() => {
                                setSelectedTransfer(tr);
                                setIsDetailOpen(true);
                              }}
                              style={{
                                background: 'transparent',
                                border: '1px solid var(--border)',
                                color: 'var(--text-muted)',
                                padding: '6px',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                              }}
                            >
                              <Eye size={15} />
                            </button>

                            {!tr.is_voided && (
                              <button
                                title="Hủy chuyển tiền (Void)"
                                onClick={() => setTransferToVoid(tr)}
                                style={{
                                  background: 'transparent',
                                  border: '1px solid #F5BAC2',
                                  color: 'var(--error)',
                                  padding: '6px',
                                  borderRadius: 'var(--radius-sm)',
                                  cursor: 'pointer',
                                }}
                              >
                                <Ban size={15} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Phân trang */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                borderTop: '1px solid var(--border)',
                background: 'var(--surface)',
              }}
            >
              <div style={{ fontSize: '0.85rem', color: 'var(--text-sub)' }}>
                Hiển thị {offset + 1} - {offset + transfers.length} lượt chuyển tiền
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '6px 12px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--bg-input-border)',
                    borderRadius: 'var(--radius-sm)',
                    color: offset === 0 ? 'var(--text-sub)' : 'var(--text-main)',
                    fontSize: '0.85rem',
                    cursor: offset === 0 ? 'not-allowed' : 'pointer',
                    opacity: offset === 0 ? 0.5 : 1,
                  }}
                >
                  <ChevronLeft size={16} />
                  <span>Trang trước</span>
                </button>

                <span
                  style={{
                    fontSize: '0.85rem',
                    padding: '6px 12px',
                    background: 'rgba(59, 130, 246, 0.1)',
                    color: 'var(--primary-500)',
                    borderRadius: 'var(--radius-sm)',
                    fontWeight: 600,
                  }}
                >
                  Trang {Math.floor(offset / PAGE_SIZE) + 1}
                </span>

                <button
                  disabled={!hasMore}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '6px 12px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--bg-input-border)',
                    borderRadius: 'var(--radius-sm)',
                    color: !hasMore ? 'var(--text-sub)' : 'var(--text-main)',
                    fontSize: '0.85rem',
                    cursor: !hasMore ? 'not-allowed' : 'pointer',
                    opacity: !hasMore ? 0.5 : 1,
                  }}
                >
                  <span>Trang sau</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modal Chuyển Tiền Mới */}
      <CreateTransferModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Chuyển tiền thành công! Số dư hai ví đã được cập nhật chính xác.',
          });
          void fetchTransfers();
          void loadFilterOptions();
        }}
        accounts={accounts}
        categories={categories}
        defaultFromAccountId={filterAccountId}
      />

      {/* Modal Chi Tiết Chuyển Tiền */}
      <TransferDetailModal
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedTransfer(null);
        }}
        transfer={selectedTransfer}
        onVoidClick={(tr) => setTransferToVoid(tr)}
      />

      {/* Modal Xác Nhận Hủy (Void) Chuyển Tiền */}
      {transferToVoid && (
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
            if (e.target === e.currentTarget && !voidLoading) setTransferToVoid(null);
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid #F5BAC2',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-card)',
              width: '100%',
              maxWidth: '480px',
              padding: '24px',
              animation: 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '12px',
                  background: 'var(--error-bg)',
                  color: 'var(--error)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Ban size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Xác nhận hủy chuyển tiền (Void)</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                  Giao dịch sẽ được đánh dấu hủy nhưng bảo toàn lịch sử trong PostgreSQL
                </p>
              </div>
            </div>

            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '20px' }}>
              Bạn có chắc chắn muốn hủy giao dịch chuyển{' '}
              <strong style={{ color: 'var(--primary-500)' }}>
                {formatCurrency(transferToVoid.amount, transferToVoid.currency || 'VND')}
              </strong>{' '}
              từ <strong>{transferToVoid.from_account_name}</strong> sang{' '}
              <strong>{transferToVoid.to_account_name}</strong>?
              <br />
              <br />
              Hành động này sẽ <strong>tự động hoàn nguyên số dư của cả hai ví</strong> về trạng thái ban đầu.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                disabled={voidLoading}
                onClick={() => setTransferToVoid(null)}
                style={{
                  padding: '9px 16px',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-muted)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Đóng
              </button>
              <button
                type="button"
                disabled={voidLoading}
                onClick={() => void handleConfirmVoid()}
                style={{
                  padding: '9px 18px',
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  color: '#fff',
                  fontSize: '0.875rem',
                  fontWeight: 700,
                  cursor: voidLoading ? 'not-allowed' : 'pointer',
                  opacity: voidLoading ? 0.6 : 1,
                  boxShadow: 'var(--shadow-button)',
                }}
              >
                {voidLoading ? 'Đang xử lý...' : 'Xác Nhận Hủy (Void)'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
