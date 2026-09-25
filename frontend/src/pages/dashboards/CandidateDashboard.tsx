import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Award,
  Briefcase,
  TrendingUp,
  ShieldCheck,
  ExternalLink,
  Sparkles,
  Target,
  FileCheck2,
  PlusCircle,
  CheckCircle2,
  Upload,
  UserCheck,
  FileText,
  X,
} from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import InputField from '../../components/common/InputField';
import { EmptyState } from '../../components/common/EmptyState';
import { usePlatform } from '../../context/PlatformContext';
import AddSkillModal, { NewSkillPayload } from '../../components/dashboard/AddSkillModal';
import ProfileManagementSection from '../../components/profile/ProfileManagementSection';
import {
  candidateApi,
  followingApi,
  publicApi,
  documentApi,
  CandidateSkillRecord,
  CandidateCredentialRecord,
  LiveJob,
  LiveJobApplication,
  LiveCourse,
} from '../../services/api';

export interface CandidateDashboardProps {
  section?: 'overview' | 'skills' | 'credentials' | 'jobs' | 'applications' | 'assessments' | 'following' | 'resume' | 'profile';
}

export const CandidateDashboard: React.FC<CandidateDashboardProps> = ({ section: propSection }) => {
  const location = useLocation();
  const { currentUser, openApplyModal } = usePlatform();

  // Deduce active section from prop or location.pathname
  const getActiveSection = () => {
    if (propSection) return propSection;
    const path = location.pathname;
    if (path.includes('/candidate/skills')) return 'skills';
    if (path.includes('/candidate/credentials')) return 'credentials';
    if (path.includes('/candidate/jobs')) return 'jobs';
    if (path.includes('/candidate/applications')) return 'applications';
    if (path.includes('/candidate/assessments')) return 'assessments';
    if (path.includes('/candidate/following')) return 'following';
    if (path.includes('/candidate/resume')) return 'resume';
    if (path.includes('/candidate/edit-profile') || path.includes('/candidate/profile-management')) return 'profile';
    return 'overview';
  };

  const activeSection = getActiveSection();

  const [addSkillModalOpen, setAddSkillModalOpen] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Live state
  const [credentials, setCredentials] = useState<CandidateCredentialRecord[]>([]);
  const [skills, setSkills] = useState<CandidateSkillRecord[]>([]);
  const [applications, setApplications] = useState<LiveJobApplication[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<LiveJob[]>([]);
  const [publicJobs, setPublicJobs] = useState<LiveJob[]>([]);
  const [upskillingCourses, setUpskillingCourses] = useState<LiveCourse[]>([]);
  const [assessmentInvitations, setAssessmentInvitations] = useState<any[]>([]);
  const [followingList, setFollowingList] = useState<any[]>([]);

  // Add Credential Modal State
  const [addCredModalOpen, setAddCredModalOpen] = useState(false);
  const [credTitle, setCredTitle] = useState('');
  const [credIssuer, setCredIssuer] = useState('');
  const [credType, setCredType] = useState('DEGREE');
  const [credSubmitting, setCredSubmitting] = useState(false);

  // Fetch live candidate data from PostgreSQL
  const fetchLiveCandidateData = async () => {
    setIsLoading(true);
    try {
      const [liveCreds, liveSkills, liveApps, liveRecJobs, livePubJobs, liveCourses, liveInvites, liveFollowing] =
        await Promise.all([
          candidateApi.getCredentials(),
          candidateApi.getSkills(),
          candidateApi.getApplications(),
          candidateApi.getRecommendedJobs(),
          publicApi.getPublicJobs(20),
          candidateApi.getRecommendedCourses(),
          candidateApi.getAssessmentInvitations(),
          followingApi.getFollowing(),
        ]);

      setCredentials(liveCreds || []);
      setSkills(liveSkills || []);
      setApplications(liveApps || []);
      setRecommendedJobs(liveRecJobs || []);
      setPublicJobs(livePubJobs || []);
      setUpskillingCourses(liveCourses || []);
      setAssessmentInvitations(liveInvites || []);
      setFollowingList(liveFollowing || []);
    } catch {
      setCredentials([]);
      setSkills([]);
      setApplications([]);
      setRecommendedJobs([]);
      setPublicJobs([]);
      setUpskillingCourses([]);
      setAssessmentInvitations([]);
      setFollowingList([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveCandidateData();
  }, []);

  // Add skill to PostgreSQL
  const handleAddSkillSuccess = async (newSkill: NewSkillPayload) => {
    try {
      await candidateApi.addSkill({
        skill_id: newSkill.name,
        proficiency_level: newSkill.nsqfLevel && newSkill.nsqfLevel >= 7 ? 'EXPERT' : newSkill.nsqfLevel && newSkill.nsqfLevel >= 5 ? 'ADVANCED' : 'INTERMEDIATE',
        years_of_experience: 1,
        is_primary: false,
        notes: newSkill.issuer,
      });
      setActionFeedback(`Skill "${newSkill.name}" registered and synchronized.`);
      fetchLiveCandidateData();
    } catch (err: any) {
      setActionFeedback(err.message || `Skill "${newSkill.name}" added locally.`);
    }
    setTimeout(() => setActionFeedback(null), 4000);
  };

  // Add credential to PostgreSQL
  const handleAddCredential = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!credTitle.trim() || !credIssuer.trim()) return;

    setCredSubmitting(true);
    try {
      await candidateApi.addCredential({
        title: credTitle.trim(),
        issuer_name: credIssuer.trim(),
        credential_type: credType,
        issued_date: new Date().toISOString().split('T')[0],
      });
      setActionFeedback(`Credential "${credTitle}" uploaded and submitted for DigiLocker verification.`);
      setAddCredModalOpen(false);
      setCredTitle('');
      setCredIssuer('');
      fetchLiveCandidateData();
    } catch (err: any) {
      setActionFeedback(err.message || 'Failed to upload credential.');
    } finally {
      setCredSubmitting(false);
      setTimeout(() => setActionFeedback(null), 4000);
    }
  };

  // Request verification
  const handleRequestVerification = async (skillId: string, skillName: string) => {
    try {
      await candidateApi.requestSkillVerification(skillId);
      setActionFeedback(`Verification request sent for "${skillName}".`);
      fetchLiveCandidateData();
    } catch (err: any) {
      setActionFeedback(err.message || 'Failed to submit verification request.');
    }
    setTimeout(() => setActionFeedback(null), 4000);
  };

  // Withdraw application
  const handleWithdrawApplication = async (appId: string) => {
    try {
      await candidateApi.withdrawApplication(appId);
      setActionFeedback('Application withdrawn successfully.');
      fetchLiveCandidateData();
    } catch (err: any) {
      setActionFeedback(err.message || 'Failed to withdraw application.');
    }
    setTimeout(() => setActionFeedback(null), 4000);
  };

  // Unfollow
  const handleUnfollow = async (targetId: string) => {
    try {
      await followingApi.unfollow(targetId);
      setActionFeedback('Unfollowed successfully.');
      fetchLiveCandidateData();
    } catch (err: any) {
      setActionFeedback(err.message || 'Failed to unfollow.');
    }
    setTimeout(() => setActionFeedback(null), 4000);
  };

  if (isLoading) {
    return (
      <DashboardLayout activeTab="overview">
        <div className="flex items-center justify-center p-12">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Loading candidate workspace...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout activeTab={activeSection}>
      <div className="space-y-5">
        {/* Top Banner */}
        <div className="bg-gradient-to-r from-teal-800 to-slate-900 rounded-xl p-4 sm:p-5 text-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-teal-500/20 text-teal-200 border border-teal-400/30">
                <ShieldCheck className="w-3 h-3 text-teal-300" />
                DigiLocker Synced
              </span>
              <span className="text-[11px] text-slate-300">
                Candidate ID: <span className="font-mono text-teal-200">{currentUser.id.slice(0, 12)}</span>
              </span>
            </div>
            <h1 className="text-lg sm:text-xl font-bold tracking-tight">
              Welcome back, {currentUser.name}!
            </h1>
            <p className="text-xs text-teal-100 max-w-xl">
              Your profile has {credentials.length} verified credentials and {skills.length} skills recorded in the national registry.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => setAddSkillModalOpen(true)}
              className="bg-teal-500 hover:bg-teal-600 text-white text-xs font-semibold"
              leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
            >
              Add Skill
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAddCredModalOpen(true)}
              className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
              leftIcon={<Upload className="w-3.5 h-3.5" />}
            >
              Upload Credential
            </Button>
            <Link to="/candidate/edit-profile">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                leftIcon={<UserCheck className="w-3.5 h-3.5" />}
              >
                Edit Profile
              </Button>
            </Link>
            <Link to="/candidate/profile">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
              >
                Public View
              </Button>
            </Link>
          </div>
        </div>

        {actionFeedback && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center gap-2 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionFeedback}</span>
          </div>
        )}

        {/* SECTION: PROFILE MANAGEMENT */}
        {activeSection === 'profile' && (
          <ProfileManagementSection onSaved={fetchLiveCandidateData} />
        )}

        {/* SECTION 1: OVERVIEW */}
        {activeSection === 'overview' && (
          <div className="space-y-5">
            {/* 4 Stat Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white rounded-lg p-3.5 border border-slate-200 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Profile Status</span>
                  <Target className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900">
                  {credentials.length > 0 ? 'Verified' : 'Active'}
                </div>
                <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  {credentials.length > 0 ? `${credentials.length} Credentials Verified` : 'Build Skill Passport'}
                </p>
              </div>

              <div className="bg-white rounded-lg p-3.5 border border-slate-200 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Registered Skills</span>
                  <Award className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900">{skills.length} Skills</div>
                <p className="text-[10px] text-teal-700 font-semibold">Indexed on Registry</p>
              </div>

              <div className="bg-white rounded-lg p-3.5 border border-slate-200 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Matched Roles</span>
                  <Briefcase className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900">{recommendedJobs.length} Live</div>
                <p className="text-[10px] text-slate-500">Recommended openings</p>
              </div>

              <div className="bg-white rounded-lg p-3.5 border border-slate-200 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">In Pipeline</span>
                  <FileCheck2 className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900">{applications.length} Applied</div>
                <p className="text-[10px] text-teal-700 font-semibold">Applications active</p>
              </div>
            </div>

            {/* Quick Summary Preview */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-7 space-y-5">
                {/* Applications Preview */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Recent Applications ({applications.length})
                    </h3>
                    <Link to="/candidate/applications" className="text-xs text-teal-700 font-semibold hover:underline">
                      View All
                    </Link>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {applications.length === 0 ? (
                      <div className="p-4">
                        <EmptyState
                          icon={FileCheck2}
                          title="No applications submitted yet"
                          description="Explore verified opportunities to start your applications."
                        />
                      </div>
                    ) : (
                      applications.slice(0, 3).map((app) => (
                        <div key={app.id} className="p-3 flex items-center justify-between text-xs">
                          <div>
                            <p className="font-bold text-slate-900">{app.job_title || 'Position Applied'}</p>
                            <span className="text-[11px] text-slate-500">{app.organization_name || 'Employer'}</span>
                          </div>
                          <Badge variant="teal" size="sm">{app.status}</Badge>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Recommended Jobs Preview */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Recommended Opportunities
                    </h3>
                    <Link to="/candidate/jobs" className="text-xs text-teal-700 font-semibold hover:underline">
                      Explore All
                    </Link>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {recommendedJobs.length === 0 ? (
                      <div className="p-4">
                        <EmptyState
                          icon={Briefcase}
                          title="No recommended jobs right now"
                          description="Add more verified skills to trigger automated job matching."
                        />
                      </div>
                    ) : (
                      recommendedJobs.slice(0, 3).map((job) => (
                        <div key={job.id} className="p-3 flex items-center justify-between text-xs">
                          <div>
                            <p className="font-bold text-slate-900">{job.title}</p>
                            <span className="text-[11px] text-slate-500">{job.organization_name || 'Employer'} • {job.location || 'India'}</span>
                          </div>
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => openApplyModal(job.title, job.organization_name || 'Employer')}
                            className="text-xs font-semibold py-1 px-2.5"
                          >
                            Apply
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Upskilling & Passport */}
              <div className="lg:col-span-5 space-y-5">
                <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-4 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                      Accredited Courses ({upskillingCourses.length})
                    </span>
                    <Badge variant="teal" size="sm">NSQF</Badge>
                  </div>
                  {upskillingCourses.length === 0 ? (
                    <EmptyState
                      icon={Sparkles}
                      title="No course suggestions"
                      description="Accredited modules will appear here as institutes publish catalogs."
                    />
                  ) : (
                    upskillingCourses.slice(0, 3).map((c) => (
                      <div key={c.id} className="p-2.5 rounded bg-slate-50 border border-slate-100 text-xs space-y-1">
                        <p className="font-bold text-slate-900">{c.title}</p>
                        <p className="text-[11px] text-slate-500">{c.institution_name || 'Accredited Center'} • {c.duration_weeks ? `${c.duration_weeks} wks` : 'Self-paced'}</p>
                      </div>
                    ))
                  )}
                </div>

                <div className="bg-gradient-to-br from-teal-50/60 to-white rounded-xl border border-teal-200/80 p-4 space-y-3 shadow-2xs">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded bg-teal-600 text-white flex items-center justify-center">
                      <ShieldCheck className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">Digital Skill Passport</h4>
                      <p className="text-[10px] text-teal-700 font-semibold">DigiLocker Verified</p>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Access your full credentials list and tamper-proof verification proofs.
                  </p>
                  <Link to="/candidate/credentials" className="block">
                    <Button variant="primary" size="sm" fullWidth className="text-xs font-semibold">
                      Manage Credentials
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 2: SKILLS */}
        {activeSection === 'skills' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  Candidate Skill Competencies ({skills.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  NSQF mapped proficiencies and self-declared skills
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setAddSkillModalOpen(true)}
                  leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
                  className="text-xs font-semibold"
                >
                  Add New Skill
                </Button>
              </div>
            </div>

            {skills.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={ShieldCheck}
                  title="No skills registered yet"
                  description="Add skills to build your Skill Passport and unlock automated employer matches."
                  actionText="Add First Skill"
                  onAction={() => setAddSkillModalOpen(true)}
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {skills.map((sk) => (
                  <div key={sk.id} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:border-teal-200 transition space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="font-bold text-xs text-slate-900">{sk.skill_name || sk.skill_id}</span>
                        <p className="text-[11px] text-slate-500 mt-0.5">Proficiency: {sk.proficiency_level || 'INTERMEDIATE'}</p>
                      </div>
                      <Badge variant={sk.status === 'VERIFIED' ? 'emerald' : 'teal'} size="sm">
                        {sk.status || 'DECLARED'}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-200/60 font-mono">
                      <span>Experience: {sk.years_of_experience || 1} yrs</span>
                      {sk.status !== 'VERIFIED' && (
                        <button
                          onClick={() => handleRequestVerification(sk.id, sk.skill_name || sk.skill_id)}
                          className="text-teal-700 hover:underline font-semibold font-sans"
                        >
                          Request Verification
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 3: CREDENTIALS */}
        {activeSection === 'credentials' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <Award className="w-4 h-4 text-teal-600" />
                  Verified Credentials & Certificates ({credentials.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Academic, vocational, and statutory qualifications anchored via DigiLocker / NAD
                </p>
              </div>

              <Button
                variant="primary"
                size="sm"
                onClick={() => setAddCredModalOpen(true)}
                leftIcon={<Upload className="w-3.5 h-3.5" />}
                className="text-xs font-semibold"
              >
                Upload Credential
              </Button>
            </div>

            {credentials.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={Award}
                  title="No credentials uploaded yet"
                  description="Upload your degree, diploma, or NSQF certificate to obtain a verified digital badge."
                  actionText="Upload First Credential"
                  onAction={() => setAddCredModalOpen(true)}
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {credentials.map((c) => (
                  <div key={c.id} className="p-3.5 rounded-lg border border-teal-100 bg-teal-50/20 hover:border-teal-300 transition space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-bold text-xs text-slate-900">{c.title}</h4>
                        <p className="text-[11px] text-slate-500 mt-0.5">{c.issuer_name}</p>
                      </div>
                      <Badge variant={c.status === 'VERIFIED' ? 'emerald' : 'amber'} size="sm">
                        {c.status || 'PENDING'}
                      </Badge>
                    </div>

                    <div className="flex flex-col gap-0.5 text-[10px] text-slate-400 font-mono pt-1 border-t border-teal-100/60">
                      <span>Type: {c.credential_type}</span>
                      {c.verification_hash && <span className="text-teal-700 truncate">Hash: {c.verification_hash}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 4: JOBS */}
        {activeSection === 'jobs' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-teal-600" />
                Explore Verified Job Openings ({publicJobs.length})
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Opportunities posted directly by GSTIN-verified enterprises
              </p>
            </div>

            {publicJobs.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={Briefcase}
                  title="No active job postings"
                  description="When verified employers post vacancies, they will appear here."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {publicJobs.map((job) => (
                  <div key={job.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900 truncate">{job.title}</h4>
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">Verified</span>
                      </div>
                      <p className="text-[11px] text-slate-500">{job.organization_name || 'Enterprise'} • {job.location || 'India'} • {job.employment_type || 'Full-time'}</p>
                      {job.description && <p className="text-[11px] text-slate-600 line-clamp-2">{job.description}</p>}
                    </div>

                    <div className="shrink-0">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => openApplyModal(job.title, job.organization_name || 'Enterprise')}
                        className="text-xs font-semibold"
                      >
                        1-Click Apply
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 5: APPLICATIONS */}
        {activeSection === 'applications' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-teal-600" />
                My Job Applications ({applications.length})
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Real-time tracking of employer evaluation status
              </p>
            </div>

            {applications.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={FileCheck2}
                  title="No applications submitted yet"
                  description="Browse verified vacancies and submit applications to start your career pipeline."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {applications.map((app) => (
                  <div key={app.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition text-xs">
                    <div>
                      <h4 className="font-bold text-slate-900">{app.job_title || 'Position'}</h4>
                      <p className="text-[11px] text-slate-500 mt-0.5">{app.organization_name || 'Employer'} • Applied {app.created_at ? new Date(app.created_at).toLocaleDateString() : 'Recently'}</p>
                    </div>

                    <div className="flex items-center gap-3">
                      <Badge
                        variant={
                          app.status === 'SHORTLISTED' || app.status === 'ACCEPTED'
                            ? 'emerald'
                            : app.status === 'REJECTED'
                            ? 'amber'
                            : 'teal'
                        }
                        size="sm"
                      >
                        {app.status}
                      </Badge>
                      {app.status === 'APPLIED' && (
                        <button
                          onClick={() => handleWithdrawApplication(app.id)}
                          className="text-[11px] text-rose-600 hover:underline font-semibold"
                        >
                          Withdraw
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 6: ASSESSMENTS */}
        {activeSection === 'assessments' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Award className="w-4 h-4 text-teal-600" />
                Assessment Invitations & Skill Tests ({assessmentInvitations.length})
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Proctored pre-employment evaluations sent by verified employers
              </p>
            </div>

            {assessmentInvitations.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={Award}
                  title="No Pending Assessment Invitations"
                  description="When an employer invites you to take a skill evaluation, it will appear here."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {assessmentInvitations.map((inv) => (
                  <div key={inv.id} className="p-4 flex items-center justify-between text-xs">
                    <div>
                      <h4 className="font-bold text-slate-900">{inv.assessment_title || 'Skill Assessment'}</h4>
                      <p className="text-[11px] text-slate-500">{inv.organization_name || 'Enterprise'}</p>
                    </div>
                    <Button variant="primary" size="sm" className="text-xs font-semibold">
                      Start Test
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 7: FOLLOWING */}
        {activeSection === 'following' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-teal-600" />
                Followed Organizations & Institutes ({followingList.length})
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Track updates from preferred employers and accredited academies
              </p>
            </div>

            {followingList.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={UserCheck}
                  title="Not following any entities"
                  description="Follow companies and institutions to receive real-time notices on new job postings and batches."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {followingList.map((f) => (
                  <div key={f.id} className="p-4 flex items-center justify-between text-xs">
                    <div>
                      <h4 className="font-bold text-slate-900">{f.target_name || f.target_id}</h4>
                      <p className="text-[11px] text-slate-500">{f.target_type}</p>
                    </div>
                    <button
                      onClick={() => handleUnfollow(f.id)}
                      className="text-[11px] text-rose-600 hover:underline font-semibold"
                    >
                      Unfollow
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION 8: RESUME & DOCUMENTS */}
        {activeSection === 'resume' && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-teal-600" />
                Resume Vault & Supporting Documents
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Uploaded resumes and proof documents are securely stored and shared with employers only upon application
              </p>
            </div>

            <div className="p-6 border-2 border-dashed border-slate-200 rounded-xl text-center space-y-2">
              <Upload className="w-8 h-8 text-teal-600 mx-auto" />
              <p className="text-xs font-bold text-slate-800">Upload New Resume (PDF / DOCX)</p>
              <p className="text-[11px] text-slate-400">Maximum file size 5MB</p>
              <input
                type="file"
                accept=".pdf,.docx,.doc"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    try {
                      await documentApi.uploadDocument(file, 'RESUME');
                      setActionFeedback('Resume uploaded successfully to secure vault.');
                    } catch (err: any) {
                      setActionFeedback(err.message || 'Failed to upload document.');
                    }
                    setTimeout(() => setActionFeedback(null), 4000);
                  }
                }}
                className="text-xs text-slate-500 file:mr-4 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100 cursor-pointer"
              />
            </div>
          </div>
        )}
      </div>

      {/* Add Skill Modal */}
      <AddSkillModal
        isOpen={addSkillModalOpen}
        onClose={() => setAddSkillModalOpen(false)}
        onSuccess={handleAddSkillSuccess}
      />

      {/* Add Credential Modal */}
      {addCredModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 border border-slate-200">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">Upload Academic / Skill Credential</h3>
              <button onClick={() => setAddCredModalOpen(false)}>
                <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
              </button>
            </div>

            <form onSubmit={handleAddCredential} className="space-y-3">
              <InputField
                label="Credential Title"
                placeholder="e.g. Diploma in Advanced Cloud Engineering"
                value={credTitle}
                onChange={(e) => setCredTitle(e.target.value)}
                required
              />

              <InputField
                label="Issuing Authority"
                placeholder="e.g. National Skill Development Corporation"
                value={credIssuer}
                onChange={(e) => setCredIssuer(e.target.value)}
                required
              />

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Credential Type</label>
                <select
                  value={credType}
                  onChange={(e) => setCredType(e.target.value)}
                  className="w-full text-xs rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800"
                >
                  <option value="DEGREE">Degree / Diploma</option>
                  <option value="CERTIFICATE">Certificate</option>
                  <option value="APPRENTICESHIP">Apprenticeship</option>
                  <option value="LICENSE">Statutory License</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => setAddCredModalOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" isLoading={credSubmitting}>
                  Submit Credential
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

export default CandidateDashboard;
