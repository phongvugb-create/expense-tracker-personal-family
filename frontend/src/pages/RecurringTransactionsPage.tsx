import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Repeat,
  Plus,
  ArrowLeft,
  RefreshCw,
  Edit,
  Archive,
  Play,
  Pause,
  Calendar,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowDownRight,
  ArrowUpRight,
  Tag,
  Wallet,
  Sparkles,
} from 'lucide-react';
import type {
  RecurringTransaction,
  RecurringTransactionType,
  RecurringScope,
} from '../types/recurringTransaction';
import type { Account } from '../types/account';
import type { Category } from '../types/category';
import type { Family } from '../types/family';
import { recurringTransactionService } from '../services/recurringTransactionService';
import { accountService } from '../services/accountService';
import { categoryService } from '../services/categoryService';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';
import { formatCurrency } from '../utils/accountUtils';
import { CreateRecurringTransactionModal } from '../components/CreateRecurringTransactionModal';
import { EditRecurringTransactionModal } from '../components/EditRecurringTransactionModal';

export function RecurringTransactionsPage() {
  const navigate = useNavigate();

  const [rules, setRules] = useState<RecurringTransaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [families, setFamilies] = useState<Family[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Filters
  const [filterScope, setFilterScope] = useState<RecurringScope>('all');
  const [filterFamilyId, setFilterFamilyId] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all'); // all, income, expense
  const [filterStatus, setFilterStatus] = useState<string>('all'); // all, active, paused, archived
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<RecurringTransaction | null>(null);
  const [generatingRule, setGeneratingRule] = useState<RecurringTransaction | null>(null);
  const [archivingRule, setArchivingRule] = useState<RecurringTransaction | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Tải danh mục, ví và gia đình
  const loadDependencies = useCallback(async () => {
    try {
      const [accs, cats, fams] = await Promise.all([
        accountService.getAccounts(),
        categoryService.getCategories(),
        familyService.getFamilies(),
      ]);
      setAccounts(accs);
      setCategories(cats);
      setFamilies(fams);
    } catch (err: unknown) {
      console.error('Lỗi tải dữ liệu phụ trợ:', err);
    }
  }, []);

  // Tải danh sách quy tắc định kỳ
  const fetchRules = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params: {
        scope?: RecurringScope;
        family_id?: string;
        type?: RecurringTransactionType;
        is_active?: boolean;
        is_archived?: boolean;
      } = {
        scope: filterScope,
        is_archived: filterStatus === 'archived',
      };

      if (filterFamilyId !== 'all') {
        params.family_id = filterFamilyId;
      }
      if (filterType !== 'all') {
        params.type = filterType as RecurringTransactionType;
      }
      if (filterStatus === 'active') {
        params.is_active = true;
        params.is_archived = false;
      } else if (filterStatus === 'paused') {
        params.is_active = false;
        params.is_archived = false;
      } else if (filterStatus === 'archived') {
        params.is_archived = true;
      }

      const data = await recurringTransactionService.getRecurringTransactions(params);
      setRules(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filterScope, filterFamilyId, filterType, filterStatus]);

  useEffect(() => {
    loadDependencies();
  }, [loadDependencies]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  // Thông báo tạm thời tự tắt sau 5s
  useEffect(() => {
    if (actionMessage) {
      const timer = setTimeout(() => setActionMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [actionMessage]);

  // Hôm nay dạng YYYY-MM-DD
  const todayStr = useMemo(() => {
    return new Date().toISOString().split('T')[0];
  }, []);

  // Danh sách quy tắc đã lọc theo searchTerm
  const filteredRules = useMemo(() => {
    return rules.filter((r) => {
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchName = r.name.toLowerCase().includes(term);
        const matchAcc = r.account_name?.toLowerCase().includes(term) || false;
        const matchCat = r.category_name?.toLowerCase().includes(term) || false;
        if (!matchName && !matchAcc && !matchCat) return false;
      }
      return true;
    });
  }, [rules, searchTerm]);

  // Các khoản đến hạn (next_due_date <= todayStr và đang active và chưa lưu trữ)
  const dueRules = useMemo(() => {
    return filteredRules.filter(
      (r) => r.is_active && !r.is_archived && r.next_due_date <= todayStr
    );
  }, [filteredRules, todayStr]);

  // Xử lý tạo giao dịch cho kỳ đến hạn
  const handleConfirmGenerate = async () => {
    if (!generatingRule) return;
    try {
      setActionLoading(true);
      const res = await recurringTransactionService.generateTransaction(generatingRule.id);
      const txCode = res.transaction_id ? res.transaction_id.slice(0, 8) : '';
      setActionMessage({
        type: 'success',
        text: res.message || `Đã phát sinh giao dịch thành công cho kỳ ${generatingRule.next_due_date}! Mã giao dịch: ${txCode}...`,
      });
      setGeneratingRule(null);
      window.dispatchEvent(new Event('notification-sync'));
      await fetchRules();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Tạm dừng quy tắc
  const handlePause = async (rule: RecurringTransaction) => {
    try {
      setActionLoading(true);
      await recurringTransactionService.pauseRecurringTransaction(rule.id);
      setActionMessage({
        type: 'success',
        text: `Đã tạm dừng quy tắc "${rule.name}"`,
      });
      await fetchRules();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Kích hoạt lại quy tắc
  const handleResume = async (rule: RecurringTransaction) => {
    try {
      setActionLoading(true);
      await recurringTransactionService.resumeRecurringTransaction(rule.id);
      setActionMessage({
        type: 'success',
        text: `Đã kích hoạt lại quy tắc "${rule.name}"`,
      });
      await fetchRules();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Lưu trữ quy tắc
  const handleConfirmArchive = async () => {
    if (!archivingRule) return;
    try {
      setActionLoading(true);
      await recurringTransactionService.archiveRecurringTransaction(archivingRule.id);
      setActionMessage({
        type: 'success',
        text: `Đã lưu trữ quy tắc "${archivingRule.name}"`,
      });
      setArchivingRule(null);
      await fetchRules();
    } catch (err: unknown) {
      setActionMessage({
        type: 'error',
        text: getErrorMessage(err),
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Diễn giải chu kỳ lặp
  const getFrequencyLabel = (freq: string, interval: number) => {
    if (interval === 1) {
      switch (freq) {
        case 'daily':
          return 'Hàng ngày';
        case 'weekly':
          return 'Hàng tuần';
        case 'monthly':
          return 'Hàng tháng';
        case 'yearly':
          return 'Hàng năm';
        default:
          return freq;
      }
    }
    switch (freq) {
      case 'daily':
        return `Mỗi ${interval} ngày`;
      case 'weekly':
        return `Mỗi ${interval} tuần`;
      case 'monthly':
        return `Mỗi ${interval} tháng`;
      case 'yearly':
        return `Mỗi ${interval} năm`;
      default:
        return `Mỗi ${interval} (${freq})`;
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', color: 'var(--text-main)', paddingBottom: '60px' }}>
      {/* Top Sticky Header */}
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
                  background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 4px 14px rgba(99, 102, 241, 0.35)',
                }}
              >
                <Repeat size={20} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.15rem', letterSpacing: '-0.02em' }}>
                  Giao Dịch Định Kỳ
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Quản lý các khoản thu và chi lặp lại theo chu kỳ định sẵn
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => fetchRules()}
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
              }}
              title="Tải lại dữ liệu"
            >
              <RefreshCw size={15} className={loading ? 'spinner' : ''} />
              <span>Đồng bộ</span>
            </button>
            <button
              onClick={() => setIsCreateOpen(true)}
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
                transition: 'all 0.2s',
              }}
            >
              <Plus size={16} />
              <span>Thêm Quy Tắc</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Page Content */}
      <main
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '24px 24px',
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
            {actionMessage.type === 'success' ? (
              <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
            ) : (
              <AlertCircle size={18} style={{ flexShrink: 0 }} />
            )}
            <span style={{ fontWeight: 500 }}>{actionMessage.text}</span>
          </div>
        )}

        {/* KHU VỰC CÁC KHOẢN ĐẾN HẠN CẦN XỬ LÝ (Highlight Section) */}
        {dueRules.length > 0 && (
          <section
            style={{
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0.04) 100%)',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              boxShadow: '0 10px 25px -5px rgba(245, 158, 11, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'rgba(245, 158, 11, 0.2)',
                  color: 'var(--warning)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Sparkles size={18} />
              </div>
              <div>
                <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#fde68a' }}>
                  Khoản Đến Hạn Cần Xác Nhận ({dueRules.length})
                </h2>
                <p style={{ fontSize: '0.75rem', color: 'var(--warning)', opacity: 0.85 }}>
                  Kỳ này đã đến ngày. Hãy bấm “Tạo giao dịch” để ghi nhận vào sổ giao dịch.
                </p>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '14px',
              }}
            >
              {dueRules.map((rule) => (
                <div
                  key={rule.id}
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px solid rgba(245, 158, 11, 0.35)',
                    borderRadius: 'var(--radius-md)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-sm)',
                          background: 'var(--warning-soft)',
                          color: 'var(--warning)',
                          border: '1px solid #FCE38E',
                        }}
                      >
                        Hạn: {rule.next_due_date}
                      </span>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: 'var(--radius-sm)',
                          background:
                            rule.type === 'expense'
                              ? 'rgba(239, 68, 68, 0.15)'
                              : 'rgba(16, 185, 129, 0.15)',
                          color: rule.type === 'expense' ? 'var(--expense)' : 'var(--income)',
                        }}
                      >
                        {rule.type === 'expense' ? 'Khoản Chi' : 'Khoản Thu'}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)', marginTop: '8px' }}>
                      {rule.name}
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginTop: '2px' }}>
                      {rule.account_name} • {rule.category_name}
                    </p>
                    <p
                      style={{
                        fontSize: '1.25rem',
                        fontWeight: 800,
                        marginTop: '8px',
                        color: rule.type === 'expense' ? 'var(--expense)' : 'var(--income)',
                      }}
                    >
                      {rule.type === 'expense' ? '-' : '+'}
                      {formatCurrency(rule.amount, rule.currency)}
                    </p>
                  </div>

                  <button
                    onClick={() => setGeneratingRule(rule)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      padding: '8px 14px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                      border: 'none',
                      color: '#ffffff',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    <Plus size={14} />
                    <span>Tạo Giao Dịch Ngay</span>
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Filter Controls Bar */}
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
              gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
              gap: '12px',
            }}
          >
            {/* Search */}
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-sub)' }} />
              <input
                type="text"
                placeholder="Tìm tên, ví, danh mục..."
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

            {/* Phạm vi */}
            <div>
              <select
                value={filterScope}
                onChange={(e) => {
                  setFilterScope(e.target.value as RecurringScope);
                  setFilterFamilyId('all');
                }}
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
                <option value="all">Tất cả phạm vi</option>
                <option value="personal">Cá nhân</option>
                <option value="family">Gia đình</option>
              </select>
            </div>

            {/* Gia đình (khi scope = family hoặc all) */}
            {filterScope !== 'personal' && (
              <div>
                <select
                  value={filterFamilyId}
                  onChange={(e) => setFilterFamilyId(e.target.value)}
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
                  <option value="all">Tất cả gia đình</option>
                  {families.map((fam) => (
                    <option key={fam.id} value={fam.id}>
                      {fam.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Loại giao dịch: Thu / Chi */}
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
                <option value="all">Tất cả loại (Thu & Chi)</option>
                <option value="expense">Khoản chi (Expense)</option>
                <option value="income">Khoản thu (Income)</option>
              </select>
            </div>

            {/* Trạng thái quy tắc */}
            <div>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
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
                <option value="all">Tất cả trạng thái</option>
                <option value="active">Đang hoạt động</option>
                <option value="paused">Đang tạm dừng</option>
                <option value="archived">Đã lưu trữ</option>
              </select>
            </div>
          </div>
        </div>

        {/* Danh sách Quy Tắc Định Kỳ */}
        <div>
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
              <p style={{ fontSize: '0.9rem' }}>Đang tải danh sách quy tắc định kỳ...</p>
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
                onClick={() => fetchRules()}
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
          ) : filteredRules.length === 0 ? (
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
                <Repeat size={24} />
              </div>
              <p style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                Chưa có quy tắc định kỳ nào
              </p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-sub)', maxWidth: '400px' }}>
                Hãy tạo quy tắc đầu tiên để quản lý tiền thuê nhà, lương hàng tháng hoặc hóa đơn định kỳ.
              </p>
              <button
                onClick={() => setIsCreateOpen(true)}
                style={{
                  marginTop: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--primary-gradient)',
                  border: 'none',
                  color: '#fff',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: 'var(--shadow-button)',
                }}
              >
                <Plus size={16} />
                <span>Thêm Quy Tắc Mới</span>
              </button>
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
                gap: '16px',
              }}
            >
              {filteredRules.map((rule) => {
                const isDue = rule.is_active && !rule.is_archived && rule.next_due_date <= todayStr;
                return (
                  <div
                    key={rule.id}
                    style={{
                      background: 'var(--bg-card)',
                      border: isDue
                        ? '1px solid rgba(245, 158, 11, 0.45)'
                        : '1px solid var(--border)',
                      borderRadius: 'var(--radius-lg)',
                      padding: '20px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      opacity: rule.is_archived ? 0.6 : 1,
                      boxShadow: isDue ? '0 8px 24px -4px rgba(245, 158, 11, 0.15)' : 'var(--shadow-card)',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div>
                      {/* Card Top: Badges */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '8px',
                          marginBottom: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              padding: '3px 8px',
                              borderRadius: 'var(--radius-sm)',
                              background:
                                rule.type === 'expense'
                                  ? 'rgba(239, 68, 68, 0.15)'
                                  : 'rgba(16, 185, 129, 0.15)',
                              color: rule.type === 'expense' ? 'var(--expense)' : 'var(--income)',
                            }}
                          >
                            {rule.type === 'expense' ? (
                              <ArrowDownRight size={13} />
                            ) : (
                              <ArrowUpRight size={13} />
                            )}
                            {rule.type === 'expense' ? 'Khoản Chi' : 'Khoản Thu'}
                          </span>

                          <span
                            style={{
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              padding: '3px 8px',
                              borderRadius: 'var(--radius-sm)',
                              background: 'var(--surface-muted)',
                              color: 'var(--text-muted)',
                            }}
                          >
                            {rule.scope === 'family' ? 'Gia đình' : 'Cá nhân'}
                          </span>
                        </div>

                        {/* Status badge */}
                        <div>
                          {rule.is_archived ? (
                            <span
                              style={{
                                fontSize: '0.75rem',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-sm)',
                                background: 'var(--surface-muted)',
                                color: 'var(--text-sub)',
                              }}
                            >
                              Đã lưu trữ
                            </span>
                          ) : !rule.is_active ? (
                            <span
                              style={{
                                fontSize: '0.75rem',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-sm)',
                                background: 'var(--warning-soft)',
                                color: 'var(--warning)',
                                border: '1px solid #FCE38E',
                              }}
                            >
                              Tạm dừng
                            </span>
                          ) : (
                            <span
                              style={{
                                fontSize: '0.75rem',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-sm)',
                                background: 'var(--income-soft)',
                                color: '#6ee7b7',
                                border: '1px solid #BCE2CE',
                              }}
                            >
                              Đang chạy
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Rule Title & Amount */}
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
                        {rule.name}
                      </h3>
                      <p
                        style={{
                          fontSize: '1.35rem',
                          fontWeight: 800,
                          color: rule.type === 'expense' ? 'var(--expense)' : 'var(--income)',
                          marginBottom: '14px',
                        }}
                      >
                        {rule.type === 'expense' ? '-' : '+'}
                        {formatCurrency(rule.amount, rule.currency)}
                      </p>

                      {/* Metadata Details */}
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                          fontSize: '0.8rem',
                          color: 'var(--text-muted)',
                          borderTop: '1px solid var(--border)',
                          paddingTop: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-sub)' }}>
                            <Wallet size={14} />
                            <span>Ví tài khoản:</span>
                          </span>
                          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                            {rule.account_name}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-sub)' }}>
                            <Tag size={14} />
                            <span>Danh mục:</span>
                          </span>
                          <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                            {rule.category_name}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-sub)' }}>
                            <Clock size={14} />
                            <span>Chu kỳ:</span>
                          </span>
                          <span style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                            {getFrequencyLabel(rule.frequency, rule.interval_value)}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-sub)' }}>
                            <Calendar size={14} />
                            <span>Kỳ kế tiếp:</span>
                          </span>
                          <span
                            style={{
                              fontWeight: 700,
                              color: isDue ? '#fbbf24' : 'var(--text-main)',
                            }}
                          >
                            {rule.next_due_date} {isDue && '(Đến hạn)'}
                          </span>
                        </div>

                        {rule.note && (
                          <p
                            style={{
                              fontStyle: 'italic',
                              color: 'var(--text-sub)',
                              fontSize: '0.75rem',
                              paddingTop: '6px',
                              borderTop: '1px dashed var(--border)',
                            }}
                          >
                            “{rule.note}”
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Card Actions Footer */}
                    <div
                      style={{
                        marginTop: '16px',
                        paddingTop: '12px',
                        borderTop: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        {!rule.is_archived && (
                          <>
                            {rule.is_active ? (
                              <button
                                onClick={() => handlePause(rule)}
                                disabled={actionLoading}
                                title="Tạm dừng quy tắc"
                                style={{
                                  padding: '7px',
                                  borderRadius: 'var(--radius-sm)',
                                  background: 'var(--surface-muted)',
                                  border: '1px solid var(--border)',
                                  color: 'var(--warning)',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                }}
                              >
                                <Pause size={15} />
                              </button>
                            ) : (
                              <button
                                onClick={() => handleResume(rule)}
                                disabled={actionLoading}
                                title="Tiếp tục quy tắc"
                                style={{
                                  padding: '7px',
                                  borderRadius: 'var(--radius-sm)',
                                  background: 'var(--income-soft)',
                                  border: '1px solid #BCE2CE',
                                  color: '#6ee7b7',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                }}
                              >
                                <Play size={15} />
                              </button>
                            )}

                            <button
                              onClick={() => setEditingRule(rule)}
                              title="Chỉnh sửa quy tắc"
                              style={{
                                padding: '7px',
                                borderRadius: 'var(--radius-sm)',
                                background: 'var(--secondary-soft)',
                                border: '1px solid #C4DDFC',
                                color: 'var(--secondary)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                              }}
                            >
                              <Edit size={15} />
                            </button>

                            <button
                              onClick={() => setArchivingRule(rule)}
                              title="Lưu trữ quy tắc"
                              style={{
                                padding: '7px',
                                borderRadius: 'var(--radius-sm)',
                                background: 'var(--expense-soft)',
                                border: '1px solid #F5BAC2',
                                color: 'var(--danger)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                              }}
                            >
                              <Archive size={15} />
                            </button>
                          </>
                        )}
                      </div>

                      {/* Nút Tạo Giao Dịch */}
                      {!rule.is_archived && rule.is_active && (
                        <button
                          onClick={() => setGeneratingRule(rule)}
                          disabled={!isDue || actionLoading}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '6px 12px',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            cursor: isDue ? 'pointer' : 'not-allowed',
                            background: isDue
                              ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                              : 'var(--surface-muted)',
                            border: isDue ? 'none' : '1px solid var(--border)',
                            color: isDue ? '#ffffff' : 'var(--text-sub)',
                            boxShadow: isDue ? '0 2px 8px rgba(245, 158, 11, 0.3)' : 'none',
                            transition: 'all 0.2s',
                          }}
                          title={
                            isDue
                              ? 'Tạo giao dịch ngay cho kỳ này'
                              : 'Chưa tới hạn hoặc đã tạo kỳ này'
                          }
                        >
                          <Plus size={14} />
                          <span>Tạo Giao Dịch</span>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* Modal Thêm Quy Tắc */}
      <CreateRecurringTransactionModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Đã tạo quy tắc định kỳ mới thành công!',
          });
          void fetchRules();
        }}
        accounts={accounts}
        categories={categories}
      />

      {/* Modal Sửa Quy Tắc */}
      <EditRecurringTransactionModal
        isOpen={!!editingRule}
        onClose={() => setEditingRule(null)}
        onSuccess={() => {
          setActionMessage({
            type: 'success',
            text: 'Đã cập nhật quy tắc thành công!',
          });
          void fetchRules();
        }}
        rule={editingRule}
        categories={categories}
      />

      {/* Modal Xác Nhận Tạo Giao Dịch */}
      {generatingRule && (
        <div className="modal-overlay">
          <div className="modal-dialog" style={{ maxWidth: '440px', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'rgba(245, 158, 11, 0.2)',
                  color: 'var(--warning)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Sparkles size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Xác Nhận Tạo Giao Dịch
                </h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Phát sinh giao dịch thực tế cho kỳ đến hạn
                </p>
              </div>
            </div>

            <div
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--bg-input-border)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                fontSize: '0.8rem',
                marginBottom: '14px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-sub)' }}>Quy tắc:</span>
                <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{generatingRule.name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-sub)' }}>Số tiền:</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: generatingRule.type === 'expense' ? 'var(--expense)' : 'var(--income)',
                  }}
                >
                  {generatingRule.type === 'expense' ? '-' : '+'}
                  {formatCurrency(generatingRule.amount, generatingRule.currency)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-sub)' }}>Kỳ đến hạn:</span>
                <span style={{ fontWeight: 700, color: 'var(--warning)' }}>{generatingRule.next_due_date}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-sub)' }}>Ví tài khoản:</span>
                <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{generatingRule.account_name}</span>
              </div>
            </div>

            <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)', lineHeight: 1.45, marginBottom: '20px' }}>
              Giao dịch sẽ được ghi vào sổ và số dư ví sẽ được cập nhật ngay lập tức. Sau đó, quy tắc sẽ tự động chuyển ngày đến hạn sang kỳ kế tiếp.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setGeneratingRule(null)}
                disabled={actionLoading}
                style={{
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleConfirmGenerate}
                disabled={actionLoading}
                style={{
                  padding: '8px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)',
                  opacity: actionLoading ? 0.6 : 1,
                }}
              >
                {actionLoading ? 'Đang tạo...' : 'Xác Nhận Tạo'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Xác Nhận Lưu Trữ */}
      {archivingRule && (
        <div className="modal-overlay">
          <div className="modal-dialog" style={{ maxWidth: '440px', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'rgba(239, 68, 68, 0.2)',
                  color: 'var(--expense)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Archive size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-main)' }}>
                  Lưu Trữ Quy Tắc Định Kỳ?
                </h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Quy tắc này sẽ không còn phát sinh giao dịch mới
                </p>
              </div>
            </div>

            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '20px' }}>
              Bạn có chắc chắn muốn lưu trữ quy tắc <strong>"{archivingRule.name}"</strong> không? Các giao dịch đã được phát sinh trước đây vẫn được giữ nguyên đầy đủ trong lịch sử.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setArchivingRule(null)}
                disabled={actionLoading}
                style={{
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleConfirmArchive}
                disabled={actionLoading}
                style={{
                  padding: '8px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: '#ef4444',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)',
                  opacity: actionLoading ? 0.6 : 1,
                }}
              >
                {actionLoading ? 'Đang lưu trữ...' : 'Lưu Trữ'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
