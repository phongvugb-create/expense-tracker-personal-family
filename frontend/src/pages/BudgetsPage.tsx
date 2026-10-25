import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart,
  Plus,
  ArrowLeft,
  RefreshCw,
  Edit,
  Archive,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Layers,
  Users,
  Search,
  ReceiptText,
  ArrowRightLeft,
  CreditCard,
} from 'lucide-react';
import type { Budget, BudgetScope, BudgetStatus } from '../types/budget';
import type { Category } from '../types/category';
import type { Family } from '../types/family';
import { budgetService } from '../services/budgetService';
import { categoryService } from '../services/categoryService';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';
import { formatCurrency } from '../utils/accountUtils';
import { CreateBudgetModal } from '../components/CreateBudgetModal';
import { EditBudgetModal } from '../components/EditBudgetModal';

export function BudgetsPage() {
  const navigate = useNavigate();

  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [families, setFamilies] = useState<Family[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Filters
  const [filterScope, setFilterScope] = useState<string>('all'); // all, personal, family
  const [filterFamilyId, setFilterFamilyId] = useState<string>('all');
  const [filterCategoryId, setFilterCategoryId] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all'); // all, normal, warning, exceeded
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [budgetToArchive, setBudgetToArchive] = useState<Budget | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);

  // Load Categories & Families
  const loadDependencies = useCallback(async () => {
    try {
      const [catData, famData] = await Promise.all([
        categoryService.getCategories({ type: 'expense' }),
        familyService.getFamilies(),
      ]);
      setCategories(catData);
      setFamilies(famData);
    } catch (err: unknown) {
      console.error('Lỗi khi tải danh mục hoặc gia đình:', err);
    }
  }, []);

  useEffect(() => {
    void loadDependencies();
  }, [loadDependencies]);

  // Load Budgets từ API
  const fetchBudgets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        ...(filterScope !== 'all' ? { scope: filterScope as BudgetScope } : {}),
        ...(filterScope === 'family' && filterFamilyId !== 'all'
          ? { family_id: filterFamilyId }
          : {}),
        ...(filterCategoryId !== 'all' ? { category_id: filterCategoryId } : {}),
        include_archived: includeArchived,
        limit: 100,
        offset: 0,
      };

      const data = await budgetService.getBudgets(params);
      setBudgets(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filterScope, filterFamilyId, filterCategoryId, includeArchived]);

  useEffect(() => {
    void fetchBudgets();
  }, [fetchBudgets]);

  // Auto dismiss toast
  useEffect(() => {
    if (actionMessage) {
      const timer = setTimeout(() => {
        setActionMessage(null);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [actionMessage]);

  // Client-side filtering by status & search term
  const displayedBudgets = useMemo(() => {
    return budgets.filter((b) => {
      // Filter status
      if (filterStatus !== 'all' && b.status !== filterStatus) {
        return false;
      }
      // Search term
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const bName = (b.name || '').toLowerCase();
        const catName = (b.category_name || '').toLowerCase();
        return bName.includes(term) || catName.includes(term);
      }
      return true;
    });
  }, [budgets, filterStatus, searchTerm]);

  // Thống kê tổng quan từ danh sách ngân sách đang hoạt động
  const overviewStats = useMemo(() => {
    const activeBudgets = budgets.filter((b) => !b.is_archived);
    const totalCount = activeBudgets.length;
    const warningCount = activeBudgets.filter((b) => b.status === 'warning').length;
    const exceededCount = activeBudgets.filter((b) => b.status === 'exceeded').length;
    const normalCount = activeBudgets.filter((b) => b.status === 'normal').length;

    return {
      totalCount,
      warningCount,
      exceededCount,
      normalCount,
    };
  }, [budgets]);

  // Xử lý Archive
  const handleConfirmArchive = async () => {
    if (!budgetToArchive) return;
    try {
      setArchiveLoading(true);
      await budgetService.archiveBudget(budgetToArchive.id);
      setActionMessage({
        type: 'success',
        text: `Đã lưu trữ ngân sách "${budgetToArchive.name || budgetToArchive.category_name}" thành công.`,
      });
      setBudgetToArchive(null);
      await fetchBudgets();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setArchiveLoading(false);
    }
  };

  // Xử lý Restore
  const handleRestore = async (b: Budget) => {
    try {
      setLoading(true);
      await budgetService.restoreBudget(b.id);
      setActionMessage({
        type: 'success',
        text: `Đã khôi phục ngân sách "${b.name || b.category_name}" về trạng thái hoạt động.`,
      });
      await fetchBudgets();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setLoading(false);
    }
  };

  // Helper render status badge
  const renderStatusBadge = (status: BudgetStatus, isArchived: boolean) => {
    if (isArchived) {
      return (
        <span
          style={{
            fontSize: '0.75rem',
            padding: '3px 8px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--surface-muted)',
            color: 'var(--text-sub)',
            fontWeight: 600,
          }}
        >
          Đã lưu trữ
        </span>
      );
    }

    if (status === 'exceeded') {
      return (
        <span
          style={{
            fontSize: '0.75rem',
            padding: '3px 8px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--expense-soft)',
            border: '1px solid #F5BAC2',
            color: 'var(--expense)',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <AlertTriangle size={12} />
          Vượt hạn mức
        </span>
      );
    }

    if (status === 'warning') {
      return (
        <span
          style={{
            fontSize: '0.75rem',
            padding: '3px 8px',
            borderRadius: 'var(--radius-full)',
            background: 'var(--warning-soft)',
            border: '1px solid #FCE38E',
            color: 'var(--warning)',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <AlertTriangle size={12} />
          Sắp chạm ngưỡng
        </span>
      );
    }

    return (
      <span
        style={{
          fontSize: '0.75rem',
          padding: '3px 8px',
          borderRadius: 'var(--radius-full)',
          background: 'var(--income-soft)',
          border: '1px solid #BCE2CE',
          color: 'var(--income)',
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
        }}
      >
        <CheckCircle2 size={12} />
        An toàn
      </span>
    );
  };

  // Helper render Progress Bar
  const renderProgressBar = (budget: Budget) => {
    const usage = Number(budget.usage_percentage) || 0;
    const clampedWidth = Math.min(Math.max(usage, 0), 100);

    let barColor = 'linear-gradient(90deg, #10b981 0%, #059669 100%)';
    if (budget.status === 'warning') {
      barColor = 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
    } else if (budget.status === 'exceeded') {
      barColor = 'linear-gradient(90deg, #ef4444 0%, #b91c1c 100%)';
    }

    return (
      <div style={{ marginTop: '14px', marginBottom: '8px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.8rem',
            marginBottom: '6px',
          }}
        >
          <span style={{ color: 'var(--text-sub)' }}>
            Đã chi:{' '}
            <strong style={{ color: 'var(--text-main)' }}>
              {formatCurrency(budget.spent_amount)}
            </strong>
          </span>
          <span
            style={{
              fontWeight: 700,
              color:
                budget.status === 'exceeded'
                  ? 'var(--danger)'
                  : budget.status === 'warning'
                  ? '#fbbf24'
                  : 'var(--income)',
            }}
          >
            {budget.usage_percentage}%
          </span>
        </div>
        <div
          style={{
            width: '100%',
            height: '8px',
            background: 'var(--surface-muted)',
            borderRadius: 'var(--radius-full)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${clampedWidth}%`,
              height: '100%',
              background: barColor,
              borderRadius: 'var(--radius-full)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>
    );
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
                <PieChart size={20} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.15rem' }}>Quản lý ngân sách</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Hạn mức & cảnh báo chi tiêu cá nhân, gia đình
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              id="budgets-accounts-nav-btn"
              onClick={() => navigate('/accounts')}
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
              <CreditCard size={16} />
              <span>Quản lý ví</span>
            </button>

            <button
              id="budgets-transfers-nav-btn"
              onClick={() => navigate('/transfers')}
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
              <ArrowRightLeft size={16} />
              <span>Chuyển tiền</span>
            </button>

            <button
              id="budgets-transactions-nav-btn"
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
              id="create-budget-btn"
              onClick={() => setIsCreateOpen(true)}
              className="btn-primary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                fontSize: '0.875rem',
              }}
            >
              <Plus size={16} />
              <span>Tạo ngân sách</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
        {/* Toast message */}
        {actionMessage && (
          <div
            style={{
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              marginBottom: '20px',
              background:
                actionMessage.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
              border: `1px solid ${
                actionMessage.type === 'success' ? 'var(--success-border)' : 'var(--error-border)'
              }`,
              color: actionMessage.type === 'success' ? 'var(--success)' : 'var(--error)',
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span>{actionMessage.text}</span>
            <button
              onClick={() => setActionMessage(null)}
              style={{
                background: 'none',
                border: 'none',
                color: 'inherit',
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Overview Stats Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '16px',
            marginBottom: '28px',
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--secondary-soft)',
                color: 'var(--primary-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <PieChart size={22} />
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>Đang hoạt động</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-main)' }}>
                {overviewStats.totalCount}
              </div>
            </div>
          </div>

          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--income-soft)',
                color: 'var(--income)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <CheckCircle2 size={22} />
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>Trạng thái An toàn</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--income)' }}>
                {overviewStats.normalCount}
              </div>
            </div>
          </div>

          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--warning-soft)',
                color: 'var(--warning)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={22} />
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>Sắp chạm ngưỡng (&gt;= 80%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--warning)' }}>
                {overviewStats.warningCount}
              </div>
            </div>
          </div>

          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--expense-soft)',
                color: 'var(--expense)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={22} />
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>Vượt hạn mức (&gt;= 100%)</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--expense)' }}>
                {overviewStats.exceededCount}
              </div>
            </div>
          </div>
        </div>

        {/* Filters Toolbar */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            padding: '18px',
            marginBottom: '24px',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '14px',
          }}
        >
          {/* Scope filter */}
          <div style={{ minWidth: '150px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
              Phạm vi
            </label>
            <select
              value={filterScope}
              onChange={(e) => setFilterScope(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              <option value="all">Tất cả phạm vi</option>
              <option value="personal">Ví cá nhân</option>
              <option value="family">Gia đình</option>
            </select>
          </div>

          {/* Family filter (khi scope family) */}
          {filterScope === 'family' && (
            <div style={{ minWidth: '180px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
                Nhóm gia đình
              </label>
              <select
                value={filterFamilyId}
                onChange={(e) => setFilterFamilyId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                <option value="all">Tất cả nhóm</option>
                {families.map((fam) => (
                  <option key={fam.id} value={fam.id}>
                    {fam.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Category filter */}
          <div style={{ minWidth: '180px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
              Danh mục
            </label>
            <select
              value={filterCategoryId}
              onChange={(e) => setFilterCategoryId(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              <option value="all">Tất cả danh mục</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status filter */}
          <div style={{ minWidth: '150px' }}>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
              Trạng thái cảnh báo
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="normal">An toàn (&lt; Ngưỡng)</option>
              <option value="warning">Cảnh báo (&gt;= Ngưỡng)</option>
              <option value="exceeded">Vượt hạn mức (&gt;= 100%)</option>
            </select>
          </div>

          {/* Include archived checkbox */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '18px' }}>
            <input
              type="checkbox"
              id="includeArchived"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <label
              htmlFor="includeArchived"
              style={{ fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              Xem cả ngân sách đã lưu trữ
            </label>
          </div>

          {/* Search box */}
          <div style={{ flex: 1, minWidth: '220px', marginLeft: 'auto', marginTop: '18px' }}>
            <div style={{ position: 'relative' }}>
              <Search
                size={16}
                color="var(--text-sub)"
                style={{ position: 'absolute', left: '10px', top: '10px' }}
              />
              <input
                type="text"
                placeholder="Tìm theo tên ngân sách, danh mục..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px 8px 34px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Refresh button */}
          <button
            onClick={() => void fetchBudgets()}
            disabled={loading}
            title="Tải lại danh sách"
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--surface-muted)',
              border: '1px solid var(--border)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              marginTop: '18px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.85rem',
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Làm mới</span>
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div
            style={{
              background: 'var(--error-bg)',
              border: '1px solid var(--error-border)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              textAlign: 'center',
              color: 'var(--error)',
              marginBottom: '24px',
            }}
          >
            <AlertTriangle size={32} style={{ margin: '0 auto 12px' }} />
            <p style={{ fontWeight: 600, marginBottom: '8px' }}>Không thể tải danh sách ngân sách</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-sub)', marginBottom: '16px' }}>
              {error}
            </p>
            <button
              onClick={() => void fetchBudgets()}
              className="btn-primary"
              style={{ padding: '8px 16px', fontSize: '0.85rem' }}
            >
              Thử lại ngay
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div
            style={{
              padding: '60px 0',
              textAlign: 'center',
              color: 'var(--text-sub)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <RefreshCw size={28} className="spin" style={{ color: 'var(--primary-500)' }} />
            <p style={{ fontSize: '0.9rem' }}>Đang tải dữ liệu ngân sách và tính toán chi tiêu...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && displayedBudgets.length === 0 && (
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '48px 24px',
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
              <PieChart size={28} />
            </div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '8px' }}>
              Chưa có ngân sách nào phù hợp
            </h3>
            <p
              style={{
                color: 'var(--text-sub)',
                fontSize: '0.875rem',
                maxWidth: '460px',
                margin: '0 auto 20px',
                lineHeight: 1.5,
              }}
            >
              Hãy tạo ngân sách để kiểm soát chi tiêu cho các danh mục cần thiết, nhận cảnh báo khi sắp chạm hạn mức.
            </p>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="btn-primary"
              style={{ padding: '9px 20px', fontSize: '0.875rem' }}
            >
              <Plus size={16} />
              <span>Tạo ngân sách đầu tiên</span>
            </button>
          </div>
        )}

        {/* Budget Cards Grid */}
        {!loading && !error && displayedBudgets.length > 0 && (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
              gap: '20px',
            }}
          >
            {displayedBudgets.map((b) => (
              <div
                key={b.id}
                style={{
                  background: 'var(--bg-card)',
                  border: `1px solid ${
                    b.status === 'exceeded'
                      ? 'rgba(239, 68, 68, 0.4)'
                      : b.status === 'warning'
                      ? 'rgba(245, 158, 11, 0.4)'
                      : 'var(--border)'
                  }`,
                  borderRadius: 'var(--radius-lg)',
                  padding: '22px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  opacity: b.is_archived ? 0.65 : 1,
                  boxShadow:
                    b.status === 'exceeded'
                      ? '0 4px 20px rgba(239, 68, 68, 0.1)'
                      : '0 4px 12px rgba(0, 0, 0, 0.2)',
                  transition: 'all 0.2s',
                }}
              >
                <div>
                  {/* Card Header: Category & Badges */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: '12px',
                      marginBottom: '12px',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '0.75rem',
                          color: 'var(--text-sub)',
                          marginBottom: '4px',
                        }}
                      >
                        {b.scope === 'personal' ? (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              background: 'var(--secondary-soft)',
                              color: 'var(--secondary)',
                              padding: '2px 6px',
                              borderRadius: 'var(--radius-sm)',
                              fontWeight: 600,
                            }}
                          >
                            <Layers size={11} /> Cá nhân
                          </span>
                        ) : (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              background: 'rgba(99, 102, 241, 0.12)',
                              color: 'var(--text-primary)',
                              padding: '2px 6px',
                              borderRadius: 'var(--radius-sm)',
                              fontWeight: 600,
                            }}
                          >
                            <Users size={11} /> Gia đình
                          </span>
                        )}
                        <span>•</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>
                          {b.category_name || 'Chi tiêu'}
                        </span>
                      </div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                        {b.name || b.category_name || 'Ngân sách chi tiêu'}
                      </h3>
                    </div>

                    <div>{renderStatusBadge(b.status, b.is_archived)}</div>
                  </div>

                  {/* Period date */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.8rem',
                      color: 'var(--text-sub)',
                      marginBottom: '14px',
                    }}
                  >
                    <Calendar size={13} />
                    <span>
                      {new Date(b.period_start).toLocaleDateString('vi-VN')} –{' '}
                      {new Date(b.period_end).toLocaleDateString('vi-VN')}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  {renderProgressBar(b)}

                  {/* Financial Metrics */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '10px',
                      marginTop: '14px',
                      background: 'var(--surface-muted)',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-sub)' }}>HẠN MỨC</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                        {formatCurrency(b.amount_limit)}
                      </div>
                    </div>

                    <div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-sub)' }}>
                        {b.status === 'exceeded' ? 'VƯỢT HẠN MỨC' : 'CÒN LẠI'}
                      </div>
                      <div
                        style={{
                          fontSize: '0.95rem',
                          fontWeight: 700,
                          color: b.status === 'exceeded' ? 'var(--danger)' : 'var(--income)',
                        }}
                      >
                        {b.status === 'exceeded'
                          ? `+${formatCurrency(b.overspent_amount)}`
                          : formatCurrency(b.remaining_amount)}
                      </div>
                    </div>
                  </div>

                  {/* Warning Threshold Info */}
                  <div
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-sub)',
                      marginTop: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <span>Ngưỡng cảnh báo:</span>
                    <strong style={{ color: 'var(--text-muted)' }}>{b.warning_threshold}%</strong>
                  </div>
                </div>

                {/* Card Actions Footer */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '8px',
                    marginTop: '18px',
                    paddingTop: '14px',
                    borderTop: '1px solid var(--border)',
                  }}
                >
                  {!b.is_archived ? (
                    <>
                      <button
                        onClick={() => setEditingBudget(b)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '6px 12px',
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--surface-muted)',
                          border: '1px solid var(--border)',
                          color: 'var(--text-muted)',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Edit size={13} />
                        <span>Chỉnh sửa</span>
                      </button>
                      <button
                        onClick={() => setBudgetToArchive(b)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '6px 12px',
                          borderRadius: 'var(--radius-md)',
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.2)',
                          color: 'var(--danger)',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Archive size={13} />
                        <span>Lưu trữ</span>
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => void handleRestore(b)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '6px 14px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--income-soft)',
                        border: '1px solid #BCE2CE',
                        color: '#6ee7b7',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      <RotateCcw size={13} />
                      <span>Khôi phục ngân sách</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      <CreateBudgetModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={(newB) => {
          setActionMessage({
            type: 'success',
            text: `Đã tạo ngân sách "${newB.name || newB.category_name}" thành công!`,
          });
          void fetchBudgets();
        }}
        categories={categories}
        families={families}
      />

      {/* Edit Modal */}
      <EditBudgetModal
        isOpen={!!editingBudget}
        onClose={() => setEditingBudget(null)}
        onSuccess={(updatedB) => {
          setActionMessage({
            type: 'success',
            text: `Đã cập nhật ngân sách "${updatedB.name || updatedB.category_name}" thành công!`,
          });
          void fetchBudgets();
        }}
        budget={editingBudget}
        categories={categories}
      />

      {/* Archive Confirmation Dialog */}
      {budgetToArchive && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 60,
            padding: '16px',
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              maxWidth: '460px',
              width: '100%',
              padding: '24px',
              boxShadow: 'var(--shadow-modal)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  background: 'var(--expense-soft)',
                  color: 'var(--expense)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Archive size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>
                Xác nhận lưu trữ ngân sách
              </h3>
            </div>

            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '20px' }}>
              Bạn có chắc chắn muốn lưu trữ ngân sách{' '}
              <strong>"{budgetToArchive.name || budgetToArchive.category_name}"</strong>? Ngân sách
              sẽ được ẩn khỏi danh sách chính nhưng dữ liệu lịch sử và các giao dịch liên quan vẫn
              được bảo toàn hoàn toàn. Bạn có thể khôi phục lại bất kỳ lúc nào.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setBudgetToArchive(null)}
                disabled={archiveLoading}
                style={{
                  padding: '9px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmArchive()}
                disabled={archiveLoading}
                style={{
                  padding: '9px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(239, 68, 68, 0.8)',
                  border: 'none',
                  color: '#fff',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  cursor: archiveLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {archiveLoading ? 'Đang lưu trữ...' : 'Xác nhận lưu trữ'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
