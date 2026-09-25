import React, { useState, useEffect, useRef } from 'react';
import {
  User,
  Camera,
  Image as ImageIcon,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  candidateApi,
  userApi,
  resolveMediaUrl,
} from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import Button from '../common/Button';
import InputField from '../common/InputField';

interface ProfileManagementSectionProps {
  onSaved?: () => void;
  isModal?: boolean;
  onClose?: () => void;
}

export const ProfileManagementSection: React.FC<ProfileManagementSectionProps> = ({
  onSaved,
  isModal = false,
  onClose,
}) => {
  const { refreshUser } = useAuth();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [coverUploading, setCoverUploading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const avatarInputRef = useRef<HTMLInputElement>(null);
  const coverInputRef = useRef<HTMLInputElement>(null);

  // Profile Form States
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [username, setUsername] = useState('');
  const [initialUsername, setInitialUsername] = useState('');
  const [headline, setHeadline] = useState('');
  const [bio, setBio] = useState('');
  const [location, setLocation] = useState('');
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [coverUrl, setCoverUrl] = useState('');
  const [completionPercentage, setCompletionPercentage] = useState(0);

  // Dynamic Lists
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');

  const [education, setEducation] = useState<Array<{
    id: string;
    institution: string;
    degree: string;
    field_of_study: string;
    start_date: string;
    end_date: string;
    grade?: string;
  }>>([]);

  const [experience, setExperience] = useState<Array<{
    id: string;
    title: string;
    organization: string;
    employment_type: string;
    location: string;
    start_date: string;
    end_date: string;
    description: string;
  }>>([]);

  const [projects, setProjects] = useState<Array<{
    id: string;
    title: string;
    description: string;
    tags: string[];
    link?: string;
  }>>([]);

  const [certifications, setCertifications] = useState<Array<{
    id: string;
    title: string;
    issuer: string;
    issue_date: string;
    credential_id?: string;
    url?: string;
  }>>([]);

  const [coursesCompleted, setCoursesCompleted] = useState<Array<{
    id: string;
    title: string;
    institution: string;
    duration: string;
    completion_date: string;
  }>>([]);

  const [achievements, setAchievements] = useState<Array<{
    id: string;
    title: string;
    issuer: string;
    year: string;
    description: string;
  }>>([]);

  const [languages, setLanguages] = useState<Array<{
    id: string;
    language: string;
    proficiency: string;
  }>>([]);

  const [careerPreferences, setCareerPreferences] = useState<{
    desired_roles?: string[];
    work_mode?: string;
    target_locations?: string[];
    expected_salary?: string;
  }>({
    desired_roles: [],
    work_mode: 'Hybrid',
    target_locations: [],
    expected_salary: '',
  });

  const [desiredRoleInput, setDesiredRoleInput] = useState('');

  // Collapsible accordion sections for ease of navigation
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    basic: true,
    skills: true,
    education: true,
    experience: true,
    projects: false,
    certifications: false,
    courses: false,
    achievements: false,
    languages: false,
    career: false,
  });

  const toggleSection = (sec: string) => {
    setOpenSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  // Load existing profile from backend
  const loadProfileData = async () => {
    setLoading(true);
    try {
      const [profileData, userMe] = await Promise.all([
        candidateApi.getProfile(),
        userApi.getMe().catch(() => null),
      ]);

      if (userMe?.email) {
        setRegisteredEmail(userMe.email);
      }
      if (userMe?.username) {
        setUsername(userMe.username);
        setInitialUsername(userMe.username);
      }

      if (profileData) {
        setFirstName(profileData.first_name || '');
        setLastName(profileData.last_name || '');
        setHeadline(profileData.headline || '');
        setBio(profileData.bio || '');
        setLocation(profileData.preferred_location || '');
        setAvatarUrl(profileData.profile_photo_path || '');
        setCoverUrl(profileData.cover_photo_path || '');
        setCompletionPercentage(profileData.profile_completion_percentage || 0);

        if (Array.isArray(profileData.education)) setEducation(profileData.education);
        if (Array.isArray(profileData.experience)) setExperience(profileData.experience);
        if (Array.isArray(profileData.projects)) setProjects(profileData.projects);
        if (Array.isArray(profileData.certifications)) setCertifications(profileData.certifications);
        if (Array.isArray(profileData.courses_completed)) setCoursesCompleted(profileData.courses_completed);
        if (Array.isArray(profileData.achievements)) setAchievements(profileData.achievements);
        if (Array.isArray(profileData.languages)) setLanguages(profileData.languages);
        if (profileData.career_preferences && typeof profileData.career_preferences === 'object') {
          setCareerPreferences(profileData.career_preferences);
        }
      }

      // Load skills
      const liveSkills = await candidateApi.getSkills();
      if (liveSkills && liveSkills.length > 0) {
        setSkills(liveSkills.map((s: any) => s.skill?.name || s.name || s.skill_id || s));
      }
    } catch {
      // Keep empty fields empty
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfileData();
  }, []);

  // Avatar file upload
  const handleAvatarFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAvatarUploading(true);
    setFeedback(null);
    try {
      const res = await userApi.uploadAvatar(file);
      if (res.avatar_url || res.url) {
        setAvatarUrl(res.avatar_url || res.url);
        setFeedback({ type: 'success', message: 'Profile photo updated successfully!' });
        await refreshUser();
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Failed to upload profile photo.' });
    } finally {
      setAvatarUploading(false);
      if (avatarInputRef.current) avatarInputRef.current.value = '';
    }
  };

  // Cover file upload
  const handleCoverFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setCoverUploading(true);
    setFeedback(null);
    try {
      const res = await userApi.uploadCover(file);
      if (res.cover_url || res.url) {
        setCoverUrl(res.cover_url || res.url);
        setFeedback({ type: 'success', message: 'Cover banner updated successfully!' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Failed to upload cover banner.' });
    } finally {
      setCoverUploading(false);
      if (coverInputRef.current) coverInputRef.current.value = '';
    }
  };

  // Add Skill
  const handleAddSkill = () => {
    const val = skillInput.trim();
    if (val && !skills.includes(val)) {
      setSkills([...skills, val]);
      setSkillInput('');
    }
  };

  // Remove Skill
  const handleRemoveSkill = (idx: number) => {
    setSkills(skills.filter((_, i) => i !== idx));
  };

  // Add Education
  const handleAddEducation = () => {
    setEducation([
      ...education,
      {
        id: `edu_${Date.now()}`,
        institution: '',
        degree: '',
        field_of_study: '',
        start_date: '',
        end_date: '',
        grade: '',
      },
    ]);
  };

  // Add Experience
  const handleAddExperience = () => {
    setExperience([
      ...experience,
      {
        id: `exp_${Date.now()}`,
        title: '',
        organization: '',
        employment_type: 'Full-time',
        location: '',
        start_date: '',
        end_date: '',
        description: '',
      },
    ]);
  };

  // Add Project
  const handleAddProject = () => {
    setProjects([
      ...projects,
      {
        id: `proj_${Date.now()}`,
        title: '',
        description: '',
        tags: [],
        link: '',
      },
    ]);
  };

  // Add Certification
  const handleAddCertification = () => {
    setCertifications([
      ...certifications,
      {
        id: `cert_${Date.now()}`,
        title: '',
        issuer: '',
        issue_date: '',
        credential_id: '',
        url: '',
      },
    ]);
  };

  // Add Course Completed
  const handleAddCourse = () => {
    setCoursesCompleted([
      ...coursesCompleted,
      {
        id: `course_${Date.now()}`,
        title: '',
        institution: '',
        duration: '',
        completion_date: '',
      },
    ]);
  };

  // Add Achievement
  const handleAddAchievement = () => {
    setAchievements([
      ...achievements,
      {
        id: `ach_${Date.now()}`,
        title: '',
        issuer: '',
        year: '',
        description: '',
      },
    ]);
  };

  // Add Language
  const handleAddLanguage = () => {
    setLanguages([
      ...languages,
      {
        id: `lang_${Date.now()}`,
        language: '',
        proficiency: 'Intermediate',
      },
    ]);
  };

  // Add Desired Role
  const handleAddDesiredRole = () => {
    const val = desiredRoleInput.trim();
    const curr = careerPreferences.desired_roles || [];
    if (val && !curr.includes(val)) {
      setCareerPreferences({
        ...careerPreferences,
        desired_roles: [...curr, val],
      });
      setDesiredRoleInput('');
    }
  };

  // SAVE ALL TO DATABASE
  const handleSaveProfile = async () => {
    setSaving(true);
    setFeedback(null);

    const cleanUsername = username.trim().replace(/^@/, '');
    if (cleanUsername && cleanUsername !== initialUsername) {
      try {
        await userApi.updateUsername(cleanUsername);
        setInitialUsername(cleanUsername);
        setUsername(cleanUsername);
      } catch (err: any) {
        setFeedback({
          type: 'error',
          message: err.response?.data?.detail || err.message || 'Failed to update username. It may be taken.',
        });
        setSaving(false);
        return;
      }
    }

    const payload = {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      headline: headline.trim(),
      bio: bio.trim(),
      preferred_location: location.trim(),
      skills: skills,
      education: education.filter((e) => e.institution.trim() || e.degree.trim()),
      experience: experience.filter((e) => e.title.trim() || e.organization.trim()),
      projects: projects.filter((p) => p.title.trim()),
      certifications: certifications.filter((c) => c.title.trim()),
      courses_completed: coursesCompleted.filter((c) => c.title.trim()),
      achievements: achievements.filter((a) => a.title.trim()),
      languages: languages.filter((l) => l.language.trim()),
      career_preferences: careerPreferences,
    };

    try {
      const res = await candidateApi.updateProfile(payload);
      if (res && res.profile_completion_percentage !== undefined) {
        setCompletionPercentage(res.profile_completion_percentage);
      }
      await refreshUser();
      setFeedback({
        type: 'success',
        message: 'Profile successfully updated and synchronized to registry!',
      });
      if (onSaved) onSaved();
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to save profile changes.',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center space-y-3">
          <Loader2 className="w-8 h-8 text-teal-600 animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-medium">Loading profile management...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
            Profile Management & Verification
          </h2>
          <p className="text-xs text-slate-500">
            Keep your credentials, employment history, and professional profile up to date.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Completion Score pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-teal-50 border border-teal-200">
            <span className="text-[11px] font-bold text-teal-800">
              Completion: {completionPercentage}%
            </span>
            <div className="w-16 h-2 bg-teal-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-600 rounded-full transition-all duration-300"
                style={{ width: `${completionPercentage}%` }}
              />
            </div>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={handleSaveProfile}
            disabled={saving}
            className="text-xs font-semibold py-2 px-4 shadow-2xs bg-teal-600 hover:bg-teal-700 text-white"
            leftIcon={saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
          >
            {saving ? 'Saving...' : 'Save Profile'}
          </Button>

          {isModal && onClose && (
            <Button variant="outline" size="sm" onClick={onClose} className="text-xs">
              Close
            </Button>
          )}
        </div>
      </div>

      {feedback && (
        <div
          className={`p-3.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 animate-in fade-in ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border border-rose-200 text-rose-800'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* 1. MEDIA ASSETS (PHOTO & COVER BANNER) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            1. Visual Assets (Profile Photo & Banner)
          </span>
        </div>

        {/* Cover Preview & Uploader */}
        <div className="relative h-36 sm:h-44 bg-slate-800 overflow-hidden">
          {coverUrl ? (
            <img
              src={resolveMediaUrl(coverUrl)}
              alt="Cover preview"
              className="w-full h-full object-cover opacity-80"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-400 text-xs">
              No cover banner uploaded
            </div>
          )}

          <input
            type="file"
            ref={coverInputRef}
            onChange={handleCoverFileChange}
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
          />

          <button
            onClick={() => coverInputRef.current?.click()}
            disabled={coverUploading}
            className="absolute top-3 right-3 px-2.5 py-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white text-xs font-medium flex items-center gap-1.5 transition backdrop-blur-xs"
          >
            {coverUploading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <ImageIcon className="w-3.5 h-3.5" />
            )}
            <span>{coverUrl ? 'Change Cover' : 'Upload Cover'}</span>
          </button>
        </div>

        {/* Avatar Preview & Uploader */}
        <div className="p-5 pt-0 relative flex flex-col sm:flex-row sm:items-end justify-between gap-4 -mt-12">
          <div className="flex items-end gap-3">
            <div className="relative inline-block">
              {avatarUrl ? (
                <img
                  src={resolveMediaUrl(avatarUrl)}
                  alt="Avatar"
                  className="w-24 h-24 rounded-full object-cover border-4 border-white shadow-md bg-white ring-2 ring-slate-200"
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-slate-100 border-4 border-white shadow-md flex items-center justify-center text-slate-400 ring-2 ring-slate-200">
                  <User className="w-10 h-10" />
                </div>
              )}

              <input
                type="file"
                ref={avatarInputRef}
                onChange={handleAvatarFileChange}
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
              />

              <button
                onClick={() => avatarInputRef.current?.click()}
                disabled={avatarUploading}
                className="absolute bottom-0 right-0 p-2 rounded-full bg-teal-600 hover:bg-teal-700 text-white shadow-md border-2 border-white transition"
                title="Upload Photo"
              >
                {avatarUploading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Camera className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            <div className="pb-1">
              <h3 className="text-sm font-bold text-slate-900">Profile Photo</h3>
              <p className="text-[11px] text-slate-400">
                Recommended PNG or JPG, max 5MB. Anchored to public verification.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 2. BASIC IDENTITY (HEADLINE, BIO, LOCATION, REGISTERED EMAIL) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('basic')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            2. Basic Identity & Location
          </span>
          {openSections.basic ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.basic && (
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <InputField
                label="First Name"
                placeholder="e.g. Rajesh"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
              <InputField
                label="Last Name"
                placeholder="e.g. Kumar"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Public Username / Handle
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-xs font-semibold text-slate-400">@</span>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))}
                    placeholder="rajeshkumar"
                    className="w-full pl-7 pr-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800 font-mono"
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Your profile URL: /profile/@{username || 'handle'}
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Registered Account Email
                </label>
                <input
                  type="text"
                  disabled
                  value={registeredEmail}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 bg-slate-100 text-slate-500 cursor-not-allowed font-mono"
                />
                <p className="text-[10px] text-slate-400 mt-1">
                  Masked for external public viewers per privacy rules.
                </p>
              </div>
            </div>

            <InputField
              label="Professional Headline"
              placeholder="e.g. Certified Full Stack Developer | NSQF Level 6"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              helperText="Brief summary appearing right below your name on search and profile."
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Executive Bio / Professional Summary
              </label>
              <textarea
                rows={3}
                placeholder="Share your vocational background, technical expertise, and career aspirations..."
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800"
              />
            </div>

            <div>
              <InputField
                label="Location"
                placeholder="e.g. Bengaluru, Karnataka"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* 3. SKILLS */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('skills')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            3. Skills & Competencies ({skills.length})
          </span>
          {openSections.skills ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.skills && (
          <div className="p-5 space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Add a new skill (e.g. Python, CNC Machining, React)..."
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddSkill();
                  }
                }}
                className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddSkill}
                className="text-xs"
                leftIcon={<Plus className="w-3.5 h-3.5" />}
              >
                Add Skill
              </Button>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              {skills.map((sk, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 text-teal-800 border border-teal-200 text-xs font-medium"
                >
                  {sk}
                  <button
                    onClick={() => handleRemoveSkill(idx)}
                    className="hover:text-rose-600 transition"
                  >
                    &times;
                  </button>
                </span>
              ))}
              {skills.length === 0 && (
                <p className="text-xs text-slate-400 italic">No skills listed yet.</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 4. EDUCATION */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('education')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            4. Education & Academic Background ({education.length})
          </span>
          {openSections.education ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.education && (
          <div className="p-5 space-y-4">
            {education.map((edu, idx) => (
              <div key={edu.id || idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 relative">
                <button
                  onClick={() => setEducation(education.filter((_, i) => i !== idx))}
                  className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1"
                  title="Remove"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-8">
                  <InputField
                    label="Institution / College / School"
                    placeholder="e.g. Government Polytechnic, Delhi"
                    value={edu.institution}
                    onChange={(e) => {
                      const upd = [...education];
                      upd[idx].institution = e.target.value;
                      setEducation(upd);
                    }}
                  />
                  <InputField
                    label="Degree / Diploma"
                    placeholder="e.g. Diploma in Electrical Engineering"
                    value={edu.degree}
                    onChange={(e) => {
                      const upd = [...education];
                      upd[idx].degree = e.target.value;
                      setEducation(upd);
                    }}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <InputField
                    label="Field of Study"
                    placeholder="e.g. Power Systems"
                    value={edu.field_of_study}
                    onChange={(e) => {
                      const upd = [...education];
                      upd[idx].field_of_study = e.target.value;
                      setEducation(upd);
                    }}
                  />
                  <InputField
                    label="Start Date"
                    type="date"
                    value={edu.start_date}
                    onChange={(e) => {
                      const upd = [...education];
                      upd[idx].start_date = e.target.value;
                      setEducation(upd);
                    }}
                  />
                  <InputField
                    label="End Date"
                    type="date"
                    value={edu.end_date}
                    onChange={(e) => {
                      const upd = [...education];
                      upd[idx].end_date = e.target.value;
                      setEducation(upd);
                    }}
                  />
                </div>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={handleAddEducation}
              className="text-xs"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Education Record
            </Button>
          </div>
        )}
      </div>

      {/* 5. EXPERIENCE & APPRENTICESHIPS */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('experience')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            5. Work Experience & Apprenticeships ({experience.length})
          </span>
          {openSections.experience ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.experience && (
          <div className="p-5 space-y-4">
            {experience.map((exp, idx) => (
              <div key={exp.id || idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 relative">
                <button
                  onClick={() => setExperience(experience.filter((_, i) => i !== idx))}
                  className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1"
                  title="Remove"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-8">
                  <InputField
                    label="Job / Apprenticeship Title"
                    placeholder="e.g. Junior Systems Technician"
                    value={exp.title}
                    onChange={(e) => {
                      const upd = [...experience];
                      upd[idx].title = e.target.value;
                      setExperience(upd);
                    }}
                  />
                  <InputField
                    label="Company / Organization"
                    placeholder="e.g. Bharat Heavy Electricals Ltd."
                    value={exp.organization}
                    onChange={(e) => {
                      const upd = [...experience];
                      upd[idx].organization = e.target.value;
                      setExperience(upd);
                    }}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Employment Type
                    </label>
                    <select
                      value={exp.employment_type}
                      onChange={(e) => {
                        const upd = [...experience];
                        upd[idx].employment_type = e.target.value;
                        setExperience(upd);
                      }}
                      className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800"
                    >
                      <option value="Full-time">Full-time</option>
                      <option value="Apprenticeship">Apprenticeship</option>
                      <option value="Internship">Internship</option>
                      <option value="Contract">Contract</option>
                    </select>
                  </div>
                  <InputField
                    label="Start Date"
                    type="date"
                    value={exp.start_date}
                    onChange={(e) => {
                      const upd = [...experience];
                      upd[idx].start_date = e.target.value;
                      setExperience(upd);
                    }}
                  />
                  <InputField
                    label="End Date"
                    type="date"
                    value={exp.end_date}
                    onChange={(e) => {
                      const upd = [...experience];
                      upd[idx].end_date = e.target.value;
                      setExperience(upd);
                    }}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Responsibilities & Impact
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Key responsibilities, machines handled, software tools..."
                    value={exp.description}
                    onChange={(e) => {
                      const upd = [...experience];
                      upd[idx].description = e.target.value;
                      setExperience(upd);
                    }}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800"
                  />
                </div>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={handleAddExperience}
              className="text-xs"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Experience Record
            </Button>
          </div>
        )}
      </div>

      {/* 6. PROJECTS */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('projects')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            6. Technical Projects ({projects.length})
          </span>
          {openSections.projects ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.projects && (
          <div className="p-5 space-y-4">
            {projects.map((proj, idx) => (
              <div key={proj.id || idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 relative">
                <button
                  onClick={() => setProjects(projects.filter((_, i) => i !== idx))}
                  className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1"
                  title="Remove"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-8">
                  <InputField
                    label="Project Title"
                    placeholder="e.g. Automated Solar Tracking Inverter"
                    value={proj.title}
                    onChange={(e) => {
                      const upd = [...projects];
                      upd[idx].title = e.target.value;
                      setProjects(upd);
                    }}
                  />
                  <InputField
                    label="Project Link / Demo"
                    placeholder="e.g. https://github.com/..."
                    value={proj.link || ''}
                    onChange={(e) => {
                      const upd = [...projects];
                      upd[idx].link = e.target.value;
                      setProjects(upd);
                    }}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Project Description
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Architecture, algorithms, technologies employed..."
                    value={proj.description}
                    onChange={(e) => {
                      const upd = [...projects];
                      upd[idx].description = e.target.value;
                      setProjects(upd);
                    }}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800"
                  />
                </div>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={handleAddProject}
              className="text-xs"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Project
            </Button>
          </div>
        )}
      </div>

      {/* 7. CERTIFICATIONS & COURSES */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('certifications')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            7. Certifications & Courses ({certifications.length + coursesCompleted.length})
          </span>
          {openSections.certifications ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.certifications && (
          <div className="p-5 space-y-4">
            {certifications.map((c, idx) => (
              <div key={c.id || idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 relative">
                <button
                  onClick={() => setCertifications(certifications.filter((_, i) => i !== idx))}
                  className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1"
                  title="Remove"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-8">
                  <InputField
                    label="Certificate Title"
                    placeholder="e.g. AWS Certified Solutions Architect"
                    value={c.title}
                    onChange={(e) => {
                      const upd = [...certifications];
                      upd[idx].title = e.target.value;
                      setCertifications(upd);
                    }}
                  />
                  <InputField
                    label="Issuing Organization"
                    placeholder="e.g. Amazon Web Services"
                    value={c.issuer}
                    onChange={(e) => {
                      const upd = [...certifications];
                      upd[idx].issuer = e.target.value;
                      setCertifications(upd);
                    }}
                  />
                </div>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={handleAddCertification}
              className="text-xs"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Certification
            </Button>

            {/* Courses Completed */}
            <div className="pt-4 border-t border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-slate-800">Courses Completed</h4>
              {coursesCompleted.map((crs, idx) => (
                <div key={crs.id || idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 relative">
                  <button
                    onClick={() => setCoursesCompleted(coursesCompleted.filter((_, i) => i !== idx))}
                    className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1"
                    title="Remove"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-8">
                    <InputField
                      label="Course Name"
                      placeholder="e.g. Machine Learning Specialization"
                      value={crs.title}
                      onChange={(e) => {
                        const upd = [...coursesCompleted];
                        upd[idx].title = e.target.value;
                        setCoursesCompleted(upd);
                      }}
                    />
                    <InputField
                      label="Institution / Platform"
                      placeholder="e.g. Stanford Online / Coursera"
                      value={crs.institution}
                      onChange={(e) => {
                        const upd = [...coursesCompleted];
                        upd[idx].institution = e.target.value;
                        setCoursesCompleted(upd);
                      }}
                    />
                  </div>
                </div>
              ))}

              <Button
                variant="outline"
                size="sm"
                onClick={handleAddCourse}
                className="text-xs"
                leftIcon={<Plus className="w-3.5 h-3.5" />}
              >
                Add Course
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 8. ACHIEVEMENTS & LANGUAGES */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('languages')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            8. Languages & Honors ({languages.length + achievements.length})
          </span>
          {openSections.languages ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.languages && (
          <div className="p-5 space-y-4">
            <h4 className="text-xs font-bold text-slate-800">Spoken Languages</h4>
            {languages.map((l, idx) => (
              <div key={l.id || idx} className="flex items-center gap-3">
                <input
                  type="text"
                  placeholder="e.g. English, Hindi, Tamil"
                  value={l.language}
                  onChange={(e) => {
                    const upd = [...languages];
                    upd[idx].language = e.target.value;
                    setLanguages(upd);
                  }}
                  className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
                <select
                  value={l.proficiency}
                  onChange={(e) => {
                    const upd = [...languages];
                    upd[idx].proficiency = e.target.value;
                    setLanguages(upd);
                  }}
                  className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white"
                >
                  <option value="Beginner">Beginner</option>
                  <option value="Intermediate">Intermediate</option>
                  <option value="Fluent">Fluent</option>
                  <option value="Native">Native</option>
                </select>
                <button
                  onClick={() => setLanguages(languages.filter((_, i) => i !== idx))}
                  className="text-slate-400 hover:text-rose-600 p-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            <Button
              variant="outline"
              size="sm"
              onClick={handleAddLanguage}
              className="text-xs"
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add Language
            </Button>

            {/* Achievements & Honors */}
            <div className="pt-4 border-t border-slate-200 space-y-3">
              <h4 className="text-xs font-bold text-slate-800">Achievements & Honors</h4>
              {achievements.map((ach, idx) => (
                <div key={ach.id || idx} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50 space-y-3 relative">
                  <button
                    onClick={() => setAchievements(achievements.filter((_, i) => i !== idx))}
                    className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1"
                    title="Remove"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pr-8">
                    <InputField
                      label="Title / Honor"
                      placeholder="e.g. Smart India Hackathon Winner"
                      value={ach.title}
                      onChange={(e) => {
                        const upd = [...achievements];
                        upd[idx].title = e.target.value;
                        setAchievements(upd);
                      }}
                    />
                    <InputField
                      label="Issuing Body / Year"
                      placeholder="e.g. AICTE / Ministry of Education (2024)"
                      value={ach.issuer}
                      onChange={(e) => {
                        const upd = [...achievements];
                        upd[idx].issuer = e.target.value;
                        setAchievements(upd);
                      }}
                    />
                  </div>
                </div>
              ))}

              <Button
                variant="outline"
                size="sm"
                onClick={handleAddAchievement}
                className="text-xs"
                leftIcon={<Plus className="w-3.5 h-3.5" />}
              >
                Add Achievement
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 9. CAREER PREFERENCES */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <button
          onClick={() => toggleSection('career')}
          className="w-full p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-left"
        >
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            9. Career Preferences
          </span>
          {openSections.career ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {openSections.career && (
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Preferred Work Mode
                </label>
                <select
                  value={careerPreferences.work_mode || 'Hybrid'}
                  onChange={(e) =>
                    setCareerPreferences({ ...careerPreferences, work_mode: e.target.value })
                  }
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800"
                >
                  <option value="On-site">On-site</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="Remote">Remote</option>
                </select>
              </div>

              <InputField
                label="Target Expected CTC / Stipend"
                placeholder="e.g. ₹5,00,000 LPA or ₹25,000/month"
                value={careerPreferences.expected_salary || ''}
                onChange={(e) =>
                  setCareerPreferences({ ...careerPreferences, expected_salary: e.target.value })
                }
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Target Roles / Titles
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  placeholder="e.g. Mechanical Engineer, CNC Operator..."
                  value={desiredRoleInput}
                  onChange={(e) => setDesiredRoleInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddDesiredRole();
                    }
                  }}
                  className="flex-1 px-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAddDesiredRole}
                  className="text-xs"
                >
                  Add Role
                </Button>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {(careerPreferences.desired_roles || []).map((role, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 text-xs font-medium border border-slate-200"
                  >
                    {role}
                    <button
                      onClick={() =>
                        setCareerPreferences({
                          ...careerPreferences,
                          desired_roles: (careerPreferences.desired_roles || []).filter(
                            (_, i) => i !== idx
                          ),
                        })
                      }
                      className="hover:text-rose-600 ml-1"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Save Bar */}
      <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs flex items-center justify-between">
        <p className="text-xs text-slate-500">
          All changes are anchored in PostgreSQL and immediately updated across the platform.
        </p>
        <Button
          variant="primary"
          size="sm"
          onClick={handleSaveProfile}
          disabled={saving}
          className="text-xs font-semibold py-2 px-5 bg-teal-600 hover:bg-teal-700 text-white"
          leftIcon={saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
        >
          {saving ? 'Saving...' : 'Save Profile'}
        </Button>
      </div>
    </div>
  );
};

export default ProfileManagementSection;
