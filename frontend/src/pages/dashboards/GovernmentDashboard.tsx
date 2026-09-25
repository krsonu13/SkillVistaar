import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Landmark,
  ShieldCheck,
  Award,
  CheckCircle2,
  FolderTree,
  Building2,
  School,
  TrendingUp,
  ChevronRight,
  X,
  RefreshCw,
} from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import { EmptyState } from '../../components/common/EmptyState';
import { usePlatform } from '../../context/PlatformContext';
import { useRealtime } from '../../context/RealtimeContext';
import {
  governmentApi,
  followingApi,
  verificationApi,
  GovtDashboardStats,
  GovtUnitNode,
  VerificationAppRecord,
} from '../../services/api';
import { PendingVerificationDocument } from '../../types/document';

export interface GovernmentDashboardProps {
  section?:
    | 'overview'
    | 'trends'
    | 'demand'
    | 'districts'
    | 'organizations'
    | 'courses'
    | 'following'
    | 'drilldown'
    | 'documents'
    | 'verifications';
}

export const GovernmentDashboard: React.FC<GovernmentDashboardProps> = ({ section: propSection }) => {
  const location = useLocation();
  const { currentUser } = usePlatform();

  // Deduce active section
  const getActiveSection = () => {
    if (propSection) return propSection;
    const path = location.pathname;
    if (path.includes('/government/drill-down')) return 'drilldown';
    if (path.includes('/government/verifications')) return 'verifications';
    if (path.includes('/government/documents')) return 'documents';
    if (path.includes('/government/trends')) return 'trends';
    if (path.includes('/government/demand')) return 'demand';
    if (path.includes('/government/districts')) return 'districts';
    if (path.includes('/government/organizations')) return 'organizations';
    if (path.includes('/government/courses')) return 'courses';
    if (path.includes('/government/following')) return 'following';
    return 'overview';
  };

  const activeSection = getActiveSection();
  const { subscribe } = useRealtime();

  const [liveStats, setLiveStats] = useState<GovtDashboardStats | null>(null);
  const [_hierarchy, setHierarchy] = useState<GovtUnitNode[]>([]);
  const [_selectedUnit, setSelectedUnit] = useState<GovtUnitNode | null>(null);
  const [emergingSkills, setEmergingSkills] = useState<any[]>([]);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [_followingList, setFollowingList] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Drill-down state
  const [drillDownData, setDrillDownData] = useState<any>(null);
  const [drillDownLoading, setDrillDownLoading] = useState(false);
  const [drillDownUnitId, setDrillDownUnitId] = useState<string | undefined>(undefined);
  const [drillDownHistory, setDrillDownHistory] = useState<Array<{ id: string; name: string }>>([]);

  // Pending Applications state
  const [pendingApps, setPendingApps] = useState<VerificationAppRecord[]>([]);
  const [appsLoading, setAppsLoading] = useState(false);
  const [reviewingApp, setReviewingApp] = useState<VerificationAppRecord | null>(null);
  const [appReviewAction, setAppReviewAction] = useState<'APPROVE' | 'REJECT' | 'REQUEST_MORE_INFO' | 'UNDER_REVIEW'>('APPROVE');
  const [appReviewRemarks, setAppReviewRemarks] = useState('');
  const [appRejectionReason, setAppRejectionReason] = useState('');
  const [appMoreInfoRemarks, setAppMoreInfoRemarks] = useState('');
  const [submittingAppReview, setSubmittingAppReview] = useState(false);

  // Pending Documents state
  const [pendingDocs, setPendingDocs] = useState<PendingVerificationDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [reviewingDoc, setReviewingDoc] = useState<PendingVerificationDocument | null>(null);
  const [reviewAction, setReviewAction] = useState<'APPROVE' | 'REJECT' | 'REQUEST_INFORMATION' | 'START_REVIEW'>('APPROVE');
  const [reviewRemarks, setReviewRemarks] = useState('');
  const [reviewReason, setReviewReason] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewFeedback, setReviewFeedback] = useState<string | null>(null);

  const loadPendingApps = async () => {
    setAppsLoading(true);
    try {
      const apps = await verificationApi.getPending();
      setPendingApps(apps);
    } catch {
      setPendingApps([]);
    } finally {
      setAppsLoading(false);
    }
  };

  const handleOpenAppReviewModal = (app: VerificationAppRecord) => {
    setReviewingApp(app);
    setAppReviewAction('APPROVE');
    setAppReviewRemarks('');
    setAppRejectionReason('');
    setAppMoreInfoRemarks('');
  };

  const handleSubmitAppReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingApp) return;
    setSubmittingAppReview(true);
    setReviewFeedback(null);
    try {
      await verificationApi.reviewApplication(reviewingApp.id, {
        action: appReviewAction,
        remarks: appReviewRemarks.trim() || undefined,
        rejection_reason: appRejectionReason.trim() || undefined,
        request_information_remarks: appMoreInfoRemarks.trim() || undefined,
      });
      setReviewFeedback(`Application review decision '${appReviewAction}' recorded and applicant notified.`);
      setReviewingApp(null);
      await loadPendingApps();
      await loadGovtData();
    } catch (err: any) {
      setReviewFeedback(err?.response?.data?.detail || 'Failed to submit application review decision.');
    } finally {
      setSubmittingAppReview(false);
      setTimeout(() => setReviewFeedback(null), 5000);
    }
  };

  // Real-time event listener for verification queue updates
  useEffect(() => {
    const unsub = subscribe('VERIFICATION_QUEUE_UPDATED', () => {
      loadPendingApps();
      loadPendingDocs();
      loadGovtData();
    });
    return () => unsub();
  }, [subscribe]);

  const loadGovtData = async () => {
    setIsLoading(true);
    try {
      const [stats, tree, trends, orgs, following] = await Promise.all([
        governmentApi.getDashboard(),
        governmentApi.getHierarchy(),
        governmentApi.getEmergingSkills(),
        governmentApi.getOrganizations(),
        followingApi.getFollowing(),
      ]);
      if (stats) setLiveStats(stats);
      if (tree && tree.length > 0) {
        setHierarchy(tree);
        setSelectedUnit(tree[0]);
      }
      setEmergingSkills(trends || []);
      setOrganizations(orgs || []);
      setFollowingList(following || []);
    } catch {
      // keep clean empty state
    } finally {
      setIsLoading(false);
    }
  };

  const loadDrillDown = async (unitId?: string) => {
    setDrillDownLoading(true);
    try {
      const data = await governmentApi.getDrillDown(unitId);
      setDrillDownData(data);
    } catch {
      setDrillDownData(null);
    } finally {
      setDrillDownLoading(false);
    }
  };

  const loadPendingDocs = async () => {
    setDocsLoading(true);
    try {
      const docs = await governmentApi.getPendingDocuments();
      setPendingDocs(docs);
    } catch {
      setPendingDocs([]);
    } finally {
      setDocsLoading(false);
    }
  };

  useEffect(() => {
    loadGovtData();
    loadPendingApps();
    loadPendingDocs();
  }, []);

  useEffect(() => {
    if (activeSection === 'drilldown') {
      loadDrillDown(drillDownUnitId);
    } else if (activeSection === 'documents') {
      loadPendingDocs();
    } else if (activeSection === 'verifications') {
      loadPendingApps();
    }
  }, [activeSection, drillDownUnitId]);

  const handleDrillIntoUnit = (subUnit: { id: string; name: string }) => {
    if (drillDownData?.current_unit) {
      setDrillDownHistory((prev) => [
        ...prev,
        { id: drillDownData.current_unit.id, name: drillDownData.current_unit.name },
      ]);
    }
    setDrillDownUnitId(subUnit.id);
  };

  const handleDrillBack = (targetUnitId?: string, targetIndex?: number) => {
    if (targetIndex !== undefined) {
      setDrillDownHistory((prev) => prev.slice(0, targetIndex));
    } else {
      setDrillDownHistory([]);
    }
    setDrillDownUnitId(targetUnitId);
  };

  const handleOpenReviewModal = (doc: PendingVerificationDocument) => {
    setReviewingDoc(doc);
    setReviewAction('APPROVE');
    setReviewRemarks('');
    setReviewReason('');
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingDoc) return;
    setSubmittingReview(true);
    setReviewFeedback(null);
    try {
      await governmentApi.reviewDocument(reviewingDoc.id, {
        action: reviewAction,
        remarks: reviewRemarks.trim() || undefined,
        reason: reviewReason.trim() || undefined,
      });
      setReviewFeedback(`Statutory verification action '${reviewAction}' recorded successfully.`);
      setReviewingDoc(null);
      await loadPendingDocs();
      await loadGovtData();
    } catch (err: any) {
      setReviewFeedback(err?.response?.data?.detail || 'Failed to submit verification action.');
    } finally {
      setSubmittingReview(false);
      setTimeout(() => setReviewFeedback(null), 5000);
    }
  };

  const activeUnit = liveStats?.unit || {
    name: currentUser.name,
    code: 'GOV-HQ',
    level: 1,
    unit_type: 'Central Governance',
  };

  if (isLoading) {
    return (
      <DashboardLayout activeTab="districts">
        <div className="flex items-center justify-center p-12">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Loading government workspace...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout activeTab={activeSection}>
      <div className="space-y-5">
        {/* Government Top Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-teal-950 to-slate-900 rounded-xl p-4 sm:p-5 text-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-teal-500/20 text-teal-200 border border-teal-400/30">
                <Landmark className="w-3.5 h-3.5 text-teal-300" />
                Level {activeUnit.level} • {activeUnit.unit_type}
              </span>
              <span className="text-[11px] text-slate-300 font-mono">
                Code: {activeUnit.code}
              </span>
            </div>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight">
              {activeUnit.name} Governance Portal
            </h1>
            <p className="text-xs text-teal-100 max-w-2xl">
              Multi-tier statutory jurisdiction authority. Verify institutional compliance, audit employer credentials, and inspect regional skill-demand telemetry.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link to="/government/verifications">
              <Button
                variant={activeSection === 'verifications' ? 'primary' : 'outline'}
                size="sm"
                className={`text-xs font-semibold flex items-center gap-1.5 ${
                  activeSection === 'verifications'
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                    : 'bg-white/10 hover:bg-white/20 text-white border-white/20'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Applications Queue
                {pendingApps.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full bg-white text-emerald-800 text-[10px] font-bold">
                    {pendingApps.length}
                  </span>
                )}
              </Button>
            </Link>
            <Link to="/government/documents">
              <Button
                variant={activeSection === 'documents' ? 'primary' : 'outline'}
                size="sm"
                className={`text-xs font-semibold flex items-center gap-1.5 ${
                  activeSection === 'documents'
                    ? 'bg-teal-600 hover:bg-teal-700 text-white'
                    : 'bg-white/10 hover:bg-white/20 text-white border-white/20'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Document Verification
                {pendingDocs.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full bg-white text-teal-800 text-[10px] font-bold">
                    {pendingDocs.length}
                  </span>
                )}
              </Button>
            </Link>
            <Link to="/government/drill-down">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                leftIcon={<FolderTree className="w-3.5 h-3.5" />}
              >
                Jurisdiction Drill-Down
              </Button>
            </Link>
          </div>
        </div>

        {reviewFeedback && (
          <div className="p-3 bg-teal-50 border border-teal-200 text-teal-800 rounded-lg text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
            <span>{reviewFeedback}</span>
          </div>
        )}

        {/* SECTION: OVERVIEW */}
        {activeSection === 'overview' && (
          <div className="space-y-5">
            {/* Real stats cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Approved Institutes</span>
                  <School className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {liveStats?.statistics?.total_institutes ?? 0}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">In jurisdiction</p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Active Employers</span>
                  <Building2 className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {liveStats?.statistics?.total_employers ?? 0}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">Registered enterprises</p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Pending Verifications</span>
                  <TrendingUp className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {liveStats?.statistics?.pending_verifications ?? 0}
                </div>
                <p className="text-[10px] text-amber-600 font-semibold">Awaiting review</p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Verified Credentials</span>
                  <Award className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {liveStats?.statistics?.verified_credentials ?? 0}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">Verified credentials</p>
              </div>
            </div>

            {/* Split: Quick Actions & Registered Entities */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-8 space-y-5">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                    <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                      Regional Entities in Jurisdiction ({organizations.length})
                    </h3>
                    <Link to="/government/organizations" className="text-xs text-teal-700 font-semibold hover:underline">
                      View All
                    </Link>
                  </div>
                  <div className="divide-y divide-slate-100 dark:divide-slate-800 mt-2">
                    {organizations.length === 0 ? (
                      <div className="p-6 text-center text-xs text-slate-500">
                        No organizations currently registered under this jurisdiction.
                      </div>
                    ) : (
                      organizations.slice(0, 6).map((org) => (
                        <div key={org.id} className="py-2.5 flex items-center justify-between text-xs">
                          <div>
                            <span className="font-semibold text-slate-900 dark:text-slate-100">
                              {org.legal_name || org.display_name}
                            </span>
                            <span className="text-slate-400 ml-2">({org.organization_type})</span>
                          </div>
                          <Badge variant={org.verification_status === 'APPROVED' ? 'emerald' : 'amber'} size="sm">
                            {org.verification_status}
                          </Badge>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-4 space-y-4">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-2.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                    Administrative Functions
                  </h4>
                  <div className="space-y-1.5">
                    <Link
                      to="/government/documents"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-teal-600" />
                        Pending Document Review
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                    <Link
                      to="/government/drill-down"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <FolderTree className="w-4 h-4 text-teal-600" />
                        Jurisdiction Drill-Down
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                    <Link
                      to="/government/trends"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-teal-600" />
                        Regional Skill Trends
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SECTION: JURISDICTION DRILL-DOWN */}
        {activeSection === 'drilldown' && (
          <div className="space-y-5">
            {/* Breadcrumb Navigation */}
            <div className="flex items-center gap-2 p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs shadow-xs overflow-x-auto">
              <button
                onClick={() => handleDrillBack(undefined)}
                className={`font-semibold hover:underline ${
                  drillDownHistory.length === 0 ? 'text-teal-700 dark:text-teal-400 font-bold' : 'text-slate-600 dark:text-slate-400'
                }`}
              >
                Top Jurisdiction
              </button>

              {drillDownHistory.map((h, idx) => (
                <React.Fragment key={h.id}>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                  <button
                    onClick={() => handleDrillBack(h.id, idx)}
                    className="font-medium text-slate-600 hover:underline"
                  >
                    {h.name}
                  </button>
                </React.Fragment>
              ))}

              {drillDownData?.current_unit && drillDownHistory.length > 0 && (
                <>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-bold text-teal-700 dark:text-teal-300">
                    {drillDownData.current_unit.name}
                  </span>
                </>
              )}
            </div>

            {drillDownLoading ? (
              <div className="flex justify-center items-center py-16 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
                <RefreshCw className="w-8 h-8 text-teal-600 animate-spin" />
              </div>
            ) : drillDownData ? (
              <div className="space-y-5">
                {/* Current Unit Info Banner */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-teal-100 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300">
                        Level {drillDownData.current_unit.level} • {drillDownData.current_unit.unit_type}
                      </span>
                      <span className="text-xs font-mono text-slate-500">
                        {drillDownData.current_unit.code}
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                      {drillDownData.current_unit.name}
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Statutory Jurisdiction Area: {drillDownData.current_unit.jurisdiction}
                    </p>
                  </div>

                  {/* Aggregates */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-center">
                      <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                        {drillDownData.aggregates?.active_jobs ?? 0}
                      </div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Active Jobs</div>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-center">
                      <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                        {drillDownData.aggregates?.approved_institutions ?? 0}
                      </div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Institutes</div>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-center">
                      <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                        {drillDownData.aggregates?.total_courses ?? 0}
                      </div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Courses</div>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-center">
                      <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
                        {drillDownData.aggregates?.total_learners_placed ?? 0}
                      </div>
                      <div className="text-[10px] text-slate-500 uppercase font-semibold">Placed</div>
                    </div>
                  </div>
                </div>

                {/* Sub-Units Cards (Drill Down deeper) */}
                {drillDownData.sub_units && drillDownData.sub_units.length > 0 && (
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-3">
                    <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                      <FolderTree className="w-4 h-4 text-teal-600" />
                      Subordinate Administrative Units ({drillDownData.sub_units.length})
                    </h3>
                    <p className="text-xs text-slate-500">
                      Click any subordinate unit to drill down into district/local jurisdiction
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2">
                      {drillDownData.sub_units.map((u: any) => (
                        <div
                          key={u.id}
                          className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 hover:border-teal-400 transition space-y-2"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                              Level {u.level} • {u.unit_type}
                            </span>
                            <span className="font-mono text-[10px] text-slate-400">{u.code}</span>
                          </div>
                          <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">{u.name}</h4>
                          <button
                            onClick={() => handleDrillIntoUnit(u)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-teal-600 hover:text-teal-700 pt-1"
                          >
                            Drill Down &rarr;
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Registered Organizations in Jurisdiction */}
                <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-teal-600" />
                    Organizations Bounded in this Jurisdiction ({drillDownData.organizations?.length ?? 0})
                  </h3>

                  {drillDownData.organizations?.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-500">
                      No entities registered directly under this unit.
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {drillDownData.organizations.map((org: any) => (
                        <div key={org.id} className="py-3 flex items-center justify-between text-xs">
                          <div>
                            <h4 className="font-bold text-slate-900 dark:text-slate-100">{org.name}</h4>
                            <p className="text-[11px] text-slate-500">
                              {org.organization_type} • Reg: {org.registration_number || 'N/A'}
                            </p>
                          </div>
                          <Badge variant={org.verification_status === 'APPROVED' ? 'emerald' : 'amber'} size="sm">
                            {org.verification_status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* SECTION: VERIFICATION APPLICATIONS QUEUE */}
        {activeSection === 'verifications' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Statutory Entity Verification Queue ({pendingApps.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Institutional, employer, and subordinate government applications requiring statutory clearing in your jurisdiction
                </p>
              </div>
              <button
                onClick={loadPendingApps}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${appsLoading ? 'animate-spin' : ''}`} /> Refresh Queue
              </button>
            </div>

            {appsLoading ? (
              <div className="flex justify-center items-center py-12">
                <RefreshCw className="w-6 h-6 text-teal-600 animate-spin" />
              </div>
            ) : pendingApps.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={ShieldCheck}
                  title="Queue is empty"
                  description="No entity registration applications currently awaiting statutory verification in your jurisdiction."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Applicant Entity</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Nodal Contact</th>
                      <th className="px-4 py-3">Submitted</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Review Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {pendingApps.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3.5">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {app.organization_name || app.government_unit_name || app.applicant_name || 'Organization'}
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Ref: {app.id.slice(0, 8).toUpperCase()}
                          </span>
                        </td>

                        <td className="px-4 py-3.5">
                          <Badge variant="teal" size="sm">
                            {app.application_type}
                          </Badge>
                        </td>

                        <td className="px-4 py-3.5">
                          <div className="font-medium text-slate-800 dark:text-slate-200">
                            {app.applicant_name || app.applicant_username || 'Authorized Officer'}
                          </div>
                          {app.applicant_email && (
                            <span className="text-[10px] text-slate-400 font-mono block">
                              {app.applicant_email}
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                          {app.submitted_at || app.created_at ? new Date(app.submitted_at || app.created_at).toLocaleDateString() : 'Recent'}
                        </td>

                        <td className="px-4 py-3.5">
                          <Badge
                            variant={
                              app.status === 'APPROVED' ? 'emerald' :
                              app.status === 'REJECTED' ? 'slate' :
                              app.status === 'MORE_INFORMATION_REQUIRED' ? 'amber' :
                              'teal'
                            }
                            size="sm"
                          >
                            {app.status}
                          </Badge>
                        </td>

                        <td className="px-4 py-3.5 text-right">
                          <button
                            onClick={() => handleOpenAppReviewModal(app)}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs transition"
                          >
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Review
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* MODAL: APPLICATION REVIEW */}
        {reviewingApp && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
            <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      Review Verification Application
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      {reviewingApp.organization_name || reviewingApp.applicant_entity_name || reviewingApp.government_unit_name || reviewingApp.applicant_name || 'Organization'} ({reviewingApp.application_type})
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setReviewingApp(null)}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleSubmitAppReview} className="p-5 space-y-4 text-xs">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1.5">
                    Statutory Decision
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setAppReviewAction('APPROVE')}
                      className={`py-2 px-3 rounded-lg border font-semibold text-center transition ${
                        appReviewAction === 'APPROVE'
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-500 text-emerald-800 dark:text-emerald-200'
                          : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }`}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      onClick={() => setAppReviewAction('REQUEST_MORE_INFO')}
                      className={`py-2 px-3 rounded-lg border font-semibold text-center transition ${
                        appReviewAction === 'REQUEST_MORE_INFO'
                          ? 'bg-amber-50 dark:bg-amber-950/40 border-amber-500 text-amber-800 dark:text-amber-200'
                          : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }`}
                    >
                      More Info
                    </button>
                    <button
                      type="button"
                      onClick={() => setAppReviewAction('REJECT')}
                      className={`py-2 px-3 rounded-lg border font-semibold text-center transition ${
                        appReviewAction === 'REJECT'
                          ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-500 text-rose-800 dark:text-rose-200'
                          : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                      }`}
                    >
                      Reject
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1.5">
                    Statutory Audit Remarks
                  </label>
                  <textarea
                    rows={2}
                    value={appReviewRemarks}
                    onChange={(e) => setAppReviewRemarks(e.target.value)}
                    placeholder="Enter audit remarks or compliance notes..."
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  />
                </div>

                {appReviewAction === 'REQUEST_MORE_INFO' && (
                  <div>
                    <label className="block text-xs font-semibold text-amber-600 uppercase mb-1.5">
                      Required Information / Documents *
                    </label>
                    <textarea
                      rows={2}
                      value={appMoreInfoRemarks}
                      onChange={(e) => setAppMoreInfoRemarks(e.target.value)}
                      placeholder="Specify required documents, affiliation proofs, or clarifications..."
                      className="w-full px-3 py-2 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 rounded-lg text-xs text-amber-900 dark:text-amber-100"
                      required
                    />
                  </div>
                )}

                {appReviewAction === 'REJECT' && (
                  <div>
                    <label className="block text-xs font-semibold text-rose-600 uppercase mb-1.5">
                      Statutory Rejection Reason *
                    </label>
                    <textarea
                      rows={2}
                      value={appRejectionReason}
                      onChange={(e) => setAppRejectionReason(e.target.value)}
                      placeholder="Specify regulatory clause or reason for rejection..."
                      className="w-full px-3 py-2 bg-rose-50 dark:bg-rose-950/40 border border-rose-300 rounded-lg text-xs text-rose-900 dark:text-rose-100"
                      required
                    />
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setReviewingApp(null)}
                    className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAppReview}
                    className={`px-4 py-2 text-sm font-semibold rounded-lg text-white shadow-sm flex items-center gap-2 ${
                      appReviewAction === 'APPROVE' ? 'bg-emerald-600 hover:bg-emerald-700' :
                      appReviewAction === 'REJECT' ? 'bg-rose-600 hover:bg-rose-700' :
                      'bg-amber-600 hover:bg-amber-700'
                    }`}
                  >
                    {submittingAppReview && <RefreshCw className="w-4 h-4 animate-spin" />}
                    Confirm Application Decision
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* SECTION: DOCUMENT VERIFICATION */}
        {activeSection === 'documents' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  Statutory Document Verification Queue ({pendingDocs.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Statutory documents submitted by employers and institutes within your jurisdiction
                </p>
              </div>
              <button
                onClick={loadPendingDocs}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh Queue
              </button>
            </div>

            {docsLoading ? (
              <div className="flex justify-center items-center py-12">
                <RefreshCw className="w-6 h-6 text-teal-600 animate-spin" />
              </div>
            ) : pendingDocs.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={ShieldCheck}
                  title="Queue is empty"
                  description="No organization documents currently awaiting statutory verification in your jurisdiction."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Applicant Entity</th>
                      <th className="px-4 py-3">Document Title & Type</th>
                      <th className="px-4 py-3">Issuing Authority</th>
                      <th className="px-4 py-3">Jurisdiction</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Review Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {pendingDocs.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                        <td className="px-4 py-3.5">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">{doc.organization_name}</div>
                          <span className="text-[10px] text-slate-400">{doc.organization_type}</span>
                        </td>

                        <td className="px-4 py-3.5">
                          <div className="font-medium text-slate-800 dark:text-slate-200">{doc.title}</div>
                          <div className="text-[10px] text-slate-500">{doc.document_type}</div>
                          {doc.document_number && (
                            <div className="text-[10px] font-mono text-slate-500">No: {doc.document_number}</div>
                          )}
                        </td>

                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                          {doc.issuing_authority || 'Not Specified'}
                        </td>

                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                          {doc.jurisdiction_name}
                        </td>

                        <td className="px-4 py-3.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                            {doc.status}
                          </span>
                        </td>

                        <td className="px-4 py-3.5 text-right">
                          <button
                            onClick={() => handleOpenReviewModal(doc)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white shadow-xs"
                          >
                            Review & Verify
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Document Review Modal */}
        {reviewingDoc && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-xl">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-teal-600" />
                  Statutory Verification Decision
                </h3>
                <button onClick={() => setReviewingDoc(null)} className="p-1 text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl space-y-1 text-xs">
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Entity:</span>{' '}
                  <span className="font-bold text-slate-900 dark:text-slate-100">{reviewingDoc.organization_name}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Document:</span>{' '}
                  {reviewingDoc.title} ({reviewingDoc.document_type})
                </div>
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Authority:</span>{' '}
                  {reviewingDoc.issuing_authority || 'N/A'}
                </div>
              </div>

              <form onSubmit={handleSubmitReview} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1.5">
                    Verification Action *
                  </label>
                  <select
                    value={reviewAction}
                    onChange={(e) => setReviewAction(e.target.value as any)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-semibold"
                    required
                  >
                    <option value="APPROVE">Approve & Issue Statutory Verification</option>
                    <option value="REQUEST_INFORMATION">Request Clarification / Additional Information</option>
                    <option value="REJECT">Reject Document (State Statutory Non-Compliance)</option>
                    <option value="START_REVIEW">Mark Under Official Investigation</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1.5">
                    Verification Remarks / Instructions
                  </label>
                  <textarea
                    rows={3}
                    value={reviewRemarks}
                    onChange={(e) => setReviewRemarks(e.target.value)}
                    placeholder="Official comments recorded in permanent audit trail..."
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-xs"
                  />
                </div>

                {reviewAction === 'REJECT' && (
                  <div>
                    <label className="block text-xs font-semibold text-rose-600 uppercase mb-1.5">
                      Statutory Rejection Reason *
                    </label>
                    <textarea
                      rows={2}
                      value={reviewReason}
                      onChange={(e) => setReviewReason(e.target.value)}
                      placeholder="Specify regulatory clause or reason for rejection..."
                      className="w-full px-3 py-2 bg-rose-50 dark:bg-rose-950/40 border border-rose-300 rounded-lg text-xs text-rose-900 dark:text-rose-100"
                      required
                    />
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setReviewingDoc(null)}
                    className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className={`px-4 py-2 text-sm font-semibold rounded-lg text-white shadow-sm flex items-center gap-2 ${
                      reviewAction === 'APPROVE' ? 'bg-emerald-600 hover:bg-emerald-700' :
                      reviewAction === 'REJECT' ? 'bg-rose-600 hover:bg-rose-700' :
                      'bg-teal-600 hover:bg-teal-700'
                    }`}
                  >
                    {submittingReview && <RefreshCw className="w-4 h-4 animate-spin" />}
                    Confirm Verification Decision
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* SECTION: TRENDS */}
        {activeSection === 'trends' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-teal-600" />
                Regional Skill Demand Trends
              </h3>
            </div>
            {emergingSkills.length === 0 ? (
              <EmptyState icon={TrendingUp} title="No trend signals" description="Emerging regional skills will be displayed here." />
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {emergingSkills.map((sk: any, idx: number) => (
                  <div key={idx} className="py-3 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">{sk.skill_name || sk.name}</span>
                    <Badge variant="teal" size="sm">High Demand</Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION: ORGANIZATIONS */}
        {activeSection === 'organizations' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                <Building2 className="w-4 h-4 text-teal-600" />
                Accredited Organizations & Enterprises ({organizations.length})
              </h3>
            </div>
            {organizations.length === 0 ? (
              <EmptyState icon={Building2} title="No organizations listed" description="Organizations registered within this jurisdiction will appear here." />
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {organizations.map((org) => (
                  <div key={org.id} className="p-3.5 flex items-center justify-between text-xs">
                    <div>
                      <p className="font-bold text-slate-900 dark:text-slate-100">{org.legal_name || org.display_name}</p>
                      <p className="text-[11px] text-slate-500">{org.organization_type} • {org.address || 'India'}</p>
                    </div>
                    <Badge variant={org.verification_status === 'APPROVED' ? 'emerald' : 'amber'} size="sm">
                      {org.verification_status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default GovernmentDashboard;
