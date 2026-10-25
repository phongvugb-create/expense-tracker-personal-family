import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Plus,
  ArrowLeft,
  RefreshCw,
  UserPlus,
  Edit2,
  Trash2,
  LogOut,
  Mail,
  Calendar,
  KeyRound,
  ShieldAlert,
  ShieldCheck,
  Clock,
  Ban,
  ChevronRight,
  CreditCard,
} from 'lucide-react';
import type { Family, FamilyMember, FamilyInvitation, FamilyRole } from '../types/family';
import { familyService } from '../services/familyService';
import { getErrorMessage } from '../services/apiClient';
import { CreateFamilyModal } from '../components/CreateFamilyModal';
import { InviteMemberModal } from '../components/InviteMemberModal';

export function FamiliesPage() {
  const navigate = useNavigate();

  // Danh sách gia đình
  const [families, setFamilies] = useState<Family[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Nhóm đang được chọn xem chi tiết
  const [selectedFamilyId, setSelectedFamilyId] = useState<string | null>(null);
  const [selectedFamily, setSelectedFamily] = useState<Family | null>(null);

  // Chi tiết thành viên & lời mời của nhóm đang chọn
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [invitations, setInvitations] = useState<FamilyInvitation[]>([]);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isInviteOpen, setIsInviteOpen] = useState(false);

  // Inline rename nhóm
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);

  // Role update state
  const [updatingMemberId, setUpdatingMemberId] = useState<string | null>(null);

  // Leave / Kick confirm dialog state
  const [memberToAction, setMemberToAction] = useState<{
    member: FamilyMember;
    isKick: boolean;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Flash message tự tắt
  useEffect(() => {
    if (actionMessage) {
      const timer = setTimeout(() => setActionMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [actionMessage]);

  /**
   * Tải danh sách nhóm gia đình của user hiện tại
   */
  const fetchFamilies = useCallback(async (selectIdAfterFetch?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await familyService.getFamilies();
      setFamilies(data);

      if (data.length > 0) {
        if (selectIdAfterFetch && data.some((f) => f.id === selectIdAfterFetch)) {
          setSelectedFamilyId(selectIdAfterFetch);
        } else if (!selectedFamilyId || !data.some((f) => f.id === selectedFamilyId)) {
          setSelectedFamilyId(data[0].id);
        }
      } else {
        setSelectedFamilyId(null);
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [selectedFamilyId]);

  useEffect(() => {
    void fetchFamilies();
  }, [fetchFamilies]);

  /**
   * Tải chi tiết nhóm (thành viên + lời mời) khi selectedFamilyId thay đổi
   */
  const fetchFamilyDetail = useCallback(async (familyId: string) => {
    try {
      setLoadingDetail(true);
      // Lấy chi tiết nhóm để cập nhật my_role mới nhất
      const famDetail = await familyService.getFamilyDetail(familyId);
      setSelectedFamily(famDetail);
      setRenameValue(famDetail.name);

      // Lấy danh sách thành viên
      const membersData = await familyService.getFamilyMembers(familyId);
      setMembers(membersData);

      // Nếu là owner hoặc editor thì mới có quyền tải danh sách lời mời
      if (famDetail.my_role === 'owner' || famDetail.my_role === 'editor') {
        try {
          const invData = await familyService.getFamilyInvitations(familyId);
          setInvitations(invData);
        } catch {
          setInvitations([]);
        }
      } else {
        setInvitations([]);
      }
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    if (selectedFamilyId) {
      void fetchFamilyDetail(selectedFamilyId);
    } else {
      setSelectedFamily(null);
      setMembers([]);
      setInvitations([]);
    }
  }, [selectedFamilyId, fetchFamilyDetail]);

  /**
   * Xử lý đổi tên nhóm
   */
  const handleRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFamily || !renameValue.trim()) return;

    try {
      setRenameLoading(true);
      const updated = await familyService.updateFamily(selectedFamily.id, {
        name: renameValue.trim(),
      });
      setSelectedFamily(updated);
      setIsRenaming(false);
      setActionMessage({
        type: 'success',
        text: `Đã đổi tên nhóm thành "${updated.name}".`,
      });
      await fetchFamilies(updated.id);
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setRenameLoading(false);
    }
  };

  /**
   * Xử lý thay đổi vai trò thành viên
   */
  const handleRoleChange = async (member: FamilyMember, newRole: 'editor' | 'viewer') => {
    if (!selectedFamily) return;
    try {
      setUpdatingMemberId(member.id);
      await familyService.updateMemberRole(selectedFamily.id, member.id, { role: newRole });
      setActionMessage({
        type: 'success',
        text: `Đã cập nhật vai trò của ${member.display_name} thành ${
          newRole === 'editor' ? 'Biên tập viên' : 'Người xem'
        }.`,
      });
      await fetchFamilyDetail(selectedFamily.id);
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setUpdatingMemberId(null);
    }
  };

  /**
   * Xử lý xác nhận rời nhóm hoặc kick thành viên
   */
  const handleConfirmLeaveOrKick = async () => {
    if (!selectedFamily || !memberToAction) return;
    try {
      setActionLoading(true);
      await familyService.leaveFamily(selectedFamily.id, memberToAction.member.id);
      const isKick = memberToAction.isKick;
      setActionMessage({
        type: 'success',
        text: isKick
          ? `Đã loại ${memberToAction.member.display_name} khỏi nhóm gia đình.`
          : `Bạn đã rời khỏi nhóm "${selectedFamily.name}".`,
      });
      setMemberToAction(null);

      // Nếu chính user rời nhóm thì tải lại danh sách gia đình
      if (!isKick) {
        await fetchFamilies();
      } else {
        await fetchFamilyDetail(selectedFamily.id);
        await fetchFamilies(selectedFamily.id);
      }
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    } finally {
      setActionLoading(false);
    }
  };

  /**
   * Xử lý thu hồi lời mời
   */
  const handleRevokeInvitation = async (invitationId: string, email: string) => {
    if (!selectedFamily) return;
    try {
      await familyService.revokeInvitation(selectedFamily.id, invitationId);
      setActionMessage({
        type: 'success',
        text: `Đã thu hồi lời mời gửi đến "${email}".`,
      });
      await fetchFamilyDetail(selectedFamily.id);
    } catch (err: unknown) {
      setActionMessage({ type: 'error', text: getErrorMessage(err) });
    }
  };

  const getRoleBadge = (role: FamilyRole) => {
    switch (role) {
      case 'owner':
        return (
          <span
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--expense-soft)',
              color: 'var(--danger)',
              fontSize: '0.725rem',
              fontWeight: 700,
              border: '1px solid #F5BAC2',
            }}
          >
            Chủ nhóm (Owner)
          </span>
        );
      case 'editor':
        return (
          <span
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--secondary-soft)',
              color: 'var(--secondary)',
              fontSize: '0.725rem',
              fontWeight: 700,
              border: '1px solid #C4DDFC',
            }}
          >
            Biên tập viên (Editor)
          </span>
        );
      case 'viewer':
        return (
          <span
            style={{
              padding: '3px 8px',
              borderRadius: 'var(--radius-full)',
              background: 'rgba(156, 163, 175, 0.15)',
              color: 'var(--text-sub)',
              fontSize: '0.725rem',
              fontWeight: 700,
              border: '1px solid rgba(156, 163, 175, 0.3)',
            }}
          >
            Người xem (Viewer)
          </span>
        );
    }
  };

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
                  background: 'rgba(99, 102, 241, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#818cf8',
                }}
              >
                <Users size={20} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.15rem' }}>Quản lý nhóm gia đình</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)' }}>
                  Phân quyền thành viên & chia sẻ ví tài chính
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              id="accept-invitation-nav-btn"
              onClick={() => navigate('/families/accept-invitation')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(99, 102, 241, 0.12)',
                border: '1px solid rgba(99, 102, 241, 0.3)',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <KeyRound size={15} />
              <span>Nhập mã lời mời</span>
            </button>

            <button
              onClick={() => fetchFamilies(selectedFamilyId || undefined)}
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
              id="open-create-family-btn"
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
              <span>Tạo nhóm mới</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
        {/* Flash Message */}
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
              background: actionMessage.type === 'success' ? 'var(--success-bg)' : 'var(--error-bg)',
              border: `1px solid ${actionMessage.type === 'success' ? 'var(--success-border)' : 'var(--error-border)'}`,
              color: actionMessage.type === 'success' ? 'var(--success)' : 'var(--danger)',
            }}
          >
            <ShieldCheck size={18} />
            <span>{actionMessage.text}</span>
          </div>
        )}

        {/* Global Error */}
        {error && (
          <div
            style={{
              padding: '16px 20px',
              borderRadius: 'var(--radius-md)',
              marginBottom: '24px',
              background: 'var(--error-bg)',
              border: '1px solid var(--error-border)',
              color: 'var(--danger)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <ShieldAlert size={20} />
            <div>{error}</div>
          </div>
        )}

        {/* Layout 2 cột: Sidebar Danh sách nhóm + Chi tiết nhóm */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-sub)' }}>
            Đang tải dữ liệu gia đình...
          </div>
        ) : families.length === 0 ? (
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
                width: '60px',
                height: '60px',
                borderRadius: '16px',
                background: 'rgba(99, 102, 241, 0.12)',
                color: '#818cf8',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <Users size={30} />
            </div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '8px' }}>
              Bạn chưa tham gia nhóm gia đình nào
            </h2>
            <p
              style={{
                color: 'var(--text-muted)',
                fontSize: '0.9rem',
                maxWidth: '460px',
                margin: '0 auto 24px',
                lineHeight: 1.5,
              }}
            >
              Hãy tạo một nhóm gia đình mới để mời các thành viên, phân quyền và chia sẻ ví tài chính chung, hoặc nhập mã lời mời nếu bạn nhận được token từ người khác.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={() => setIsCreateOpen(true)}
                className="btn-primary"
                style={{ padding: '10px 22px' }}
              >
                + Tạo nhóm đầu tiên
              </button>
              <button
                onClick={() => navigate('/families/accept-invitation')}
                style={{
                  padding: '10px 20px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Nhập mã token lời mời
              </button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', alignItems: 'flex-start' }}>
            {/* Cột trái: Danh sách các nhóm gia đình */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-sub)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Nhóm của bạn ({families.length})
              </div>

              {families.map((fam) => {
                const isSelected = fam.id === selectedFamilyId;
                return (
                  <div
                    key={fam.id}
                    onClick={() => setSelectedFamilyId(fam.id)}
                    style={{
                      background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'var(--bg-card)',
                      border: `1px solid ${isSelected ? '#818cf8' : 'var(--border)'}`,
                      borderRadius: 'var(--radius-md)',
                      padding: '16px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ fontWeight: 700, fontSize: '1rem', color: isSelected ? '#fff' : 'var(--text-main)' }}>
                        {fam.name}
                      </div>
                      <ChevronRight size={16} color={isSelected ? '#818cf8' : 'var(--text-sub)'} />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.775rem' }}>
                      {getRoleBadge(fam.my_role)}
                      <span style={{ color: 'var(--text-sub)' }}>{fam.member_count} thành viên</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Cột phải: Chi tiết nhóm được chọn */}
            {selectedFamily && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* Header chi tiết nhóm */}
                <div
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '24px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', marginBottom: '16px' }}>
                    <div style={{ flex: 1 }}>
                      {isRenaming ? (
                        <form onSubmit={handleRename} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input
                            type="text"
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            disabled={renameLoading}
                            className="form-input"
                            style={{ maxWidth: '320px', padding: '6px 12px', fontSize: '1.1rem', fontWeight: 700 }}
                            autoFocus
                          />
                          <button
                            type="submit"
                            disabled={renameLoading}
                            className="btn-primary"
                            style={{ padding: '6px 14px', fontSize: '0.85rem' }}
                          >
                            {renameLoading ? 'Lưu...' : 'Lưu'}
                          </button>
                          <button
                            type="button"
                            onClick={() => setIsRenaming(false)}
                            style={{
                              padding: '6px 12px',
                              background: 'var(--surface-muted)',
                              border: '1px solid var(--border)',
                              color: 'var(--text-muted)',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '0.85rem',
                              cursor: 'pointer',
                            }}
                          >
                            Hủy
                          </button>
                        </form>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <h2 style={{ fontSize: '1.45rem', fontWeight: 800 }}>{selectedFamily.name}</h2>
                          {selectedFamily.my_role === 'owner' && (
                            <button
                              onClick={() => setIsRenaming(true)}
                              title="Đổi tên nhóm"
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--text-sub)',
                                cursor: 'pointer',
                                padding: '4px',
                              }}
                            >
                              <Edit2 size={16} />
                            </button>
                          )}
                        </div>
                      )}
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', marginTop: '4px' }}>
                        Mã nhóm (UUID): <code style={{ color: 'var(--secondary)' }}>{selectedFamily.id}</code>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      {/* Nút mời thành viên (Owner / Editor) */}
                      {(selectedFamily.my_role === 'owner' || selectedFamily.my_role === 'editor') && (
                        <button
                          id="open-invite-modal-btn"
                          onClick={() => setIsInviteOpen(true)}
                          className="btn-primary"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '8px 16px',
                            fontSize: '0.85rem',
                          }}
                        >
                          <UserPlus size={16} />
                          <span>Mời thành viên</span>
                        </button>
                      )}

                      {/* Liên kết tới trang Quản lý ví để tạo ví gia đình */}
                      <button
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
                        <CreditCard size={15} />
                        <span>Xem ví chung</span>
                      </button>
                    </div>
                  </div>

                  {/* Thông tin vai trò & ngày tạo */}
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '20px',
                      paddingTop: '16px',
                      borderTop: '1px solid var(--border)',
                      fontSize: '0.85rem',
                    }}
                  >
                    <div>
                      <span style={{ color: 'var(--text-sub)' }}>Vai trò của bạn: </span>
                      {getRoleBadge(selectedFamily.my_role)}
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-sub)' }}>Số thành viên: </span>
                      <strong>{selectedFamily.member_count}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-sub)' }}>Ngày thành lập: </span>
                      <span>{new Date(selectedFamily.created_at).toLocaleDateString('vi-VN')}</span>
                    </div>
                  </div>
                </div>

                {/* Danh sách thành viên */}
                <div
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '24px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                      Thành viên trong nhóm ({members.length})
                    </h3>
                  </div>

                  {loadingDetail ? (
                    <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-sub)' }}>
                      Đang tải danh sách thành viên...
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {members.map((member) => {
                        const isOwner = member.is_owner || member.role === 'owner';
                        return (
                          <div
                            key={member.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '12px 16px',
                              background: 'var(--surface-muted)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--radius-md)',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <div
                                style={{
                                  width: '38px',
                                  height: '38px',
                                  borderRadius: '50%',
                                  background: isOwner ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                  color: isOwner ? 'var(--primary)' : 'var(--secondary)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontWeight: 700,
                                }}
                              >
                                {member.display_name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span>{member.display_name}</span>
                                  {isOwner && (
                                    <span style={{ fontSize: '0.7rem', color: 'var(--danger)', fontWeight: 700 }}>[Owner]</span>
                                  )}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-sub)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <Mail size={12} />
                                  <span>{member.email}</span>
                                  <span>•</span>
                                  <Calendar size={12} />
                                  <span>Gia nhập {new Date(member.joined_at).toLocaleDateString('vi-VN')}</span>
                                </div>
                              </div>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              {/* Phân quyền vai trò: Chỉ Owner mới có quyền thay đổi role thành viên thông thường */}
                              {selectedFamily.my_role === 'owner' && !isOwner ? (
                                <select
                                  value={member.role}
                                  onChange={(e) => handleRoleChange(member, e.target.value as 'editor' | 'viewer')}
                                  disabled={updatingMemberId === member.id}
                                  style={{
                                    padding: '5px 10px',
                                    borderRadius: 'var(--radius-sm)',
                                    background: 'var(--bg-input)',
                                    border: '1px solid var(--border)',
                                    color: 'var(--text-main)',
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                  }}
                                >
                                  <option value="editor">Biên tập viên (Editor)</option>
                                  <option value="viewer">Người xem (Viewer)</option>
                                </select>
                              ) : (
                                getRoleBadge(member.role)
                              )}

                              {/* Hành động Loại thành viên (Owner kick) hoặc Tự rời nhóm (Leave) */}
                              {!isOwner && selectedFamily.my_role === 'owner' && (
                                <button
                                  onClick={() => setMemberToAction({ member, isKick: true })}
                                  title="Loại thành viên khỏi nhóm"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    border: '1px solid #F5BAC2',
                                    color: 'var(--danger)',
                                    padding: '6px',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: 'pointer',
                                  }}
                                >
                                  <Trash2 size={15} />
                                </button>
                              )}

                              {/* Nếu chính là bản thân mình (không phải owner) thì có nút rời nhóm */}
                              {!isOwner && selectedFamily.my_role !== 'owner' && (
                                <button
                                  onClick={() => setMemberToAction({ member, isKick: false })}
                                  title="Rời khỏi nhóm này"
                                  style={{
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    border: '1px solid #F5BAC2',
                                    color: 'var(--danger)',
                                    padding: '6px 12px',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                  }}
                                >
                                  <LogOut size={14} />
                                  <span>Rời nhóm</span>
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Danh sách lời mời (Chỉ hiển thị cho Owner hoặc Editor) */}
                {(selectedFamily.my_role === 'owner' || selectedFamily.my_role === 'editor') && (
                  <div
                    style={{
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-lg)',
                      padding: '24px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                      <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                        Lời mời tham gia ({invitations.length})
                      </h3>
                      <button
                        onClick={() => setIsInviteOpen(true)}
                        style={{
                          background: 'var(--surface-muted)',
                          border: '1px solid var(--border)',
                          color: 'var(--text-muted)',
                          padding: '6px 12px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        + Mời thêm
                      </button>
                    </div>

                    {invitations.length === 0 ? (
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-sub)', textAlign: 'center', padding: '16px' }}>
                        Không có lời mời nào đang chờ xử lý.
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {invitations.map((inv) => {
                          const isPending = inv.status === 'pending';
                          return (
                            <div
                              key={inv.id}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '12px 16px',
                                background: 'rgba(0, 0, 0, 0.2)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-md)',
                              }}
                            >
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '4px' }}>
                                  {inv.invited_email}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-sub)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span>Đề xuất: <strong>{inv.role === 'editor' ? 'Biên tập viên' : 'Người xem'}</strong></span>
                                  <span>•</span>
                                  <Clock size={12} />
                                  <span>Hết hạn: {new Date(inv.expires_at).toLocaleString('vi-VN')}</span>
                                </div>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                {isPending ? (
                                  <>
                                    <span
                                      style={{
                                        fontSize: '0.725rem',
                                        padding: '3px 8px',
                                        borderRadius: 'var(--radius-full)',
                                        background: 'var(--warning-soft)',
                                        color: 'var(--warning)',
                                        fontWeight: 600,
                                      }}
                                    >
                                      Đang chờ
                                    </span>
                                    <button
                                      onClick={() => handleRevokeInvitation(inv.id, inv.invited_email)}
                                      title="Thu hồi lời mời"
                                      style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px',
                                        padding: '5px 10px',
                                        borderRadius: 'var(--radius-sm)',
                                        background: 'rgba(239, 68, 68, 0.1)',
                                        border: '1px solid #F5BAC2',
                                        color: 'var(--danger)',
                                        fontSize: '0.75rem',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                      }}
                                    >
                                      <Ban size={12} />
                                      <span>Thu hồi</span>
                                    </button>
                                  </>
                                ) : (
                                  <span
                                    style={{
                                      fontSize: '0.725rem',
                                      padding: '3px 8px',
                                      borderRadius: 'var(--radius-full)',
                                      background:
                                        inv.status === 'accepted'
                                          ? 'rgba(16, 185, 129, 0.15)'
                                          : 'rgba(156, 163, 175, 0.15)',
                                      color:
                                        inv.status === 'accepted' ? 'var(--success)' : 'var(--text-sub)',
                                      fontWeight: 600,
                                    }}
                                  >
                                    {inv.status === 'accepted'
                                      ? 'Đã tham gia'
                                      : inv.status === 'revoked'
                                      ? 'Đã thu hồi'
                                      : 'Hết hạn'}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Modal Tạo nhóm mới */}
      <CreateFamilyModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={(newFamilyId) => {
          setActionMessage({ type: 'success', text: 'Tạo nhóm gia đình mới thành công!' });
          void fetchFamilies(newFamilyId);
        }}
      />

      {/* Modal Mời thành viên */}
      {selectedFamily && (
        <InviteMemberModal
          familyId={selectedFamily.id}
          familyName={selectedFamily.name}
          isOpen={isInviteOpen}
          onClose={() => setIsInviteOpen(false)}
          onSuccess={() => {
            void fetchFamilyDetail(selectedFamily.id);
          }}
        />
      )}

      {/* Confirmation Dialog: Leave / Kick */}
      {memberToAction && selectedFamily && (
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
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid #F5BAC2',
              borderRadius: 'var(--radius-lg)',
              maxWidth: '440px',
              width: '100%',
              padding: '24px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--danger)', marginBottom: '12px' }}>
              <ShieldAlert size={22} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>
                {memberToAction.isKick ? 'Xác nhận loại thành viên' : 'Xác nhận rời khỏi nhóm'}
              </h3>
            </div>

            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '20px' }}>
              {memberToAction.isKick
                ? `Bạn có chắc chắn muốn loại thành viên "${memberToAction.member.display_name}" khỏi nhóm "${selectedFamily.name}"? Họ sẽ không còn quyền truy cập vào các ví chung của gia đình nữa.`
                : `Bạn có chắc chắn muốn rời khỏi nhóm "${selectedFamily.name}"? Bạn sẽ không còn quyền truy cập vào các ví chung của gia đình này nữa.`}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={() => setMemberToAction(null)}
                disabled={actionLoading}
                style={{
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--surface-muted)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                }}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={handleConfirmLeaveOrKick}
                disabled={actionLoading}
                style={{
                  padding: '8px 18px',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--error)',
                  border: 'none',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                }}
              >
                {actionLoading ? 'Đang xử lý...' : memberToAction.isKick ? 'Loại thành viên' : 'Rời nhóm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
