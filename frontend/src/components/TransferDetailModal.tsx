import {
  X,
  ArrowRightLeft,
  Calendar,
  Clock,
  FileText,
  Ban,
  CheckCircle,
  Coins,
} from 'lucide-react';
import type { Transfer } from '../types/transfer';
import { formatCurrency } from '../utils/accountUtils';

interface TransferDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  transfer: Transfer | null;
  onVoidClick?: (transfer: Transfer) => void;
}

export function TransferDetailModal({
  isOpen,
  onClose,
  transfer,
  onVoidClick,
}: TransferDetailModalProps) {
  if (!isOpen || !transfer) return null;

  const curr = transfer.currency || 'VND';

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
          maxWidth: '520px',
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
                width: '42px',
                height: '42px',
                borderRadius: '12px',
                background: transfer.is_voided
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'rgba(59, 130, 246, 0.15)',
                color: transfer.is_voided ? 'var(--error)' : 'var(--primary-500)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <ArrowRightLeft size={22} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                Chi tiết chuyển tiền
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                <span
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: transfer.is_voided ? 'var(--error-bg)' : 'var(--success-bg)',
                    color: transfer.is_voided ? 'var(--error)' : 'var(--success)',
                    border: `1px solid ${
                      transfer.is_voided ? 'var(--error-border)' : 'var(--success-border)'
                    }`,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  {transfer.is_voided ? (
                    <>
                      <Ban size={12} />
                      <span>Đã hủy (Voided)</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle size={12} />
                      <span>Hoàn tất</span>
                    </>
                  )}
                </span>
              </div>
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

        {/* Số Tiền Nổi Bật */}
        <div
          style={{
            background: transfer.is_voided
              ? 'rgba(239, 68, 68, 0.08)'
              : 'linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(99, 102, 241, 0.05) 100%)',
            border: `1px solid ${
              transfer.is_voided ? 'rgba(239, 68, 68, 0.25)' : 'rgba(59, 130, 246, 0.3)'
            }`,
            borderRadius: 'var(--radius-md)',
            padding: '20px',
            textAlign: 'center',
            marginBottom: '20px',
          }}
        >
          <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '4px' }}>
            SỐ TIỀN CHUYỂN
          </div>
          <div
            style={{
              fontSize: '1.85rem',
              fontWeight: 800,
              color: transfer.is_voided ? 'var(--text-sub)' : 'var(--primary-500)',
              textDecoration: transfer.is_voided ? 'line-through' : 'none',
            }}
          >
            {formatCurrency(transfer.amount, curr)}
          </div>
          {Number(transfer.fee_amount) > 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginTop: '4px' }}>
              Phí chuyển tiền: <strong style={{ color: 'var(--error)' }}>{formatCurrency(transfer.fee_amount, curr)}</strong>
            </div>
          )}
        </div>

        {/* Thông tin 2 ví nguồn và đích */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
            background: 'var(--bg-input)',
            padding: '14px',
            borderRadius: 'var(--radius-md)',
            marginBottom: '18px',
          }}
        >
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '2px' }}>
              VÍ NGUỒN (CHUYỂN ĐI)
            </div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--error)' }}>
              {transfer.from_account_name || 'Ví tài chính'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', marginBottom: '2px' }}>
              VÍ ĐÍCH (NHẬN ĐẾN)
            </div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--success)' }}>
              {transfer.to_account_name || 'Ví tài chính'}
            </div>
          </div>
        </div>

        {/* Bảng Chi Tiết Thuộc Tính */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
              <Calendar size={15} />
              <span>Thời gian phát sinh</span>
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              {new Date(transfer.occurred_at).toLocaleString('vi-VN')}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
              <Coins size={15} />
              <span>Loại tiền tệ</span>
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              {curr}
            </span>
          </div>

          {transfer.note && (
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
                <FileText size={15} />
                <span>Ghi chú</span>
              </span>
              <span style={{ fontSize: '0.85rem', maxWidth: '65%', textAlign: 'right' }}>
                {transfer.note}
              </span>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-sub)', fontSize: '0.85rem' }}>
              <Clock size={15} />
              <span>Thời điểm tạo</span>
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-sub)', fontFamily: 'monospace' }}>
              {new Date(transfer.created_at).toLocaleString('vi-VN')}
            </span>
          </div>

          {transfer.is_voided && transfer.voided_at && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--error)', fontSize: '0.85rem' }}>
                <Ban size={15} />
                <span>Thời điểm hủy (void)</span>
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--error)', fontFamily: 'monospace' }}>
                {new Date(transfer.voided_at).toLocaleString('vi-VN')}
              </span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            {!transfer.is_voided && onVoidClick && (
              <button
                type="button"
                onClick={() => onVoidClick(transfer)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  background: 'var(--expense-soft)',
                  border: '1px solid #F5BAC2',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--error)',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <Ban size={14} />
                <span>Hủy chuyển tiền</span>
              </button>
            )}
          </div>

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
