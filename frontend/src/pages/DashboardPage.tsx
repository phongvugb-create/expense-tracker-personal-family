import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  WalletCards,
  LogOut,
  User as UserIcon,
  CreditCard,
  PieChart,
  Users,
  CalendarCheck,
  ArrowRight,
  ArrowLeftRight,
  ReceiptText,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  RefreshCw,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  ChevronRight,
  BarChart3,
  Repeat,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { dashboardService } from '../services/dashboardService';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';
import { formatCurrency } from '../utils/accountUtils';
import { NotificationBell } from '../components/NotificationBell';
import type { DashboardSummaryResponse, DashboardScope, MonthlyTrendPoint } from '../types/dashboard';
import type { Family } from '../types/family';

export function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Date filters: mặc định tháng và năm hiện tại
  const now = new Date();
  const [selectedYear, setSelectedYear] = useState<number>(now.getFullYear());
  const [selectedMonth, setSelectedMonth] = useState<number>(now.getMonth() + 1);
  const [selectedScope, setSelectedScope] = useState<DashboardScope>('all');
  const [selectedFamilyId, setSelectedFamilyId] = useState<string>('');

  const [families, setFamilies] = useState<Family[]>([]);
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredTrendPoint, setHoveredTrendPoint] = useState<MonthlyTrendPoint | null>(null);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Load danh sách gia đình
  const loadFamilies = useCallback(async () => {
    try {
      const famData = await familyService.getFamilies();
      setFamilies(famData);
      if (famData.length > 0 && !selectedFamilyId) {
        setSelectedFamilyId(famData[0].id);
      }
    } catch (err: unknown) {
      console.error('Lỗi khi tải danh sách gia đình:', err);
    }
  }, [selectedFamilyId]);

  useEffect(() => {
    void loadFamilies();
  }, [loadFamilies]);

  // Load Dashboard summary data
  const fetchSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        year: selectedYear,
        month: selectedMonth,
        scope: selectedScope,
        ...(selectedScope === 'family' && selectedFamilyId
          ? { family_id: selectedFamilyId }
          : {}),
      };

      const data = await dashboardService.getSummary(params);
      setSummary(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [selectedYear, selectedMonth, selectedScope, selectedFamilyId]);

  useEffect(() => {
    void fetchSummary();
  }, [fetchSummary]);

  // Render SVG Trend Chart with Interactive Tooltip
  const renderTrendChart = () => {
    if (!summary || summary.monthly_trend.length === 0) {
      return (
        <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
          Chưa có dữ liệu giao dịch trong 6 tháng gần nhất để vẽ biểu đồ.
        </div>
      );
    }

    // Lọc lấy trend của VND (hoặc currency đầu tiên)
    const primaryCurrency = summary.cash_flow_by_currency[0]?.currency || 'VND';
    const points = summary.monthly_trend.filter((p) => p.currency === primaryCurrency);

    if (points.length === 0) {
      return (
        <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
          Chưa có dữ liệu giao dịch ({primaryCurrency}) trong 6 tháng gần nhất.
        </div>
      );
    }

    const maxVal = Math.max(
      ...points.map((p) => Math.max(Number(p.income) || 0, Number(p.expense) || 0)),
      1
    );

    const chartHeight = 170;

    // Helper tính chiều cao tỷ lệ đảm bảo các tháng nhỏ vẫn hiển thị rõ ràng và có thể bấm/rê chuột
    const getBarHeight = (val: number, max: number, maxHeight: number) => {
      if (val <= 0) return 0;
      // Đảm bảo tối thiểu 7px cho các giá trị thực tế > 0 để không bị bẹp thành đường thẳng vô hình
      const minHeight = 7;
      const usableHeight = maxHeight - minHeight;
      return minHeight + (val / max) * usableHeight;
    };

    // Điểm dữ liệu được hiển thị trên thanh thanh tra (mặc định tháng mới nhất nếu chưa rê chuột)
    const currentActive = hoveredTrendPoint || points[points.length - 1];

    return (
      <div style={{ marginTop: '16px' }}>
        {/* Active Month Live Inspector Banner & Legend */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '10px',
            marginBottom: '16px',
            padding: '10px 14px',
            background: 'var(--surface-muted)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
          }}
        >
          {/* Active Month Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap', fontSize: '0.825rem' }}>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentActive.display_label}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--income)' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Thu:</span>
              <strong style={{ color: 'var(--income)' }}>+{formatCurrency(currentActive.income, currentActive.currency)}</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--expense)' }} />
              <span style={{ color: 'var(--text-secondary)' }}>Chi:</span>
              <strong style={{ color: 'var(--expense)' }}>-{formatCurrency(currentActive.expense, currentActive.currency)}</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Dòng tiền:</span>
              <strong style={{ color: Number(currentActive.net) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                {Number(currentActive.net) >= 0 ? '+' : ''}{formatCurrency(currentActive.net, currentActive.currency)}
              </strong>
            </div>
          </div>

          {/* Quick legend info */}
          <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontStyle: 'italic' }}>
            {hoveredTrendPoint ? 'Đang xem chi tiết' : 'Rê chuột hoặc chạm cột để xem'}
          </div>
        </div>

        {/* Bar chart canvas with reference lines */}
        <div
          style={{
            position: 'relative',
            height: `${chartHeight + 36}px`,
            borderBottom: '1px solid var(--border)',
            paddingBottom: '26px',
          }}
        >
          {/* Reference grid line at 50% */}
          <div
            style={{
              position: 'absolute',
              top: `${(chartHeight / 2) + 6}px`,
              left: 0,
              right: 0,
              borderTop: '1px dashed #E1E8DF',
              pointerEvents: 'none',
              zIndex: 0,
            }}
          />

          {/* Columns container */}
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              height: `${chartHeight}px`,
              gap: '8px',
              position: 'relative',
              zIndex: 1,
            }}
          >
            {points.map((p) => {
              const incVal = Number(p.income) || 0;
              const expVal = Number(p.expense) || 0;
              const incH = getBarHeight(incVal, maxVal, chartHeight - 20);
              const expH = getBarHeight(expVal, maxVal, chartHeight - 20);
              const isHovered = hoveredTrendPoint?.month_key === p.month_key;

              return (
                <div
                  key={p.month_key}
                  onMouseEnter={() => setHoveredTrendPoint(p)}
                  onMouseLeave={() => setHoveredTrendPoint(null)}
                  onClick={() => setHoveredTrendPoint(isHovered ? null : p)}
                  onTouchStart={() => setHoveredTrendPoint(p)}
                  style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    height: '100%',
                    justifyContent: 'flex-end',
                    cursor: 'pointer',
                    position: 'relative',
                    padding: '0 4px',
                    borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
                    background: isHovered ? 'rgba(40, 107, 87, 0.08)' : 'transparent',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {/* Floating tooltip on hover */}
                  {isHovered && (
                    <div
                      style={{
                        position: 'absolute',
                        bottom: 'calc(100% + 8px)',
                        zIndex: 50,
                        background: '#FFFFFF',
                        border: '1px solid var(--border)',
                        boxShadow: '0 10px 25px -4px rgba(36, 53, 44, 0.15), 0 0 0 1px var(--border)',
                        borderRadius: 'var(--radius-md)',
                        padding: '10px 14px',
                        whiteSpace: 'nowrap',
                        pointerEvents: 'none',
                        animation: 'modalFadeIn 0.15s ease-out',
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-primary)', marginBottom: '6px' }}>
                        Tháng {p.display_label}
                      </div>
                      <div style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--income)' }} />
                        <span style={{ color: 'var(--text-secondary)' }}>Thu:</span>
                        <strong style={{ color: 'var(--income)' }}>+{formatCurrency(p.income, p.currency)}</strong>
                      </div>
                      <div style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--expense)' }} />
                        <span style={{ color: 'var(--text-secondary)' }}>Chi:</span>
                        <strong style={{ color: 'var(--expense)' }}>-{formatCurrency(p.expense, p.currency)}</strong>
                      </div>
                      <div style={{ fontSize: '0.72rem', borderTop: '1px solid var(--border)', paddingTop: '4px', marginTop: '4px', color: 'var(--text-secondary)' }}>
                        Dòng tiền: <strong style={{ color: Number(p.net) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                          {Number(p.net) >= 0 ? '+' : ''}{formatCurrency(p.net, p.currency)}
                        </strong>
                      </div>
                    </div>
                  )}

                  {/* Bars side by side */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-end',
                      gap: '4px',
                      width: '100%',
                      justifyContent: 'center',
                    }}
                  >
                    {/* Income bar */}
                    <div
                      style={{
                        width: '42%',
                        maxWidth: '22px',
                        height: `${incH}px`,
                        background: 'linear-gradient(180deg, #2EC183 0%, #21845A 100%)',
                        borderRadius: '4px 4px 0 0',
                        boxShadow: isHovered ? '0 0 8px rgba(33, 132, 90, 0.4)' : 'none',
                        transition: 'height 0.3s ease, filter 0.15s ease',
                        filter: isHovered ? 'brightness(1.08)' : 'none',
                      }}
                    />
                    {/* Expense bar */}
                    <div
                      style={{
                        width: '42%',
                        maxWidth: '22px',
                        height: `${expH}px`,
                        background: 'linear-gradient(180deg, #E67A66 0%, #C75D49 100%)',
                        borderRadius: '4px 4px 0 0',
                        boxShadow: isHovered ? '0 0 8px rgba(199, 93, 73, 0.4)' : 'none',
                        transition: 'height 0.3s ease, filter 0.15s ease',
                        filter: isHovered ? 'brightness(1.08)' : 'none',
                      }}
                    />
                  </div>

                  {/* Month label beneath bar */}
                  <span
                    style={{
                      position: 'absolute',
                      bottom: '-22px',
                      fontSize: '0.75rem',
                      fontWeight: isHovered ? 700 : 500,
                      color: isHovered ? 'var(--primary)' : 'var(--text-secondary)',
                      transition: 'color 0.15s ease',
                    }}
                  >
                    {p.display_label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', paddingBottom: '60px' }}>
      {/* Top Navbar */}
      <header className="app-header">
        <div className="dashboard-header-container">
          {/* 1. Left Brand */}
          <div className="dashboard-brand">
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
              <div style={{ fontWeight: 700, fontSize: '1.05rem', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                Expense Tracker
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-sub)' }}>
                Bản Demo Quản Lý Chi Tiêu
              </div>
            </div>
          </div>

          {/* 2. Middle Navigation items */}
          <nav className="dashboard-nav">
            <button
              id="dashboard-families-nav-btn"
              onClick={() => navigate('/families')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--secondary-soft)',
                border: '1px solid #C4DDFC',
                color: 'var(--secondary)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <Users size={15} />
              <span>Gia đình</span>
            </button>

            <button
              id="dashboard-budgets-nav-btn"
              onClick={() => navigate('/budgets')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--warning-soft)',
                border: '1px solid #FCE38E',
                color: 'var(--warning)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <PieChart size={15} />
              <span>Ngân sách</span>
            </button>

            <button
              id="dashboard-reports-nav-btn"
              onClick={() => navigate('/reports')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary-soft)',
                border: '1px solid #BEE4D7',
                color: 'var(--primary)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <BarChart3 size={15} />
              <span>Báo cáo</span>
            </button>

            <button
              id="dashboard-recurring-nav-btn"
              onClick={() => navigate('/recurring-transactions')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--secondary-soft)',
                border: '1px solid #C4DDFC',
                color: 'var(--secondary)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <Repeat size={15} />
              <span>Định kỳ</span>
            </button>

            <button
              id="dashboard-transfers-nav-btn"
              onClick={() => navigate('/transfers')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--secondary-soft)',
                border: '1px solid #C4DDFC',
                color: 'var(--secondary)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <ArrowLeftRight size={15} />
              <span>Chuyển tiền</span>
            </button>

            <button
              id="dashboard-transactions-nav-btn"
              onClick={() => navigate('/transactions')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--income-soft)',
                border: '1px solid #BCE2CE',
                color: 'var(--income)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <ReceiptText size={15} />
              <span>Sổ giao dịch</span>
            </button>

            <button
              id="dashboard-accounts-nav-btn"
              onClick={() => navigate('/accounts')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '6px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary-gradient)',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: 'var(--shadow-button)',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease',
              }}
            >
              <CreditCard size={15} />
              <span>Quản lý ví</span>
            </button>
          </nav>

          {/* 3. Right User Utility Cluster (Bell, User profile pill, Logout button) */}
          <div className="dashboard-user-actions">
            {/* Notification Bell Center */}
            <NotificationBell />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '5px 12px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
              }}
            >
              <div
                style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  background: 'var(--primary-soft)',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <UserIcon size={14} />
              </div>
              <div className="dashboard-user-name" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                {user?.display_name}
              </div>
            </div>

            <button
              id="dashboard-logout-btn"
              onClick={handleLogout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                background: 'var(--danger-soft)',
                border: '1px solid #F5BAC2',
                color: 'var(--danger)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.825rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease',
              }}
            >
              <LogOut size={15} />
              <span>Đăng xuất</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '28px 24px' }}>
        {/* Filter Controls Header */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            marginBottom: '24px',
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-card)',
            padding: '16px 20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'var(--primary-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary)',
              }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Tổng Quan Tài Chính</h2>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                Kỳ báo cáo: Tháng {selectedMonth}/{selectedYear}
              </div>
            </div>
          </div>

          {/* Filter dropdowns */}
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px' }}>
            {/* Scope */}
            <select
              value={selectedScope}
              onChange={(e) => setSelectedScope(e.target.value as DashboardScope)}
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              <option value="all">Toàn bộ (Cá nhân & Gia đình)</option>
              <option value="personal">Chỉ cá nhân</option>
              <option value="family">Chỉ gia đình</option>
            </select>

            {/* Family select if scope is family */}
            {selectedScope === 'family' && families.length > 0 && (
              <select
                value={selectedFamilyId}
                onChange={(e) => setSelectedFamilyId(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-input)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              >
                {families.map((fam) => (
                  <option key={fam.id} value={fam.id}>
                    {fam.name}
                  </option>
                ))}
              </select>
            )}

            {/* Month */}
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>
                  Tháng {m}
                </option>
              ))}
            </select>

            {/* Year */}
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-input)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
            >
              {[selectedYear - 1, selectedYear, selectedYear + 1].map((y) => (
                <option key={y} value={y}>
                  Năm {y}
                </option>
              ))}
            </select>

            {/* Refresh */}
            <button
              onClick={() => void fetchSummary()}
              disabled={loading}
              title="Làm mới dữ liệu"
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.85rem',
              }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              <span>Tải lại</span>
            </button>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div
            style={{
              padding: '16px',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--error-bg)',
              border: '1px solid var(--error-border)',
              color: 'var(--error)',
              fontSize: '0.9rem',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={20} />
              <span>{error}</span>
            </div>
            <button
              onClick={() => void fetchSummary()}
              className="btn-primary"
              style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--text-sub)' }}>
            <RefreshCw size={32} className="spin" style={{ color: 'var(--primary-500)', margin: '0 auto 12px' }} />
            <p style={{ fontSize: '0.95rem' }}>Đang tổng hợp dữ liệu tài chính thời gian thực từ PostgreSQL...</p>
          </div>
        )}

        {/* Dashboard Data View */}
        {!loading && summary && (
          <>
            {/* 1. Metric Cards Row: Số dư khả dụng & Dòng tiền */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '16px',
                marginBottom: '28px',
              }}
            >
              {/* Card 1: Số dư khả dụng */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                    SỐ DƯ KHẢ DỤNG
                  </span>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      background: 'var(--secondary-soft)',
                      color: 'var(--secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Wallet size={18} />
                  </div>
                </div>
                {summary.balances_by_currency.length > 0 ? (
                  summary.balances_by_currency.map((b) => (
                    <div key={b.currency} style={{ marginBottom: '6px' }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                        {formatCurrency(b.total_balance, b.currency)}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                        {b.active_accounts_count} ví hoạt động
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-sub)' }}>0 ₫</div>
                )}
              </div>

              {/* Card 2: Tổng thu nhập trong kỳ */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                    TỔNG THU TRONG KỲ
                  </span>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      background: 'var(--income-soft)',
                      color: 'var(--income)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <TrendingUp size={18} />
                  </div>
                </div>
                {summary.cash_flow_by_currency.length > 0 ? (
                  summary.cash_flow_by_currency.map((cf) => (
                    <div key={cf.currency} style={{ marginBottom: '4px' }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--income)' }}>
                        +{formatCurrency(cf.total_income, cf.currency)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-sub)' }}>0 ₫</div>
                )}
              </div>

              {/* Card 3: Tổng chi tiêu trong kỳ */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                    TỔNG CHI TRONG KỲ
                  </span>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      background: 'var(--expense-soft)',
                      color: 'var(--expense)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <TrendingDown size={18} />
                  </div>
                </div>
                {summary.cash_flow_by_currency.length > 0 ? (
                  summary.cash_flow_by_currency.map((cf) => (
                    <div key={cf.currency} style={{ marginBottom: '4px' }}>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--expense)' }}>
                        -{formatCurrency(cf.total_expense, cf.currency)}
                      </div>
                      {Number(cf.total_transfer_fee) > 0 && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                          (Phí chuyển: {formatCurrency(cf.total_transfer_fee, cf.currency)})
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-sub)' }}>0 ₫</div>
                )}
              </div>

              {/* Card 4: Dòng tiền thuần (Net Cash Flow) */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                    DÒNG TIỀN THUẦN
                  </span>
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
                    <CalendarCheck size={18} />
                  </div>
                </div>
                {summary.cash_flow_by_currency.length > 0 ? (
                  summary.cash_flow_by_currency.map((cf) => {
                    const isPositive = Number(cf.net_cash_flow) >= 0;
                    return (
                      <div key={cf.currency} style={{ marginBottom: '4px' }}>
                        <div
                          style={{
                            fontSize: '1.5rem',
                            fontWeight: 800,
                            color: isPositive ? 'var(--income)' : 'var(--expense)',
                          }}
                        >
                          {isPositive ? '+' : ''}
                          {formatCurrency(cf.net_cash_flow, cf.currency)}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-sub)' }}>0 ₫</div>
                )}
              </div>
            </div>

            {/* 2. Cảnh báo ngân sách (Budget Alerts Banner nếu có) */}
            {summary.budget_alerts.length > 0 && (
              <div
                style={{
                  background: 'var(--warning-soft)',
                  border: '1px solid #FCE38E',
                  borderRadius: 'var(--radius-lg)',
                  padding: '18px 22px',
                  marginBottom: '28px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--warning)', fontWeight: 700, fontSize: '0.95rem' }}>
                    <AlertTriangle size={18} />
                    <span>Cảnh báo ngân sách chi tiêu ({summary.budget_alerts.length} mục)</span>
                  </div>
                  <button
                    onClick={() => navigate('/budgets')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--warning)',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <span>Xem tất cả</span> <ChevronRight size={14} />
                  </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                  {summary.budget_alerts.map((alert) => (
                    <div
                      key={alert.id}
                      style={{
                        background: '#FFFFFF',
                        border: `1px solid ${
                          alert.status === 'exceeded' ? 'var(--danger)' : '#FCE38E'
                        }`,
                        borderRadius: 'var(--radius-md)',
                        padding: '12px 14px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                          {alert.name || alert.category_name}
                        </span>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            color: alert.status === 'exceeded' ? 'var(--danger)' : 'var(--warning)',
                          }}
                        >
                          {alert.status === 'exceeded' ? 'VƯỢT HẠN MỨC' : 'CẢNH BÁO'} ({alert.usage_percentage}%)
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                        Đã chi: <strong>{formatCurrency(alert.spent_amount)}</strong> / Hạn mức: {formatCurrency(alert.amount_limit)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. Grid 2 cột: Biểu đồ xu hướng 6 tháng & Cơ cấu chi tiêu */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))',
                gap: '20px',
                marginBottom: '28px',
              }}
            >
              {/* Biểu đồ xu hướng */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                      Xu Hướng Thu & Chi 6 Tháng
                    </h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)', margin: '4px 0 0' }}>
                      Đối sánh dòng tiền qua từng tháng
                    </p>
                  </div>
                </div>
                {renderTrendChart()}
              </div>

              {/* Cơ cấu chi tiêu theo danh mục */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                      Cơ Cấu Chi Tiêu Trong Kỳ
                    </h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)', margin: '4px 0 0' }}>
                      Tỷ trọng các danh mục chi tiêu lớn nhất
                    </p>
                  </div>
                  <button
                    onClick={() => navigate('/transactions')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-500)',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Chi tiết
                  </button>
                </div>

                {summary.expense_categories.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {summary.expense_categories.slice(0, 5).map((cat) => (
                      <div key={cat.category_id}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600 }}>{cat.category_name}</span>
                          <div>
                            <span style={{ fontWeight: 700 }}>
                              {formatCurrency(cat.total_amount, cat.currency)}
                            </span>
                            <span style={{ color: 'var(--text-sub)', marginLeft: '8px', fontSize: '0.8rem' }}>
                              ({cat.percentage}%)
                            </span>
                          </div>
                        </div>
                        <div
                          style={{
                            width: '100%',
                            height: '6px',
                            background: 'var(--surface-muted)',
                            borderRadius: 'var(--radius-full)',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${Math.min(Number(cat.percentage), 100)}%`,
                              height: '100%',
                              background: 'var(--primary-gradient)',
                              borderRadius: 'var(--radius-full)',
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
                    Chưa có giao dịch chi tiêu nào trong tháng {selectedMonth}/{selectedYear}.
                  </div>
                )}
              </div>
            </div>

            {/* 4. Grid 2 cột: Hoạt động gần đây (Giao dịch thu/chi & Chuyển tiền) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))',
                gap: '20px',
                marginBottom: '32px',
              }}
            >
              {/* Giao dịch thu chi gần đây */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                    Giao Dịch Gần Đây
                  </h3>
                  <button
                    onClick={() => navigate('/transactions')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-500)',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Xem tất cả
                  </button>
                </div>

                {summary.recent_transactions.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {summary.recent_transactions.map((tx) => (
                      <div
                        key={tx.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--surface-muted)',
                          border: '1px solid var(--border)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div
                            style={{
                              width: '32px',
                              height: '32px',
                              borderRadius: '8px',
                              background:
                                tx.type === 'income'
                                  ? 'var(--income-soft)'
                                  : 'var(--expense-soft)',
                              color: tx.type === 'income' ? 'var(--income)' : 'var(--expense)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          >
                            {tx.type === 'income' ? <ArrowDownRight size={16} /> : <ArrowUpRight size={16} />}
                          </div>
                          <div>
                            <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                              {tx.category_name || (tx.type === 'income' ? 'Thu nhập' : 'Chi tiêu')}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                              {tx.account_name} • {new Date(tx.occurred_at).toLocaleDateString('vi-VN')}
                            </div>
                          </div>
                        </div>
                        <div
                          style={{
                            fontSize: '0.9rem',
                            fontWeight: 700,
                            color: tx.type === 'income' ? 'var(--income)' : 'var(--expense)',
                          }}
                        >
                          {tx.type === 'income' ? '+' : '-'}
                          {formatCurrency(tx.amount, tx.currency)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
                    Chưa có giao dịch thu chi nào gần đây.
                  </div>
                )}
              </div>

              {/* Chuyển tiền gần đây */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '24px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                    Chuyển Tiền Gần Đây
                  </h3>
                  <button
                    onClick={() => navigate('/transfers')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--primary-500)',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Xem tất cả
                  </button>
                </div>

                {summary.recent_transfers.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {summary.recent_transfers.map((tr) => (
                      <div
                        key={tr.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-md)',
                          background: 'var(--surface-muted)',
                          border: '1px solid var(--border)',
                          opacity: tr.is_voided ? 0.6 : 1,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div
                            style={{
                              width: '32px',
                              height: '32px',
                              borderRadius: '8px',
                              background: 'var(--secondary-soft)',
                              color: 'var(--secondary)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          >
                            <ArrowLeftRight size={16} />
                          </div>
                          <div>
                            <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                              {tr.from_account_name} ➔ {tr.to_account_name}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                              {new Date(tr.occurred_at).toLocaleDateString('vi-VN')}{' '}
                              {tr.is_voided && (
                                <span style={{ color: 'var(--expense)', fontWeight: 600 }}>• Đã hủy (Void)</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>
                            {formatCurrency(tr.amount, tr.currency)}
                          </div>
                          {Number(tr.fee_amount) > 0 && (
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-sub)' }}>
                              Phí: {formatCurrency(tr.fee_amount, tr.currency)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '36px 0', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
                    Chưa có giao dịch chuyển tiền nào gần đây.
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Roadmap Preview - Module Links */}
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>
          Lối Tắt Các Chức Năng Hệ Thống
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '20px',
          }}
        >
          <div
            id="roadmap-accounts-card"
            onClick={() => navigate('/accounts')}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              transition: 'all 0.2s',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--primary-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary)',
                marginBottom: '16px',
              }}
            >
              <CreditCard size={22} />
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '8px' }}>
              Quản Lý Ví Cá Nhân & Gia Đình
            </h3>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '16px' }}>
              Hỗ trợ tạo ví tiền mặt, ngân hàng, ví điện tử với số dư ban đầu và số dư thực tế từ PostgreSQL.
            </p>
            <span style={{ fontSize: '0.85rem', color: 'var(--primary-500)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>Truy cập ngay</span> <ArrowRight size={14} />
            </span>
          </div>

          <div
            id="roadmap-transactions-card"
            onClick={() => navigate('/transactions')}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              transition: 'all 0.2s',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--income-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--success)',
                marginBottom: '16px',
              }}
            >
              <ReceiptText size={22} />
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '8px' }}>
              Sổ Giao Dịch Thu Chi
            </h3>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '16px' }}>
              Ghi chép và quản lý các khoản thu nhập, chi tiêu, tự động tính số dư ví và lưu trữ PostgreSQL.
            </p>
            <span style={{ fontSize: '0.85rem', color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>Truy cập ngay</span> <ArrowRight size={14} />
            </span>
          </div>

          <div
            id="roadmap-transfers-card"
            onClick={() => navigate('/transfers')}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              transition: 'all 0.2s',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--secondary-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--secondary)',
                marginBottom: '16px',
              }}
            >
              <ArrowLeftRight size={22} />
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '8px' }}>
              Chuyển Tiền Giữa Hai Ví
            </h3>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '16px' }}>
              Hạch toán kép giữa hai tài khoản, bảo toàn số dư thực tế, hỗ trợ phí giao dịch và hủy hiệu lực (void).
            </p>
            <span style={{ fontSize: '0.85rem', color: 'var(--secondary)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>Truy cập ngay</span> <ArrowRight size={14} />
            </span>
          </div>

          <div
            id="roadmap-budgets-card"
            onClick={() => navigate('/budgets')}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)', boxShadow: 'var(--shadow-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              transition: 'all 0.2s',
              cursor: 'pointer',
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                background: 'var(--warning-soft)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--warning)',
                marginBottom: '16px',
              }}
            >
              <CalendarCheck size={22} />
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '8px' }}>
              Ngân Sách & Cảnh Báo
            </h3>
            <p style={{ color: 'var(--text-sub)', fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '16px' }}>
              Thiết lập hạn mức chi tiêu theo danh mục, tự động tính chi tiêu thực tế và cảnh báo ngưỡng 80%, 100%.
            </p>
            <span style={{ fontSize: '0.85rem', color: 'var(--warning)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>Truy cập ngay</span> <ArrowRight size={14} />
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
