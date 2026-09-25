import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Clock,
  ShieldCheck,
  ArrowLeft,
  LogOut,
  RefreshCw,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Building2,
  ChevronRight,
  Info,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useRealtime } from '../context/RealtimeContext';
import { userApi, verificationApi } from '../services/api';
import { getDashboardPath } from '../types/auth';
import Button from '../components/common/Button';

interface VerificationDoc {
  id: string;
  document_type: string;
  file_name: string;
  file_url: string;
  status: string;
  uploaded_at?: string;
  verified_at?: string;
}

interface VerificationStatusData {
  verification_status: string;
  application_id?: string | null;
  application_type?: string;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  remarks?: string | null;
  rejection_reason?: string | null;
  can_update_documents?: boolean;
  documents?: VerificationDoc[];
  organization?: {
    id: string;
    legal_name: string;
    display_name: string;
    status: string;
  } | null;
  government_unit?: {
    id: string;
    name: string;
    code: string;
    level: number;
    status: string;
  } | null;
}

export const VerificationPendingPage: React.FC = () => {
  const { user, logout, refreshUser } = useAuth();
  const { subscribe } = useRealtime();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<VerificationStatusData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Resubmission state for MORE_INFORMATION_REQUIRED
  const [resubmitNotes, setResubmitNotes] = useState('');
  const [resubmitDocUrl, setResubmitDocUrl] = useState('');
  const [submittingResubmit, setSubmittingResubmit] = useState(false);
  const [resubmitSuccess, setResubmitSuccess] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setErrorMessage(null);
      const res = await userApi.getVerificationStatus();
      setData(res);

      // If approved, refresh session so auth context knows
      if (res.verification_status === 'APPROVED') {
        await refreshUser();
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to load statutory verification details.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [refreshUser]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Real-time listener for verification status updates
  useEffect(() => {
    const unsub = subscribe('VERIFICATION_STATUS_UPDATED', async (eventData: any) => {
      await fetchStatus();
      if (eventData?.status === 'APPROVED') {
        const fresh = await refreshUser();
        if (fresh) {
          navigate(getDashboardPath(fresh));
        }
      }
    });
    return () => unsub();
  }, [subscribe, fetchStatus, refreshUser, navigate]);

  const handleManualRefresh = () => {
    setRefreshing(true);
    fetchStatus();
  };

  const handleResubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data?.application_id) return;
    setSubmittingResubmit(true);
    setErrorMessage(null);
    setResubmitSuccess(null);
    try {
      await verificationApi.resubmitApplication(data.application_id, {
        notes: resubmitNotes.trim() || undefined,
        additional_document_urls: resubmitDocUrl.trim() ? [resubmitDocUrl.trim()] : [],
      });
      setResubmitSuccess('Additional documentation submitted. Application is now under statutory review.');
      setResubmitNotes('');
      setResubmitDocUrl('');
      await fetchStatus();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || 'Failed to submit additional documentation.');
    } finally {
      setSubmittingResubmit(false);
    }
  };

  const handleProceedToDashboard = () => {
    if (user) {
      navigate(getDashboardPath(user));
    } else {
      navigate('/dashboard');
    }
  };

  const status = data?.verification_status || user?.verification_status || 'PENDING';
  const isApproved = status === 'APPROVED';
  const isRejected = status === 'REJECTED';
  const isMoreInfo = status === 'MORE_INFORMATION_REQUIRED';

  const formatDocType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-teal-500/20 selection:text-teal-300">
      {/* Top Bar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-teal-500 to-emerald-400 flex items-center justify-center text-slate-950 font-black text-sm shadow-md shadow-teal-500/10">
            SV
          </div>
          <div>
            <div className="font-extrabold text-sm tracking-tight text-white flex items-center gap-2">
              <span>SkillVistaar</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-teal-400 border border-slate-700">
                Statutory Registry
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Institutional & Government Verification Gateway</p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700/80 border border-slate-700 text-slate-300 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-teal-400' : ''}`} />
            <span className="hidden sm:inline">Refresh Status</span>
          </button>
          <Button
            variant="outline"
            size="sm"
            onClick={logout}
            className="text-xs py-1.5 px-3 border-slate-700 text-slate-300 hover:bg-slate-800"
            leftIcon={<LogOut className="w-3.5 h-3.5" />}
          >
            Sign Out
          </Button>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:py-10 space-y-6">
        {loading && !data ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <RefreshCw className="w-8 h-8 text-teal-400 animate-spin mb-4" />
            <p className="text-sm font-semibold text-slate-200">Loading statutory verification status...</p>
            <p className="text-xs text-slate-500 mt-1">Connecting to official verification registry</p>
          </div>
        ) : (
          <>
            {errorMessage && (
              <div className="p-3 bg-red-950/40 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-center gap-2">
                <XCircle className="w-4 h-4 shrink-0 text-red-400" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Status Header Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div
                className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 border ${
                  isApproved
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : isRejected
                    ? 'bg-red-500/10 border-red-500/30 text-red-400'
                    : isMoreInfo
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                    : 'bg-teal-500/10 border-teal-500/30 text-teal-400'
                }`}
              >
                {isApproved ? (
                  <CheckCircle2 className="w-8 h-8" />
                ) : isRejected ? (
                  <XCircle className="w-8 h-8" />
                ) : (
                  <Clock className="w-8 h-8 animate-pulse" />
                )}
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                      isApproved
                        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                        : isRejected
                        ? 'bg-red-500/15 text-red-300 border-red-500/30'
                        : isMoreInfo
                        ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                        : 'bg-teal-500/15 text-teal-300 border-teal-500/30'
                    }`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    {status}
                  </span>
                  {user?.username && (
                    <span className="font-mono text-xs text-slate-400 font-medium">@{user.username}</span>
                  )}
                </div>

                <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                  {isApproved
                    ? 'Statutory Verification Approved!'
                    : isRejected
                    ? 'Application Requires Attention or Resubmission'
                    : isMoreInfo
                    ? 'Clarification Requested by Verifier'
                    : 'Statutory Verification in Progress'}
                </h1>

                <p className="text-xs text-slate-400 mt-1 max-w-xl leading-relaxed">
                  {isApproved
                    ? 'Your organization has been officially verified and published to the National SkillVistaar Registry.'
                    : isRejected
                    ? 'Your application was rejected or returned. Please review the reasons and resubmit updated documents.'
                    : isMoreInfo
                    ? 'The reviewing statutory nodal officer has requested additional documentation or clarification before clearing this account.'
                    : 'Your registration credentials and uploaded documentation are currently queued for statutory nodal verification.'}
                </p>
              </div>
            </div>

            {isApproved && (
              <Button
                variant="primary"
                onClick={handleProceedToDashboard}
                className="w-full sm:w-auto shrink-0 bg-emerald-600 hover:bg-emerald-500 py-2.5 px-5 font-bold shadow-lg shadow-emerald-600/20"
                rightIcon={<ChevronRight className="w-4 h-4" />}
              >
                Access Dashboard
              </Button>
            )}
          </div>

          {/* Reviewer Remarks Alert */}
          {(data?.remarks || isMoreInfo) && (
            <div className="mt-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs space-y-1 text-amber-200">
              <div className="flex items-center gap-2 font-bold text-amber-300">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Verifier Remarks / Action Required</span>
              </div>
              <p className="pl-6 text-amber-100/90 leading-relaxed font-sans">
                {data?.remarks || 'Please upload the latest statutory registration or accreditation certificate to proceed.'}
              </p>
            </div>
          )}

          {/* Clarification Submission Form when More Info Required */}
          {isMoreInfo && data?.application_id && (
            <div className="mt-6 p-5 rounded-xl bg-slate-900 border border-amber-500/40 text-xs space-y-3">
              <div className="flex items-center gap-2 font-bold text-amber-300">
                <FileText className="w-4 h-4 text-amber-400" />
                <span>Submit Requested Clarification & Documents</span>
              </div>
              <p className="text-slate-400 text-xs">
                Provide clarifying notes and links to any newly issued certificates or statutory documentation requested by the verifier.
              </p>

              {resubmitSuccess && (
                <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{resubmitSuccess}</span>
                </div>
              )}

              <form onSubmit={handleResubmit} className="space-y-3 pt-1">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                    Clarification Notes / Explanations *
                  </label>
                  <textarea
                    rows={3}
                    value={resubmitNotes}
                    onChange={(e) => setResubmitNotes(e.target.value)}
                    placeholder="Provide details regarding the requested information or clarification..."
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                    Supporting Document Cloud URL / Reference (Optional)
                  </label>
                  <input
                    type="url"
                    value={resubmitDocUrl}
                    onChange={(e) => setResubmitDocUrl(e.target.value)}
                    placeholder="https://drive.google.com/... or cloud document link"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 font-mono"
                  />
                </div>

                <div className="flex justify-end pt-1">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={submittingResubmit}
                    className="bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs"
                    leftIcon={submittingResubmit ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : undefined}
                  >
                    Submit Clarification for Review
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* Rejection Reason Alert */}
          {data?.rejection_reason && (
            <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-xs space-y-1 text-red-200">
              <div className="flex items-center gap-2 font-bold text-red-300">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>Rejection Reason</span>
              </div>
              <p className="pl-6 text-red-100/90 leading-relaxed font-sans">{data.rejection_reason}</p>
            </div>
          )}
        </div>

        {/* Statutory Review Timeline */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Clock className="w-4 h-4 text-teal-400" />
              Statutory Verification Timeline
            </h2>
            <span className="text-[11px] text-slate-400 font-mono">
              Ref: {data?.application_id ? data.application_id.slice(0, 8).toUpperCase() : 'PENDING'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3 rounded-xl bg-slate-950 border border-emerald-500/40 text-xs space-y-1">
              <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>1. Submitted</span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                {data?.submitted_at ? new Date(data.submitted_at).toLocaleDateString() : 'Active'}
              </p>
            </div>

            <div
              className={`p-3 rounded-xl border text-xs space-y-1 ${
                status !== 'PENDING'
                  ? 'bg-slate-950 border-emerald-500/40 text-emerald-300'
                  : 'bg-slate-950 border-teal-500/40 text-teal-300'
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold">
                {status !== 'PENDING' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Clock className="w-3.5 h-3.5 text-teal-400 animate-spin" />
                )}
                <span>2. Assigned</span>
              </div>
              <p className="text-[11px] text-slate-400">Jurisdiction Officer</p>
            </div>

            <div
              className={`p-3 rounded-xl border text-xs space-y-1 ${
                isApproved
                  ? 'bg-slate-950 border-emerald-500/40 text-emerald-300'
                  : isMoreInfo
                  ? 'bg-slate-950 border-amber-500/40 text-amber-300'
                  : 'bg-slate-950 border-slate-800 text-slate-400'
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold">
                {isApproved ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Clock className="w-3.5 h-3.5" />
                )}
                <span>3. Review</span>
              </div>
              <p className="text-[11px] text-slate-400">Document Audit</p>
            </div>

            <div
              className={`p-3 rounded-xl border text-xs space-y-1 ${
                isApproved
                  ? 'bg-slate-950 border-emerald-500/40 text-emerald-300'
                  : 'bg-slate-950 border-slate-800 text-slate-400'
              }`}
            >
              <div className="flex items-center gap-1.5 font-bold">
                {isApproved ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <ShieldCheck className="w-3.5 h-3.5" />
                )}
                <span>4. Clearance</span>
              </div>
              <p className="text-[11px] text-slate-400">Registry Seal</p>
            </div>
          </div>
        </div>

        {/* Entity & Documents Two-Column Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Organization / Government Unit Details */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Building2 className="w-4 h-4 text-teal-400" />
              Registered Entity Information
            </h2>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Legal Entity</span>
                <span className="font-semibold text-slate-200">
                  {data?.organization?.legal_name ||
                    data?.government_unit?.name ||
                    user?.name ||
                    'Registered Organization'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Stakeholder Type</span>
                <span className="font-mono text-teal-400 font-semibold">{user?.account_type || 'INSTITUTION'}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-800">
                <span className="text-slate-400">Jurisdiction / Level</span>
                <span className="font-medium text-slate-200">
                  {data?.government_unit ? `Level ${data.government_unit.level} (${data.government_unit.code})` : 'National Registry'}
                </span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-slate-400">Primary Contact Identifier</span>
                <span className="font-medium text-slate-300 font-mono">
                  {user?.email || user?.phone || 'Confidential'}
                </span>
              </div>
            </div>
          </div>

          {/* Submitted Verification Documents */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-teal-400" />
                Submitted Documents
              </h2>
              <span className="text-[11px] text-slate-400 font-mono">
                {data?.documents?.length || 0} attached
              </span>
            </div>

            {data?.documents && data.documents.length > 0 ? (
              <div className="space-y-2">
                {data.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs hover:border-slate-700 transition"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-4 h-4 text-teal-400 shrink-0" />
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-200 truncate">{doc.file_name}</p>
                        <p className="text-[11px] text-slate-500 font-mono">{formatDocType(doc.document_type)}</p>
                      </div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase shrink-0 border ${
                        doc.status === 'VERIFIED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : doc.status === 'REJECTED'
                          ? 'bg-red-500/10 text-red-400 border-red-500/30'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                      }`}
                    >
                      {doc.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center space-y-1">
                <Info className="w-5 h-5 text-slate-500 mx-auto" />
                <p className="text-xs text-slate-400">No documents uploaded with initial signup.</p>
                <p className="text-[11px] text-slate-500">
                  Initial verification was initialized from statutory master records.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800 text-xs">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-slate-400 hover:text-white transition font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to SkillVistaar Home</span>
          </Link>

          <div className="flex items-center gap-3">
            {isApproved ? (
              <Button
                variant="primary"
                onClick={handleProceedToDashboard}
                className="bg-emerald-600 hover:bg-emerald-500 px-6 font-bold"
                rightIcon={<ChevronRight className="w-4 h-4" />}
              >
                Go to Dashboard
              </Button>
            ) : (
              <Button
                variant="outline"
                onClick={handleManualRefresh}
                disabled={refreshing}
                className="border-slate-700 text-slate-300 hover:bg-slate-800 text-xs"
                leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />}
              >
                Check Verification Again
              </Button>
            )}
          </div>
        </div>
        </>
        )}
      </main>
    </div>
  );
};

export default VerificationPendingPage;
