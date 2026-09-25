import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation, Link, useSearchParams, useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  Award,
  MapPin,
  Globe,
  Calendar,
  Check,
  Plus,
  MessageSquare,
  Share2,
  Briefcase,
  GraduationCap,
  Landmark,
  Shield,
  Heart,
  MessageCircle,
  ExternalLink,
  ChevronRight,
  Lock,
  ArrowLeft,
  Camera,
  MoreVertical,
  Copy,
  Edit3,
  Mail,
  Loader2,
  TrendingUp,
} from 'lucide-react';
import Navbar from '../../components/common/Navbar';
import Footer from '../../components/common/Footer';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import FollowListModal from '../../components/profile/FollowListModal';
import DirectMessagingModal from '../../components/messaging/DirectMessagingModal';
import ProfileManagementModal from '../../components/profile/ProfileManagementModal';
import JobApplyModal from '../../components/profile/JobApplyModal';
import { EmptyState } from '../../components/common/EmptyState';
import { usePlatform } from '../../context/PlatformContext';
import { useAuth } from '../../context/AuthContext';
import { followingApi, userApi, resolveMediaUrl } from '../../services/api';
import { UserProfile } from '../../types/profile';
import { platformService, LivePublicProfile } from '../../api/platformService';
import { AccountType } from '../../types/auth';

const convertLiveToUserProfile = (live: LivePublicProfile): UserProfile => {
  const roleMap: Record<string, AccountType> = {
    CANDIDATE: 'candidate',
    EMPLOYER: 'employer',
    TRAINING_INSTITUTE: 'institute',
    GOVERNMENT: 'government',
    SUPER_ADMIN: 'admin',
  };
  const role: AccountType = roleMap[live.account_type] || 'candidate';
  const username = live.username || (live.handle ? live.handle.replace(/^@/, '') : (live.email?.split('@')[0] || live.id));
  const name =
    live.name ||
    live.organization?.display_name ||
    live.organization?.legal_name ||
    live.full_name ||
    (live.first_name ? `${live.first_name} ${live.last_name || ''}`.trim() : (live.username || 'User'));

  return {
    id: live.id,
    username,
    name,
    role,
    avatar: live.avatar || '',
    coverImage: live.cover_image || '',
    email: live.email,
    isSelf: Boolean(live.is_self),
    profileCompletionPercentage: live.profile_completion_percentage || 0,
    headline:
      live.headline ||
      (live.account_type === 'EMPLOYER'
        ? `${live.organization?.organization_type || 'Enterprise'} Entity`
        : live.account_type === 'TRAINING_INSTITUTE'
        ? 'Accredited Training Institute'
        : live.account_type === 'GOVERNMENT'
        ? `Jurisdiction: ${live.jurisdiction || 'Public Authority'}`
        : live.account_type === 'SUPER_ADMIN'
        ? 'Central System Administrator'
        : 'Verified Candidate'),
    bio: live.bio || '',
    location: [live.city, live.state].filter(Boolean).join(', ') || live.location || live.jurisdiction || live.organization?.address || '',
    website: live.organization?.website || '',
    isVerified: Boolean(live.is_verified),
    badgeType:
      live.account_type === 'GOVERNMENT'
        ? 'gov_gold'
        : live.account_type === 'SUPER_ADMIN'
        ? 'admin'
        : live.account_type === 'EMPLOYER'
        ? 'enterprise'
        : live.account_type === 'TRAINING_INSTITUTE'
        ? 'nsqf'
        : 'digilocker',
    joinedDate: '2026',
    followersCount: live.followers_count || 0,
    followingCount: live.following_count || 0,
    isFollowing: Boolean(live.is_following),
    candidateDetails: {
      status: live.candidate_details?.status || 'Active Member',
      verifiedSkills: (live.candidate_details?.verified_skills || live.skills || []).map((s: any) => ({
        id: s.id,
        name: s.name,
        nsqfLevel: s.proficiency === 'EXPERT' ? 6 : s.proficiency === 'ADVANCED' ? 5 : 4,
        issuer: s.issuer || s.issuing_authority || '',
        credentialId: s.credential_id || s.id || '',
        issuedDate: s.issued_date || '',
        verificationHash: s.verification_hash || s.certificate_hash || '',
        category: s.category || 'Core',
      })),
      selfDeclaredSkills: (live.candidate_details?.self_declared_skills || []).map((s: any) => ({
        id: s.id,
        name: s.name,
        category: s.category || 'Technical',
        endorsements: s.endorsements || 0,
      })),
      education: (live.candidate_details?.education || []).map((e: any) => ({
        id: e.id || `edu_${Math.random()}`,
        institution: e.institution,
        degree: e.degree,
        fieldOfStudy: e.field_of_study || '',
        startDate: e.start_date || '',
        endDate: e.end_date || '',
        grade: e.grade,
      })),
      experience: (live.candidate_details?.experience || []).map((e: any) => ({
        id: e.id || `exp_${Math.random()}`,
        title: e.title,
        organization: e.organization,
        employmentType: e.employment_type || 'Full-time',
        location: e.location || '',
        startDate: e.start_date || '',
        endDate: e.end_date || 'Present',
        description: e.description || '',
      })),
      projects: (live.candidate_details?.projects || []).map((p: any) => ({
        id: p.id || `proj_${Math.random()}`,
        title: p.title,
        description: p.description || '',
        tags: Array.isArray(p.tags) ? p.tags : [],
        link: p.link,
      })),
      certifications: live.candidate_details?.certifications || [],
      coursesCompleted: live.candidate_details?.courses_completed || [],
      achievements: live.candidate_details?.achievements || [],
      languages: live.candidate_details?.languages || [],
      careerPreferences: live.candidate_details?.career_preferences || {},
      digilockerIdMasked: live.candidate_details?.digilocker_id_masked || undefined,
    },
    employerDetails: {
      industry: live.organization?.industry || live.organization?.organization_type || 'Enterprise',
      companySize: live.organization?.company_size || '',
      foundedYear: live.organization?.founded_year ? String(live.organization.founded_year) : '',
      headquarters: [live.organization?.city, live.organization?.state].filter(Boolean).join(', ') || live.organization?.address || '',
      gstVerified: live.organization?.verification_status === 'APPROVED' || live.organization?.verification_status === 'VERIFIED',
      openJobs: (live.jobs || []).map((j) => ({
        id: j.id,
        title: j.title,
        type: (j.employment_type as any) || 'Full-time',
        location: j.location || 'India',
        salary: j.salary_min && j.salary_max ? `₹${(j.salary_min / 100000).toFixed(1)} - ${(j.salary_max / 100000).toFixed(1)} LPA` : 'Competitive',
        applicantsCount: j.applicant_count || 0,
        postedAt: new Date(j.created_at).toLocaleDateString(),
        description: j.description || '',
        skills: [],
      })),
      techStack: [],
    },
    instituteDetails: {
      affiliation: live.organization?.affiliation || '',
      accreditationCode: live.organization?.accreditation_code || '',
      placementRate: live.organization?.placement_rate || '',
      coursesOffered: (live.courses || []).map((c) => ({
        id: c.id,
        title: c.title,
        nsqfLevel: 4,
        duration: `${c.duration_weeks || 12} Weeks`,
        mode: 'In-person',
        enrolledCount: c.enrolled_count || 0,
        placementRate: 'Active Batch',
        certifiedBy: c.institution_name || 'Accredited',
        nextBatchDate: 'Enrollment Open',
      })),
      campusLocations: [],
      activeBatchesCount: live.courses?.length || 0,
    },
    governmentDetails: {
      ministryDepartment: live.organization?.display_name || live.jurisdiction || 'Government Authority',
      jurisdictionLevel: (live.government_level as any) || (live.jurisdiction?.includes('District') ? 'District' : live.jurisdiction?.includes('State') ? 'State' : 'Central'),
      jurisdictionTerritory: live.jurisdiction || live.state || 'India',
      activeSchemes: [],
      nodalOfficersCount: live.nodal_officers_count || 0,
      annualBeneficiaries: live.annual_beneficiaries || '',
    },
    adminDetails: {
      adminRoleTitle: 'Platform Operations Authority',
      clearanceLevel: 'Super Administrator',
      systemResponsibilities: ['Cryptographic Trust', 'Statutory Verification', 'User Governance'],
    },
    posts: [],
  };
};

