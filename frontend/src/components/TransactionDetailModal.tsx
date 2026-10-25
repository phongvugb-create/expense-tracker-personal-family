import { X, ArrowDownRight, ArrowUpRight, Calendar, Tag, Wallet, User, Clock, FileText } from 'lucide-react';
import type { Transaction } from '../types/transaction';
import { formatCurrency } from '../utils/accountUtils';

interface TransactionDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: Transaction | null;
  currency?: string;
}

export function TransactionDetailModal({
  isOpen,
  onClose,
  transaction,
  currency = 'VND',
}: TransactionDetailModalProps) {
  if (!isOpen || !transaction) return null;

  const isIncome = transaction.type === 'income';

  return (
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
        zIndex: 50,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-card)',
          width: '100%',
          maxWidth: '500px',
          padding: '28px',
          animation: 'fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '12px',
                background: isIncome
                  ? 'rgba(16, 185, 129, 0.15)'
                  : 'rgba(239, 68, 68, 0.15)',
                color: isIncome ? 'var(--success)' : 'var(--error)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {isIncome ? <ArrowDownRight size={24} /> : <ArrowUpRight size={24} />}
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                Chi tiết giao dịch
              </h2>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  background: isIncome ? 'var(--success-bg)' : 'var(--error-bg)',
                  color: isIncome ? 'var(--success)' : 'var(--error)',
                  border: `1px solid ${isIncome ? 'var(--success-border)' : 'var(--error-border)'}`,
                }}
              >
                {isIncome ? 'Khoản Thu Nhập' : 'Khoản Chi Tiêu'}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-sub)',
              cursor: 'pointer',
              padding: '6px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Số tiền lớn nổi bật */}
        <div
          style={{
            background: isIncome
              ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(5, 150, 105, 0.05) 100%)'
              : 'linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(220, 38, 38, 0.05) 100%)',
            border: `1px solid ${isIncome ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            borderRadius: 'var(--radius-md)',
            padding: '20px',
            textAlign: 'center',
            marginBottom: '20px',
          }}
        >
          <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
            SỐ TIỀN PHÁT SINH
          </div>
          <div
            style={{
              fontSize: '1.85rem',
              fontWeight: 800,
              color: isIncome ? 'var(--success)' : 'var(--error)',
            }}
          >
            {isIncome ? '+' : '-'}{formatCurrency(transaction.amount, currency)}
          </div>
        </div>

        {/* Thông tin chi tiết dạng bảng grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.875rem' }}>
              <Wallet size={16} />
              <span>Ví tài khoản</span>
            </span>
            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
              {transaction.account_name || 'Ví tài chính'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.875rem' }}>
              <Tag size={16} />
              <span>Danh mục</span>
            </span>
            <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#f472b6' }}>
              {transaction.category_name || 'Chung'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.875rem' }}>
              <Calendar size={16} />
              <span>Thời gian phát sinh</span>
            </span>
            <span style={{ fontSize: '0.875rem' }}>
              {new Date(transaction.occurred_at).toLocaleString('vi-VN')}
            </span>
          </div>

          {transaction.note && (
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.875rem' }}>
                <FileText size={16} />
                <span>Ghi chú</span>
              </span>
              <span style={{ fontSize: '0.875rem', maxWidth: '60%', textAlign: 'right', color: 'var(--text-main)' }}>
                {transaction.note}
              </span>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.875rem' }}>
              <User size={16} />
              <span>Người tạo</span>
            </span>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              {transaction.creator_name || 'Chính bạn'}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.875rem' }}>
              <Clock size={16} />
              <span>Thời gian ghi sổ</span>
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', fontFamily: 'monospace' }}>
              {new Date(transaction.created_at).toLocaleString('vi-VN')}
            </span>
          </div>
        </div>

        {/* Close Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '9px 20px',
              background: 'var(--bg-input)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-main)',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}
