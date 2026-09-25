import React, { useState, useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import {
  Briefcase,
  Users,
  ShieldCheck,
  PlusCircle,
  ExternalLink,
  TrendingUp,
  Clock,
  CheckCircle2,
  Award,
  Building,
  FileText,
  MapPin,
  Play,
  Pause,
  XCircle,
  Archive,
  Send,
  Edit,
  RefreshCw,
  X,
  Check,
} from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import { EmptyState } from '../../components/common/EmptyState';
import { usePlatform } from '../../context/PlatformContext';
import { useAuth } from '../../context/AuthContext';
import PostJobModal, { NewJobPayload } from '../../components/dashboard/PostJobModal';
import DocumentCenter from '../../components/dashboard/DocumentCenter';
import {
  employerApi,
  followingApi,
  LiveJob,
  LiveJobApplication,
} from '../../services/api';

export interface EmployerDashboardProps {
  section?:
    | 'overview'
    | 'jobs'
    | 'jobs_create'
    | 'job_detail'
    | 'applications'
    | 'assessments'
    | 'assessments_create'
    | 'documents'
    | 'profile'
    | 'following';
}

export const EmployerDashboard: React.FC<EmployerDashboardProps> = ({ section: propSection }) => {
  const location = useLocation();
  const params = useParams<{ jobId?: string }>();
  const { currentUser } = usePlatform();
  const { user } = useAuth();

  // Deduce active section
  const getActiveSection = () => {
    if (propSection) return propSection;
    const path = location.pathname;
    if (path.includes('/employer/jobs/create')) return 'jobs_create';
    if (params.jobId || path.match(/\/employer\/jobs\/[^/]+$/)) return 'job_detail';
    if (path.includes('/employer/jobs')) return 'jobs';
    if (path.includes('/employer/applications')) return 'applications';
    if (path.includes('/employer/assessments/create')) return 'assessments_create';
    if (path.includes('/employer/assessments')) return 'assessments';
    if (path.includes('/employer/documents')) return 'documents';
    if (path.includes('/employer/profile')) return 'profile';
    if (path.includes('/employer/following')) return 'following';
    return 'overview';
  };

  const activeSection = getActiveSection();

  const [isPostJobModalOpen, setIsPostJobModalOpen] = useState(activeSection === 'jobs_create');
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);
  const [applicantFilter, setApplicantFilter] = useState<'ALL' | 'NEW' | 'INTERVIEW' | 'SELECTED'>('ALL');
  const [isLoading, setIsLoading] = useState(true);

  // Real backend states
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [jobs, setJobs] = useState<LiveJob[]>([]);
  const [applicants, setApplicants] = useState<LiveJobApplication[]>([]);
  const [_assessments, setAssessments] = useState<any[]>([]);
  const [_followingList, setFollowingList] = useState<any[]>([]);


  // Profile Edit modal
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);
  const [editSector, setEditSector] = useState('');
  const [editCompanySize, setEditCompanySize] = useState('');
  const [editAddress, setEditAddress] = useState('');
  const [editWebsite, setEditWebsite] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  // Action busy states for jobs
  const [jobActionLoading, setJobActionLoading] = useState<string | null>(null);

  const fetchEmployerData = async () => {
    setIsLoading(true);
    try {
      const [dash, prof, liveJobs, liveApps, liveAssess, liveFollowing] = await Promise.all([
        employerApi.getDashboard(),
        employerApi.getProfile(),
        employerApi.getJobs(),
        employerApi.getApplications(),
        employerApi.getAssessments(),
        followingApi.getFollowing(),
      ]);
      setDashboardData(dash);
      setProfile(prof);
      if (prof) {
        setEditSector(prof.sector || '');
        setEditCompanySize(prof.company_size || '');
        setEditAddress(prof.address || '');
        setEditWebsite(prof.website || '');
      }
      setJobs(liveJobs || []);
      setApplicants(liveApps || []);
      setAssessments(liveAssess || []);
      setFollowingList(liveFollowing || []);
    } catch {
      // Clean empty states
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployerData();
  }, []);

  useEffect(() => {
    if (activeSection === 'jobs_create') {
      setIsPostJobModalOpen(true);
    }
  }, [activeSection]);

  const handlePostJobSuccess = async (newJob: NewJobPayload) => {
    try {
      const salaryNums = newJob.salary.match(/\d+(\.\d+)?/g);
      const minSal = salaryNums && salaryNums[0] ? parseFloat(salaryNums[0]) * 100000 : 500000;
      const maxSal = salaryNums && salaryNums[1] ? parseFloat(salaryNums[1]) * 100000 : minSal + 300000;

      await employerApi.postJob({
        title: newJob.title,
        description: newJob.description || 'Enterprise role in skill operations.',
        employment_type: newJob.type === 'Apprenticeship' ? 'APPRENTICESHIP' : 'FULL_TIME',
        location: newJob.location,
        salary_min: minSal,
        salary_max: maxSal,
        openings: 5,
        skill_ids: [],
      });

      setFeedbackMsg(`Position "${newJob.title}" created successfully.`);
      setIsPostJobModalOpen(false);
      await fetchEmployerData();
    } catch (err: any) {
      setFeedbackMsg(err?.response?.data?.detail || 'Failed to post vacancy.');
    }
    setTimeout(() => setFeedbackMsg(null), 4000);
  };

  // Job 6-state lifecycle actions
  const handleJobAction = async (jobId: string, action: 'submit_review' | 'publish' | 'pause' | 'resume' | 'close' | 'archive') => {
    setJobActionLoading(jobId);
    try {
      if (action === 'submit_review') {
        await employerApi.submitJobReview(jobId);
        setFeedbackMsg('Job submitted for compliance review.');
      } else if (action === 'publish') {
        await employerApi.publishJob(jobId);
        setFeedbackMsg('Job published and visible to candidates.');
      } else if (action === 'pause') {
        await employerApi.pauseJob(jobId);
        setFeedbackMsg('Job paused.');
      } else if (action === 'resume') {
        await employerApi.resumeJob(jobId);
        setFeedbackMsg('Job resumed.');
      } else if (action === 'close') {
        await employerApi.closeJob(jobId);
        setFeedbackMsg('Job closed to new applications.');
      } else if (action === 'archive') {
        await employerApi.archiveJob(jobId);
        setFeedbackMsg('Job archived.');
      }
      await fetchEmployerData();
    } catch (err: any) {
      setFeedbackMsg(err?.response?.data?.detail || `Failed to ${action} job.`);
    } finally {
      setJobActionLoading(null);
      setTimeout(() => setFeedbackMsg(null), 4000);
    }
  };

  const handleUpdateApplicantStatus = async (appId: string, newStatus: string) => {
    try {
      await employerApi.updateApplicationStatus(appId, newStatus);
      setFeedbackMsg(`Applicant status updated to ${newStatus}.`);
      await fetchEmployerData();
    } catch (err: any) {
      setFeedbackMsg(err?.response?.data?.detail || 'Failed to update applicant status.');
    }
    setTimeout(() => setFeedbackMsg(null), 4000);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await employerApi.updateProfile({
        sector: editSector.trim() || undefined,
        company_size: editCompanySize.trim() || undefined,
        address: editAddress.trim() || undefined,
        website: editWebsite.trim() || undefined,
      });
      setFeedbackMsg('Employer profile updated successfully.');
      setIsEditProfileOpen(false);
      await fetchEmployerData();
    } catch (err: any) {
      setFeedbackMsg(err?.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setSavingProfile(false);
      setTimeout(() => setFeedbackMsg(null), 4000);
    }
  };


  const isVerified =
    profile?.verification_status === 'APPROVED' || dashboardData?.organization?.verification_status === 'APPROVED';

  const stats = dashboardData?.stats || {
    active_postings: jobs.filter((j) => j.status === 'PUBLISHED').length,
    total_applicants: applicants.length,
    interviews_scheduled: applicants.filter((a) => a.status === 'INTERVIEW').length,
    verified_hires: applicants.filter((a) => a.status === 'SELECTED').length,
  };

  const jurisdictionHierarchy = profile?.jurisdiction_hierarchy || [];

  const filteredApplicants = applicants.filter((app) => {
    if (applicantFilter === 'ALL') return true;
    if (applicantFilter === 'NEW') return app.status === 'APPLIED' || app.status === 'NEW';
    if (applicantFilter === 'INTERVIEW') return app.status === 'INTERVIEW' || app.status === 'ASSESSMENT';
    if (applicantFilter === 'SELECTED') return app.status === 'SELECTED';
    return true;
  });

  const selectedJob = params.jobId ? jobs.find((j) => j.id === params.jobId) : null;

  if (isLoading) {
    return (
      <DashboardLayout activeTab="jobs">
        <div className="flex items-center justify-center p-12">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Loading employer workspace...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout activeTab={activeSection}>
      <div className="space-y-5">
        {/* Employer Top Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-teal-950 rounded-xl p-4 sm:p-5 text-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              {isVerified ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-200 border border-emerald-400/40">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
                  GSTIN Verified Enterprise
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 text-amber-200 border border-amber-400/40">
                  <Clock className="w-3.5 h-3.5 text-amber-300" />
                  Statutory Verification Pending
                </span>
              )}
              {profile?.registration_number && (
                <span className="text-[11px] text-slate-300 font-mono">
                  CIN/PAN: {profile.registration_number}
                </span>
              )}
              {profile?.sector && (
                <span className="text-[11px] text-teal-300 font-medium">
                  {profile.sector}
                </span>
              )}
            </div>

            <h1 className="text-lg sm:text-xl font-bold tracking-tight">
              {profile?.legal_name || currentUser.name} Talent Operations
            </h1>
            <p className="text-xs text-slate-300 max-w-2xl">
              {profile?.company_size ? `${profile.company_size} Enterprise. ` : ''}
              Create job postings through compliance lifecycle, screen candidate credentials, and maintain statutory verification.
            </p>

            {/* Jurisdiction breadcrumbs */}
            {jurisdictionHierarchy.length > 0 && (
              <div className="flex items-center gap-1.5 text-[11px] text-teal-200/80 pt-1">
                <MapPin className="w-3.5 h-3.5 text-teal-300" />
                <span>Jurisdiction:</span>
                {jurisdictionHierarchy.map((u: any, idx: number) => (
                  <span key={u.id} className="flex items-center gap-1">
                    {idx > 0 && <span className="text-teal-400/50">&rsaquo;</span>}
                    <span className="font-medium text-white">{u.name}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsPostJobModalOpen(true)}
              leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
              className="text-xs font-semibold bg-teal-600 hover:bg-teal-700"
            >
              Post Opening
            </Button>
            <Link to="/employer/documents">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                leftIcon={<FileText className="w-3.5 h-3.5" />}
              >
                Document Center
              </Button>
            </Link>
            <Link to="/employer/profile">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
              >
                Company Profile
              </Button>
            </Link>
          </div>
        </div>

        {feedbackMsg && (
          <div className="p-3 bg-teal-50 border border-teal-200 text-teal-800 rounded-lg text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* SECTION: OVERVIEW */}
        {activeSection === 'overview' && (
          <div className="space-y-5">
            {/* Real Stats Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Active Postings</span>
                  <Briefcase className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.active_postings}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">Published Positions</p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Total Applicants</span>
                  <Users className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.total_applicants}
                </div>
                <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> Candidate pipeline
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Interviewing</span>
                  <Clock className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.interviews_scheduled}
                </div>
                <p className="text-[10px] text-slate-500">Scheduled / Assessment</p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Verified Hires</span>
                  <Award className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.verified_hires}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">Offer Accepted</p>
              </div>
            </div>

            {/* Split: Live Jobs & Quick Actions */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-8 space-y-5">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                      Recent Vacancies ({jobs.length})
                    </h3>
                    <Link to="/employer/jobs" className="text-xs text-teal-700 dark:text-teal-400 font-semibold hover:underline">
                      Manage All
                    </Link>
                  </div>
                  <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    {jobs.length === 0 ? (
                      <div className="p-6">
                        <EmptyState
                          icon={Briefcase}
                          title="No job postings yet"
                          description="Create your first vacancy to start receiving verified candidates."
                          actionText="Post Opening"
                          onAction={() => setIsPostJobModalOpen(true)}
                        />
                      </div>
                    ) : (
                      jobs.slice(0, 5).map((j) => (
                        <div key={j.id} className="p-3.5 space-y-1.5 hover:bg-slate-50/60 dark:hover:bg-slate-800/50 transition">
                          <div className="flex items-center justify-between">
                            <h4 className="font-bold text-xs text-slate-900 dark:text-slate-100">{j.title}</h4>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              j.status === 'PUBLISHED' ? 'bg-emerald-100 text-emerald-800' :
                              j.status === 'PAUSED' ? 'bg-amber-100 text-amber-800' :
                              j.status === 'CLOSED' ? 'bg-slate-200 text-slate-700' :
                              'bg-blue-100 text-blue-800'
                            }`}>
                              {j.status}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500">
                            {j.employment_type || 'Full-Time'} • {j.location || 'India'} • {j.applicant_count || 0} Applicants
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-4 space-y-4">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-2.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                    Enterprise Quick Links
                  </h4>
                  <div className="space-y-1.5">
                    <Link
                      to="/employer/documents"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-teal-600" />
                        Document Center
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                    <Link
                      to="/employer/applications"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-teal-600" />
                        Candidate Pipeline
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                    <Link
                      to="/employer/profile"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <Building className="w-4 h-4 text-teal-600" />
                        Company Profile & Units
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SECTION: DOCUMENT CENTER */}
        {activeSection === 'documents' && (
          <DocumentCenter
            organizationId={profile?.organization_id}
            organizationName={profile?.legal_name}
            isVerifiedOrg={isVerified}
          />
        )}

        {/* SECTION: JOBS LIST WITH 6-STATE LIFECYCLE CONTROLS */}
        {activeSection === 'jobs' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-teal-600" />
                  Job Vacancies & Lifecycle Management ({jobs.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Full 6-state lifecycle: DRAFT &rarr; REVIEW &rarr; PUBLISHED &rarr; PAUSED &rarr; CLOSED &rarr; ARCHIVED
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsPostJobModalOpen(true)}
                leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
                className="text-xs font-semibold"
              >
                Post New Opening
              </Button>
            </div>

            {jobs.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={Briefcase}
                  title="No openings listed"
                  description="Your organization currently has no job postings. Click below to post a new job."
                  actionText="Post New Opening"
                  onAction={() => setIsPostJobModalOpen(true)}
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {jobs.map((job) => (
                  <div key={job.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <div className="space-y-1 max-w-xl">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">{job.title}</h4>
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          job.status === 'PUBLISHED' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' :
                          job.status === 'PAUSED' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300' :
                          job.status === 'CLOSED' ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300' :
                          job.status === 'ARCHIVED' ? 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-400' :
                          'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                        }`}>
                          {job.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">
                        {job.employment_type || 'Full-time'} • {job.location || 'India'} • {job.applicant_count || 0} Applicants
                      </p>
                      {job.description && (
                        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{job.description}</p>
                      )}
                    </div>

                    {/* Lifecycle Action Buttons */}
                    <div className="flex flex-wrap items-center gap-2 shrink-0">
                      {job.status === 'DRAFT' && (
                        <button
                          onClick={() => handleJobAction(job.id, 'submit_review')}
                          disabled={jobActionLoading === job.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                        >
                          <Send className="w-3.5 h-3.5" /> Submit Review
                        </button>
                      )}

                      {(job.status === 'SUBMITTED' || job.status === 'UNDER_REVIEW' || job.status === 'DRAFT') && (
                        <button
                          onClick={() => handleJobAction(job.id, 'publish')}
                          disabled={jobActionLoading === job.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white shadow-xs"
                        >
                          <Play className="w-3.5 h-3.5" /> Publish
                        </button>
                      )}

                      {job.status === 'PUBLISHED' && (
                        <>
                          <button
                            onClick={() => handleJobAction(job.id, 'pause')}
                            disabled={jobActionLoading === job.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white shadow-xs"
                          >
                            <Pause className="w-3.5 h-3.5" /> Pause
                          </button>
                          <button
                            onClick={() => handleJobAction(job.id, 'close')}
                            disabled={jobActionLoading === job.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-xs"
                          >
                            <XCircle className="w-3.5 h-3.5" /> Close
                          </button>
                        </>
                      )}

                      {job.status === 'PAUSED' && (
                        <>
                          <button
                            onClick={() => handleJobAction(job.id, 'resume')}
                            disabled={jobActionLoading === job.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white shadow-xs"
                          >
                            <Play className="w-3.5 h-3.5" /> Resume
                          </button>
                          <button
                            onClick={() => handleJobAction(job.id, 'close')}
                            disabled={jobActionLoading === job.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-xs"
                          >
                            <XCircle className="w-3.5 h-3.5" /> Close
                          </button>
                        </>
                      )}

                      {job.status === 'CLOSED' && (
                        <button
                          onClick={() => handleJobAction(job.id, 'archive')}
                          disabled={jobActionLoading === job.id}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-semibold bg-slate-600 hover:bg-slate-700 text-white shadow-xs"
                        >
                          <Archive className="w-3.5 h-3.5" /> Archive
                        </button>
                      )}

                      <Link to={`/employer/jobs/${job.id}`}>
                        <Button variant="outline" size="sm" className="text-xs">
                          Details
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION: JOB DETAIL */}
        {activeSection === 'job_detail' && (
          <div className="space-y-5">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
                <div>
                  <Link to="/employer/jobs" className="text-xs text-teal-600 hover:underline flex items-center gap-1 mb-1 font-medium">
                    &larr; Back to all vacancies
                  </Link>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100">
                      {selectedJob?.title || 'Job Opening Details'}
                    </h3>
                    {selectedJob && (
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        selectedJob.status === 'PUBLISHED' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' :
                        selectedJob.status === 'DRAFT' ? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300' :
                        selectedJob.status === 'SUBMIT_FOR_REVIEW' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300' :
                        selectedJob.status === 'PAUSED' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/60 dark:text-yellow-300' :
                        'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                      }`}>
                        {selectedJob.status}
                      </span>
                    )}
                  </div>
                </div>

                {selectedJob && (
                  <div className="flex flex-wrap items-center gap-2">
                    {selectedJob.status === 'DRAFT' && (
                      <button
                        onClick={() => handleJobAction(selectedJob.id, 'submit_review')}
                        disabled={jobActionLoading === selectedJob.id}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white shadow-xs"
                      >
                        <Send className="w-3.5 h-3.5" /> Submit for Review
                      </button>
                    )}
                    {selectedJob.status === 'SUBMIT_FOR_REVIEW' && (
                      <button
                        onClick={() => handleJobAction(selectedJob.id, 'publish')}
                        disabled={jobActionLoading === selectedJob.id}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Publish Vacancy
                      </button>
                    )}
                    {selectedJob.status === 'PUBLISHED' && (
                      <>
                        <button
                          onClick={() => handleJobAction(selectedJob.id, 'pause')}
                          disabled={jobActionLoading === selectedJob.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-yellow-600 hover:bg-yellow-700 text-white shadow-xs"
                        >
                          <Pause className="w-3.5 h-3.5" /> Pause
                        </button>
                        <button
                          onClick={() => handleJobAction(selectedJob.id, 'close')}
                          disabled={jobActionLoading === selectedJob.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-xs"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Close
                        </button>
                      </>
                    )}
                    {selectedJob.status === 'PAUSED' && (
                      <>
                        <button
                          onClick={() => handleJobAction(selectedJob.id, 'resume')}
                          disabled={jobActionLoading === selectedJob.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white shadow-xs"
                        >
                          <Play className="w-3.5 h-3.5" /> Resume
                        </button>
                        <button
                          onClick={() => handleJobAction(selectedJob.id, 'close')}
                          disabled={jobActionLoading === selectedJob.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-xs"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Close
                        </button>
                      </>
                    )}
                    {selectedJob.status === 'CLOSED' && (
                      <button
                        onClick={() => handleJobAction(selectedJob.id, 'archive')}
                        disabled={jobActionLoading === selectedJob.id}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold bg-slate-600 hover:bg-slate-700 text-white shadow-xs"
                      >
                        <Archive className="w-3.5 h-3.5" /> Archive
                      </button>
                    )}
                  </div>
                )}
              </div>

              {!selectedJob ? (
                <div className="p-8">
                  <EmptyState
                    icon={Briefcase}
                    title="Job opening not found"
                    description="The requested position could not be found or has been archived."
                    actionText="View All Vacancies"
                    onAction={() => window.location.assign('/employer/jobs')}
                  />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Job metadata grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Department</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{selectedJob.department || 'General'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Location</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{selectedJob.location || 'Remote'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Job Type</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{selectedJob.type}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Experience Level</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{selectedJob.experience_level || '1-3 years'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Openings</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{selectedJob.openings_count || 1} positions</span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Salary Range</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {selectedJob.salary_min && selectedJob.salary_max
                          ? `₹${selectedJob.salary_min.toLocaleString()} - ₹${selectedJob.salary_max.toLocaleString()}`
                          : 'Competitive'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Posted On</span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{new Date(selectedJob.created_at).toLocaleDateString()}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 font-semibold uppercase block text-[10px]">Total Applicants</span>
                      <span className="font-medium text-teal-600 font-bold">{selectedJob.applicant_count || 0} candidates</span>
                    </div>
                  </div>

                  {/* Required Skills */}
                  {selectedJob.required_skills && selectedJob.required_skills.length > 0 && (
                    <div className="space-y-1.5">
                      <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Required Skills</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedJob.required_skills.map((skill, idx) => (
                          <span key={idx} className="px-2.5 py-1 rounded-md bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 text-xs font-semibold border border-teal-200 dark:border-teal-800">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {selectedJob.description && (
                    <div className="space-y-1.5">
                      <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Job Description</h4>
                      <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                        {selectedJob.description}
                      </div>
                    </div>
                  )}

                  {/* Applicants for this vacancy */}
                  <div className="space-y-3 pt-4 border-t border-slate-100 dark:border-slate-800">
                    <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                      <Users className="w-4 h-4 text-teal-600" />
                      Applications for this Position ({applicants.filter((a) => a.job_id === selectedJob.id || a.job_title === selectedJob.title).length})
                    </h4>
                    {applicants.filter((a) => a.job_id === selectedJob.id || a.job_title === selectedJob.title).length === 0 ? (
                      <p className="text-xs text-slate-400 py-3">No candidates have applied to this opening yet.</p>
                    ) : (
                      <div className="divide-y divide-slate-100 dark:divide-slate-800">
                        {applicants
                          .filter((a) => a.job_id === selectedJob.id || a.job_title === selectedJob.title)
                          .map((app) => (
                            <div key={app.id} className="py-3 flex items-center justify-between">
                              <div>
                                <span className="font-semibold text-xs text-slate-900 dark:text-slate-100">{app.candidate_name || 'Candidate'}</span>
                                <span className="ml-2 text-[10px] text-slate-400 font-mono">Match: {app.match_score ? `${app.match_score}%` : '85%'}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant={app.status === 'SELECTED' ? 'emerald' : 'teal'} size="sm">
                                  {app.status}
                                </Badge>
                                {app.status !== 'SELECTED' && (
                                  <button
                                    onClick={() => handleUpdateApplicantStatus(app.id, 'SELECTED')}
                                    className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                                  >
                                    Hire
                                  </button>
                                )}
                              </div>
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

        {/* SECTION: CANDIDATE APPLICATION PIPELINE */}
        {activeSection === 'applications' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <Users className="w-4 h-4 text-teal-600" />
                  Candidate Pipeline ({applicants.length})
                </h3>
                <p className="text-[11px] text-slate-500">Screen, schedule interviews, and record verified hires</p>
              </div>

              {/* Status filter */}
              <div className="flex gap-2">
                {(['ALL', 'NEW', 'INTERVIEW', 'SELECTED'] as const).map((filterVal) => (
                  <button
                    key={filterVal}
                    onClick={() => setApplicantFilter(filterVal)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                      applicantFilter === filterVal
                        ? 'bg-teal-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
                    }`}
                  >
                    {filterVal}
                  </button>
                ))}
              </div>
            </div>

            {filteredApplicants.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={Users}
                  title="No applicants found"
                  description="Candidates who apply to your active vacancies will appear here."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredApplicants.map((app) => (
                  <div key={app.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">{app.candidate_name || 'Applicant'}</h4>
                        <Badge variant={app.status === 'SELECTED' ? 'emerald' : 'teal'} size="sm">
                          {app.status}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Job: {app.job_title || 'Position'} • Match Score: {app.match_score ? `${app.match_score}%` : '85%'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {app.status !== 'INTERVIEW' && app.status !== 'SELECTED' && (
                        <button
                          onClick={() => handleUpdateApplicantStatus(app.id, 'INTERVIEW')}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-950/60 dark:text-blue-300"
                        >
                          Schedule Interview
                        </button>
                      )}
                      {app.status !== 'SELECTED' && (
                        <button
                          onClick={() => handleUpdateApplicantStatus(app.id, 'SELECTED')}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:text-emerald-300 flex items-center gap-1"
                        >
                          <Check className="w-3 h-3" /> Select / Hire
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION: COMPANY PROFILE & JURISDICTION */}
        {activeSection === 'profile' && (
          <div className="space-y-5">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <Building className="w-4 h-4 text-teal-600" />
                    Enterprise Operational Profile
                  </h3>
                  <p className="text-xs text-slate-500">Corporate identity, company size, sector, and registered jurisdiction</p>
                </div>
                <button
                  onClick={() => setIsEditProfileOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 hover:bg-teal-100 transition"
                >
                  <Edit className="w-3.5 h-3.5" /> Edit Profile
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Legal Company Name</span>
                    <div className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5">{profile?.legal_name || currentUser.name}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">CIN / Registration No.</span>
                    <div className="font-mono text-slate-800 dark:text-slate-200 mt-0.5">{profile?.registration_number || 'Pending'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Industry Sector</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.sector || 'Information Technology & Engineering'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Company Size</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.company_size || 'Mid-Market (250-1000 employees)'}</div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Official Email</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.email || user?.email || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Contact Phone</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.phone || user?.phone || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Registered Office Address</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.address || 'Not specified'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Statutory Verification Status</span>
                    <div className="mt-1">
                      {isVerified ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Approved by Government Jurisdiction
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                          <Clock className="w-3.5 h-3.5" /> Statutory Verification Pending
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Jurisdiction Hierarchy */}
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold block mb-2">
                  Jurisdiction Hierarchy (Country &rarr; State &rarr; District &rarr; Local Area)
                </span>
                {jurisdictionHierarchy.length > 0 ? (
                  <div className="flex flex-wrap items-center gap-2 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
                    {jurisdictionHierarchy.map((u: any, idx: number) => (
                      <div key={u.id} className="flex items-center gap-2">
                        {idx > 0 && <span className="text-slate-400 font-bold">&rarr;</span>}
                        <div className="px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 font-medium">
                          <span className="text-[10px] uppercase tracking-wider text-slate-500 block">{u.unit_type}</span>
                          <span className="text-slate-900 dark:text-slate-100 font-semibold">{u.name}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">Unassigned jurisdiction. Register unit with state nodal authority.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Edit Profile Modal */}
        {isEditProfileOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-xl">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Update Organization Details
                </h3>
                <button onClick={() => setIsEditProfileOpen(false)} className="p-1 text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveProfile} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Industry Sector
                  </label>
                  <input
                    type="text"
                    value={editSector}
                    onChange={(e) => setEditSector(e.target.value)}
                    placeholder="e.g. IT & Software, Manufacturing, Automotive"
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Company Size
                  </label>
                  <select
                    value={editCompanySize}
                    onChange={(e) => setEditCompanySize(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
                  >
                    <option value="">Select company size</option>
                    <option value="1-50 employees">Startup (1-50 employees)</option>
                    <option value="50-250 employees">Small & Medium (50-250 employees)</option>
                    <option value="250-1000 employees">Mid-Market (250-1000 employees)</option>
                    <option value="1000+ employees">Large Enterprise (1000+ employees)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Registered Office Address
                  </label>
                  <input
                    type="text"
                    value={editAddress}
                    onChange={(e) => setEditAddress(e.target.value)}
                    placeholder="e.g. Pune Tech Park, Hinjawadi Phase 2"
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Corporate Website
                  </label>
                  <input
                    type="url"
                    value={editWebsite}
                    onChange={(e) => setEditWebsite(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setIsEditProfileOpen(false)}
                    className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingProfile}
                    className="px-4 py-2 text-sm font-semibold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-sm flex items-center gap-2"
                  >
                    {savingProfile && <RefreshCw className="w-4 h-4 animate-spin" />}
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Post Job Modal */}
        <PostJobModal
          isOpen={isPostJobModalOpen}
          onClose={() => setIsPostJobModalOpen(false)}
          onSuccess={handlePostJobSuccess}
          companyName={profile?.legal_name || currentUser.name}
        />
      </div>
    </DashboardLayout>
  );
};

export default EmployerDashboard;
