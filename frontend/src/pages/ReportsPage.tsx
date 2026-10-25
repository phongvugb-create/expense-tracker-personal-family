import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Download,
  RefreshCw,
  ArrowUpRight,
  Wallet,
  PieChart as PieIcon,
  Clock,
  AlertCircle,
  FileText,
  CreditCard,
  CheckCircle2,
} from 'lucide-react';
import type { ReportSummaryResponse } from '../types/report';
import type { Family } from '../types/family';
import { reportService } from '../services/reportService';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';

export function ReportsPage() {
  const navigate = useNavigate();

  // Mặc định khoảng ngày: Đầu tháng đến ngày hôm nay
  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().split('T')[0];
  });
  const [dateTo, setDateTo] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });

  const [scope, setScope] = useState<'all' | 'personal' | 'family'>('all');
  const [familyId, setFamilyId] = useState<string>('');
  const [families, setFamilies] = useState<Family[]>([]);

  const [data, setData] = useState<ReportSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Lấy danh sách nhóm gia đình hợp lệ
  const loadFamilies = useCallback(async () => {
    try {
      const list = await familyService.getFamilies();
      setFamilies(list);
    } catch (err) {
      console.error('Không thể tải danh sách gia đình:', err);
    }
  }, []);

  useEffect(() => {
    void loadFamilies();
  }, [loadFamilies]);

  // Tải dữ liệu báo cáo
  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await reportService.getSummary({
        date_from: dateFrom,
        date_to: dateTo,
        scope,
        family_id: scope === 'family' && familyId ? familyId : undefined,
      });
      setData(res);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, scope, familyId]);

  useEffect(() => {
    void fetchReport();
  }, [fetchReport]);

  // Xuất file CSV
  const handleExportCsv = async () => {
    try {
      setDownloading(true);
      setActionSuccess(null);
      await reportService.downloadCsv({
        date_from: dateFrom,
        date_to: dateTo,
        scope,
        family_id: scope === 'family' && familyId ? familyId : undefined,
      });
      setActionSuccess('Xuất tệp CSV thành công!');
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err) {
      setError(`Lỗi xuất CSV: ${getErrorMessage(err)}`);
    } finally {
      setDownloading(false);
    }
  };

  // Format tiền tệ
  const formatMoney = (valStr: string | number, curr: string = 'VND') => {
    const num = typeof valStr === 'string' ? parseFloat(valStr) : valStr;
    if (isNaN(num)) return '0 ' + curr;
    return new Intl.NumberFormat('vi-VN').format(num) + ' ' + curr;
  };

  // Group trend theo currency
  const trendCurrencies = useMemo(() => {
    if (!data?.monthly_trend) return [];
    const set = new Set<string>();
    data.monthly_trend.forEach((p) => set.add(p.currency));
    return Array.from(set);
  }, [data]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', paddingBottom: '80px' }}>
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
            maxWidth: '1280px',
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-button)',
              }}
            >
              <BarChart3 size={20} color="#fff" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.15rem', letterSpacing: '-0.02em' }}>
                Thống Kê & Báo Cáo
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                Phân tích dòng tiền và hiệu suất chi tiêu thời gian thực
              </div>
            </div>
          </div>

          {/* Navigation links */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => navigate('/dashboard')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface-muted)',
                border: '1px solid var(--border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Dashboard
            </button>
            <button
              onClick={() => navigate('/transactions')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid #BCE2CE',
                color: '#6ee7b7',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Sổ giao dịch
            </button>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
        {/* Filter Controls Bar */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: '20px',
            marginBottom: '24px',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '16px' }}>
              {/* Date From */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                  Từ ngày
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="input-field"
                    style={{ padding: '8px 12px', fontSize: '0.85rem', borderRadius: 'var(--radius-md)' }}
                  />
                </div>
              </div>

              {/* Date To */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                  Đến ngày
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="input-field"
                    style={{ padding: '8px 12px', fontSize: '0.85rem', borderRadius: 'var(--radius-md)' }}
                  />
                </div>
              </div>

              {/* Scope Selector */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                  Phạm vi
                </label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value as any)}
                  className="input-field"
                  style={{ padding: '8px 12px', fontSize: '0.85rem', borderRadius: 'var(--radius-md)' }}
                >
                  <option value="all">Tất cả dữ liệu</option>
                  <option value="personal">Chỉ cá nhân</option>
                  <option value="family">Không gian gia đình</option>
                </select>
              </div>

              {/* Family Selector (if scope is family) */}
              {scope === 'family' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-sub)', fontWeight: 600 }}>
                    Nhóm gia đình
                  </label>
                  <select
                    value={familyId}
                    onChange={(e) => setFamilyId(e.target.value)}
                    className="input-field"
                    style={{ padding: '8px 12px', fontSize: '0.85rem', borderRadius: 'var(--radius-md)' }}
                  >
                    <option value="">Tất cả gia đình của tôi</option>
                    {families.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'flex-end', marginTop: 'auto' }}>
                <button
                  onClick={() => fetchReport()}
                  className="btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 16px', fontSize: '0.85rem' }}
                >
                  <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
                  <span>Áp dụng</span>
                </button>
              </div>
            </div>

            {/* Export CSV Button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button
                onClick={handleExportCsv}
                disabled={downloading || loading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '9px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(34, 197, 94, 0.15)',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                  color: '#4ade80',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: downloading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <Download size={16} />
                <span>{downloading ? 'Đang xuất...' : 'Xuất CSV'}</span>
              </button>
            </div>
          </div>

          {actionSuccess && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.25)',
                color: '#4ade80',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <CheckCircle2 size={16} />
              <span>{actionSuccess}</span>
            </div>
          )}

          {error && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid #F5BAC2',
                color: 'var(--expense)',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Content Section */}
        {loading && !data ? (
          <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-sub)' }}>
            <RefreshCw size={36} className="animate-spin" style={{ margin: '0 auto 16px', opacity: 0.7 }} />
            <div style={{ fontSize: '1rem', fontWeight: 600 }}>Đang tổng hợp báo cáo tài chính...</div>
          </div>
        ) : !data || data.cash_flow_by_currency.length === 0 ? (
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-lg)',
              padding: '60px 20px',
              textAlign: 'center',
              color: 'var(--text-sub)',
            }}
          >
            <FileText size={48} style={{ margin: '0 auto 16px', opacity: 0.4 }} />
            <h3 style={{ fontSize: '1.2rem', color: 'var(--text-main)', marginBottom: '8px' }}>
              Không có dữ liệu trong khoảng thời gian này
            </h3>
            <p style={{ maxWidth: '450px', margin: '0 auto 20px', fontSize: '0.9rem' }}>
              Hãy thử chọn khoảng thời gian rộng hơn hoặc thêm các giao dịch thu/chi mới.
            </p>
            <button onClick={() => navigate('/transactions')} className="btn-primary">
              Đi tới Sổ giao dịch
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* 1. Tổng quan Dòng tiền theo từng Currency */}
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Wallet size={18} color="#6366f1" />
                <span>Tổng quan dòng tiền trong kỳ</span>
              </h2>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                {data.cash_flow_by_currency.map((cf) => (
                  <div
                    key={cf.currency}
                    style={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-lg)',
                      padding: '20px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-main)' }}>
                        Loại tiền: {cf.currency}
                      </span>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          padding: '2px 8px',
                          borderRadius: '12px',
                          background: parseFloat(cf.net_cash_flow) >= 0 ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: parseFloat(cf.net_cash_flow) >= 0 ? 'var(--income)' : 'var(--expense)',
                          fontWeight: 600,
                        }}
                      >
                        {parseFloat(cf.net_cash_flow) >= 0 ? 'Dương tiền' : 'Âm tiền'}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                      <div style={{ background: 'var(--surface-muted)', padding: '10px', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>Tổng Thu</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--income)', marginTop: '2px' }}>
                          +{formatMoney(cf.total_income, cf.currency)}
                        </div>
                      </div>

                      <div style={{ background: 'var(--surface-muted)', padding: '10px', borderRadius: 'var(--radius-md)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>Tổng Chi</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--expense)', marginTop: '2px' }}>
                          -{formatMoney(cf.total_expense, cf.currency)}
                        </div>
                      </div>
                    </div>

                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)' }}>Dòng tiền thuần (Net):</span>
                      <span style={{ fontSize: '1.05rem', fontWeight: 700, color: parseFloat(cf.net_cash_flow) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                        {formatMoney(cf.net_cash_flow, cf.currency)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 2. So sánh với kỳ trước (Comparison) */}
            {data.comparison && data.comparison.by_currency.length > 0 && (
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                }}
              >
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <ArrowUpRight size={18} color="#f59e0b" />
                  <span>So sánh với kỳ trước ({data.comparison.previous_date_from} đến {data.comparison.previous_date_to})</span>
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '16px' }}>
                  Đánh giá tốc độ tăng trưởng thu nhập và mức độ kiểm soát chi tiêu so với cùng độ dài thời gian trước đó.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                  {data.comparison.by_currency.map((cmp) => (
                    <div
                      key={cmp.currency}
                      style={{
                        background: 'var(--surface-muted)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-main)' }}>
                        Tiền tệ: {cmp.currency}
                      </div>

                      {/* Chi tiêu */}
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                          <span style={{ color: 'var(--text-sub)' }}>Chi tiêu kỳ này:</span>
                          <span style={{ fontWeight: 600 }}>{formatMoney(cmp.current_expense, cmp.currency)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginTop: '2px' }}>
                          <span style={{ color: 'var(--text-sub)' }}>Chi tiêu kỳ trước:</span>
                          <span>{formatMoney(cmp.previous_expense, cmp.currency)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginTop: '4px', fontWeight: 700 }}>
                          <span>Thay đổi chi tiêu:</span>
                          <span style={{ color: parseFloat(cmp.expense_change_amount) > 0 ? 'var(--expense)' : 'var(--income)' }}>
                            {parseFloat(cmp.expense_change_amount) > 0 ? '+' : ''}
                            {formatMoney(cmp.expense_change_amount, cmp.currency)}
                            {cmp.expense_change_percentage && ` (${cmp.expense_change_percentage}%)`}
                          </span>
                        </div>
                      </div>

                      {/* Thu nhập */}
                      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                          <span style={{ color: 'var(--text-sub)' }}>Thu nhập kỳ này:</span>
                          <span style={{ fontWeight: 600 }}>{formatMoney(cmp.current_income, cmp.currency)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginTop: '4px', fontWeight: 700 }}>
                          <span>Thay đổi thu nhập:</span>
                          <span style={{ color: parseFloat(cmp.income_change_amount) >= 0 ? 'var(--income)' : 'var(--expense)' }}>
                            {parseFloat(cmp.income_change_amount) > 0 ? '+' : ''}
                            {formatMoney(cmp.income_change_amount, cmp.currency)}
                            {cmp.income_change_percentage && ` (${cmp.income_change_percentage}%)`}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. Biểu đồ Xu hướng thu/chi theo tháng */}
            {data.monthly_trend.length > 0 && (
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                }}
              >
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <BarChart3 size={18} color="#3b82f6" />
                  <span>Xu hướng thu chi theo từng tháng</span>
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '20px' }}>
                  Biểu đồ cột so sánh tổng thu nhập và chi tiêu qua các tháng trong khoảng thời gian đã chọn.
                </p>

                {trendCurrencies.map((curr) => {
                  const points = data.monthly_trend.filter((p) => p.currency === curr);
                  const maxVal = Math.max(
                    ...points.flatMap((p) => [parseFloat(p.income), parseFloat(p.expense)]),
                    1
                  );

                  return (
                    <div key={curr} style={{ marginBottom: '24px' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-sub)', marginBottom: '12px' }}>
                        Đơn vị: {curr}
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'flex-end',
                          gap: '16px',
                          overflowX: 'auto',
                          paddingBottom: '12px',
                          minHeight: '180px',
                        }}
                      >
                        {points.map((p) => {
                          const incH = Math.max(Math.round((parseFloat(p.income) / maxVal) * 130), 4);
                          const expH = Math.max(Math.round((parseFloat(p.expense) / maxVal) * 130), 4);

                          return (
                            <div
                              key={p.month_key}
                              style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                minWidth: '64px',
                                gap: '6px',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '140px' }}>
                                {/* Income Bar */}
                                <div
                                  title={`Thu: ${formatMoney(p.income, curr)}`}
                                  style={{
                                    width: '18px',
                                    height: `${incH}px`,
                                    background: 'linear-gradient(180deg, #2EC183 0%, #21845A 100%)',
                                    borderRadius: '4px 4px 0 0',
                                  }}
                                />
                                {/* Expense Bar */}
                                <div
                                  title={`Chi: ${formatMoney(p.expense, curr)}`}
                                  style={{
                                    width: '18px',
                                    height: `${expH}px`,
                                    background: 'linear-gradient(180deg, #E67A66 0%, #C75D49 100%)',
                                    borderRadius: '4px 4px 0 0',
                                  }}
                                />
                              </div>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                                {p.display_label}
                              </span>
                            </div>
                          );
                        })}
                      </div>

                      {/* Legend */}
                      <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: 'var(--text-sub)', marginTop: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '10px', height: '10px', background: '#10b981', borderRadius: '2px' }} />
                          <span>Thu nhập</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '10px', height: '10px', background: '#ef4444', borderRadius: '2px' }} />
                          <span>Chi tiêu</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 4. Hai cột: Cơ cấu chi tiêu danh mục & Thống kê theo ví */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
              {/* Category Breakdown */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                }}
              >
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <PieIcon size={18} color="#ec4899" />
                  <span>Cơ cấu chi tiêu theo danh mục</span>
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '16px' }}>
                  Tỷ trọng các nhóm chi tiêu trong kỳ theo từng loại tiền tệ.
                </p>

                {data.category_breakdown.length === 0 ? (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
                    Chưa có khoản chi tiêu nào trong khoảng thời gian này.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {data.category_breakdown.map((cat) => (
                      <div key={cat.category_id + cat.currency} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                            {cat.category_name}
                          </span>
                          <span style={{ color: 'var(--text-sub)' }}>
                            {formatMoney(cat.total_amount, cat.currency)} ({cat.percentage}%)
                          </span>
                        </div>
                        <div
                          style={{
                            height: '6px',
                            background: 'var(--surface-muted)',
                            borderRadius: '3px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${Math.min(parseFloat(cat.percentage), 100)}%`,
                              background: cat.category_color || 'linear-gradient(90deg, #ec4899, #8b5cf6)',
                              borderRadius: '3px',
                              transition: 'width 0.3s ease',
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Account Breakdown */}
              <div
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                }}
              >
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CreditCard size={18} color="#14b8a6" />
                  <span>Hiệu suất thu/chi theo ví</span>
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '16px' }}>
                  Dòng tiền biến động trên từng tài khoản cá nhân hoặc nhóm gia đình.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {data.account_breakdown.map((acc) => (
                    <div
                      key={acc.account_id}
                      style={{
                        padding: '12px',
                        background: 'var(--surface-muted)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-md)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{acc.account_name}</span>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: acc.scope === 'personal' ? 'rgba(99, 102, 241, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                            color: acc.scope === 'personal' ? 'var(--primary)' : 'var(--warning)',
                          }}
                        >
                          {acc.scope === 'personal' ? 'Cá nhân' : 'Gia đình'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-sub)' }}>
                        <span>Thu: <strong style={{ color: 'var(--income)' }}>+{formatMoney(acc.total_income, acc.currency)}</strong></span>
                        <span>Chi: <strong style={{ color: 'var(--expense)' }}>-{formatMoney(acc.total_expense, acc.currency)}</strong></span>
                        <span>Net: <strong style={{ color: parseFloat(acc.net_amount) >= 0 ? 'var(--income)' : 'var(--expense)' }}>{formatMoney(acc.net_amount, acc.currency)}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 5. Top 10 khoản chi lớn nhất */}
            <div
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                padding: '20px',
              }}
            >
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={18} color="#f97316" />
                <span>Top 10 khoản chi lớn nhất trong kỳ</span>
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '16px' }}>
                Danh sách các chi tiêu có giá trị cao nhất giúp nhận diện các khoản chi trọng yếu.
              </p>

              {data.top_expenses.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
                  Không có khoản chi nào trong kỳ.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-sub)', textAlign: 'left' }}>
                        <th style={{ padding: '10px 12px' }}>Thời gian</th>
                        <th style={{ padding: '10px 12px' }}>Danh mục</th>
                        <th style={{ padding: '10px 12px' }}>Ví</th>
                        <th style={{ padding: '10px 12px' }}>Ghi chú</th>
                        <th style={{ padding: '10px 12px', textAlign: 'right' }}>Số tiền</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_expenses.map((tx) => (
                        <tr
                          key={tx.id}
                          style={{
                            borderBottom: '1px solid var(--border)',
                            transition: 'background 0.2s',
                          }}
                        >
                          <td style={{ padding: '12px', color: 'var(--text-sub)' }}>
                            {new Date(tx.occurred_at).toLocaleDateString('vi-VN')}
                          </td>
                          <td style={{ padding: '12px', fontWeight: 600 }}>
                            {tx.category_name || 'Khác'}
                          </td>
                          <td style={{ padding: '12px', color: 'var(--text-sub)' }}>
                            {tx.account_name}
                          </td>
                          <td style={{ padding: '12px', color: 'var(--text-sub)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {tx.description || '-'}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right', fontWeight: 700, color: 'var(--expense)' }}>
                            -{formatMoney(tx.amount, tx.currency)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default ReportsPage;
