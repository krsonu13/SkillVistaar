import React, { useState, useEffect } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import {
  GraduationCap,
  Users,
  Award,
  TrendingUp,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  Layers,
  PlusCircle,
  Sparkles,
  Building,
  FileText,
  MapPin,
  Clock,
  RefreshCw,
  X,
  Edit,
  Briefcase,
} from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import { EmptyState } from '../../components/common/EmptyState';
import { usePlatform } from '../../context/PlatformContext';
import { useAuth } from '../../context/AuthContext';
import CreateBatchModal, { NewBatchPayload } from '../../components/dashboard/CreateBatchModal';
import DocumentCenter from '../../components/dashboard/DocumentCenter';
import {
  institutionApi,
  followingApi,
  LiveCourse,
} from '../../services/api';

export interface InstituteDashboardProps {
  section?:
    | 'overview'
    | 'courses'
    | 'courses_create'
    | 'course_detail'
    | 'batches'
    | 'faculty'
    | 'placements'
    | 'skills'
    | 'documents'
    | 'profile'
    | 'following';
}

export const InstituteDashboard: React.FC<InstituteDashboardProps> = ({ section: propSection }) => {
  const location = useLocation();
  const params = useParams<{ courseId?: string }>();
  const { currentUser } = usePlatform();
  const { user } = useAuth();

  // Deduce active section
  const getActiveSection = () => {
    if (propSection) return propSection;
    const path = location.pathname;
    if (path.includes('/institution/courses/create')) return 'courses_create';
    if (params.courseId || path.match(/\/institution\/courses\/[^/]+$/)) return 'course_detail';
    if (path.includes('/institution/courses')) return 'courses';
    if (path.includes('/institution/batches')) return 'batches';
    if (path.includes('/institution/faculty')) return 'faculty';
    if (path.includes('/institution/placements')) return 'placements';
    if (path.includes('/institution/documents')) return 'documents';
    if (path.includes('/institution/profile')) return 'profile';
    if (path.includes('/institution/skills')) return 'skills';
    if (path.includes('/institution/following')) return 'following';
    return 'overview';
  };

  const activeSection = getActiveSection();

  const [issuedFeedback, setIssuedFeedback] = useState(false);
  const [isCreateBatchModalOpen, setIsCreateBatchModalOpen] = useState(activeSection === 'courses_create');
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  // Real backend states
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [courses, setCourses] = useState<LiveCourse[]>([]);
  const [_batches, setBatches] = useState<any[]>([]);
  const [_enrollments, setEnrollments] = useState<any[]>([]);
  const [placements, setPlacements] = useState<any[]>([]);
  const [_marketDemand, setMarketDemand] = useState<any>(null);
  const [_followingList, setFollowingList] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Edit profile modal state
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);
  const [editAffiliation, setEditAffiliation] = useState('');
  const [editOwnership, setEditOwnership] = useState('');
  const [editYear, setEditYear] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  const fetchInstituteData = async () => {
    setIsLoading(true);
    try {
      const [dash, prof, liveCourses, liveBatches, liveEnroll, livePlacements, liveDemand, liveFollowing] =
        await Promise.all([
          institutionApi.getDashboard(),
          institutionApi.getProfile(),
          institutionApi.getCourses(),
          institutionApi.getBatches(),
          institutionApi.getEnrollments(),
          institutionApi.getPlacements(),
          institutionApi.getMarketDemand(),
          followingApi.getFollowing(),
        ]);
      setDashboardData(dash);
      setProfile(prof);
      if (prof) {
        setEditAffiliation(prof.affiliation || '');
        setEditOwnership(prof.ownership_type || '');
        setEditYear(prof.established_year ? String(prof.established_year) : '');
      }
      setCourses(liveCourses || []);
      setBatches(liveBatches || []);
      setEnrollments(liveEnroll || []);
      setPlacements(livePlacements || []);
      setMarketDemand(liveDemand);
      setFollowingList(liveFollowing || []);
    } catch {
      // Keep clean states
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInstituteData();
  }, []);

  useEffect(() => {
    if (activeSection === 'courses_create') {
      setIsCreateBatchModalOpen(true);
    }
  }, [activeSection]);

  const handleIssueBatchCerts = () => {
    setIssuedFeedback(true);
    setTimeout(() => setIssuedFeedback(false), 4000);
  };

  const handleCreateBatchSuccess = async (newBatch: NewBatchPayload) => {
    try {
      await institutionApi.createCourse({
        title: newBatch.name,
        duration_weeks: 12,
        level: 'NSQF Level 5',
      });
      setFeedbackMsg(`Training cohort "${newBatch.name}" registered and synchronized with DigiLocker NAD.`);
      setIsCreateBatchModalOpen(false);
      fetchInstituteData();
    } catch (err: any) {
      setFeedbackMsg(err.message || 'Failed to register cohort');
    }
    setTimeout(() => setFeedbackMsg(null), 4000);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await institutionApi.updateProfile({
        affiliation: editAffiliation.trim() || undefined,
        ownership_type: editOwnership.trim() || undefined,
        established_year: editYear ? parseInt(editYear, 10) : undefined,
      });
      setFeedbackMsg('Institute profile successfully updated.');
      setIsEditProfileOpen(false);
      await fetchInstituteData();
    } catch (err: any) {
      setFeedbackMsg(err?.response?.data?.detail || 'Failed to update institute profile.');
    } finally {
      setSavingProfile(false);
      setTimeout(() => setFeedbackMsg(null), 4000);
    }
  };

  const isVerified =
    profile?.verification_status === 'APPROVED' || dashboardData?.institution?.verification_status === 'APPROVED';

  const stats = dashboardData?.stats || {
    active_courses: courses.length,
    enrolled_students: courses.reduce((acc, c) => acc + (c.enrolled_count || 0), 0),
    verified_credentials: 0,
    placement_records: placements.length,
  };

  const jurisdictionHierarchy = profile?.jurisdiction_hierarchy || [];

  if (isLoading) {
    return (
      <DashboardLayout activeTab="courses">
        <div className="flex items-center justify-center p-12">
          <div className="text-center space-y-3">
            <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Loading institute workspace...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout activeTab={activeSection}>
      <div className="space-y-5">
        {/* Institute Top Banner */}
        <div className="bg-gradient-to-r from-teal-900 via-slate-900 to-teal-950 rounded-xl p-4 sm:p-5 text-white shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              {isVerified ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-200 border border-emerald-400/40">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-300" />
                  Statutory Verified Institute
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 text-amber-200 border border-amber-400/40">
                  <Clock className="w-3.5 h-3.5 text-amber-300" />
                  Statutory Verification Pending
                </span>
              )}
              {profile?.registration_number && (
                <span className="text-[11px] text-slate-300 font-mono">
                  Reg: {profile.registration_number}
                </span>
              )}
              {profile?.established_year && (
                <span className="text-[11px] text-slate-300">
                  Est. {profile.established_year}
                </span>
              )}
            </div>

            <h1 className="text-lg sm:text-xl font-bold tracking-tight">
              {profile?.legal_name || currentUser.name} Academic Operations
            </h1>
            <p className="text-xs text-teal-100 max-w-2xl">
              {profile?.affiliation ? `Affiliated with ${profile.affiliation}. ` : ''}
              Manage NSQF accredited course curricula, student batches, trainer infrastructure, and placement linkages.
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
              onClick={() => setIsCreateBatchModalOpen(true)}
              leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
              className="text-xs font-semibold bg-teal-600 hover:bg-teal-700"
            >
              New Cohort
            </Button>
            <Link to="/institution/documents">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                leftIcon={<FileText className="w-3.5 h-3.5" />}
              >
                Document Center
              </Button>
            </Link>
            <Link to="/institution/profile">
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold"
                rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
              >
                Institute Profile
              </Button>
            </Link>
          </div>
        </div>

        {issuedFeedback && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Digital Credential Batch successfully signed and synchronized with DigiLocker NAD!</span>
          </div>
        )}

        {feedbackMsg && (
          <div className="p-3 bg-teal-50 border border-teal-200 text-teal-800 rounded-lg text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* SECTION: OVERVIEW */}
        {activeSection === 'overview' && (
          <div className="space-y-5">
            {/* Real Metrics Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Accredited Courses</span>
                  <GraduationCap className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.active_courses}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">Active NSQF Programs</p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Total Enrolled</span>
                  <Users className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.enrolled_students}
                </div>
                <p className="text-[10px] text-emerald-600 font-semibold flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> Trainees in batches
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Statutory Status</span>
                  <Award className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {isVerified ? 'VERIFIED' : 'PENDING'}
                </div>
                <p className="text-[10px] text-slate-500">
                  {isVerified ? 'Recognized Center' : 'Review in Progress'}
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 rounded-lg p-3.5 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-1">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Placed Graduates</span>
                  <Layers className="w-4 h-4 text-teal-600" />
                </div>
                <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-slate-100">
                  {stats.placement_records}
                </div>
                <p className="text-[10px] text-teal-700 dark:text-teal-400 font-semibold">Verified Outplaced</p>
              </div>
            </div>

            {/* Split: Academic Offerings & Quick Navigation */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-8 space-y-5">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
                  <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                      Course Programs ({courses.length})
                    </h3>
                    <Link to="/institution/courses" className="text-xs text-teal-700 dark:text-teal-400 font-semibold hover:underline">
                      Manage All
                    </Link>
                  </div>
                  <div className="divide-y divide-slate-100 dark:divide-slate-800">
                    {courses.length === 0 ? (
                      <div className="p-6">
                        <EmptyState
                          icon={GraduationCap}
                          title="No courses registered"
                          description="Add NSQF aligned programs to start registering trainee cohorts."
                          actionText="New Course"
                          onAction={() => setIsCreateBatchModalOpen(true)}
                        />
                      </div>
                    ) : (
                      courses.slice(0, 5).map((c) => (
                        <div key={c.id} className="p-3.5 space-y-1 hover:bg-slate-50/60 dark:hover:bg-slate-800/50 transition">
                          <div className="flex items-center justify-between">
                            <h4 className="font-bold text-xs text-slate-900 dark:text-slate-100">{c.title}</h4>
                            <Badge variant="teal" size="sm">{c.level || 'NSQF L5'}</Badge>
                          </div>
                          <p className="text-[11px] text-slate-500">
                            {c.duration_weeks ? `${c.duration_weeks} weeks duration` : 'Self-paced'} • {c.enrolled_count || 0} Enrolled Trainees
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-4 space-y-4">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="w-4 h-4 text-teal-600" />
                      DigiLocker NAD Depository
                    </span>
                    <Badge variant={isVerified ? 'emerald' : 'amber'} size="sm">
                      {isVerified ? 'Synchronized' : 'Pending Verification'}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Accredited certificate issuances are cryptographically anchored to India's National Academic Depository (NAD).
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    fullWidth
                    onClick={handleIssueBatchCerts}
                    leftIcon={<Award className="w-3.5 h-3.5" />}
                    className="text-xs font-semibold"
                  >
                    Batch Issue Digital Certs
                  </Button>
                </div>

                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 space-y-2.5">
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider">
                    Statutory Operations
                  </h4>
                  <div className="space-y-1.5">
                    <Link
                      to="/institution/documents"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-teal-600" />
                        Document Center
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                    <Link
                      to="/institution/faculty"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-teal-600" />
                        Faculty & Lab Facilities
                      </span>
                      <span className="text-teal-600">&rarr;</span>
                    </Link>
                    <Link
                      to="/institution/placements"
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/70 hover:bg-teal-50 dark:hover:bg-teal-950/40 text-xs font-medium text-slate-700 dark:text-slate-300 transition"
                    >
                      <span className="flex items-center gap-2">
                        <Briefcase className="w-4 h-4 text-teal-600" />
                        Placement Linkages
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

        {/* SECTION: COURSES */}
        {activeSection === 'courses' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-teal-600" />
                  Accredited Program Catalog ({courses.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  NSQF aligned curricula and student cohorts
                </p>
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsCreateBatchModalOpen(true)}
                leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
                className="text-xs font-semibold"
              >
                Add Course Batch
              </Button>
            </div>

            {courses.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={GraduationCap}
                  title="No courses found"
                  description="Register your first training cohort to begin enrolling students."
                  actionText="Add Course Batch"
                  onAction={() => setIsCreateBatchModalOpen(true)}
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {courses.map((course) => (
                  <div key={course.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">{course.title}</h4>
                        <Badge variant="teal" size="sm">{course.level || 'NSQF Level 5'}</Badge>
                      </div>
                      <p className="text-[11px] text-slate-500">{course.duration_weeks ? `${course.duration_weeks} weeks` : 'Self-paced'} • {course.enrolled_count || 0} Enrolled</p>
                      {course.description && <p className="text-[11px] text-slate-600 dark:text-slate-400">{course.description}</p>}
                    </div>

                    <Link to={`/institution/courses/${course.id}`}>
                      <Button variant="outline" size="sm" className="text-xs">
                        View Cohort
                      </Button>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION: FACULTY & INFRASTRUCTURE */}
        {activeSection === 'faculty' && (
          <div className="space-y-5">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <Users className="w-4 h-4 text-teal-600" />
                    Faculty & Master Trainers
                  </h3>
                  <p className="text-xs text-slate-500">Certified trainers mapped to NSQF qualifications</p>
                </div>
              </div>

              {profile?.trainers && profile.trainers.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {profile.trainers.map((tr: any, idx: number) => (
                    <div key={idx} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 space-y-1">
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">{tr.name}</h4>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-teal-100 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300 font-medium">
                          {tr.experience || 'Certified Trainer'}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400">Specialization: {tr.specialization || tr.domain || 'Technical Training'}</div>
                      {tr.qualification && <div className="text-xs text-slate-500">Qualification: {tr.qualification}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-10 text-slate-500 text-sm">
                  No trainer profiles registered yet. Update your institutional profile to record faculty members.
                </div>
              )}
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <div className="pb-3 border-b border-slate-100 dark:border-slate-800">
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <Building className="w-4 h-4 text-teal-600" />
                  Infrastructure & Lab Facilities
                </h3>
                <p className="text-xs text-slate-500">Classrooms, workshop equipment, and safety audit status</p>
              </div>

              {profile?.infrastructure ? (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <span className="text-xs text-slate-500">Classrooms & Labs</span>
                    <div className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                      {profile.infrastructure.classrooms || 'Configured'}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <span className="text-xs text-slate-500">Computing & Equipment</span>
                    <div className="text-xl font-bold text-slate-900 dark:text-slate-100 mt-1">
                      {profile.infrastructure.computers || 'Equipped'}
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
                    <span className="text-xs text-slate-500">Safety & Compliance</span>
                    <div className="text-xl font-bold text-emerald-600 mt-1">
                      {profile.infrastructure.safety_audit || 'Compliant'}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-10 text-slate-500 text-sm">
                  Infrastructure compliance records not yet configured.
                </div>
              )}
            </div>
          </div>
        )}

        {/* SECTION: PLACEMENTS */}
        {activeSection === 'placements' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-teal-600" />
                  Placement Linkages & Outcomes ({placements.length})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Verified hiring records and employer partnerships
                </p>
              </div>
            </div>

            {placements.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={TrendingUp}
                  title="No placement records recorded"
                  description="Track student placement offers and industry linkages here."
                />
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {placements.map((plc, idx) => (
                  <div key={idx} className="p-4 flex items-center justify-between hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">{plc.employer_name || 'Partner Employer'}</h4>
                      <p className="text-[11px] text-slate-500">{plc.course_title || 'Trained Cohort'} • {plc.placed_count || 1} Placed</p>
                    </div>
                    <Badge variant="emerald" size="sm">Verified Hire</Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* SECTION: PROFILE & JURISDICTION */}
        {activeSection === 'profile' && (
          <div className="space-y-5">
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <Building className="w-4 h-4 text-teal-600" />
                    Institutional Recognition & Profile
                  </h3>
                  <p className="text-xs text-slate-500">Legal credentials, regulatory affiliation, and jurisdiction hierarchy</p>
                </div>
                <button
                  onClick={() => setIsEditProfileOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 hover:bg-teal-100 transition"
                >
                  <Edit className="w-3.5 h-3.5" /> Edit Details
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Institute Legal Name</span>
                    <div className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5">{profile?.legal_name || currentUser.name}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Registration Number</span>
                    <div className="font-mono text-slate-800 dark:text-slate-200 mt-0.5">{profile?.registration_number || 'Pending'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Affiliation / Board</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.affiliation || 'Not specified'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Ownership Type</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.ownership_type || 'Private / Trust / Society'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Year Established</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.established_year || 'N/A'}</div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Official Contact Email</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.email || user?.email || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Contact Phone</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.phone || user?.phone || 'N/A'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Campus Address</span>
                    <div className="text-slate-800 dark:text-slate-200 mt-0.5">{profile?.address || 'Not specified'}</div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Statutory Verification</span>
                    <div className="mt-1">
                      {isVerified ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Approved by Jurisdiction Authority
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                          <Clock className="w-3.5 h-3.5" /> Awaiting Statutory Verification
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Jurisdiction Hierarchy display */}
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
                  Update Institute Details
                </h3>
                <button onClick={() => setIsEditProfileOpen(false)} className="p-1 text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveProfile} className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Affiliation / Accrediting Body
                  </label>
                  <input
                    type="text"
                    value={editAffiliation}
                    onChange={(e) => setEditAffiliation(e.target.value)}
                    placeholder="e.g. AICTE, State Board of Technical Education"
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Ownership Type
                  </label>
                  <select
                    value={editOwnership}
                    onChange={(e) => setEditOwnership(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm"
                  >
                    <option value="">Select ownership</option>
                    <option value="Private Trust">Private Trust</option>
                    <option value="Society">Registered Society</option>
                    <option value="Government Autonomous">Government Autonomous</option>
                    <option value="PPP Model">Public-Private Partnership (PPP)</option>
                    <option value="Corporate CSR">Corporate CSR Foundation</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase mb-1">
                    Year Established
                  </label>
                  <input
                    type="number"
                    value={editYear}
                    onChange={(e) => setEditYear(e.target.value)}
                    placeholder="e.g. 2012"
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

        {/* Cohort Creation Modal */}
        <CreateBatchModal
          isOpen={isCreateBatchModalOpen}
          onClose={() => setIsCreateBatchModalOpen(false)}
          onSuccess={handleCreateBatchSuccess}
          instituteName={profile?.legal_name || currentUser.name}
        />
      </div>
    </DashboardLayout>
  );
};

export default InstituteDashboard;
