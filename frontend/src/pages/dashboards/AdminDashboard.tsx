import React, { useState, useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Users,
  CheckCircle2,
  ExternalLink,
  Building2,
  Landmark,
  Search,
  RefreshCw,
  Clock,
  FileText,
  Sliders,
  AlertTriangle,
  AlertCircle,
  History,
  RotateCcw,
  Lock,
  Unlock,
  X,
  ChevronDown,
  ChevronRight,
  Check,
  Info,
  Server,
  Mail,
  Smartphone,
  Save,
} from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import Button from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import {
  adminApi,
  AdminStats,
  PlatformUser,
  AuditLogRecord,
  VerificationAppRecord,
  PlatformConfigHistoryItem,
} from '../../services/api';

export interface AdminDashboardProps {
  section?: 'overview' | 'verification' | 'verification_detail' | 'verifiers' | 'users' | 'platform_control' | 'audit_logs';
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ section: propSection }) => {
  const location = useLocation();
  const params = useParams<{ applicationId?: string }>();

  // Determine active section from route or prop
  const getActiveSection = (): 'overview' | 'verification' | 'verification_detail' | 'verifiers' | 'users' | 'platform_control' | 'audit_logs' => {
    if (propSection) return propSection;
    const path = location.pathname;
    if (params.applicationId || path.match(/\/admin\/verification\/[^/]+$/)) return 'verification_detail';
    if (path.includes('/admin/verification')) return 'verification';
    if (path.includes('/admin/verifiers')) return 'verifiers';
    if (path.includes('/admin/users')) return 'users';
    if (path.includes('/admin/platform-control')) return 'platform_control';
    if (path.includes('/admin/audit-logs')) return 'audit_logs';
    return 'overview';
  };

  const activeSection = getActiveSection();

  // Core Data State
  const [liveStats, setLiveStats] = useState<AdminStats | null>(null);
  const [usersList, setUsersList] = useState<PlatformUser[]>([]);
  const [auditLogsList, setAuditLogsList] = useState<AuditLogRecord[]>([]);
  const [verificationQueue, setVerificationQueue] = useState<VerificationAppRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusFeedback, setStatusFeedback] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Verification Center State
  const [verificationTier, setVerificationTier] = useState<string>('all');
  const [verificationStatusFilter, setVerificationStatusFilter] = useState<string>('all');
  const [verificationSearch, setVerificationSearch] = useState<string>('');
  const [selectedVerificationApp, setSelectedVerificationApp] = useState<VerificationAppRecord | null>(null);
  const [isVerificationModalOpen, setIsVerificationModalOpen] = useState(false);
  const [verificationAction, setVerificationAction] = useState<'APPROVE' | 'REJECT' | 'REQUEST_INFO' | 'SUSPEND' | 'REVOKE'>('APPROVE');
  const [verificationReason, setVerificationReason] = useState('');
  const [verificationRemarks, setVerificationRemarks] = useState('');
  const [isSubmittingVerification, setIsSubmittingVerification] = useState(false);

  // User Management State
  const [userSearch, setUserSearch] = useState('');
  const [accountTypeFilter, setAccountTypeFilter] = useState('ALL');
  const [userStatusFilter, setUserStatusFilter] = useState('ALL');
  const [selectedUserDetail, setSelectedUserDetail] = useState<any | null>(null);
  const [isUserDetailOpen, setIsUserDetailOpen] = useState(false);
  const [isLoadingUserDetail, setIsLoadingUserDetail] = useState(false);

  // User Warning Modal
  const [isWarningModalOpen, setIsWarningModalOpen] = useState(false);
  const [warningTargetUser, setWarningTargetUser] = useState<PlatformUser | null>(null);
  const [warningTitle, setWarningTitle] = useState('');
  const [warningMessage, setWarningMessage] = useState('');
  const [warningReason, setWarningReason] = useState('');
  const [warningSeverity, setWarningSeverity] = useState('NORMAL');
  const [isSubmittingWarning, setIsSubmittingWarning] = useState(false);

  // User Status Modal (Suspend / Block / Restore)
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [statusTargetUser, setStatusTargetUser] = useState<PlatformUser | null>(null);
  const [statusActionType, setStatusActionType] = useState<'suspend' | 'activate'>('suspend');
  const [statusReason, setStatusReason] = useState('');
  const [isSubmittingStatus, setIsSubmittingStatus] = useState(false);

  // Platform & Form Control State
  const [activeConfigTab, setActiveConfigTab] = useState<'landing' | 'signup' | 'login' | 'announcements'>('landing');
  const [landingConfig, setLandingConfig] = useState<any>({
    hero_badge: 'Government-Anchored Ecosystem',
    hero_title: "India's Unified Digital Skilling & Workforce Exchange",
    hero_subtitle: 'Empowering youth, enterprises, and institutions with verified digital credentials and transparent career pathways.',
    stats_candidates_label: 'Skilled Candidates',
    stats_employers_label: 'Hiring Enterprises',
    stats_institutes_label: 'Accredited Colleges',
    stats_credentials_label: 'Digital Certificates',
  });
  const [signupConfig, setSignupConfig] = useState<any>({
    candidate_fields: { fullName_required: true, dob_required: false, education_required: false, domain_required: true },
    employer_fields: { companyName_required: true, cin_required: false, industry_required: true, location_required: true },
    institute_fields: { instituteName_required: true, aisheCode_required: false, instituteType_required: true },
    government_fields: { departmentName_required: true, designation_required: true, officialEmailOnly: true },
    general: { secondaryVerificationRequired: true, termsAcceptanceMandatory: true, minPasswordLength: 8, resendCooldownSeconds: 60 },
  });
  const [loginConfig, setLoginConfig] = useState<any>({
    enabled_stakeholders: ['candidate', 'employer', 'institute', 'government', 'admin'],
    disclaimer_text: 'Protected Government-Affiliated Information System. Unauthorized access attempts are monitored, recorded, and prosecuted under applicable IT Acts.',
    support_email: 'support@skillvistaar.gov.in',
    max_login_attempts: 5,
    lockout_duration_minutes: 15,
  });
  const [announcementConfig, setAnnouncementConfig] = useState<any>({
    banner_enabled: true,
    banner_title: 'Scheduled Infrastructure Upgrade',
    banner_message: 'Unified National Registry synchronization is active. All services operating at full capacity.',
    severity: 'NORMAL',
    target_audience: 'ALL',
  });

  // Config Modals & History
  const [isConfigReasonModalOpen, setIsConfigReasonModalOpen] = useState(false);
  const [configChangeReason, setConfigChangeReason] = useState('');
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [configHistory, setConfigHistory] = useState<PlatformConfigHistoryItem[]>([]);
  const [showHistoryView, setShowHistoryView] = useState(false);
  const [inspectVersionJson, setInspectVersionJson] = useState<any | null>(null);

  // Audit Logs State
  const [auditActionFilter, setAuditActionFilter] = useState('ALL');
  const [auditResourceFilter, setAuditResourceFilter] = useState('ALL');
  const [auditSearch, setAuditSearch] = useState('');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setStatusFeedback({ text, type });
    setTimeout(() => setStatusFeedback(null), 5000);
  };

  // ---------------------------------------------------------------------------
  // Data Loaders
  // ---------------------------------------------------------------------------
  const loadPlatformData = async () => {
    setIsLoading(true);
    try {
      const [stats, users, logs, vq] = await Promise.all([
        adminApi.getStats(),
        adminApi.getUsers({ limit: 100 }),
        adminApi.getAuditLogs(100),
        adminApi.getVerifications({ limit: 100 }),
      ]);

      if (stats) setLiveStats(stats);
      setUsersList(users || []);
      setAuditLogsList(logs || []);
      setVerificationQueue(vq || []);
    } catch {
      showToast('Failed to sync administrative telemetry.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const loadConfigData = async () => {
    try {
      const [landRes, signRes, logRes, annRes] = await Promise.all([
        adminApi.getPlatformConfig('landing_content'),
        adminApi.getPlatformConfig('auth_signup_config'),
        adminApi.getPlatformConfig('auth_login_config'),
        adminApi.getPlatformConfig('system_announcements'),
      ]);

      if (landRes?.config_data) setLandingConfig(landRes.config_data);
      if (signRes?.config_data) setSignupConfig(signRes.config_data);
      if (logRes?.config_data) setLoginConfig(logRes.config_data);
      if (annRes?.config_data) setAnnouncementConfig(annRes.config_data);
    } catch {
      // keep defaults
    }
  };

  useEffect(() => {
    loadPlatformData();
    loadConfigData();
  }, []);

  // ---------------------------------------------------------------------------
  // Verification Center Handlers
  // ---------------------------------------------------------------------------
  const handleOpenVerificationAction = (app: VerificationAppRecord) => {
    setSelectedVerificationApp(app);
    setVerificationAction('APPROVE');
    setVerificationReason('');
    setVerificationRemarks('');
    setIsVerificationModalOpen(true);
  };

  const handleSubmitVerificationAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVerificationApp) return;

    if (verificationAction !== 'APPROVE' && !verificationReason.trim()) {
      showToast('A formal rationale is required for this action.', 'error');
      return;
    }

    setIsSubmittingVerification(true);
    try {
      await adminApi.performVerificationAction(
        selectedVerificationApp.id,
        verificationAction,
        verificationReason.trim() || undefined,
        verificationRemarks.trim() || undefined
      );

      showToast(`Verification application marked as ${verificationAction}. Permanent audit entry created.`);
      setIsVerificationModalOpen(false);
      setSelectedVerificationApp(null);
      loadPlatformData();
    } catch (err: any) {
      showToast(err.response?.data?.detail || err.message || 'Action failed.', 'error');
    } finally {
      setIsSubmittingVerification(false);
    }
  };

  const filteredVerifications = verificationQueue.filter((item) => {
    // Tier matching
    if (verificationTier !== 'all') {
      const t = (item.tier || '').toLowerCase();
      const appType = (item.application_type || '').toLowerCase();
      if (verificationTier === 'central' && !(t === 'central' || appType.includes('central'))) return false;
      if (verificationTier === 'state' && !(t === 'state' || appType.includes('state'))) return false;
      if (verificationTier === 'district' && !(t === 'district' || appType.includes('district'))) return false;
      if (verificationTier === 'local' && !(t === 'local' || appType.includes('local') || appType.includes('block') || appType.includes('municipal'))) return false;
      if (verificationTier === 'employer' && !(t === 'employer' || appType.includes('employer'))) return false;
      if (verificationTier === 'institute' && !(t === 'institute' || appType.includes('institute') || appType.includes('college'))) return false;
    }

    // Status matching
    if (verificationStatusFilter !== 'all' && item.status !== verificationStatusFilter) {
      return false;
    }

    // Search matching
    if (verificationSearch.trim()) {
      const kw = verificationSearch.toLowerCase();
      const match =
        (item.applicant_email || '').toLowerCase().includes(kw) ||
        (item.applicant_entity_name || '').toLowerCase().includes(kw) ||
        (item.submitted_data?.legal_name || '').toLowerCase().includes(kw) ||
        (item.government_unit_name || '').toLowerCase().includes(kw) ||
        item.id.toLowerCase().includes(kw);
      if (!match) return false;
    }

    return true;
  });

  // ---------------------------------------------------------------------------
  // User Management Handlers
  // ---------------------------------------------------------------------------
  const handleOpenUserDetail = async (user: PlatformUser) => {
    setIsLoadingUserDetail(true);
    setIsUserDetailOpen(true);
    try {
      const detail = await adminApi.getUserDetail(user.id);
      setSelectedUserDetail(detail);
    } catch {
      showToast('Failed to load user account profile.', 'error');
    } finally {
      setIsLoadingUserDetail(false);
    }
  };

  const handleOpenStatusModal = (user: PlatformUser, action: 'suspend' | 'activate') => {
    setStatusTargetUser(user);
    setStatusActionType(action);
    setStatusReason('');
    setIsStatusModalOpen(true);
  };

  const handleSubmitStatusUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!statusTargetUser) return;
    if (!statusReason.trim()) {
      showToast('A mandatory administrative reason must be provided.', 'error');
      return;
    }

    setIsSubmittingStatus(true);
    const isSuspended = statusActionType === 'suspend';
    try {
      await adminApi.updateUserStatus(
        statusTargetUser.id,
        !isSuspended,
        isSuspended,
        statusReason.trim()
      );
      showToast(`User account ${isSuspended ? 'suspended' : 'reactivated'} successfully.`);
      setIsStatusModalOpen(false);
      setStatusTargetUser(null);
      loadPlatformData();
      if (selectedUserDetail && selectedUserDetail.id === statusTargetUser.id) {
        handleOpenUserDetail(statusTargetUser);
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail || err.message || 'Failed to update user status.', 'error');
    } finally {
      setIsSubmittingStatus(false);
    }
  };

  const handleUnlockUser = async (user: PlatformUser) => {
    try {
      await adminApi.unlockUser(user.id);
      showToast(`Account locked status cleared for user ${user.email || user.id}.`);
      loadPlatformData();
    } catch (err: any) {
      showToast(err.response?.data?.detail || err.message || 'Failed to unlock user.', 'error');
    }
  };

  const handleOpenWarningModal = (user: PlatformUser) => {
    setWarningTargetUser(user);
    setWarningTitle('');
    setWarningMessage('');
    setWarningReason('');
    setWarningSeverity('NORMAL');
    setIsWarningModalOpen(true);
  };

  const handleSubmitWarning = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!warningTargetUser) return;

    if (!warningTitle.trim() || !warningMessage.trim() || !warningReason.trim()) {
      showToast('All warning fields are mandatory.', 'error');
      return;
    }

    setIsSubmittingWarning(true);
    try {
      await adminApi.issueUserWarning(
        warningTargetUser.id,
        warningTitle.trim(),
        warningMessage.trim(),
        warningReason.trim(),
        warningSeverity
      );
      showToast(`Administrative warning issued to ${warningTargetUser.email || warningTargetUser.id}.`);
      setIsWarningModalOpen(false);
      setWarningTargetUser(null);
      loadPlatformData();
      if (selectedUserDetail && selectedUserDetail.id === warningTargetUser.id) {
        handleOpenUserDetail(warningTargetUser);
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail || err.message || 'Failed to issue warning.', 'error');
    } finally {
      setIsSubmittingWarning(false);
    }
  };

  const filteredUsers = usersList.filter((u) => {
    if (accountTypeFilter !== 'ALL' && u.account_type !== accountTypeFilter) return false;
    if (userStatusFilter === 'ACTIVE' && (u.is_suspended || !u.is_active)) return false;
    if (userStatusFilter === 'SUSPENDED' && !u.is_suspended) return false;
    if (userStatusFilter === 'LOCKED' && !u.is_locked) return false;

    if (userSearch.trim()) {
      const kw = userSearch.toLowerCase();
      const match =
        (u.email || '').toLowerCase().includes(kw) ||
        (u.phone || '').includes(kw) ||
        (u.entity_name || '').toLowerCase().includes(kw) ||
        u.id.toLowerCase().includes(kw);
      if (!match) return false;
    }
    return true;
  });

  // ---------------------------------------------------------------------------
  // Platform & Form Control Handlers
  // ---------------------------------------------------------------------------
  const getConfigKeyForActiveTab = (): string => {
    switch (activeConfigTab) {
      case 'landing':
        return 'landing_content';
      case 'signup':
        return 'auth_signup_config';
      case 'login':
        return 'auth_login_config';
      case 'announcements':
        return 'system_announcements';
    }
  };

  const getActiveConfigData = (): Record<string, any> => {
    switch (activeConfigTab) {
      case 'landing':
        return landingConfig;
      case 'signup':
        return signupConfig;
      case 'login':
        return loginConfig;
      case 'announcements':
        return announcementConfig;
    }
  };

  const handleOpenConfigReasonModal = () => {
    setConfigChangeReason('');
    setIsConfigReasonModalOpen(true);
  };

  const handleSubmitConfigSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!configChangeReason.trim()) {
      showToast('A clear rationale for this configuration change is required.', 'error');
      return;
    }

    setIsSavingConfig(true);
    const key = getConfigKeyForActiveTab();
    const data = getActiveConfigData();
    try {
      await adminApi.savePlatformConfig(key, data, configChangeReason.trim());
      showToast(`Configuration for '${key}' updated and immutably versioned.`);
      setIsConfigReasonModalOpen(false);
      loadConfigData();
      loadPlatformData();
      if (showHistoryView) {
        handleLoadHistory();
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail || err.message || 'Failed to save configuration.', 'error');
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleLoadHistory = async () => {
    const key = getConfigKeyForActiveTab();
    try {
      const history = await adminApi.getPlatformConfigHistory(key);
      setConfigHistory(history);
      setShowHistoryView(true);
    } catch {
      showToast('Failed to load version history.', 'error');
    }
  };

  const handleRollbackVersion = async (version: number) => {
    const key = getConfigKeyForActiveTab();
    const reason = prompt(`Please enter the rollback justification for reverting ${key} to version ${version}:`);
    if (!reason || !reason.trim()) return;

    try {
      await adminApi.rollbackPlatformConfig(key, version, reason.trim());
      showToast(`Successfully rolled back '${key}' to version ${version}.`);
      loadConfigData();
      handleLoadHistory();
      loadPlatformData();
    } catch (err: any) {
      showToast(err.response?.data?.detail || err.message || 'Rollback failed.', 'error');
    }
  };

  // ---------------------------------------------------------------------------
  // Audit Logs Filter
  // ---------------------------------------------------------------------------
  const filteredAuditLogs = auditLogsList.filter((log) => {
    if (auditActionFilter !== 'ALL' && log.action !== auditActionFilter) return false;
    if (auditResourceFilter !== 'ALL' && log.resource_type !== auditResourceFilter) return false;
    if (auditSearch.trim()) {
      const kw = auditSearch.toLowerCase();
      const match =
        (log.description || '').toLowerCase().includes(kw) ||
        (log.actor_email || '').toLowerCase().includes(kw) ||
        (log.resource_id || '').toLowerCase().includes(kw) ||
        log.id.toLowerCase().includes(kw);
      if (!match) return false;
    }
    return true;
  });

  return (
    <DashboardLayout activeTab={activeSection}>
      <div className="space-y-5">
        {/* ================================================================= */}
        {/* SUPER ADMIN TOPBAR & TELEMETRY BANNER */}
        {/* ================================================================= */}
        <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-teal-950 rounded-xl p-4 sm:p-5 text-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-slate-800">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold bg-purple-500/20 text-purple-200 border border-purple-400/30 tracking-wide uppercase">
                <Shield className="w-3.5 h-3.5 text-purple-300" />
                Root Trust Authority
              </span>
              <span className="text-[11px] text-slate-300">
                Clearance: <span className="font-semibold text-teal-200">Level 1 - Central Governance</span>
              </span>
            </div>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center gap-2">
              SkillVistaar Public Trust & Central Operations
            </h1>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Centralized administrative authority. Governs 6-tier verification queues, platform user access, configurable registration/landing rules, and cryptographic audit records.
            </p>

            {/* Live System Telemetry Status Pills */}
            <div className="pt-2 flex flex-wrap items-center gap-2 text-[11px]">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700 text-slate-200">
                <Server className="w-3 h-3 text-emerald-400" />
                <span>PostgreSQL DB:</span>
                <span className="text-emerald-400 font-bold">Connected</span>
              </div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700 text-slate-200">
                <Mail className="w-3 h-3 text-teal-400" />
                <span>Gmail SMTP:</span>
                <span className={`font-bold ${liveStats?.system_health?.smtp_ready ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {liveStats?.system_health?.smtp_ready ? 'Ready' : 'Not Configured'}
                </span>
              </div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700 text-slate-200">
                <Smartphone className="w-3 h-3 text-sky-400" />
                <span>SMS Delivery:</span>
                <span className="font-bold text-sky-300">
                  {liveStats?.system_health?.sms_provider === 'sandbox' || liveStats?.system_health?.sms_provider === 'dummy'
                    ? 'Sandbox (Active)'
                    : (liveStats?.system_health?.sms_provider?.toUpperCase() || 'Sandbox (Active)')}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadPlatformData}
              isLoading={isLoading}
              className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Sync Telemetry
            </Button>
            <Link to="/admin/profile">
              <Button
                variant="primary"
                size="sm"
                className="text-xs font-semibold bg-teal-600 hover:bg-teal-700"
                rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
              >
                Authority Profile
              </Button>
            </Link>
          </div>
        </div>

        {/* Global Toast Feedback */}
        {statusFeedback && (
          <div
            className={`p-3 rounded-lg text-xs font-semibold flex items-center justify-between gap-2 animate-in fade-in ${
              statusFeedback.type === 'success'
                ? 'bg-emerald-50 border border-emerald-200 text-emerald-900'
                : 'bg-rose-50 border border-rose-200 text-rose-900'
            }`}
          >
            <div className="flex items-center gap-2">
              {statusFeedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{statusFeedback.text}</span>
            </div>
            <button
              onClick={() => setStatusFeedback(null)}
              className="text-slate-400 hover:text-slate-700 p-0.5"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* ================================================================= */}
        {/* VIEW 1: OVERVIEW DASHBOARD */}
        {/* ================================================================= */}
        {activeSection === 'overview' && (
          <div className="space-y-5">
            {/* Primary KPI Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-2xs space-y-1.5">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-bold uppercase tracking-wider">Platform Users</span>
                  <Users className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-2xl font-black text-slate-900">
                  {liveStats ? liveStats.users.total : usersList.length}
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-600">
                  <span className="font-semibold text-emerald-600">
                    {liveStats ? liveStats.users.active : usersList.filter((u) => u.is_active && !u.is_suspended).length} Active
                  </span>
                  <span>•</span>
                  <span className="font-semibold text-rose-600">
                    {liveStats ? liveStats.users.suspended : usersList.filter((u) => u.is_suspended).length} Suspended
                  </span>
                </div>
              </div>

              <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-2xs space-y-1.5">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-bold uppercase tracking-wider">Organizations</span>
                  <Building2 className="w-4 h-4 text-sky-600" />
                </div>
                <div className="text-2xl font-black text-slate-900">
                  {liveStats ? (liveStats.organizations?.total ?? liveStats.organizations_count) : 0}
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-600">
                  <span className="font-semibold text-emerald-600">
                    {liveStats?.organizations?.verified ?? 0} Verified
                  </span>
                  <span>•</span>
                  <span className="font-semibold text-amber-600">
                    {liveStats?.organizations?.pending ?? 0} Pending
                  </span>
                </div>
              </div>

              <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-2xs space-y-1.5">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-bold uppercase tracking-wider">Hierarchy Units</span>
                  <Landmark className="w-4 h-4 text-purple-600" />
                </div>
                <div className="text-2xl font-black text-slate-900">
                  {liveStats ? liveStats.government_units_count : 0}
                </div>
                <p className="text-[11px] text-slate-500 font-medium">4-Tier Central to Local Jurisdiction</p>
              </div>

              <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-2xs space-y-1.5">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-bold uppercase tracking-wider">Pending Verifications</span>
                  <ShieldAlert className="w-4 h-4 text-amber-600" />
                </div>
                <div className="text-2xl font-black text-amber-600">
                  {liveStats ? (liveStats.verifications?.total_pending ?? verificationQueue.filter((v) => v.status === 'PENDING').length) : verificationQueue.filter((v) => v.status === 'PENDING').length}
                </div>
                <p className="text-[11px] text-slate-500 font-medium">Action Queue Across 6 Tiers</p>
              </div>
            </div>

            {/* 6-Tier Verification Breakdown Snapshot */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-4 sm:p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-teal-600" />
                    6-Tier Verification Queue Distribution
                  </h3>
                  <p className="text-xs text-slate-500">Central, State, District, Local Government, Enterprises & Colleges</p>
                </div>
                <Link to="/admin/verification">
                  <Button variant="outline" size="sm" className="text-xs">
                    Open Full Verification Center
                  </Button>
                </Link>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {[
                  { tier: 'Central Govt', count: liveStats?.verifications?.by_tier?.central ?? 0, color: 'border-purple-200 bg-purple-50/50 text-purple-900' },
                  { tier: 'State Govt', count: liveStats?.verifications?.by_tier?.state ?? 0, color: 'border-blue-200 bg-blue-50/50 text-blue-900' },
                  { tier: 'District Govt', count: liveStats?.verifications?.by_tier?.district ?? 0, color: 'border-teal-200 bg-teal-50/50 text-teal-900' },
                  { tier: 'Local Govt', count: liveStats?.verifications?.by_tier?.local ?? 0, color: 'border-emerald-200 bg-emerald-50/50 text-emerald-900' },
                  { tier: 'Employers', count: liveStats?.verifications?.by_tier?.employer ?? 0, color: 'border-amber-200 bg-amber-50/50 text-amber-900' },
                  { tier: 'Colleges/ITIs', count: liveStats?.verifications?.by_tier?.institute ?? 0, color: 'border-indigo-200 bg-indigo-50/50 text-indigo-900' },
                ].map((item, idx) => (
                  <div key={idx} className={`p-3 rounded-lg border ${item.color} text-center space-y-1`}>
                    <p className="text-[11px] font-semibold text-slate-600">{item.tier}</p>
                    <p className="text-xl font-bold">{item.count}</p>
                    <span className="text-[10px] text-slate-500">Pending</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Split Section: Pending Queue Snapshot & Recent Audit Trail */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Pending Queue Snapshot */}
              <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-amber-600" />
                    Pending Verification Applications
                  </h3>
                  <Link to="/admin/verification" className="text-xs text-teal-700 font-semibold hover:underline">
                    View All ({verificationQueue.length})
                  </Link>
                </div>

                <div className="divide-y divide-slate-100">
                  {verificationQueue.filter((v) => v.status === 'PENDING').length === 0 ? (
                    <div className="p-6">
                      <EmptyState
                        icon={CheckCircle2}
                        title="Verification Queue Empty"
                        description="All organization, employer, and institutional applications have been processed."
                      />
                    </div>
                  ) : (
                    verificationQueue
                      .filter((v) => v.status === 'PENDING')
                      .slice(0, 5)
                      .map((item) => (
                        <div key={item.id} className="p-3.5 flex items-center justify-between text-xs hover:bg-slate-50 transition-colors">
                          <div className="space-y-0.5">
                            <p className="font-bold text-slate-900">
                              {item.applicant_entity_name || item.submitted_data?.legal_name || `Application #${item.id.slice(0, 8)}`}
                            </p>
                            <p className="text-[11px] text-slate-500">
                              {item.application_type} • Contact: {item.applicant_email || 'Direct Portal'}
                            </p>
                            {item.government_unit_name && (
                              <p className="text-[10px] text-teal-700 font-semibold">
                                Jurisdiction: {item.government_unit_name}
                              </p>
                            )}
                          </div>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => handleOpenVerificationAction(item)}
                            className="text-xs py-1 px-2.5 bg-teal-600 hover:bg-teal-700"
                          >
                            Review & Action
                          </Button>
                        </div>
                      ))
                  )}
                </div>
              </div>

              {/* Recent Audit Trail Snapshot */}
              <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-teal-600" />
                    Recent Administrative Audit Log
                  </h3>
                  <Link to="/admin/audit-logs" className="text-xs text-teal-700 font-semibold hover:underline">
                    Full Trail ({auditLogsList.length})
                  </Link>
                </div>

                <div className="divide-y divide-slate-100">
                  {auditLogsList.length === 0 ? (
                    <div className="p-6">
                      <EmptyState
                        icon={FileText}
                        title="No Audit Records"
                        description="Administrative actions and state transitions will be permanently recorded here."
                      />
                    </div>
                  ) : (
                    auditLogsList.slice(0, 5).map((log) => (
                      <div key={log.id} className="p-3 flex items-start justify-between text-xs space-y-0.5">
                        <div className="space-y-0.5 max-w-[80%]">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900">{log.action}</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-mono">
                              {log.resource_type}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600 line-clamp-1">{log.description}</p>
                          <p className="text-[10px] text-slate-400">
                            Actor: {log.actor_email || log.actor_user_id || 'System'}
                          </p>
                        </div>
                        <span className="text-[10px] text-slate-400 whitespace-nowrap font-mono">
                          {log.created_at ? new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* VIEW 2: 6-TIER VERIFICATION CENTER */}
        {/* ================================================================= */}
        {(activeSection === 'verification' || activeSection === 'verification_detail') && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-teal-600" />
                    6-Tier Entity Verification Center
                  </h2>
                  <p className="text-xs text-slate-500">
                    Review and authorize government hierarchies, employers, and training institutions with permanent audit trail logging.
                  </p>
                </div>

                {/* Status Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">Status:</span>
                  <select
                    value={verificationStatusFilter}
                    onChange={(e) => setVerificationStatusFilter(e.target.value)}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-teal-500"
                  >
                    <option value="all">All Statuses</option>
                    <option value="PENDING">PENDING</option>
                    <option value="VERIFIED">VERIFIED</option>
                    <option value="REJECTED">REJECTED</option>
                    <option value="SUSPENDED">SUSPENDED</option>
                  </select>
                </div>
              </div>

              {/* 6 Tier Tabs */}
              <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-100">
                {[
                  { id: 'all', label: 'All Tiers' },
                  { id: 'central', label: '1. Central Government' },
                  { id: 'state', label: '2. State Government' },
                  { id: 'district', label: '3. District Government' },
                  { id: 'local', label: '4. Local / Municipal' },
                  { id: 'employer', label: '5. Employers & Industry' },
                  { id: 'institute', label: '6. Colleges & ITIs' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setVerificationTier(tab.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                      verificationTier === tab.id
                        ? 'bg-teal-700 text-white shadow-2xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by entity name, email, phone, or application ID..."
                  value={verificationSearch}
                  onChange={(e) => setVerificationSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            </div>

            {/* Applications List */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
              {filteredVerifications.length === 0 ? (
                <div className="p-8">
                  <EmptyState
                    icon={CheckCircle2}
                    title="No Applications Found"
                    description="No verification applications match your selected tier and status criteria."
                  />
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {filteredVerifications.map((item) => (
                    <div key={item.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/80 transition-colors">
                      <div className="space-y-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">
                            {item.applicant_entity_name || item.submitted_data?.legal_name || `App #${item.id.slice(0, 8)}`}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              item.status === 'VERIFIED'
                                ? 'bg-emerald-100 text-emerald-800'
                                : item.status === 'PENDING'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}
                          >
                            {item.status}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
                            {item.application_type}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                          <span>Applicant: {item.applicant_email || item.applicant_user_id}</span>
                          {item.applicant_phone && <span>• Phone: {item.applicant_phone}</span>}
                          {item.government_unit_name && (
                            <span className="text-teal-700 font-semibold">
                              • Unit: {item.government_unit_name}
                            </span>
                          )}
                          <span>
                            • Submitted: {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}
                          </span>
                        </div>

                        {item.remarks && (
                          <p className="text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                            <span className="font-semibold">Notes:</span> {item.remarks}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleOpenVerificationAction(item)}
                          className="text-xs bg-teal-600 hover:bg-teal-700"
                        >
                          Review & Action
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* VIEW 3: USER DIRECTORY & ACCESS GOVERNANCE */}
        {/* ================================================================= */}
        {activeSection === 'users' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Users className="w-4 h-4 text-teal-600" />
                    Platform User Directory & Access Governance
                  </h2>
                  <p className="text-xs text-slate-500">
                    Search, inspect profiles, enforce suspensions, clear lockouts, and issue administrative statutory warnings.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={accountTypeFilter}
                    onChange={(e) => setAccountTypeFilter(e.target.value)}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium"
                  >
                    <option value="ALL">All Account Types</option>
                    <option value="CANDIDATE">Candidates</option>
                    <option value="EMPLOYER">Employers</option>
                    <option value="TRAINING_INSTITUTE">Institutes</option>
                    <option value="GOVERNMENT">Government</option>
                    <option value="SUPER_ADMIN">Super Admins</option>
                  </select>

                  <select
                    value={userStatusFilter}
                    onChange={(e) => setUserStatusFilter(e.target.value)}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="ACTIVE">Active Only</option>
                    <option value="SUSPENDED">Suspended Only</option>
                    <option value="LOCKED">Locked Out Only</option>
                  </select>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search users by email, phone, name, or account ID..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
              {filteredUsers.length === 0 ? (
                <div className="p-8">
                  <EmptyState
                    icon={Users}
                    title="No Users Found"
                    description="No platform users match your search and filter criteria."
                  />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                        <th className="p-3">User / Identity</th>
                        <th className="p-3">Role</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Verification</th>
                        <th className="p-3">Warnings</th>
                        <th className="p-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredUsers.map((user) => (
                        <tr key={user.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="p-3">
                            <div className="space-y-0.5">
                              <p className="font-bold text-slate-900">{user.email || 'No email'}</p>
                              <p className="text-[11px] text-slate-500">{user.entity_name || user.phone || user.id}</p>
                            </div>
                          </td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                              {user.account_type}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col gap-1">
                              {user.is_suspended ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                                  <AlertCircle className="w-3 h-3" /> Suspended
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                                  <Check className="w-3 h-3" /> Active
                                </span>
                              )}
                              {user.is_locked && (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                                  <Lock className="w-3 h-3" /> Locked Out
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-[11px] text-slate-500">
                            <div className="space-y-0.5">
                              <p>Email: {user.email_verified ? '✓ Verified' : 'Unverified'}</p>
                              <p>Phone: {user.phone_verified ? '✓ Verified' : 'Unverified'}</p>
                            </div>
                          </td>
                          <td className="p-3">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                (user.warnings_count ?? 0) > 0
                                  ? 'bg-amber-100 text-amber-900 border border-amber-200'
                                  : 'bg-slate-100 text-slate-500'
                              }`}
                            >
                              {user.warnings_count ?? 0} Warnings
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOpenUserDetail(user)}
                                className="text-xs py-1 px-2 text-slate-700"
                              >
                                Inspect
                              </Button>

                              {user.is_locked && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleUnlockUser(user)}
                                  className="text-xs py-1 px-2 text-amber-700 border-amber-300 hover:bg-amber-50"
                                >
                                  <Unlock className="w-3 h-3" /> Unlock
                                </Button>
                              )}

                              {user.is_suspended ? (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleOpenStatusModal(user, 'activate')}
                                  className="text-xs py-1 px-2 text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                                >
                                  Restore
                                </Button>
                              ) : (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleOpenStatusModal(user, 'suspend')}
                                  className="text-xs py-1 px-2 text-rose-700 border-rose-300 hover:bg-rose-50"
                                >
                                  Suspend
                                </Button>
                              )}

                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleOpenWarningModal(user)}
                                className="text-xs py-1 px-2 text-amber-700 border-amber-200 hover:bg-amber-50"
                              >
                                Warn
                              </Button>
                            </div>
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

        {/* ================================================================= */}
        {/* VIEW 4: PLATFORM & FORM CONTROL WITH VERSION ROLLBACK */}
        {/* ================================================================= */}
        {activeSection === 'platform_control' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-teal-600" />
                    Dynamic Form & Platform Controls
                  </h2>
                  <p className="text-xs text-slate-500">
                    Modify public landing content, signup fields, and statutory security policies without editing code. All changes are version-controlled with rollback support.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLoadHistory}
                    leftIcon={<History className="w-3.5 h-3.5" />}
                    className="text-xs"
                  >
                    Version History & Rollback
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleOpenConfigReasonModal}
                    leftIcon={<Save className="w-3.5 h-3.5" />}
                    className="text-xs bg-teal-600 hover:bg-teal-700"
                  >
                    Save Changes
                  </Button>
                </div>
              </div>

              {/* Module Selector Tabs */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
                {[
                  { id: 'landing', label: 'Landing Page Content' },
                  { id: 'signup', label: 'Auth & Signup Rules' },
                  { id: 'login', label: 'Login & Lockout Policies' },
                  { id: 'announcements', label: 'System Announcements' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveConfigTab(tab.id as any);
                      setShowHistoryView(false);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                      activeConfigTab === tab.id
                        ? 'bg-teal-700 text-white shadow-2xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Version History Drawer / Modal */}
            {showHistoryView ? (
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <History className="w-4 h-4 text-teal-600" />
                    Version Timeline for {getConfigKeyForActiveTab()}
                  </h3>
                  <button
                    onClick={() => setShowHistoryView(false)}
                    className="text-xs text-slate-500 hover:text-slate-800"
                  >
                    Close History
                  </button>
                </div>

                {configHistory.length === 0 ? (
                  <EmptyState
                    icon={History}
                    title="No Prior Versions"
                    description="This configuration is currently at baseline version 1."
                  />
                ) : (
                  <div className="divide-y divide-slate-100">
                    {configHistory.map((item) => (
                      <div key={item.id} className="py-3 flex items-start justify-between gap-4 text-xs">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900">Version {item.version}</span>
                            {item.is_active && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                                Current Active
                              </span>
                            )}
                            <span className="text-slate-400 font-mono">
                              {new Date(item.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-slate-600">
                            <span className="font-semibold">Rationale:</span> {item.change_reason || 'Initial seed configuration'}
                          </p>
                          <p className="text-[10px] text-slate-400">Admin Actor: {item.updated_by_user_id || 'System'}</p>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            onClick={() => setInspectVersionJson(item.config_data)}
                            className="px-2.5 py-1 rounded border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium"
                          >
                            Inspect Data
                          </button>
                          {!item.is_active && (
                            <button
                              onClick={() => handleRollbackVersion(item.version)}
                              className="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold flex items-center gap-1"
                            >
                              <RotateCcw className="w-3 h-3" /> Rollback
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Inspect JSON Modal */}
                {inspectVersionJson && (
                  <div className="mt-4 p-4 rounded-lg bg-slate-900 text-slate-200 text-xs font-mono overflow-auto max-h-60 border border-slate-700">
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                      <span className="text-slate-400 font-bold">Snapshot Configuration JSON</span>
                      <button onClick={() => setInspectVersionJson(null)} className="text-slate-400 hover:text-white">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <pre>{JSON.stringify(inspectVersionJson, null, 2)}</pre>
                  </div>
                )}
              </div>
            ) : (
              /* Config Editor Forms */
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-5">
                {/* 1. Landing Page Config */}
                {activeConfigTab === 'landing' && (
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Landing Page Hero & Metrics Configuration
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">Hero Badge Text</label>
                        <input
                          type="text"
                          value={landingConfig.hero_badge || ''}
                          onChange={(e) => setLandingConfig({ ...landingConfig, hero_badge: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">Hero Title</label>
                        <input
                          type="text"
                          value={landingConfig.hero_title || ''}
                          onChange={(e) => setLandingConfig({ ...landingConfig, hero_title: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                        />
                      </div>
                      <div className="sm:col-span-2">
                        <label className="block text-xs font-semibold text-slate-700 mb-1">Hero Subtitle</label>
                        <textarea
                          rows={2}
                          value={landingConfig.hero_subtitle || ''}
                          onChange={(e) => setLandingConfig({ ...landingConfig, hero_subtitle: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">Candidates Metric Label</label>
                        <input
                          type="text"
                          value={landingConfig.stats_candidates_label || ''}
                          onChange={(e) => setLandingConfig({ ...landingConfig, stats_candidates_label: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1">Employers Metric Label</label>
                        <input
                          type="text"
                          value={landingConfig.stats_employers_label || ''}
                          onChange={(e) => setLandingConfig({ ...landingConfig, stats_employers_label: e.target.value })}
                          className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Signup Rules Config */}
                {activeConfigTab === 'signup' && (
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Stakeholder Registration Field Requirements
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2">
                        <p className="font-bold text-slate-900">Candidate Fields</p>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={signupConfig.candidate_fields?.dob_required ?? false}
                            onChange={(e) =>
                              setSignupConfig({
                                ...signupConfig,
                                candidate_fields: { ...signupConfig.candidate_fields, dob_required: e.target.checked },
                              })
                            }
                          />
                          <span>Require Date of Birth during signup</span>
                        </label>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={signupConfig.candidate_fields?.education_required ?? false}
                            onChange={(e) =>
                              setSignupConfig({
                                ...signupConfig,
                                candidate_fields: { ...signupConfig.candidate_fields, education_required: e.target.checked },
                              })
                            }
                          />
                          <span>Require Highest Education qualification</span>
                        </label>
                      </div>

                      <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2">
                        <p className="font-bold text-slate-900">Employer Fields</p>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={signupConfig.employer_fields?.cin_required ?? false}
                            onChange={(e) =>
                              setSignupConfig({
                                ...signupConfig,
                                employer_fields: { ...signupConfig.employer_fields, cin_required: e.target.checked },
                              })
                            }
                          />
                          <span>Require Corporate CIN / Registration Number</span>
                        </label>
                      </div>

                      <div className="sm:col-span-2 p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2">
                        <p className="font-bold text-slate-900">Security & Cooldown Rules</p>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-slate-600 mb-1">Minimum Password Length</label>
                            <input
                              type="number"
                              value={signupConfig.general?.minPasswordLength ?? 8}
                              onChange={(e) =>
                                setSignupConfig({
                                  ...signupConfig,
                                  general: { ...signupConfig.general, minPasswordLength: Number(e.target.value) },
                                })
                              }
                              className="w-full px-2 py-1 rounded border border-slate-200"
                            />
                          </div>
                          <div>
                            <label className="block text-slate-600 mb-1">OTP Resend Cooldown (Seconds)</label>
                            <input
                              type="number"
                              value={signupConfig.general?.resendCooldownSeconds ?? 60}
                              onChange={(e) =>
                                setSignupConfig({
                                  ...signupConfig,
                                  general: { ...signupConfig.general, resendCooldownSeconds: Number(e.target.value) },
                                })
                              }
                              className="w-full px-2 py-1 rounded border border-slate-200"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. Login Policies */}
                {activeConfigTab === 'login' && (
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Authentication & Statutory Disclaimer Policies
                    </h3>
                    <div className="space-y-3 text-xs">
                      <div>
                        <label className="block font-semibold text-slate-700 mb-1">Statutory Disclaimer Banner Text</label>
                        <textarea
                          rows={2}
                          value={loginConfig.disclaimer_text || ''}
                          onChange={(e) => setLoginConfig({ ...loginConfig, disclaimer_text: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block font-semibold text-slate-700 mb-1">Max Failed Attempts Before Lockout</label>
                          <input
                            type="number"
                            value={loginConfig.max_login_attempts ?? 5}
                            onChange={(e) => setLoginConfig({ ...loginConfig, max_login_attempts: Number(e.target.value) })}
                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200"
                          />
                        </div>
                        <div>
                          <label className="block font-semibold text-slate-700 mb-1">Lockout Duration (Minutes)</label>
                          <input
                            type="number"
                            value={loginConfig.lockout_duration_minutes ?? 15}
                            onChange={(e) => setLoginConfig({ ...loginConfig, lockout_duration_minutes: Number(e.target.value) })}
                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. System Announcements */}
                {activeConfigTab === 'announcements' && (
                  <div className="space-y-4">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      System Broadcast Announcement
                    </h3>
                    <div className="space-y-3 text-xs">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={announcementConfig.banner_enabled ?? true}
                          onChange={(e) => setAnnouncementConfig({ ...announcementConfig, banner_enabled: e.target.checked })}
                        />
                        <span className="font-semibold text-slate-800">Enable Broadcast Banner across platform</span>
                      </label>
                      <div>
                        <label className="block font-semibold text-slate-700 mb-1">Announcement Title</label>
                        <input
                          type="text"
                          value={announcementConfig.banner_title || ''}
                          onChange={(e) => setAnnouncementConfig({ ...announcementConfig, banner_title: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-slate-200"
                        />
                      </div>
                      <div>
                        <label className="block font-semibold text-slate-700 mb-1">Announcement Message</label>
                        <textarea
                          rows={2}
                          value={announcementConfig.banner_message || ''}
                          onChange={(e) => setAnnouncementConfig({ ...announcementConfig, banner_message: e.target.value })}
                          className="w-full px-3 py-1.5 rounded-lg border border-slate-200"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block font-semibold text-slate-700 mb-1">Severity</label>
                          <select
                            value={announcementConfig.severity || 'NORMAL'}
                            onChange={(e) => setAnnouncementConfig({ ...announcementConfig, severity: e.target.value })}
                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
                          >
                            <option value="NORMAL">NORMAL (Teal Banner)</option>
                            <option value="INFO">INFO (Blue Banner)</option>
                            <option value="WARNING">WARNING (Amber Banner)</option>
                            <option value="CRITICAL">CRITICAL (Rose Banner)</option>
                          </select>
                        </div>
                        <div>
                          <label className="block font-semibold text-slate-700 mb-1">Audience</label>
                          <select
                            value={announcementConfig.target_audience || 'ALL'}
                            onChange={(e) => setAnnouncementConfig({ ...announcementConfig, target_audience: e.target.value })}
                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
                          >
                            <option value="ALL">All Stakeholders</option>
                            <option value="CANDIDATES">Candidates Only</option>
                            <option value="EMPLOYERS">Employers Only</option>
                            <option value="INSTITUTES">Institutes Only</option>
                            <option value="GOVERNMENT">Government Only</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* VIEW 5: IMMUTABLE AUDIT TRAIL */}
        {/* ================================================================= */}
        {activeSection === 'audit_logs' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <FileText className="w-4 h-4 text-teal-600" />
                    Immutable Administrative Audit Log
                  </h2>
                  <p className="text-xs text-slate-500">
                    Cryptographically recorded audit entries detailing actor identity, action type, resource changes, timestamps, and rationales.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={auditActionFilter}
                    onChange={(e) => setAuditActionFilter(e.target.value)}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium"
                  >
                    <option value="ALL">All Actions</option>
                    <option value="APPROVE">APPROVE</option>
                    <option value="REJECT">REJECT</option>
                    <option value="SUSPEND">SUSPEND</option>
                    <option value="RESTORE">RESTORE</option>
                    <option value="WARNING_ISSUED">WARNING_ISSUED</option>
                    <option value="CONFIG_UPDATED">CONFIG_UPDATED</option>
                    <option value="CONFIG_ROLLBACK">CONFIG_ROLLBACK</option>
                    <option value="LOGIN">LOGIN</option>
                  </select>

                  <select
                    value={auditResourceFilter}
                    onChange={(e) => setAuditResourceFilter(e.target.value)}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-medium"
                  >
                    <option value="ALL">All Resources</option>
                    <option value="user">Users</option>
                    <option value="VerificationApplication">Verification Apps</option>
                    <option value="platform_config">Platform Config</option>
                    <option value="user_warning">Warnings</option>
                  </select>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search audit trail by description, actor email, or resource ID..."
                  value={auditSearch}
                  onChange={(e) => setAuditSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
              </div>
            </div>

            {/* Audit Logs Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
              {filteredAuditLogs.length === 0 ? (
                <div className="p-8">
                  <EmptyState
                    icon={FileText}
                    title="No Audit Records Found"
                    description="No audit trail records matched your filter criteria."
                  />
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {filteredAuditLogs.map((log) => {
                    const isExpanded = expandedLogId === log.id;
                    return (
                      <div key={log.id} className="p-3.5 hover:bg-slate-50/80 transition-colors text-xs space-y-2">
                        <div
                          className="flex items-start justify-between cursor-pointer"
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  log.action === 'APPROVE'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : log.action === 'REJECT' || log.action === 'SUSPEND'
                                    ? 'bg-rose-100 text-rose-800'
                                    : log.action === 'WARNING_ISSUED'
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-slate-100 text-slate-800'
                                }`}
                              >
                                {log.action}
                              </span>
                              <span className="font-semibold text-slate-900">{log.resource_type}</span>
                              {log.resource_id && (
                                <span className="text-slate-400 font-mono text-[10px]">
                                  #{log.resource_id.slice(0, 8)}
                                </span>
                              )}
                            </div>
                            <p className="text-slate-700">{log.description}</p>
                            <p className="text-[10px] text-slate-400">
                              Actor: {log.actor_email || log.actor_user_id || 'System'}
                              {log.ip_address && ` • IP: ${log.ip_address}`}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-[11px] text-slate-400 font-mono">
                              {new Date(log.created_at).toLocaleString()}
                            </span>
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4 text-slate-400" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-slate-400" />
                            )}
                          </div>
                        </div>

                        {/* Expanded Metadata JSON */}
                        {isExpanded && log.metadata_json && (
                          <div className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg text-[11px] font-mono border border-slate-800 overflow-x-auto">
                            <div className="text-slate-400 text-[10px] mb-1 font-bold uppercase tracking-wider">
                              Metadata & Cryptographic Details
                            </div>
                            <pre>{JSON.stringify(log.metadata_json, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL 1: VERIFICATION ACTION MODAL */}
        {/* ================================================================= */}
        {isVerificationModalOpen && selectedVerificationApp && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  Perform Verification Action
                </h3>
                <button
                  onClick={() => setIsVerificationModalOpen(false)}
                  className="text-slate-400 hover:text-slate-700"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs space-y-1">
                <p className="font-bold text-slate-900">
                  {selectedVerificationApp.applicant_entity_name || selectedVerificationApp.submitted_data?.legal_name || 'Application'}
                </p>
                <p className="text-slate-600">
                  Tier: <span className="font-semibold">{selectedVerificationApp.tier || selectedVerificationApp.application_type}</span>
                </p>
                <p className="text-slate-600">
                  Applicant: {selectedVerificationApp.applicant_email || selectedVerificationApp.applicant_user_id}
                </p>
              </div>

              <form onSubmit={handleSubmitVerificationAction} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Select Action</label>
                  <select
                    value={verificationAction}
                    onChange={(e) => setVerificationAction(e.target.value as any)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white font-medium"
                  >
                    <option value="APPROVE">APPROVE - Issue Authenticated Platform Status</option>
                    <option value="REJECT">REJECT - Issue Statutory Rejection</option>
                    <option value="REQUEST_INFO">REQUEST_INFO - Solicit Additional Clarification</option>
                    <option value="SUSPEND">SUSPEND - Temporarily Suspend Authorization</option>
                    <option value="REVOKE">REVOKE - Permanently Revoke Credentials</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Formal Rationale {verificationAction !== 'APPROVE' && <span className="text-rose-600">*</span>}
                  </label>
                  <textarea
                    rows={2}
                    required={verificationAction !== 'APPROVE'}
                    value={verificationReason}
                    onChange={(e) => setVerificationReason(e.target.value)}
                    placeholder="Enter official rationale to be permanently written to the audit log..."
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Internal Admin Remarks (Optional)</label>
                  <input
                    type="text"
                    value={verificationRemarks}
                    onChange={(e) => setVerificationRemarks(e.target.value)}
                    placeholder="Reference numbers, internal verification notes..."
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200"
                  />
                </div>

                <div className="p-2.5 rounded-lg bg-teal-50/50 border border-teal-100 text-teal-900 text-[11px] leading-relaxed flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-teal-600 shrink-0 mt-0.5" />
                  <span>
                    Immutable Record: Your administrator ID, timestamp, decision rationale, and previous state will be permanently preserved in the platform audit log.
                  </span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsVerificationModalOpen(false)}
                    className="text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={isSubmittingVerification}
                    className="text-xs bg-teal-600 hover:bg-teal-700"
                  >
                    Confirm & Record
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL 2: USER PROFILE & STATUTORY DETAILS DRAWER */}
        {/* ================================================================= */}
        {isUserDetailOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/50 backdrop-blur-xs animate-in fade-in">
            <div className="bg-white h-full w-full max-w-md p-5 shadow-2xl border-l border-slate-200 overflow-y-auto space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Users className="w-4 h-4 text-teal-600" />
                  User Account Inspection
                </h3>
                <button onClick={() => setIsUserDetailOpen(false)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {isLoadingUserDetail || !selectedUserDetail ? (
                <div className="p-8 text-center text-xs text-slate-500">Loading comprehensive account record...</div>
              ) : (
                <div className="space-y-4 text-xs">
                  {/* Account Summary */}
                  <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-1.5">
                    <p className="font-bold text-slate-900 text-sm">{selectedUserDetail.email || 'No email'}</p>
                    <p className="text-slate-500">Account ID: <span className="font-mono">{selectedUserDetail.id}</span></p>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-800">
                        {selectedUserDetail.account_type}
                      </span>
                      {selectedUserDetail.is_suspended ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                          Suspended
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          Active
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Linked Profile Info */}
                  {selectedUserDetail.candidate && (
                    <div className="p-3 rounded-lg border border-slate-200 space-y-1">
                      <p className="font-semibold text-slate-800">Linked Candidate Profile</p>
                      <p className="text-slate-600">Name: {selectedUserDetail.candidate.name}</p>
                      <p className="text-slate-600">Profile Status: {selectedUserDetail.candidate.status}</p>
                    </div>
                  )}

                  {selectedUserDetail.organization && (
                    <div className="p-3 rounded-lg border border-slate-200 space-y-1">
                      <p className="font-semibold text-slate-800">Linked Organization</p>
                      <p className="text-slate-600">Legal Name: {selectedUserDetail.organization.legal_name}</p>
                      <p className="text-slate-600">Type: {selectedUserDetail.organization.type}</p>
                      <p className="text-slate-600">Verification: {selectedUserDetail.organization.verification_status}</p>
                    </div>
                  )}

                  {selectedUserDetail.government_unit && (
                    <div className="p-3 rounded-lg border border-slate-200 space-y-1">
                      <p className="font-semibold text-slate-800">Assigned Government Unit</p>
                      <p className="text-slate-600">Unit Name: {selectedUserDetail.government_unit.name}</p>
                      <p className="text-slate-600">Level: {selectedUserDetail.government_unit.level}</p>
                    </div>
                  )}

                  {/* Warnings History */}
                  <div className="space-y-2">
                    <h4 className="font-bold text-slate-900 flex items-center justify-between">
                      <span>Prior Statutory Warnings</span>
                      <span className="text-[10px] text-slate-500 font-normal">
                        ({selectedUserDetail.warnings?.length || 0} issued)
                      </span>
                    </h4>

                    {(!selectedUserDetail.warnings || selectedUserDetail.warnings.length === 0) ? (
                      <p className="text-slate-400 italic">No administrative warnings have been issued to this account.</p>
                    ) : (
                      <div className="space-y-2">
                        {selectedUserDetail.warnings.map((w: any) => (
                          <div key={w.id} className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/50 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-amber-900">{w.warning_title}</span>
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-200 text-amber-900 font-bold">
                                {w.severity}
                              </span>
                            </div>
                            <p className="text-slate-700">{w.warning_message}</p>
                            <p className="text-[10px] text-slate-500">
                              Reason: {w.reason} • {new Date(w.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL 3: ISSUE ADMINISTRATIVE WARNING */}
        {/* ================================================================= */}
        {isWarningModalOpen && warningTargetUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  Issue Administrative Statutory Warning
                </h3>
                <button onClick={() => setIsWarningModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs">
                <p className="font-bold text-slate-900">{warningTargetUser.email || warningTargetUser.id}</p>
                <p className="text-slate-500">Account Type: {warningTargetUser.account_type}</p>
              </div>

              <form onSubmit={handleSubmitWarning} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Warning Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Non-compliance with Skill Credentialing Guidelines"
                    value={warningTitle}
                    onChange={(e) => setWarningTitle(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">In-App Warning Message (Delivered to User)</label>
                  <textarea
                    rows={2}
                    required
                    placeholder="State the violation and required corrective action..."
                    value={warningMessage}
                    onChange={(e) => setWarningMessage(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Administrative Reason (Audit Record)</label>
                  <input
                    type="text"
                    required
                    placeholder="Formal statutory rationale for administrative record..."
                    value={warningReason}
                    onChange={(e) => setWarningReason(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Severity Level</label>
                  <select
                    value={warningSeverity}
                    onChange={(e) => setWarningSeverity(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 bg-white"
                  >
                    <option value="LOW">LOW - Advisory Notice</option>
                    <option value="NORMAL">NORMAL - Standard Compliance Warning</option>
                    <option value="HIGH">HIGH - Urgent Rectification Required</option>
                    <option value="CRITICAL">CRITICAL - Final Notice Prior to Account Suspension</option>
                  </select>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsWarningModalOpen(false)}
                    className="text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={isSubmittingWarning}
                    className="text-xs bg-amber-600 hover:bg-amber-700 text-white"
                  >
                    Dispatch Warning
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL 4: USER SUSPENSION / RESTORATION MODAL */}
        {/* ================================================================= */}
        {isStatusModalOpen && statusTargetUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  {statusActionType === 'suspend' ? 'Suspend User Access' : 'Restore User Access'}
                </h3>
                <button onClick={() => setIsStatusModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-xs text-slate-600">
                You are about to {statusActionType === 'suspend' ? 'suspend all platform access for' : 'restore access to'}{' '}
                <span className="font-bold text-slate-900">{statusTargetUser.email || statusTargetUser.id}</span>.
              </p>

              <form onSubmit={handleSubmitStatusUpdate} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Mandatory Administrative Reason <span className="text-rose-600">*</span>
                  </label>
                  <textarea
                    rows={2}
                    required
                    placeholder="Specify the compliance or security reason for this action..."
                    value={statusReason}
                    onChange={(e) => setStatusReason(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsStatusModalOpen(false)}
                    className="text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={isSubmittingStatus}
                    className={`text-xs ${
                      statusActionType === 'suspend'
                        ? 'bg-rose-600 hover:bg-rose-700'
                        : 'bg-emerald-600 hover:bg-emerald-700'
                    }`}
                  >
                    Confirm {statusActionType === 'suspend' ? 'Suspension' : 'Restoration'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODAL 5: CONFIG SAVE REASON MODAL */}
        {/* ================================================================= */}
        {isConfigReasonModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
            <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Save className="w-4 h-4 text-teal-600" />
                  Confirm Configuration Revision
                </h3>
                <button onClick={() => setIsConfigReasonModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-xs text-slate-600">
                A new immutable version will be registered for configuration key{' '}
                <span className="font-bold text-slate-900 font-mono">{getConfigKeyForActiveTab()}</span>.
              </p>

              <form onSubmit={handleSubmitConfigSave} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Change Rationale / Justification <span className="text-rose-600">*</span>
                  </label>
                  <textarea
                    rows={2}
                    required
                    placeholder="Describe why this configuration is being modified (e.g. Updated FY26 skilling stats)..."
                    value={configChangeReason}
                    onChange={(e) => setConfigChangeReason(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:ring-1 focus:ring-teal-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsConfigReasonModalOpen(false)}
                    className="text-xs"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={isSavingConfig}
                    className="text-xs bg-teal-600 hover:bg-teal-700"
                  >
                    Save & Create Version
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default AdminDashboard;
