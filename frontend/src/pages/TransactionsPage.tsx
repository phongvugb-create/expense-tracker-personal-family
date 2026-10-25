import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ReceiptText,
  Plus,
  ArrowLeft,
  RefreshCw,
  Trash2,
  Edit,
  Eye,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Wallet,
  ChevronLeft,
  ChevronRight,
  X,
  CreditCard,
  ArrowLeftRight,
  PieChart,
} from 'lucide-react';
import type { Account } from '../types/account';
import type { Category, CategoryType } from '../types/category';
import type { Transaction } from '../types/transaction';
import { accountService } from '../services/accountService';
import { categoryService } from '../services/categoryService';
import { transactionService } from '../services/transactionService';
import { getErrorMessage } from '../services/apiClient';
import { formatCurrency } from '../utils/accountUtils';
import { CreateTransactionModal } from '../components/CreateTransactionModal';
import { EditTransactionModal } from '../components/EditTransactionModal';
import { TransactionDetailModal } from '../components/TransactionDetailModal';

const PAGE_SIZE = 15;

export function TransactionsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Danh sách ví và danh mục phục vụ bộ lọc & tạo giao dịch
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Dữ liệu giao dịch
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Bộ lọc
  const [filterType, setFilterType] = useState<CategoryType | 'all'>('all');
  const [filterAccountId, setFilterAccountId] = useState<string>(() => {
    return searchParams.get('account_id') || '';
  });
  const [filterCategoryId, setFilterCategoryId] = useState<string>('');
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');

  // Phân trang
  const [offset, setOffset] = useState<number>(0);
  const [hasMore, setHasMore] = useState<boolean>(false);

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);

  // Xóa mềm confirm modal
  const [txToDelete, setTxToDelete] = useState<Transaction | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  /**
   * Tải danh sách ví và danh mục ban đầu
   */
  const loadFilterOptions = useCallback(async () => {
    try {
      const [accs, cats] = await Promise.all([
        accountService.getAccounts(),
        categoryService.getCategories(),
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
   * Tải danh sách giao dịch theo bộ lọc và phân trang từ Backend API
   */
  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Validate date_from <= date_to
      if (filterDateFrom && filterDateTo && filterDateFrom > filterDateTo) {
        setError('Ngày bắt đầu không được lớn hơn ngày kết thúc.');
        setLoading(false);
        return;
      }

      const params = {
        ...(filterType !== 'all' ? { type: filterType } : {}),
        ...(filterAccountId ? { account_id: filterAccountId } : {}),
        ...(filterCategoryId ? { category_id: filterCategoryId } : {}),
        ...(filterDateFrom ? { date_from: new Date(filterDateFrom).toISOString() } : {}),
        ...(filterDateTo
          ? {
              date_to: new Date(`${filterDateTo}T23:59:59.999Z`).toISOString(),
            }
          : {}),
        limit: PAGE_SIZE + 1, // Lấy dư 1 phần tử để xác định hasMore
        offset,
      };

      const data = await transactionService.getTransactions(params);

      if (data.length > PAGE_SIZE) {
        setHasMore(true);
        setTransactions(data.slice(0, PAGE_SIZE));
      } else {
        setHasMore(false);
        setTransactions(data);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filterType, filterAccountId, filterCategoryId, filterDateFrom, filterDateTo, offset]);

  useEffect(() => {
    void fetchTransactions();
  }, [fetchTransactions]);

  // Đổi bộ lọc thì reset offset về 0
  const handleFilterChange = (updater: () => void) => {
    updater();
    setOffset(0);
  };

  /**
   * Tính toán thống kê trên trang hiện tại
   */
  const pageStats = useMemo(() => {
    let incomeSum = 0;
    let expenseSum = 0;
    let hasMixedCurrencies = false;
    let baseCurrency = 'VND';

    if (transactions.length > 0) {
      // Tìm ví của giao dịch đầu tiên để lấy currency mẫu
      const firstAcc = accounts.find((a) => a.id === transactions[0].account_id);
      if (firstAcc) baseCurrency = firstAcc.currency;

      for (const tx of transactions) {
        const acc = accounts.find((a) => a.id === tx.account_id);
        if (acc && acc.currency !== baseCurrency) {
          hasMixedCurrencies = true;
        }
        const val = Number(tx.amount);
        if (!isNaN(val)) {
          if (tx.type === 'income') incomeSum += val;
          if (tx.type === 'expense') expenseSum += val;
        }
      }
    }

    return {
      incomeSum,
      expenseSum,
      hasMixedCurrencies,
      currency: baseCurrency,
      count: transactions.length,
    };
  }, [transactions, accounts]);

  /**
   * Xử lý xóa mềm giao dịch
   */
  const handleConfirmDelete = async () => {
    if (!txToDelete) return;
    try {
      setDeleteLoading(true);
      await transactionService.deleteTransaction(txToDelete.id);
      setActionMessage({
        type: 'success',
        text: 'Đã xóa mềm giao dịch thành công. Số dư ví đã được tự động hoàn nguyên!',
      });
      setTxToDelete(null);
      void fetchTransactions();
      // Reload lại danh sách ví để cập nhật số dư mới nhất
      void loadFilterOptions();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setDeleteLoading(false);
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
                <ReceiptText size={20} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em' }}>
                  Sổ Giao Dịch
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Lịch sử Thu & Chi thực tế
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              id="transactions-budgets-nav-btn"
              onClick={() => navigate('/budgets')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--warning-soft)',
                border: '1px solid #FCE38E',
                color: 'var(--warning)',
                padding: '9px 16px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <PieChart size={16} />
              <span>Ngân sách</span>
            </button>

            <button
              id="transactions-transfers-nav-btn"
              onClick={() => navigate('/transfers')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'var(--secondary-soft)',
                border: '1px solid #C4DDFC',
                color: 'var(--secondary)',
                padding: '9px 16px',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <ArrowLeftRight size={16} />
              <span>Chuyển tiền</span>
            </button>

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
              <span>Ghi Giao Dịch Mới</span>
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

        {/* Thống kê nhanh trang hiện tại */}
        {transactions.length > 0 && !pageStats.hasMixedCurrencies && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '16px',
              marginBottom: '24px',
            }}
          >
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '18px 20px',
              }}
            >
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
                TỔNG THU TRANG NÀY ({pageStats.count} GIAO DỊCH)
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--success)' }}>
                +{formatCurrency(pageStats.incomeSum.toFixed(2), pageStats.currency)}
              </div>
            </div>

            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '18px 20px',
              }}
            >
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
                TỔNG CHI TRANG NÀY
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--error)' }}>
                -{formatCurrency(pageStats.expenseSum.toFixed(2), pageStats.currency)}
              </div>
            </div>

            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '18px 20px',
              }}
            >
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
                DÒNG TIỀN RÒNG TRANG NÀY
              </div>
              <div
                style={{
                  fontSize: '1.4rem',
                  fontWeight: 700,
                  color:
                    pageStats.incomeSum - pageStats.expenseSum >= 0
                      ? 'var(--primary-500)'
                      : 'var(--error)',
                }}
              >
                {pageStats.incomeSum - pageStats.expenseSum >= 0 ? '+' : ''}
                {formatCurrency((pageStats.incomeSum - pageStats.expenseSum).toFixed(2), pageStats.currency)}
              </div>
            </div>
          </div>
        )}

        {/* Thanh Bộ Lọc Đa Chiều */}
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
            {/* Lọc Loại Giao Dịch */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '6px' }}>
                Loại giao dịch
              </label>
              <select
                value={filterType}
                onChange={(e) =>
                  handleFilterChange(() => setFilterType(e.target.value as CategoryType | 'all'))
                }
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
                <option value="all">Tất cả loại giao dịch</option>
                <option value="expense">Khoản Chi tiêu (-)</option>
                <option value="income">Khoản Thu nhập (+)</option>
              </select>
            </div>

            {/* Lọc Theo Ví */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '6px' }}>
                Ví tài chính
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

            {/* Lọc Theo Danh Mục */}
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '6px' }}>
                Danh mục
              </label>
              <select
                value={filterCategoryId}
                onChange={(e) => handleFilterChange(() => setFilterCategoryId(e.target.value))}
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
                <option value="">Tất cả danh mục</option>
                {categories
                  .filter((cat) => filterType === 'all' || cat.type === filterType)
                  .map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name} ({cat.type === 'income' ? 'Thu' : 'Chi'})
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

            {/* Nút Làm Mới */}
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => {
                  setFilterType('all');
                  setFilterAccountId('');
                  setFilterCategoryId('');
                  setFilterDateFrom('');
                  setFilterDateTo('');
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
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>Đặt lại</span>
              </button>
              <button
                type="button"
                onClick={() => void fetchTransactions()}
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

        {/* Danh Sách Giao Dịch */}
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
            <div>Đang tải dữ liệu giao dịch từ PostgreSQL...</div>
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
            <div style={{ fontWeight: 600, marginBottom: '8px' }}>Không thể tải lịch sử giao dịch</div>
            <div style={{ fontSize: '0.875rem', marginBottom: '16px' }}>{error}</div>
            <button
              onClick={() => void fetchTransactions()}
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
        ) : transactions.length === 0 ? (
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
              <ReceiptText size={32} />
            </div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px' }}>
              Chưa có giao dịch nào phù hợp
            </h3>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.9rem', maxWidth: '420px', margin: '0 auto 20px' }}>
              Bạn chưa ghi nhận khoản thu chi nào với bộ lọc hiện tại hoặc chưa tạo giao dịch mới.
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
              <span>Ghi giao dịch đầu tiên</span>
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
                      DANH MỤC & GHI CHÚ
                    </th>
                    <th style={{ padding: '14px 20px', fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                      VÍ TÀI CHÍNH
                    </th>
                    <th style={{ padding: '14px 20px', fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                      LOẠI
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
                      SỐ TIỀN
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
                  {transactions.map((tx) => {
                    const isIncome = tx.type === 'income';
                    const txAcc = accounts.find((a) => a.id === tx.account_id);
                    const curr = txAcc?.currency || 'VND';

                    return (
                      <tr
                        key={tx.id}
                        style={{
                          borderBottom: '1px solid var(--border)',
                          transition: 'background 0.15s ease',
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
                            {new Date(tx.occurred_at).toLocaleDateString('vi-VN')}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                            {new Date(tx.occurred_at).toLocaleTimeString('vi-VN', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                        </td>

                        {/* Danh mục & Ghi chú */}
                        <td style={{ padding: '16px 20px' }}>
                          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                            {tx.category_name || 'Chung'}
                          </div>
                          {tx.note ? (
                            <div
                              style={{
                                fontSize: '0.8rem',
                                color: 'var(--text-muted)',
                                maxWidth: '320px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {tx.note}
                            </div>
                          ) : (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontStyle: 'italic' }}>
                              Không có ghi chú
                            </div>
                          )}
                        </td>

                        {/* Ví */}
                        <td style={{ padding: '16px 20px', fontSize: '0.85rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Wallet size={14} color="var(--primary-500)" />
                            <span>{tx.account_name || txAcc?.name || 'Ví tài chính'}</span>
                          </div>
                          {tx.creator_name && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                              Bởi: {tx.creator_name}
                            </div>
                          )}
                        </td>

                        {/* Loại */}
                        <td style={{ padding: '16px 20px' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              padding: '4px 10px',
                              borderRadius: 'var(--radius-full)',
                              background: isIncome ? 'var(--success-bg)' : 'var(--error-bg)',
                              color: isIncome ? 'var(--success)' : 'var(--error)',
                              border: `1px solid ${
                                isIncome ? 'var(--success-border)' : 'var(--error-border)'
                              }`,
                            }}
                          >
                            {isIncome ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}
                            <span>{isIncome ? 'Thu nhập' : 'Chi tiêu'}</span>
                          </span>
                        </td>

                        {/* Số tiền */}
                        <td
                          style={{
                            padding: '16px 20px',
                            textAlign: 'right',
                            fontWeight: 700,
                            fontSize: '0.95rem',
                            color: isIncome ? 'var(--success)' : 'var(--error)',
                          }}
                        >
                          {isIncome ? '+' : '-'}{formatCurrency(tx.amount, curr)}
                        </td>

                        {/* Thao tác */}
                        <td style={{ padding: '16px 20px', textAlign: 'center' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <button
                              title="Xem chi tiết"
                              onClick={() => {
                                setSelectedTx(tx);
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
                            <button
                              title="Chỉnh sửa"
                              onClick={() => {
                                setSelectedTx(tx);
                                setIsEditOpen(true);
                              }}
                              style={{
                                background: 'transparent',
                                border: '1px solid #C4DDFC',
                                color: 'var(--primary-500)',
                                padding: '6px',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                              }}
                            >
                              <Edit size={15} />
                            </button>
                            <button
                              title="Xóa mềm"
                              onClick={() => setTxToDelete(tx)}
                              style={{
                                background: 'transparent',
                                border: '1px solid #F5BAC2',
                                color: 'var(--error)',
                                padding: '6px',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                              }}
                            >
                              <Trash2 size={15} />
                            </button>
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
                Hiển thị {offset + 1} - {offset + transactions.length} giao dịch
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

      {/* Modal Thêm Giao Dịch */}
      <CreateTransactionModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Tạo giao dịch thành công! Số dư ví đã được cập nhật.',
          });
          void fetchTransactions();
          void loadFilterOptions();
        }}
        accounts={accounts}
        categories={categories}
        defaultAccountId={filterAccountId}
        defaultType={filterType !== 'all' ? filterType : 'expense'}
      />

      {/* Modal Chỉnh Sửa Giao Dịch */}
      <EditTransactionModal
        isOpen={isEditOpen}
        onClose={() => {
          setIsEditOpen(false);
          setSelectedTx(null);
        }}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Cập nhật giao dịch thành công! Số dư ví đã được tự động đồng bộ.',
          });
          void fetchTransactions();
          void loadFilterOptions();
        }}
        transaction={selectedTx}
        accounts={accounts}
        categories={categories}
      />

      {/* Modal Chi Tiết Giao Dịch */}
      <TransactionDetailModal
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedTx(null);
        }}
        transaction={selectedTx}
      />

      {/* Modal Xác Nhận Xóa Mềm */}
      {txToDelete && (
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
            if (e.target === e.currentTarget && !deleteLoading) setTxToDelete(null);
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
                <Trash2 size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Xác nhận xóa mềm giao dịch</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                  Giao dịch sẽ bị ẩn khỏi sổ giao dịch nhưng bảo toàn trong PostgreSQL
                </p>
              </div>
            </div>

            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '20px' }}>
              Bạn có chắc chắn muốn xóa giao dịch <strong>{txToDelete.category_name}</strong> với số tiền{' '}
              <strong style={{ color: txToDelete.type === 'income' ? 'var(--success)' : 'var(--error)' }}>
                {txToDelete.type === 'income' ? '+' : '-'}{formatCurrency(txToDelete.amount)}
              </strong>?
              <br />
              Hành động này sẽ <strong>tự động hoàn nguyên số dư của ví</strong> liên quan.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                disabled={deleteLoading}
                onClick={() => setTxToDelete(null)}
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
                Hủy bỏ
              </button>
              <button
                type="button"
                disabled={deleteLoading}
                onClick={() => void handleConfirmDelete()}
                style={{
                  padding: '9px 18px',
                  background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  color: '#fff',
                  fontSize: '0.875rem',
                  fontWeight: 700,
                  cursor: deleteLoading ? 'not-allowed' : 'pointer',
                  opacity: deleteLoading ? 0.6 : 1,
                  boxShadow: 'var(--shadow-button)',
                }}
              >
                {deleteLoading ? 'Đang xóa...' : 'Đồng ý xóa'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