export const PublicProfilePage: React.FC = () => {
  const { username } = useParams<{ username: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user: authUser } = useAuth();

  const {
    currentUser,
    openMessageModal,
    applyModal,
    openApplyModal,
    closeApplyModal,
  } = usePlatform();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isFollowLoading, setIsFollowLoading] = useState<boolean>(false);

  // Messaging & Edit Modals State
  const [directMessageOpen, setDirectMessageOpen] = useState(false);
  const [profileEditOpen, setProfileEditOpen] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [coverUploading, setCoverUploading] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const avatarInputRef = useRef<HTMLInputElement>(null);
  const coverInputRef = useRef<HTMLInputElement>(null);
  const moreMenuRef = useRef<HTMLDivElement>(null);

  // Follow Modal State
  const [followModalOpen, setFollowModalOpen] = useState(false);
  const [followModalType, setFollowModalType] = useState<'Followers' | 'Following'>('Followers');

  // Tab State
  const tabParam = searchParams.get('tab');
  const [activeTab, setActiveTab] = useState<string>(tabParam || 'overview');

  // Close more menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(e.target as Node)) {
        setMoreMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profile) return;
    setAvatarUploading(true);
    try {
      const res = await userApi.uploadAvatar(file);
      if (res.avatar_url || res.url) {
        setProfile((prev) => (prev ? { ...prev, avatar: res.avatar_url || res.url } : null));
        showToast('Profile photo updated successfully!');
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to upload profile photo');
    } finally {
      setAvatarUploading(false);
      if (avatarInputRef.current) avatarInputRef.current.value = '';
    }
  };

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !profile) return;
    setCoverUploading(true);
    try {
      const res = await userApi.uploadCover(file);
      if (res.cover_url || res.url) {
        setProfile((prev) => (prev ? { ...prev, coverImage: res.cover_url || res.url } : null));
        showToast('Cover photo updated successfully!');
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to upload cover banner');
    } finally {
      setCoverUploading(false);
      if (coverInputRef.current) coverInputRef.current.value = '';
    }
  };

  const handleCopyUsername = () => {
    if (profile?.username && navigator.clipboard) {
      navigator.clipboard.writeText(`@${profile.username}`);
      showToast(`Copied @${profile.username} to clipboard!`);
    }
    setMoreMenuOpen(false);
  };

  const handleToggleFollow = async () => {
    if (!profile) return;
    if (!authUser) {
      navigate('/login');
      return;
    }
    if (authUser.id === profile.id) return;

    const prevFollowing = profile.isFollowing;
    const prevCount = profile.followersCount;

    // Optimistic UI update
    setProfile((prev) =>
      prev
        ? {
            ...prev,
            isFollowing: !prevFollowing,
            followersCount: !prevFollowing ? prevCount + 1 : Math.max(0, prevCount - 1),
          }
        : null
    );

    try {
      setIsFollowLoading(true);
      const res = await followingApi.toggleFollow('USER', profile.id);
      if (res && res.is_following !== undefined) {
        setProfile((prev) =>
          prev
            ? {
                ...prev,
                isFollowing: res.is_following,
                followersCount:
                  res.followers_count ??
                  (res.is_following ? prevCount + 1 : Math.max(0, prevCount - 1)),
              }
            : null
        );
      }
    } catch {
      // Revert on error
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              isFollowing: prevFollowing,
              followersCount: prevCount,
            }
          : null
      );
    } finally {
      setIsFollowLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadProfile = async () => {
      setIsLoading(true);

      let identifier = username;
      if (!identifier) {
        if (location.pathname.includes('/candidate/profile')) identifier = currentUser?.username || authUser?.username || undefined;
        else if (location.pathname.includes('/employer/profile')) identifier = currentUser?.username || authUser?.username || undefined;
        else if (location.pathname.includes('/institution/profile') || location.pathname.includes('/institute/profile')) identifier = currentUser?.username || authUser?.username || undefined;
        else if (location.pathname.includes('/government/profile')) identifier = currentUser?.username || authUser?.username || undefined;
        else if (location.pathname.includes('/admin/profile')) identifier = currentUser?.username || authUser?.username || undefined;
      }

      if (identifier) {
        try {
          const live = await platformService.getPublicProfile(identifier);
          if (isMounted) {
            if (live) {
              setProfile(convertLiveToUserProfile(live));
            } else if (currentUser && (!username || currentUser.username === identifier)) {
              setProfile(currentUser);
            } else {
              setProfile(null);
            }
          }
        } catch {
          if (isMounted) setProfile(currentUser?.username === identifier ? currentUser : null);
        }
      } else if (currentUser) {
        if (isMounted) setProfile(currentUser);
      } else {
        if (isMounted) setProfile(null);
      }

      if (isMounted) setIsLoading(false);
    };

    loadProfile();
    return () => {
      isMounted = false;
    };
  }, [username, location.pathname, currentUser, authUser]);

  useEffect(() => {
    if (tabParam) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const handleShare = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      showToast('Public profile link copied to clipboard!');
    }
    setMoreMenuOpen(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
        <Navbar />
        <main className="flex-1 flex items-center justify-center p-8">
          <div className="text-center space-y-3">
            <div className="w-9 h-9 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Resolving verified public profile...</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
        <Navbar />
        <main className="flex-1 max-w-xl mx-auto flex items-center justify-center p-8 w-full">
          <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-2xs w-full text-center">
            <EmptyState
              icon={Shield}
              title="Profile Not Found"
              description="The requested public profile does not exist or has not published verified credentials to the SkillVistaar registry."
              actionText="Return to Platform Home"
              onAction={() => { window.location.href = '/'; }}
            />
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  // Get Verification Badge Icon & Label
  const getBadgeMeta = () => {
    switch (profile.badgeType) {
      case 'digilocker':
        return {
          icon: <ShieldCheck className="w-4 h-4 text-teal-600" />,
          label: 'DigiLocker Verified',
          color: 'teal' as const,
        };
      case 'enterprise':
        return {
          icon: <Briefcase className="w-4 h-4 text-blue-600" />,
          label: 'Verified Enterprise',
          color: 'blue' as const,
        };
      case 'nsqf':
        return {
          icon: <GraduationCap className="w-4 h-4 text-emerald-600" />,
          label: 'NSQF Accredited',
          color: 'emerald' as const,
        };
      case 'gov_gold':
        return {
          icon: <Landmark className="w-4 h-4 text-amber-600" />,
          label: 'Government Authority',
          color: 'amber' as const,
        };
      case 'admin':
      default:
        return {
          icon: <Shield className="w-4 h-4 text-purple-600" />,
          label: 'Root Governance Authority',
          color: 'purple' as const,
        };
    }
  };

  const badgeMeta = getBadgeMeta();

  // Dynamic Tabs based on Role
  const getTabs = () => {
    const base = [
      { id: 'overview', label: 'Overview' },
      { id: 'about', label: 'About' },
    ];

    if (profile.role === 'candidate') {
      base.push({ id: 'skills', label: 'Skills & Verified Credentials' });
      base.push({ id: 'experience', label: 'Experience & Projects' });
    } else if (profile.role === 'employer') {
      base.push({ id: 'jobs', label: `Jobs & Openings (${profile.employerDetails?.openJobs.length || 0})` });
    } else if (profile.role === 'institute') {
      base.push({ id: 'courses', label: `Courses & Programs (${profile.instituteDetails?.coursesOffered.length || 0})` });
    } else if (profile.role === 'government') {
      base.push({ id: 'schemes', label: `Public Schemes (${profile.governmentDetails?.activeSchemes.length || 0})` });
    } else if (profile.role === 'admin') {
      base.push({ id: 'governance', label: 'Trust & Governance Framework' });
    }

    base.push({ id: 'activity', label: `Activity (${profile.posts.length})` });
    return base;
  };

  const tabs = getTabs();

  // Role dashboard return path
  const getDashboardPath = () => {
    switch (profile.role) {
      case 'employer':
        return '/employer/dashboard';
      case 'institute':
        return '/institution/dashboard';
      case 'government':
        return '/government/dashboard';
      case 'admin':
        return '/admin/dashboard';
      case 'candidate':
      default:
        return '/candidate/dashboard';
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      <Navbar />

      <main className="flex-1 pb-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
          {/* Top Quick Nav back to Dashboard */}
          <div className="flex items-center justify-between py-2 text-xs">
            <Link
              to={getDashboardPath()}
              className="inline-flex items-center gap-1 font-semibold text-teal-700 hover:text-teal-800 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to {profile.role.toUpperCase()} Workspace</span>
            </Link>

            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Lock className="w-3 h-3 text-slate-400" />
              <span>Public Profile • Sensitive PII Masked</span>
            </div>
          </div>

          {/* MAIN PROFILE CARD (INSTAGRAM + LINKEDIN STYLE) */}
          <div className="bg-white rounded-xl shadow-card border border-slate-200 overflow-hidden mt-1">
            {/* Cover Banner */}
            <div className="relative h-36 sm:h-52 w-full overflow-hidden bg-slate-800 group">
              {profile.coverImage ? (
                <img
                  src={resolveMediaUrl(profile.coverImage)}
                  alt="Cover"
                  className="w-full h-full object-cover opacity-85"
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-r from-slate-900 via-teal-950 to-slate-900" />
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/60 via-transparent to-transparent" />

              {/* Cover upload button for owner */}
              {(profile.isSelf || authUser?.id === profile.id) && (
                <>
                  <input
                    type="file"
                    ref={coverInputRef}
                    onChange={handleCoverUpload}
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden"
                  />
                  <button
                    onClick={() => coverInputRef.current?.click()}
                    disabled={coverUploading}
                    className="absolute top-3 right-3 px-3 py-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white text-xs font-semibold flex items-center gap-1.5 transition backdrop-blur-xs border border-white/20 shadow-md"
                    title="Change Cover Banner"
                  >
                    {coverUploading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Camera className="w-3.5 h-3.5" />
                    )}
                    <span>{coverUploading ? 'Uploading...' : 'Update Cover'}</span>
                  </button>
                </>
              )}
            </div>

            {/* Profile Info Header Bar */}
            <div className="px-5 sm:px-7 pb-5 pt-0 relative">
              <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 -mt-12 sm:-mt-16 mb-4">
                {/* Avatar with Verified Status & Owner Upload Trigger */}
                <div className="relative inline-block group">
                  {profile.avatar ? (
                    <img
                      src={resolveMediaUrl(profile.avatar)}
                      alt={profile.name}
                      className="w-24 h-24 sm:w-28 sm:h-28 rounded-full object-cover border-4 border-white shadow-md bg-white ring-2 ring-slate-200/80"
                    />
                  ) : (
                    <div className="w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-slate-100 border-4 border-white shadow-md bg-white ring-2 ring-slate-200/80 flex items-center justify-center text-slate-500 font-bold text-2xl">
                      {profile.name.charAt(0).toUpperCase()}
                    </div>
                  )}

                  <div
                    className="absolute bottom-1 right-1 p-1 bg-white rounded-full shadow-xs border border-slate-100"
                    title={badgeMeta.label}
                  >
                    {badgeMeta.icon}
                  </div>

                  {(profile.isSelf || authUser?.id === profile.id) && (
                    <>
                      <input
                        type="file"
                        ref={avatarInputRef}
                        onChange={handleAvatarUpload}
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                      />
                      <button
                        onClick={() => avatarInputRef.current?.click()}
                        disabled={avatarUploading}
                        className="absolute inset-0 rounded-full bg-black/40 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition duration-150 cursor-pointer"
                        title="Upload Photo"
                      >
                        {avatarUploading ? (
                          <Loader2 className="w-6 h-6 animate-spin text-white" />
                        ) : (
                          <div className="flex flex-col items-center">
                            <Camera className="w-5 h-5 text-white" />
                            <span className="text-[9px] font-bold mt-0.5">Upload</span>
                          </div>
                        )}
                      </button>
                    </>
                  )}
                </div>

                {/* Primary Actions: Follow, Message, More Menu, or Edit Profile */}
                <div className="flex flex-wrap items-center gap-2 pt-2 sm:pt-0">
                  {profile.isSelf || authUser?.id === profile.id ? (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setProfileEditOpen(true)}
                      className="text-xs font-semibold px-4 shadow-2xs bg-teal-600 hover:bg-teal-700 text-white"
                      leftIcon={<Edit3 className="w-3.5 h-3.5" />}
                    >
                      Edit Profile
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant={profile.isFollowing ? 'outline' : 'primary'}
                        size="sm"
                        onClick={handleToggleFollow}
                        disabled={isFollowLoading}
                        className="text-xs font-semibold px-4 shadow-2xs"
                        leftIcon={
                          profile.isFollowing ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Plus className="w-3.5 h-3.5" />
                          )
                        }
                      >
                        {profile.isFollowing ? 'Following' : 'Follow'}
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDirectMessageOpen(true)}
                        className="text-xs font-semibold px-3.5"
                        leftIcon={<MessageSquare className="w-3.5 h-3.5 text-slate-500" />}
                      >
                        Message
                      </Button>
                    </>
                  )}

                  {/* More Menu Dropdown */}
                  <div className="relative" ref={moreMenuRef}>
                    <button
                      onClick={() => setMoreMenuOpen(!moreMenuOpen)}
                      className="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                      title="More Options"
                      aria-label="More Options"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>

                    {moreMenuOpen && (
                      <div className="absolute right-0 mt-1.5 w-48 bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-30 animate-in fade-in">
                        <button
                          onClick={handleCopyUsername}
                          className="w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                        >
                          <Copy className="w-3.5 h-3.5 text-slate-400" />
                          <span>Copy @{profile.username}</span>
                        </button>
                        <button
                          onClick={handleShare}
                          className="w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                        >
                          <Share2 className="w-3.5 h-3.5 text-slate-400" />
                          <span>Share Profile Link</span>
                        </button>
                        {(profile.isSelf || authUser?.id === profile.id) && (
                          <button
                            onClick={() => {
                              setMoreMenuOpen(false);
                              setProfileEditOpen(true);
                            }}
                            className="w-full px-3 py-2 text-left text-xs font-medium text-teal-700 hover:bg-teal-50 flex items-center gap-2 border-t border-slate-100"
                          >
                            <Edit3 className="w-3.5 h-3.5 text-teal-600" />
                            <span>Edit Profile Details</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {toastMessage && (
                <div className="mb-3 p-2 bg-teal-50 border border-teal-200 text-teal-800 text-xs rounded font-medium flex items-center gap-2 animate-in fade-in">
                  <Check className="w-3.5 h-3.5 text-teal-600" />
                  <span>{toastMessage}</span>
                </div>
              )}

              {/* Identity & Metadata */}
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
                    {profile.name}
                  </h1>
                  <span className="text-xs font-semibold text-slate-400 font-mono">
                    @{profile.username}
                  </span>
                  <Badge variant={badgeMeta.color} size="sm">
                    {badgeMeta.label}
                  </Badge>
                </div>

                <div className="flex items-center gap-2">
                  <p className="text-xs sm:text-sm text-slate-700 font-medium max-w-2xl leading-relaxed">
                    {profile.headline}
                  </p>
                  {(profile.isSelf || authUser?.id === profile.id) && (
                    <button
                      onClick={() => setProfileEditOpen(true)}
                      className="p-1 rounded text-slate-400 hover:text-teal-700 transition"
                      title="Edit headline"
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                  )}
                </div>

                {/* Sub-meta strip */}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-500 pt-1">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {profile.location || 'India'}
                  </span>

                  {/* Registered email: visible to owner per privacy rules */}
                  {profile.email && (
                    <span
                      className="flex items-center gap-1 font-mono text-[11px] text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200/60"
                      title="Registered Email (Visible to owner only)"
                    >
                      <Mail className="w-3 h-3 text-teal-600" />
                      <span>{profile.email}</span>
                      <Lock className="w-2.5 h-2.5 text-slate-400 ml-0.5" />
                    </span>
                  )}

                  {profile.website && (
                    <a
                      href={profile.website}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-teal-700 hover:underline font-medium"
                    >
                      <Globe className="w-3.5 h-3.5 text-slate-400" />
                      Website
                    </a>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    Joined {profile.joinedDate}
                  </span>
                </div>

                {/* Profile Completion Bar for Candidate Profiles */}
                {profile.role === 'candidate' && (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/70 p-3 rounded-xl border border-slate-200/70">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-teal-600 shrink-0" />
                      <div>
                        <span className="text-xs font-bold text-slate-800">
                          Profile Completion: {profile.profileCompletionPercentage || 0}%
                        </span>
                        <p className="text-[10px] text-slate-500">
                          {profile.profileCompletionPercentage && profile.profileCompletionPercentage >= 80
                            ? 'All essential verified passport sections completed.'
                            : 'Complete education, experience, and certifications to reach 100%.'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 w-full sm:w-48">
                      <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal-600 rounded-full transition-all duration-300"
                          style={{ width: `${profile.profileCompletionPercentage || 0}%` }}
                        />
                      </div>
                      {(profile.isSelf || authUser?.id === profile.id) && (
                        <button
                          onClick={() => setProfileEditOpen(true)}
                          className="text-[11px] font-bold text-teal-700 hover:underline shrink-0"
                        >
                          Complete &rarr;
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Followers, Following & Core Stat Counters (Instagram style) */}
                <div className="flex items-center gap-6 text-xs pt-3 border-t border-slate-100 mt-3">
                  <button
                    onClick={() => {
                      setFollowModalType('Followers');
                      setFollowModalOpen(true);
                    }}
                    className="hover:underline flex items-center gap-1.5"
                  >
                    <strong className="font-extrabold text-slate-900 font-sans">
                      {profile.followersCount.toLocaleString()}
                    </strong>{' '}
                    <span className="text-slate-500">Followers</span>
                  </button>

                  <button
                    onClick={() => {
                      setFollowModalType('Following');
                      setFollowModalOpen(true);
                    }}
                    className="hover:underline flex items-center gap-1.5"
                  >
                    <strong className="font-extrabold text-slate-900 font-sans">
                      {profile.followingCount.toLocaleString()}
                    </strong>{' '}
                    <span className="text-slate-500">Following</span>
                  </button>

                  {/* Dynamic Core Metric */}
                  <div className="flex items-center gap-1.5 text-teal-800 font-medium bg-teal-50/70 px-2 py-0.5 rounded border border-teal-200/60">
                    <Award className="w-3.5 h-3.5 text-teal-600" />
                    <span>
                      {profile.role === 'candidate' &&
                        `${profile.candidateDetails?.verifiedSkills.length || 0} Verified NSQF Skills`}
                      {profile.role === 'employer' &&
                        `${profile.employerDetails?.openJobs.length || 0} Active Job Openings`}
                      {profile.role === 'institute' &&
                        `${profile.instituteDetails?.coursesOffered.length || 0} Accredited Programs`}
                      {profile.role === 'government' &&
                        `${profile.governmentDetails?.activeSchemes.length || 0} Active Schemes`}
                      {profile.role === 'admin' && 'Root Certificate Authority'}
                    </span>
                  </div>
                </div>
              </div>

              {/* TABS BAR */}
              <div className="flex overflow-x-auto gap-1 border-t border-slate-200 mt-4 pt-1">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`py-2.5 px-3 text-xs font-bold border-b-2 whitespace-nowrap transition-all duration-150 ${
                      activeTab === tab.id
                        ? 'border-teal-600 text-teal-800 bg-teal-50/30'
                        : 'border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* TAB CONTENTS */}
          <div className="mt-5">
            {/* 1. OVERVIEW TAB */}
            {activeTab === 'overview' && (
              <div className="space-y-4">
                {/* Bio card */}
                <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-2xs space-y-2">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Executive Profile Summary
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    {profile.bio}
                  </p>
                </div>

                {/* Role Specific Overview Cards */}
                {profile.role === 'candidate' && profile.candidateDetails && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-2xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">DigiLocker Skill Passport</span>
                        <Badge variant="teal" size="sm">
                          Verified
                        </Badge>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Masked ID: <span className="font-mono text-slate-800">{profile.candidateDetails.digilockerIdMasked}</span>
                      </p>
                      <p className="text-[11px] text-slate-600">
                        {profile.candidateDetails.verifiedSkills.length} NSQF competencies cryptographically signed.
                      </p>
                    </div>

                    <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-2xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900">Current Status</span>
                        <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                          {profile.candidateDetails.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Verified vocational graduate open to full-time enterprise deployment and structured industrial apprenticeships.
                      </p>
                    </div>
                  </div>
                )}

                {profile.role === 'employer' && profile.employerDetails && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">{profile.employerDetails.companySize}</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Enterprise Scale</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">{profile.employerDetails.openJobs.length} Roles</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Actively Hiring</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-emerald-600">GST Verified</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Statutory Compliance</p>
                    </div>
                  </div>
                )}

                {profile.role === 'institute' && profile.instituteDetails && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">{profile.instituteDetails.placementRate}</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Placement Rate</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">{profile.instituteDetails.activeBatchesCount}</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Active Cohorts</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-teal-700">NSDC CoE</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Accreditation</p>
                    </div>
                  </div>
                )}

                {profile.role === 'government' && profile.governmentDetails && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">{profile.governmentDetails.jurisdictionLevel}</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Administrative Level</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">{profile.governmentDetails.activeSchemes.length}</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Active Schemes</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-amber-600">{profile.governmentDetails.annualBeneficiaries}</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Annual Coverage</p>
                    </div>
                  </div>
                )}

                {profile.role === 'admin' && profile.adminDetails && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-purple-700">Root Level 1</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Clearance Level</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-slate-900">ECDSA P-384</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Cryptographic Anchor</p>
                    </div>
                    <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
                      <p className="text-lg font-black text-teal-700">PDI Authority</p>
                      <p className="text-[10px] text-slate-500 uppercase font-semibold">Public Trust Registry</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 2. ABOUT TAB */}
            {activeTab === 'about' && (
              <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-2xs space-y-4 text-xs sm:text-sm">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Detailed Information & Background
                </h3>
                <p className="text-slate-600 leading-relaxed">{profile.bio}</p>

                <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400 block font-semibold text-[10px] uppercase">
                      Official Entity Handle
                    </span>
                    <span className="font-mono text-slate-800">@{profile.username}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-semibold text-[10px] uppercase">
                      Primary Location
                    </span>
                    <span className="text-slate-800">{profile.location}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-semibold text-[10px] uppercase">
                      Verification Standard
                    </span>
                    <span className="text-teal-700 font-semibold">{badgeMeta.label}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block font-semibold text-[10px] uppercase">
                      Onboarding Date
                    </span>
                    <span className="text-slate-800">{profile.joinedDate}</span>
                  </div>
                </div>
              </div>
            )}

            {/* 3. SKILLS & VERIFIED CREDENTIALS (CANDIDATE) */}
            {activeTab === 'skills' && profile.candidateDetails && (
              <div className="space-y-5">
                {/* SECTION A: VERIFIED CREDENTIALS (DIGILOCKER / NSQF) */}
                <div className="bg-white rounded-xl border border-teal-200/90 p-5 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-teal-100">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-teal-600" />
                      <div>
                        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                          Cryptographically Verified Credentials
                        </h3>
                        <p className="text-[11px] text-teal-700 font-semibold">
                          Directly anchored from DigiLocker, NSDC, and NCVET repositories
                        </p>
                      </div>
                    </div>
                    <Badge variant="teal" size="sm">
                      Tamper-Proof
                    </Badge>
                  </div>

                  {profile.candidateDetails.verifiedSkills.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      {profile.candidateDetails.verifiedSkills.map((sk) => (
                        <div
                          key={sk.id}
                          className="p-3.5 rounded-lg border border-teal-100 bg-teal-50/30 space-y-1.5"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="text-xs font-bold text-slate-900 leading-snug">
                              {sk.name}
                            </h4>
                            <span className="text-[10px] font-black text-teal-800 bg-teal-100 px-1.5 py-0.5 rounded shrink-0">
                              NSQF L{sk.nsqfLevel}
                            </span>
                          </div>

                          <p className="text-[11px] text-slate-600">Issuer: {sk.issuer}</p>

                          <div className="pt-1 flex flex-col gap-0.5 text-[10px] text-slate-500 font-mono">
                            <span>Cert ID: {sk.credentialId}</span>
                            <span className="text-teal-700">Audit Hash: {sk.verificationHash}</span>
                          </div>

                          {sk.scorePercent && (
                            <div className="pt-1 text-[10px] font-semibold text-emerald-700">
                              Practical Assessment: {sk.scorePercent}%
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4">
                      <EmptyState
                        icon={Award}
                        title="No Verified Credentials Yet"
                        description="Credentials anchored from DigiLocker, NSDC, or NCVET will appear here once verified."
                      />
                    </div>
                  )}
                </div>

                {/* SECTION B: SELF-DECLARED SKILLS */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                        Self-Declared Skills & Competencies
                      </h3>
                      <p className="text-[11px] text-slate-400">
                        Added by candidate with peer and educator endorsements
                      </p>
                    </div>
                    <Badge variant="slate" size="sm">
                      Unverified
                    </Badge>
                  </div>

                  {profile.candidateDetails.selfDeclaredSkills.length > 0 ? (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {profile.candidateDetails.selfDeclaredSkills.map((sk) => (
                        <div
                          key={sk.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700"
                        >
                          <span>{sk.name}</span>
                          <span className="text-[10px] text-slate-400 font-bold">
                            • {sk.endorsements} endorsements
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 py-2">No self-declared competencies listed.</p>
                  )}
                </div>
              </div>
            )}

            {/* 4. EXPERIENCE & PROJECTS (CANDIDATE) */}
            {activeTab === 'experience' && profile.candidateDetails && (
              <div className="space-y-4">
                {/* EDUCATION CARD */}
                <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-2xs space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Education & Academic Qualifications
                  </h3>
                  {profile.candidateDetails.education && profile.candidateDetails.education.length > 0 ? (
                    <div className="divide-y divide-slate-100">
                      {profile.candidateDetails.education.map((edu) => (
                        <div key={edu.id} className="py-3 first:pt-0 space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-900">{edu.degree}</span>
                            <span className="text-[10px] text-slate-500">
                              {edu.startDate} {edu.endDate ? `- ${edu.endDate}` : ''}
                            </span>
                          </div>
                          <p className="text-[11px] font-medium text-teal-700">
                            {edu.institution} {edu.fieldOfStudy ? `• ${edu.fieldOfStudy}` : ''}
                          </p>
                          {edu.grade && (
                            <p className="text-[11px] text-slate-500">
                              Grade / Marks: <span className="font-semibold text-slate-700">{edu.grade}</span>
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4">
                      <EmptyState
                        icon={GraduationCap}
                        title="No Education Records"
                        description="Academic background and diploma history will appear here once added."
                      />
                    </div>
                  )}
                </div>

                <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-2xs space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Industrial Apprenticeship & Experience
                  </h3>
                  {profile.candidateDetails.experience.length > 0 ? (
                    <div className="divide-y divide-slate-100">
                      {profile.candidateDetails.experience.map((exp) => (
                        <div key={exp.id} className="py-3 first:pt-0 space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-bold text-slate-900">{exp.title}</span>
                            <span className="text-[10px] text-slate-500">
                              {exp.startDate} - {exp.endDate}
                            </span>
                          </div>
                          <p className="text-[11px] font-medium text-teal-700">
                            {exp.organization} • {exp.employmentType} ({exp.location})
                          </p>
                          <p className="text-xs text-slate-600 leading-relaxed pt-1">
                            {exp.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4">
                      <EmptyState
                        icon={Briefcase}
                        title="No Experience Records"
                        description="Apprenticeship or industrial experience history will appear here."
                      />
                    </div>
                  )}
                </div>

                <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-2xs space-y-3">
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Practical Projects & Open Source
                  </h3>
                  {profile.candidateDetails.projects.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {profile.candidateDetails.projects.map((pr) => (
                        <div key={pr.id} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-bold text-slate-900">{pr.title}</h4>
                            {pr.link && (
                              <a
                                href={pr.link}
                                target="_blank"
                                rel="noreferrer"
                                className="text-teal-700 hover:text-teal-800"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-600 leading-relaxed">
                            {pr.description}
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {pr.tags.map((t, idx) => (
                              <span key={idx} className="text-[9px] px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4">
                      <EmptyState
                        icon={GraduationCap}
                        title="No Practical Projects"
                        description="Applied projects and capstone portfolios will appear here."
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 5. JOBS TAB (EMPLOYER) */}
            {activeTab === 'jobs' && profile.employerDetails && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Active Enterprise Openings
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Apply directly with your SkillVistaar DigiLocker passport
                    </p>
                  </div>
                  <Badge variant="teal" size="sm">
                    {profile.employerDetails.openJobs.length} Open
                  </Badge>
                </div>

                <div className="divide-y divide-slate-100">
                  {profile.employerDetails.openJobs.length > 0 ? (
                    profile.employerDetails.openJobs.map((job) => (
                      <div key={job.id} className="py-4 first:pt-0 space-y-2">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-xs sm:text-sm font-bold text-slate-900">
                                {job.title}
                              </h4>
                              <span className="text-[10px] font-semibold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                                {job.type}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              {job.location} • <span className="font-semibold text-slate-700">{job.salary}</span>
                            </p>
                          </div>

                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => openApplyModal(job.title, profile.name)}
                            className="text-xs font-semibold px-4 self-start sm:self-auto"
                          >
                            Apply Now
                          </Button>
                        </div>

                        <p className="text-xs text-slate-600 leading-relaxed">
                          {job.description}
                        </p>

                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {job.skills.map((s, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-6">
                      <EmptyState
                        icon={Briefcase}
                        title="No Open Positions"
                        description="This employer has not published any open job vacancies yet."
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 6. COURSES TAB (INSTITUTE) */}
            {activeTab === 'courses' && profile.instituteDetails && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Accredited Vocational Curriculum
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      NSQF aligned training cohorts with industrial apprenticeship tie-ups
                    </p>
                  </div>
                  <Badge variant="emerald" size="sm">
                    {profile.instituteDetails.coursesOffered.length} Programs
                  </Badge>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {profile.instituteDetails.coursesOffered.length > 0 ? (
                    profile.instituteDetails.coursesOffered.map((crs) => (
                      <div key={crs.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-xs sm:text-sm font-bold text-slate-900">
                                {crs.title}
                              </h4>
                              <span className="text-[10px] font-bold text-teal-800 bg-teal-100 px-1.5 py-0.5 rounded">
                                NSQF Level {crs.nsqfLevel}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              Certified by: <span className="font-semibold text-slate-700">{crs.certifiedBy}</span>
                            </p>
                          </div>

                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => openMessageModal(profile.name, 'Admissions')}
                            className="text-xs font-semibold px-3"
                          >
                            Inquire for Batch
                          </Button>
                        </div>

                        <div className="pt-2 border-t border-slate-200 flex flex-wrap items-center justify-between text-[11px] text-slate-500 gap-2">
                          <span>Duration: {crs.duration} ({crs.mode})</span>
                          <span>Next Batch: {crs.nextBatchDate}</span>
                          <span className="font-bold text-emerald-700">
                            {crs.placementRate} Track Record
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-6">
                      <EmptyState
                        icon={GraduationCap}
                        title="No Active Courses"
                        description="This training institute has not published any vocational courses yet."
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 7. SCHEMES TAB (GOVERNMENT) */}
            {activeTab === 'schemes' && profile.governmentDetails && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Public Skilling Schemes & Guidelines
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      National initiatives administered by {profile.governmentDetails.ministryDepartment}
                    </p>
                  </div>
                  <Badge variant="amber" size="sm">
                    Active Portals
                  </Badge>
                </div>

                <div className="divide-y divide-slate-100">
                  {profile.governmentDetails.activeSchemes.length > 0 ? (
                    profile.governmentDetails.activeSchemes.map((sch) => (
                      <div key={sch.id} className="py-4 first:pt-0 space-y-2">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-xs sm:text-sm font-bold text-slate-900">
                                {sch.title}
                              </h4>
                              <span className="text-[10px] font-mono font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                                {sch.code}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              Nodal Agency: {sch.nodalMinistry}
                            </p>
                          </div>
                          <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                            {sch.status}
                          </span>
                        </div>

                        <p className="text-xs text-slate-600 leading-relaxed">
                          {sch.description}
                        </p>

                        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 flex flex-wrap items-center justify-between text-xs text-slate-700">
                          <span>Target: <strong>{sch.targetBeneficiaries}</strong></span>
                          <span>Annual Allocation: <strong className="text-teal-700">{sch.budgetAllocated}</strong></span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-6">
                      <EmptyState
                        icon={Landmark}
                        title="No Active Schemes"
                        description="No public skilling schemes or guidelines published for this authority."
                      />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 8. GOVERNANCE TAB (ADMIN) */}
            {activeTab === 'governance' && (
              <div className="space-y-5">
                {/* Header Banner Card */}
                <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-teal-950 rounded-xl p-5 text-white space-y-2 border border-slate-700 shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-200 border border-purple-400/30">
                      <Shield className="w-3.5 h-3.5 text-purple-300" />
                      Public Digital Infrastructure (PDI) Trust Anchor
                    </span>
                    <Badge variant="teal" size="sm">
                      Level 1 Root CA
                    </Badge>
                  </div>
                  <h3 className="text-sm sm:text-base font-extrabold tracking-tight">
                    SkillVistaar Public Trust & Statutory Governance Architecture
                  </h3>
                  <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                    Operated under the National Informatics Framework, SkillVistaar serves as the cryptographic root of trust anchoring vocational qualifications, enterprise compliance verifications, and cross-jurisdictional administration.
                  </p>
                </div>

                {/* Cryptographic Architecture Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">Key Signature Engine</span>
                      <ShieldCheck className="w-4 h-4 text-teal-600" />
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      All published certificates and credentials are signed using hardware-backed cryptographic keys (ECDSA secp256k1 & P-384).
                    </p>
                  </div>

                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">Aadhaar Vault Isolation</span>
                      <Lock className="w-4 h-4 text-teal-600" />
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Candidate Aadhaar numbers are stored in secure HSM vaults with UIDAI-compliant tokenization and irreversible hashing.
                    </p>
                  </div>

                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">Statutory Audit Logs</span>
                      <Award className="w-4 h-4 text-teal-600" />
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Append-only administrative telemetry ensuring full traceability of KYC approvals, status overrides, and credential revocations.
                    </p>
                  </div>
                </div>

                {/* Administrative Capabilities */}
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Core Platform Authority
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1">
                      <span className="font-bold text-slate-900">Cross-Entity Enforcement</span>
                      <p className="text-[11px] text-slate-600">
                        Ability to suspend non-compliant employer accounts, freeze fraudulent credentials, and enforce regulatory compliance.
                      </p>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1">
                      <span className="font-bold text-slate-900">4-Tier Government Hierarchy</span>
                      <p className="text-[11px] text-slate-600">
                        Recursive jurisdiction control guaranteeing Central, State, District, and Local skill administration without cross-boundary data leakage.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Privacy & PII Masking Guarantee */}
                <div className="p-4 bg-teal-50/70 rounded-xl border border-teal-200/80 flex items-start gap-3 text-xs">
                  <Lock className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <h4 className="font-bold text-teal-950">Statutory Privacy & Data Minimization Protocol</h4>
                    <p className="text-[11px] text-teal-900 leading-relaxed">
                      In full compliance with the Digital Personal Data Protection Act, candidate sensitive identifiers (Aadhaar number, mobile contact, residential address) are completely partitioned from public profiles. Only pre-screened employers can access candidate dossiers upon explicit application.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 9. ACTIVITY / POSTS TAB */}
            {activeTab === 'activity' && (
              <div className="space-y-4">
                {profile.posts.length > 0 ? (
                  profile.posts.map((post) => (
                    <div
                      key={post.id}
                      className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-3"
                    >
                      <div className="flex items-center gap-2.5">
                        <img
                          src={post.authorAvatar}
                          alt={post.authorName}
                          className="w-9 h-9 rounded-full object-cover border border-slate-200 shrink-0"
                        />
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold text-slate-900">{post.authorName}</span>
                            <span className="text-[10px] text-slate-400">@{post.authorUsername}</span>
                          </div>
                          <span className="text-[10px] text-slate-400">{post.timestamp}</span>
                        </div>
                      </div>

                      <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
                        {post.content}
                      </p>

                      {post.attachmentTitle && (
                        <div className="p-3 bg-teal-50/50 border border-teal-200/70 rounded-lg flex items-center justify-between text-xs font-semibold text-teal-900">
                          <span>{post.attachmentTitle}</span>
                          <ChevronRight className="w-4 h-4 text-teal-600" />
                        </div>
                      )}

                      {post.tags && (
                        <div className="flex flex-wrap gap-1.5">
                          {post.tags.map((t, idx) => (
                            <span key={idx} className="text-[10px] text-teal-700 font-semibold">
                              #{t}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className="pt-2 border-t border-slate-100 flex items-center gap-6 text-xs text-slate-500">
                        <button className="flex items-center gap-1.5 hover:text-rose-600 transition">
                          <Heart className="w-3.5 h-3.5 text-rose-500" />
                          <span>{post.likes}</span>
                        </button>
                        <button className="flex items-center gap-1.5 hover:text-teal-700 transition">
                          <MessageCircle className="w-3.5 h-3.5" />
                          <span>{post.comments} comments</span>
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="bg-white rounded-xl border border-slate-200 p-8 shadow-2xs">
                    <EmptyState
                      icon={MessageSquare}
                      title="No Activity Posts"
                      description="Platform updates, announcements, and verified milestone notices will appear here."
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />

      {/* MODALS */}
      <FollowListModal
        isOpen={followModalOpen}
        onClose={() => setFollowModalOpen(false)}
        title={followModalType}
        entityName={profile.name}
        identifier={profile.username || profile.id}
        onCountChange={(delta) => {
          if (followModalType === 'Followers') {
            setProfile((prev) => (prev ? { ...prev, followersCount: Math.max(0, prev.followersCount + delta) } : null));
          } else {
            setProfile((prev) => (prev ? { ...prev, followingCount: Math.max(0, prev.followingCount + delta) } : null));
          }
        }}
      />

      <DirectMessagingModal
        isOpen={directMessageOpen}
        onClose={() => setDirectMessageOpen(false)}
        initialRecipientId={profile.id}
        initialRecipientName={profile.name}
        initialRecipientAvatar={profile.avatar}
        initialRecipientUsername={profile.username}
      />

      <ProfileManagementModal
        isOpen={profileEditOpen}
        onClose={() => setProfileEditOpen(false)}
        onSaved={async () => {
          setProfileEditOpen(false);
          const live = await platformService.getPublicProfile(profile.username || profile.id);
          if (live) setProfile(convertLiveToUserProfile(live));
        }}
      />

      <JobApplyModal
        isOpen={applyModal.isOpen}
        onClose={closeApplyModal}
        jobTitle={applyModal.jobTitle}
        companyName={applyModal.companyName}
      />
    </div>
  );
};

export default PublicProfilePage;
