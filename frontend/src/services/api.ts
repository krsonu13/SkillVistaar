import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  AccountType,
  AuthResponse,
  AuthUser,
  LoginPayload,
  normalizeAccountType,
  OtpVerificationPayload,
  SignupPayload,
} from '../types/auth';
import {
  OrgDocument,
  OrgDocumentCreatePayload,
  PendingVerificationDocument,
} from '../types/document';

// ---------------------------------------------------------------------------
// Base URL configuration (Supports direct backend URL or Vite proxy)
// ---------------------------------------------------------------------------
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

// ---------------------------------------------------------------------------
// Unified Axios Client Instance
// ---------------------------------------------------------------------------
export const axiosClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

// Request Interceptor: Attach JWT Bearer Token if present
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('sv_auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Unified error extraction and 401 handling
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

axiosClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized token expiry with refresh attempt
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      const refreshToken = localStorage.getItem('sv_refresh_token');
      if (refreshToken) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return axiosClient(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const refreshRes = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newToken =
            refreshRes.data.access_token || refreshRes.data.token;
          if (newToken) {
            localStorage.setItem('sv_auth_token', newToken);
            if (refreshRes.data.refresh_token) {
              localStorage.setItem('sv_refresh_token', refreshRes.data.refresh_token);
            }
            axiosClient.defaults.headers.common.Authorization = `Bearer ${newToken}`;
            processQueue(null, newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return axiosClient(originalRequest);
          }
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          localStorage.removeItem('sv_auth_token');
          localStorage.removeItem('sv_refresh_token');
          localStorage.removeItem('sv_user');
          // Silently let caller handle authentication failure
        } finally {
          isRefreshing = false;
        }
      }
    }

    // Extract FastAPI detail or human-readable message
    const detail = error.response?.data?.detail;
    let message = 'An unexpected network error occurred';
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail) && detail.length > 0) {
      message = detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ');
    } else if (typeof detail === 'object' && detail !== null) {
      message = detail.msg || detail.message || JSON.stringify(detail);
    } else {
      message =
        error.response?.data?.message ||
        error.response?.data?.error ||
        error.message ||
        message;
    }

    const enhancedError: any = new Error(message);
    enhancedError.status = error.response?.status;
    enhancedError.response = error.response;
    return Promise.reject(enhancedError);
  }
);

// ---------------------------------------------------------------------------
// Helper: Normalize paginated or array responses
// ---------------------------------------------------------------------------
export function normalizeList<T>(data: any): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.applications)) return data.applications;
  return [];
}

// ---------------------------------------------------------------------------
// Type Definitions
// ---------------------------------------------------------------------------
export interface CandidateSkillRecord {
  id: string;
  candidate_profile_id?: string;
  skill_id: string;
  skill_name?: string;
  proficiency_level?: string;
  years_of_experience?: number;
  is_primary?: boolean;
  status: string;
  notes?: string;
  created_at: string;
}

export interface CandidateCredentialRecord {
  id: string;
  candidate_profile_id?: string;
  credential_type: string;
  title: string;
  issuer_name: string;
  issued_date?: string;
  status: string;
  verification_hash?: string;
  document_url?: string;
  created_at: string;
}

export interface LiveJob {
  id: string;
  organization_id?: string;
  title: string;
  description?: string;
  department?: string;
  location?: string;
  employment_type?: string;
  type?: string;
  salary_min?: number;
  salary_max?: number;
  openings?: number;
  openings_count?: number;
  experience_level?: string;
  required_skills?: string[];
  status: string;
  organization_name?: string;
  applicant_count?: number;
  created_at: string;
}

export interface LiveJobApplication {
  id: string;
  job_id: string;
  candidate_user_id: string;
  applicant_name?: string;
  candidate_name?: string;
  applicant_headline?: string;
  applicant_email?: string;
  applicant_phone?: string;
  status: string;
  cover_letter?: string;
  job_title?: string;
  match_score?: number;
  organization_name?: string;
  created_at: string;
}

export interface LiveCourse {
  id: string;
  institution_id?: string;
  title: string;
  description?: string;
  level?: string;
  duration_weeks?: number;
  status: string;
  institution_name?: string;
  enrolled_count?: number;
  created_at: string;
}

export interface LiveNotification {
  id: string;
  title: string;
  message?: string;
  notification_type?: string;
  is_read: boolean;
  created_at: string;
}

export interface GovtDashboardStats {
  unit?: {
    id: string;
    name: string;
    code: string;
    level: number;
    unit_type: string;
    status: string;
    jurisdiction?: string;
  };
  is_super_admin: boolean;
  authorized_jurisdiction_count: number;
  statistics: {
    total_employers: number;
    total_institutes: number;
    pending_verifications: number;
    approved_verifications: number;
    rejected_verifications: number;
    verified_skills: number;
    verified_credentials: number;
  };
  recent_alerts: Array<{
    id: string;
    title: string;
    level: string;
    timestamp: string;
  }>;
}

export interface GovtUnitNode {
  id: string;
  code: string;
  name: string;
  unit_type: string;
  level: number;
  status: string;
  jurisdiction?: string;
  parent_id?: string;
  children: GovtUnitNode[];
}

export interface AdminStats {
  users: {
    total: number;
    active: number;
    suspended: number;
    locked?: number;
    unverified?: number;
    by_type: Record<string, number>;
  };
  organizations?: {
    total: number;
    employers: number;
    institutes: number;
    verified: number;
    pending: number;
  };
  verifications?: {
    total_pending: number;
    by_tier: {
      central: number;
      state: number;
      district: number;
      local: number;
      employer: number;
      institute: number;
    };
  };
  government_units_count: number;
  organizations_count: number;
  warnings_count?: number;
  total_audit_logs: number;
  system_health?: {
    database: string;
    smtp_ready: boolean;
    smtp_message: string;
    sms_ready: boolean;
    sms_provider: string;
    sms_message: string;
  };
}

export interface PlatformUser {
  id: string;
  email?: string;
  phone?: string;
  account_type: string;
  entity_name?: string | null;
  is_active: boolean;
  is_suspended: boolean;
  is_locked?: boolean;
  locked_until?: string | null;
  failed_login_attempts?: number;
  email_verified: boolean;
  phone_verified: boolean;
  government_unit_id?: string | null;
  roles: string[];
  warnings_count?: number;
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface UserWarningRecord {
  id: string;
  user_id: string;
  admin_id: string;
  admin_email?: string;
  warning_title: string;
  warning_message: string;
  reason: string;
  severity: string;
  acknowledged_at?: string | null;
  created_at: string;
}

export interface PlatformConfigRecord {
  id: string;
  config_key: string;
  version: number;
  config_data: Record<string, any>;
  is_active: boolean;
  updated_by_user_id?: string | null;
  change_reason?: string | null;
  created_at: string;
}

export interface PlatformConfigHistoryItem {
  id: string;
  version: number;
  is_active: boolean;
  updated_by_user_id?: string | null;
  change_reason?: string | null;
  config_data: Record<string, any>;
  created_at: string;
}

export interface AuditLogRecord {
  id: string;
  actor_user_id?: string;
  actor_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  description?: string;
  ip_address?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface VerificationAppRecord {
  id: string;
  applicant_user_id: string;
  applicant_name?: string;
  applicant_email?: string;
  applicant_phone?: string;
  applicant_username?: string;
  applicant_entity_name?: string;
  organization_name?: string;
  verifier_user_id?: string | null;
  government_unit_id?: string | null;
  government_unit_name?: string | null;
  government_unit_level?: number | null;
  tier?: string;
  status: string;
  application_type: string;
  submitted_at?: string;
  submitted_data?: Record<string, any>;
  remarks?: string | null;
  rejection_reason?: string | null;
  documents?: any[];
  created_at: string;
  updated_at?: string;
}

export interface PublicPlatformStats {
  verified_candidates: number;
  hiring_employers: number;
  training_institutes: number;
  verified_credentials: number;
  active_jobs: number;
  verification_authority: string;
}

export interface LivePublicProfile {
  id: string;
  email?: string;
  account_type: string;
  is_active: boolean;
  is_verified?: boolean;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  name?: string;
  headline?: string;
  bio?: string;
  city?: string;
  state?: string;
  jurisdiction?: string;
  government_level?: string;
  nodal_officers_count?: number;
  annual_beneficiaries?: string;
  followers_count?: number;
  following_count?: number;
  skills?: Array<{ id: string; name: string; proficiency_level?: string; status?: string }>;
  credentials?: Array<{ id: string; title: string; issuer_name: string; credential_type: string; status: string }>;
  candidate_details?: {
    status?: string;
    verified_skills?: any[];
    self_declared_skills?: any[];
    credentials?: any[];
    education?: any[];
    experience?: any[];
    projects?: any[];
    certifications?: any[];
    courses_completed?: any[];
    achievements?: any[];
    languages?: any[];
    career_preferences?: any;
    digilocker_id_masked?: string;
  };
  jobs?: LiveJob[];
  courses?: LiveCourse[];
  organization?: {
    id: string;
    legal_name: string;
    display_name: string;
    organization_type: string;
    verification_status: string;
    website?: string;
    address?: string;
    industry?: string;
    company_size?: string;
    founded_year?: string | number;
    city?: string;
    state?: string;
    affiliation?: string;
    accreditation_code?: string;
    placement_rate?: string;
  };
}

// ---------------------------------------------------------------------------
// Authentication & Identity Services
// ---------------------------------------------------------------------------
export const authApi = {
  async login(payload: LoginPayload): Promise<AuthResponse> {
    const response = await axiosClient.post<AuthResponse>('/auth/login', {
      identifier: payload.identifier.trim(),
      password: payload.password,
    });
    const data = response.data;
    const token = data.access_token || data.token;
    if (token) localStorage.setItem('sv_auth_token', token);
    if (data.refresh_token) localStorage.setItem('sv_refresh_token', data.refresh_token);
    if (data.user) {
      const canonical = normalizeAccountType(data.user.account_type || (data.user as any).accountType);
      const normUser: AuthUser = {
        ...data.user,
        account_type: canonical,
        accountType: canonical,
        roles: data.user.roles || [canonical],
      };
      localStorage.setItem('sv_user', JSON.stringify(normUser));
      return { ...data, token, user: normUser };
    }
    return { ...data, token };
  },

  async signup(payload: SignupPayload): Promise<AuthResponse> {
    let email: string | undefined = undefined;
    if ('email' in payload && payload.email) email = payload.email.trim();
    else if ('officialEmail' in payload && payload.officialEmail) email = payload.officialEmail.trim();

    let phone: string | undefined = undefined;
    if ('phone' in payload && (payload as any).phone) phone = (payload as any).phone.trim();
    else if ('contactPhone' in payload && (payload as any).contactPhone) phone = (payload as any).contactPhone.trim();

    let fullName: string | undefined = undefined;
    if ('fullName' in payload && payload.fullName) fullName = payload.fullName.trim();
    else if ('nodalOfficerName' in payload && (payload as any).nodalOfficerName) fullName = (payload as any).nodalOfficerName.trim();

    const companyName = 'companyName' in payload ? payload.companyName : undefined;
    const instituteName = 'instituteName' in payload ? payload.instituteName : undefined;
    const departmentName = 'departmentName' in payload ? payload.departmentName : undefined;

    const backendPayload = {
      email: email || null,
      phone: phone || null,
      password: payload.password,
      account_type: normalizeAccountType(payload.accountType),
      fullName: fullName || companyName || instituteName || departmentName,
      companyName: companyName || null,
      instituteName: instituteName || null,
      departmentName: departmentName || null,
    };

    const response = await axiosClient.post<AuthResponse>('/auth/signup', backendPayload);
    return response.data;
  },

  async verifyOtp(payload: OtpVerificationPayload): Promise<AuthResponse> {
    const response = await axiosClient.post<AuthResponse>('/auth/verify-otp', {
      identifier: payload.identifier.trim(),
      otp: payload.otp.trim(),
      accountType: normalizeAccountType(payload.accountType),
    });
    const data = response.data;
    const token = data.access_token || data.token;
    if (token) localStorage.setItem('sv_auth_token', token);
    if (data.refresh_token) localStorage.setItem('sv_refresh_token', data.refresh_token);
    if (data.user) {
      const canonical = normalizeAccountType(data.user.account_type || (data.user as any).accountType);
      const normUser: AuthUser = {
        ...data.user,
        account_type: canonical,
        accountType: canonical,
        roles: data.user.roles || [canonical],
        isVerified: true,
      };
      localStorage.setItem('sv_user', JSON.stringify(normUser));
      return { ...data, token, user: normUser };
    }
    return data;
  },

  async startSignupVerification(
    accountType: string,
    channel: 'EMAIL' | 'PHONE',
    identifier: string
  ): Promise<{
    session_token: string;
    channel: string;
    identifier: string;
    expires_in_seconds: number;
    message: string;
    dev_otp?: string | null;
  }> {
    const res = await axiosClient.post('/auth/signup/start-verification', {
      account_type: normalizeAccountType(accountType),
      channel,
      identifier: identifier.trim(),
    });
    return res.data;
  },

  async verifyPrimaryContact(sessionToken: string, otp: string) {
    const res = await axiosClient.post('/auth/signup/verify-primary', {
      session_token: sessionToken,
      otp: otp.trim(),
    });
    return res.data;
  },

  async sendSecondaryOtp(
    sessionToken: string,
    channel: 'EMAIL' | 'PHONE',
    identifier: string
  ): Promise<{
    session_token: string;
    channel: string;
    identifier: string;
    expires_in_seconds: number;
    message: string;
    dev_otp?: string | null;
  }> {
    const res = await axiosClient.post('/auth/signup/send-secondary-otp', {
      session_token: sessionToken,
      channel,
      identifier: identifier.trim(),
    });
    return res.data;
  },

  async verifySecondaryContact(sessionToken: string, otp: string) {
    const res = await axiosClient.post('/auth/signup/verify-secondary', {
      session_token: sessionToken,
      otp: otp.trim(),
    });
    return res.data;
  },

  async completeSignup(
    sessionToken: string,
    password: string,
    termsAccepted: boolean,
    additionalData: Record<string, any>
  ): Promise<AuthResponse> {
    const res = await axiosClient.post<AuthResponse>('/auth/signup/complete', {
      session_token: sessionToken,
      password,
      terms_accepted: termsAccepted,
      additional_data: additionalData,
    });
    const data = res.data;
    const token = data.access_token || data.token;
    if (token) localStorage.setItem('sv_auth_token', token);
    if (data.refresh_token) localStorage.setItem('sv_refresh_token', data.refresh_token);
    if (data.user) {
      const canonical = normalizeAccountType(data.user.account_type || (data.user as any).accountType);
      const normUser: AuthUser = {
        ...data.user,
        account_type: canonical,
        accountType: canonical,
        roles: data.user.roles || [canonical],
      };
      localStorage.setItem('sv_user', JSON.stringify(normUser));
      return { ...data, token, user: normUser };
    }
    return data;
  },

  async resendOtp(identifier: string, accountType: AccountType) {
    const res = await axiosClient.post('/auth/resend-otp', {
      identifier: identifier.trim(),
      accountType: normalizeAccountType(accountType),
    });
    return res.data;
  },

  async forgotPassword(identifier: string, accountType: AccountType) {
    const res = await axiosClient.post('/auth/forgot-password', {
      identifier: identifier.trim(),
      accountType: normalizeAccountType(accountType),
    });
    return res.data;
  },

  async changePassword(currentPassword: string, newPassword: string) {
    const res = await axiosClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return res.data;
  },

  async getMe(): Promise<AuthUser> {
    const res = await axiosClient.get<AuthUser>('/auth/me');
    const user = res.data;
    const canonical = normalizeAccountType(user.account_type || (user as any).accountType);
    const normUser: AuthUser = {
      ...user,
      account_type: canonical,
      accountType: canonical,
      roles: user.roles || [canonical],
    };
    localStorage.setItem('sv_user', JSON.stringify(normUser));
    return normUser;
  },

  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('sv_refresh_token');
    if (refreshToken) {
      try {
        await axiosClient.post('/auth/logout', { refresh_token: refreshToken });
      } catch {
        // Continue clearing storage
      }
    }
    localStorage.removeItem('sv_auth_token');
    localStorage.removeItem('sv_refresh_token');
    localStorage.removeItem('sv_user');
  },
};

// ---------------------------------------------------------------------------
// Candidate Services
// ---------------------------------------------------------------------------
export const candidateApi = {
  async getProfile() {
    try {
      const res = await axiosClient.get('/candidates/me/profile');
      return res.data;
    } catch {
      return null;
    }
  },

  async updateProfile(payload: any) {
    const res = await axiosClient.put('/candidates/me/profile', payload);
    return res.data;
  },

  async getSkills(): Promise<CandidateSkillRecord[]> {
    try {
      const res = await axiosClient.get('/candidates/me/skills');
      return normalizeList<CandidateSkillRecord>(res.data);
    } catch {
      try {
        const res = await axiosClient.get('/candidate/skills');
        return normalizeList<CandidateSkillRecord>(res.data);
      } catch {
        return [];
      }
    }
  },

  async addSkill(payload: {
    skill_id: string;
    proficiency_level?: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT';
    years_of_experience?: number;
    is_primary?: boolean;
    notes?: string;
  }) {
    const res = await axiosClient.post('/candidate/skills', {
      skill_id: payload.skill_id,
      proficiency_level: payload.proficiency_level || 'INTERMEDIATE',
      years_of_experience: payload.years_of_experience || 1,
      is_primary: payload.is_primary || false,
    });
    return res.data;
  },

  async requestSkillVerification(candidateSkillId: string) {
    const res = await axiosClient.post(`/candidate/skills/${candidateSkillId}/request-verification`);
    return res.data;
  },

  async getCredentials(): Promise<CandidateCredentialRecord[]> {
    try {
      const res = await axiosClient.get('/candidates/me/credentials');
      return normalizeList<CandidateCredentialRecord>(res.data);
    } catch {
      try {
        const res = await axiosClient.get('/candidate/credentials');
        return normalizeList<CandidateCredentialRecord>(res.data);
      } catch {
        return [];
      }
    }
  },

  async addCredential(payload: {
    credential_type: string;
    title: string;
    issuer_name: string;
    issued_date?: string;
    document_url?: string;
  }) {
    const res = await axiosClient.post('/candidates/me/credentials', payload);
    return res.data;
  },

  async requestCredentialVerification(credentialId: string) {
    const res = await axiosClient.post(`/candidate/credentials/${credentialId}/request-verification`);
    return res.data;
  },

  async getApplications(): Promise<LiveJobApplication[]> {
    try {
      const res = await axiosClient.get('/applications/mine');
      return normalizeList<LiveJobApplication>(res.data);
    } catch {
      return [];
    }
  },

  async applyForJob(jobId: string, payload: {
    cover_letter?: string;
    resume_document_id?: string;
    consent_to_share_profile?: boolean;
  }) {
    const res = await axiosClient.post(`/applications/jobs/${jobId}`, payload);
    return res.data;
  },

  async withdrawApplication(applicationId: string) {
    const res = await axiosClient.post(`/applications/${applicationId}/withdraw`);
    return res.data;
  },

  async getRecommendedJobs(limit = 10): Promise<LiveJob[]> {
    try {
      const res = await axiosClient.get('/recommendations/jobs', { params: { limit } });
      return normalizeList<LiveJob>(res.data);
    } catch {
      return [];
    }
  },

  async getRecommendedCourses(limit = 10): Promise<LiveCourse[]> {
    try {
      const res = await axiosClient.get('/recommendations/courses', { params: { limit } });
      return normalizeList<LiveCourse>(res.data);
    } catch {
      return [];
    }
  },

  async getJobSkillGaps(jobId: string) {
    try {
      const res = await axiosClient.get(`/candidate/skill-gaps/job/${jobId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async getAssessmentInvitations() {
    try {
      const res = await axiosClient.get('/assessment-invitations/mine');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async startAssessmentAttempt(invitationId: string) {
    const res = await axiosClient.post('/assessment-attempts/start', { invitation_id: invitationId });
    return res.data;
  },

  async getAssessmentResults(attemptId: string) {
    const res = await axiosClient.get(`/assessment-results/candidate/${attemptId}`);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Employer Services
// ---------------------------------------------------------------------------
export const employerApi = {
  async getJobs(): Promise<LiveJob[]> {
    try {
      const res = await axiosClient.get('/jobs/me/organization');
      return normalizeList<LiveJob>(res.data);
    } catch {
      return [];
    }
  },

  async getJob(jobId: string): Promise<LiveJob | null> {
    try {
      const res = await axiosClient.get<LiveJob>(`/jobs/${jobId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async postJob(payload: {
    title: string;
    description: string;
    employment_type?: string;
    location?: string;
    salary_min?: number;
    salary_max?: number;
    openings?: number;
    skill_ids?: string[];
  }): Promise<LiveJob> {
    const res = await axiosClient.post<LiveJob>('/jobs', payload);
    return res.data;
  },

  async getDashboard() {
    try {
      const res = await axiosClient.get('/organizations/me/dashboard');
      return res.data;
    } catch {
      return null;
    }
  },

  async getProfile() {
    try {
      const res = await axiosClient.get('/organizations/me/profile');
      return res.data;
    } catch {
      return null;
    }
  },

  async updateProfile(payload: Record<string, any>) {
    const res = await axiosClient.patch('/organizations/me/profile', payload);
    return res.data;
  },

  async submitJobReview(jobId: string) {
    const res = await axiosClient.post(`/jobs/${jobId}/submit-review`);
    return res.data;
  },

  async publishJob(jobId: string) {
    const res = await axiosClient.post(`/jobs/${jobId}/publish`);
    return res.data;
  },

  async pauseJob(jobId: string) {
    const res = await axiosClient.post(`/jobs/${jobId}/pause`);
    return res.data;
  },

  async resumeJob(jobId: string) {
    const res = await axiosClient.post(`/jobs/${jobId}/resume`);
    return res.data;
  },

  async closeJob(jobId: string) {
    const res = await axiosClient.post(`/jobs/${jobId}/close`);
    return res.data;
  },

  async archiveJob(jobId: string) {
    const res = await axiosClient.post(`/jobs/${jobId}/archive`);
    return res.data;
  },

  async getApplications(): Promise<LiveJobApplication[]> {
    try {
      const res = await axiosClient.get('/applications/organization/mine');
      return normalizeList<LiveJobApplication>(res.data);
    } catch {
      return [];
    }
  },

  async updateApplicationStatus(applicationId: string, status: string, notes?: string) {
    const res = await axiosClient.patch(`/applications/${applicationId}/status`, {
      status,
      notes,
    });
    return res.data;
  },

  async getMatchingCandidates(jobId: string) {
    try {
      const res = await axiosClient.get(`/employer/matching/jobs/${jobId}/candidates`);
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getAssessments() {
    try {
      const res = await axiosClient.get('/assessments/');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async createAssessment(payload: {
    title: string;
    description?: string;
    duration_minutes?: number;
    pass_percentage?: number;
    questions?: Array<{ question_text: string; question_type: string; points: number }>;
  }) {
    const res = await axiosClient.post('/assessments/', payload);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Institution Services
// ---------------------------------------------------------------------------
export const institutionApi = {
  async getDashboard() {
    try {
      const res = await axiosClient.get('/institutions/me/dashboard');
      return res.data;
    } catch {
      return null;
    }
  },

  async getProfile() {
    try {
      const res = await axiosClient.get('/institutions/me/profile');
      return res.data;
    } catch {
      return null;
    }
  },

  async updateProfile(payload: Record<string, any>) {
    const res = await axiosClient.patch('/institutions/me/profile', payload);
    return res.data;
  },

  async getBatches() {
    try {
      const res = await axiosClient.get('/institutions/me/batches');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getEnrollments() {
    try {
      const res = await axiosClient.get('/institutions/me/enrollments');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getPlacements() {
    try {
      const res = await axiosClient.get('/institutions/me/placements');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getMarketDemand() {
    try {
      const res = await axiosClient.get('/institutions/me/market-demand');
      return res.data;
    } catch {
      return null;
    }
  },

  async getCourses(institutionId?: string): Promise<LiveCourse[]> {
    try {
      const url = institutionId ? `/courses/institutions/${institutionId}` : '/courses';
      const res = await axiosClient.get(url);
      return normalizeList<LiveCourse>(res.data);
    } catch {
      return [];
    }
  },

  async getCourse(courseId: string): Promise<LiveCourse | null> {
    try {
      const res = await axiosClient.get<LiveCourse>(`/courses/${courseId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async createCourse(payload: {
    title: string;
    description?: string;
    level?: string;
    duration_weeks?: number;
    organization_id?: string;
  }): Promise<LiveCourse> {
    const res = await axiosClient.post<LiveCourse>('/courses', payload);
    return res.data;
  },

  async getCourseAlignments(): Promise<any[]> {
    try {
      const res = await axiosClient.get('/course-alignments/');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getPlacementOutcomes(): Promise<any[]> {
    try {
      const res = await axiosClient.get('/placement-outcomes/');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },
};

// ---------------------------------------------------------------------------
// Government Services
// ---------------------------------------------------------------------------
export const governmentApi = {
  async getDashboard(): Promise<GovtDashboardStats | null> {
    try {
      const res = await axiosClient.get<GovtDashboardStats>('/government/dashboard');
      return res.data;
    } catch {
      return null;
    }
  },

  async getHierarchy(): Promise<GovtUnitNode[]> {
    try {
      const res = await axiosClient.get<GovtUnitNode[]>('/government-units/hierarchy');
      return normalizeList<GovtUnitNode>(res.data);
    } catch {
      return [];
    }
  },

  async getUnit(unitId: string) {
    try {
      const res = await axiosClient.get(`/government-units/${unitId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async getEmergingSkills(): Promise<any[]> {
    try {
      const res = await axiosClient.get('/emerging-skills/');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getDemandAnalytics() {
    try {
      const res = await axiosClient.get('/government/analytics/demand');
      return res.data;
    } catch {
      return null;
    }
  },

  async getPlacementAnalytics() {
    try {
      const res = await axiosClient.get('/government/analytics/placements');
      return res.data;
    } catch {
      return null;
    }
  },

  async getOrganizations(type?: 'EMPLOYER' | 'TRAINING_INSTITUTE') {
    try {
      const res = await axiosClient.get('/organizations', {
        params: type ? { organization_type: type } : undefined,
      });
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getDataAccessAuthorizations(): Promise<any[]> {
    try {
      const res = await axiosClient.get('/government/data-access/');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async getDrillDown(unitId?: string) {
    try {
      const res = await axiosClient.get('/government/drill-down', {
        params: unitId ? { unit_id: unitId } : undefined,
      });
      return res.data;
    } catch {
      return null;
    }
  },

  async getPendingDocuments(): Promise<PendingVerificationDocument[]> {
    try {
      const res = await axiosClient.get<PendingVerificationDocument[]>('/government/documents/pending');
      return normalizeList<PendingVerificationDocument>(res.data);
    } catch {
      return [];
    }
  },

  async reviewDocument(docId: string, actionPayload: { action: string; remarks?: string; reason?: string }): Promise<OrgDocument> {
    const res = await axiosClient.post<OrgDocument>(`/organization-documents/${docId}/action`, actionPayload);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Admin Services
// ---------------------------------------------------------------------------
export const adminApi = {
  async getStats(): Promise<AdminStats | null> {
    try {
      const res = await axiosClient.get<AdminStats>('/admin/stats');
      return res.data;
    } catch {
      return null;
    }
  },

  async getUsers(params?: {
    q?: string;
    account_type?: string;
    is_active?: boolean;
    is_suspended?: boolean;
    limit?: number;
    offset?: number;
  } | string, limit = 50): Promise<PlatformUser[]> {
    try {
      let queryParams: any = {};
      if (typeof params === 'string') {
        queryParams = { account_type: params || undefined, limit };
      } else if (params) {
        queryParams = {
          q: params.q || undefined,
          account_type: params.account_type || undefined,
          is_active: params.is_active,
          is_suspended: params.is_suspended,
          limit: params.limit ?? 50,
          offset: params.offset ?? 0,
        };
      } else {
        queryParams = { limit };
      }
      const res = await axiosClient.get('/admin/users', { params: queryParams });
      return normalizeList<PlatformUser>(res.data);
    } catch {
      return [];
    }
  },

  async getUserDetail(userId: string): Promise<any | null> {
    try {
      const res = await axiosClient.get(`/admin/users/${userId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async updateUserStatus(userId: string, is_active?: boolean, is_suspended?: boolean, reason?: string) {
    const res = await axiosClient.patch(`/admin/users/${userId}/status`, {
      is_active,
      is_suspended,
      reason,
    });
    return res.data;
  },

  async issueUserWarning(
    userId: string,
    title: string,
    message: string,
    reason: string,
    severity: string = 'NORMAL'
  ) {
    const res = await axiosClient.post(`/admin/users/${userId}/warning`, {
      title,
      message,
      reason,
      severity,
    });
    return res.data;
  },

  async unlockUser(userId: string) {
    const res = await axiosClient.post(`/admin/users/${userId}/unlock`);
    return res.data;
  },

  async assignGovtUnit(userId: string, governmentUnitId: string | null) {
    const res = await axiosClient.post(`/admin/users/${userId}/assign-govt-unit`, {
      government_unit_id: governmentUnitId,
    });
    return res.data;
  },

  async assignUserRole(userId: string, roleCode: string) {
    const res = await axiosClient.post(`/admin/users/${userId}/assign-role`, {
      role_code: roleCode,
    });
    return res.data;
  },

  async removeUserRole(userId: string, roleCode: string) {
    const res = await axiosClient.delete(`/admin/users/${userId}/roles/${roleCode}`);
    return res.data;
  },

  async getVerifications(params?: {
    tier?: string;
    status?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }): Promise<VerificationAppRecord[]> {
    try {
      const res = await axiosClient.get('/admin/verifications', {
        params: {
          tier: params?.tier || undefined,
          status: params?.status || undefined,
          q: params?.q || undefined,
          limit: params?.limit ?? 50,
          offset: params?.offset ?? 0,
        },
      });
      return normalizeList<VerificationAppRecord>(res.data);
    } catch {
      return [];
    }
  },

  async performVerificationAction(
    applicationId: string,
    action: 'APPROVE' | 'REJECT' | 'REQUEST_INFO' | 'SUSPEND' | 'REVOKE',
    reason?: string,
    remarks?: string
  ) {
    const res = await axiosClient.post(`/admin/verifications/${applicationId}/action`, {
      action,
      reason,
      remarks,
    });
    return res.data;
  },

  async getPlatformConfig(configKey: string): Promise<PlatformConfigRecord | null> {
    try {
      const res = await axiosClient.get<PlatformConfigRecord>(`/admin/platform-config/${configKey}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async savePlatformConfig(configKey: string, configData: Record<string, any>, changeReason: string) {
    const res = await axiosClient.post(`/admin/platform-config/${configKey}`, {
      config_data: configData,
      change_reason: changeReason,
    });
    return res.data;
  },

  async getPlatformConfigHistory(configKey: string): Promise<PlatformConfigHistoryItem[]> {
    try {
      const res = await axiosClient.get(`/admin/platform-config/${configKey}/history`);
      return normalizeList<PlatformConfigHistoryItem>(res.data);
    } catch {
      return [];
    }
  },

  async rollbackPlatformConfig(configKey: string, targetVersion: number, reason: string) {
    const res = await axiosClient.post(
      `/admin/platform-config/${configKey}/rollback/${targetVersion}`,
      null,
      { params: { reason } }
    );
    return res.data;
  },

  async getAuditLogs(
    limit = 50,
    action?: string,
    resourceType?: string,
    actorUserId?: string,
    search?: string
  ): Promise<AuditLogRecord[]> {
    try {
      const res = await axiosClient.get('/admin/audit-logs', {
        params: {
          limit,
          action: action || undefined,
          resource_type: resourceType || undefined,
          actor_user_id: actorUserId || undefined,
          q: search || undefined,
        },
      });
      return normalizeList<AuditLogRecord>(res.data);
    } catch {
      try {
        const res = await axiosClient.get('/audit-logs/', { params: { limit } });
        return normalizeList<AuditLogRecord>(res.data);
      } catch {
        return [];
      }
    }
  },

  async updateUserRoles(userId: string, roles: string[]) {
    const res = await axiosClient.put(`/admin/users/${userId}/roles`, { roles });
    return res.data;
  },

  async getVerificationApplications(status?: string): Promise<VerificationAppRecord[]> {
    return this.getVerifications({ status });
  },

  async getVerificationApplication(id: string): Promise<VerificationAppRecord | null> {
    try {
      const res = await axiosClient.get<VerificationAppRecord>(`/verification-applications/${id}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async approveVerification(id: string, reason?: string) {
    return this.performVerificationAction(id, 'APPROVE', reason);
  },

  async rejectVerification(id: string, reason?: string) {
    return this.performVerificationAction(id, 'REJECT', reason);
  },

  async getVerifierAuthorizations(): Promise<any[]> {
    try {
      const res = await axiosClient.get('/verifier-authorizations');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },
};

// ---------------------------------------------------------------------------
// Verification Services
// ---------------------------------------------------------------------------
export const verificationApi = {
  async getPending(applicationType?: string): Promise<VerificationAppRecord[]> {
    try {
      const res = await axiosClient.get<VerificationAppRecord[]>('/verification/pending', {
        params: applicationType ? { application_type: applicationType } : undefined,
      });
      return normalizeList<VerificationAppRecord>(res.data);
    } catch {
      return [];
    }
  },

  async reviewApplication(
    id: string,
    payload: {
      action: 'APPROVE' | 'REJECT' | 'REQUEST_MORE_INFO' | 'REQUEST_INFORMATION' | 'UNDER_REVIEW';
      remarks?: string;
      rejection_reason?: string;
      request_information_remarks?: string;
    }
  ): Promise<any> {
    const res = await axiosClient.post(`/verification/applications/${id}/review`, payload);
    return res.data;
  },

  async resubmitApplication(
    id: string,
    payload: {
      notes?: string;
      additional_document_urls?: string[];
    }
  ): Promise<any> {
    const res = await axiosClient.post(`/verification/applications/${id}/resubmit`, payload);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Notification & Social Services
// ---------------------------------------------------------------------------
export const notificationApi = {
  async getNotifications(unreadOnly = false, limit = 50): Promise<LiveNotification[]> {
    try {
      const res = await axiosClient.get('/notifications', {
        params: { unread_only: unreadOnly, limit },
      });
      return normalizeList<LiveNotification>(res.data);
    } catch {
      return [];
    }
  },

  async getUnreadCount(): Promise<number> {
    try {
      const res = await axiosClient.get<{ unread_count: number }>('/notifications/unread-count');
      return res.data.unread_count || 0;
    } catch {
      return 0;
    }
  },

  async markRead(id: string): Promise<void> {
    try {
      await axiosClient.post(`/notifications/${id}/read`);
    } catch {
      // ignore
    }
  },

  async markAllRead(): Promise<void> {
    try {
      await axiosClient.post('/notifications/read-all');
    } catch {
      // ignore
    }
  },

  async getPreferences() {
    try {
      const res = await axiosClient.get('/notifications/preferences');
      return res.data;
    } catch {
      return null;
    }
  },
};

export const followingApi = {
  async getFollowing(): Promise<any[]> {
    try {
      const res = await axiosClient.get('/following');
      return normalizeList<any>(res.data);
    } catch {
      return [];
    }
  },

  async follow(targetType: string, targetId: string) {
    const res = await axiosClient.post('/following', {
      target_type: targetType,
      target_id: targetId,
    });
    return res.data;
  },

  async toggleFollow(targetType: string, targetId: string) {
    const res = await axiosClient.post('/following/toggle', {
      target_type: targetType,
      target_id: targetId,
    });
    return res.data;
  },

  async unfollow(targetId: string) {
    const res = await axiosClient.delete(`/following/${targetId}`);
    return res.data;
  },
};

export interface SearchProfileItem {
  id: string;
  username: string;
  handle: string;
  name: string;
  account_type: 'GOVERNMENT' | 'EMPLOYER' | 'TRAINING_INSTITUTE' | 'CANDIDATE';
  headline?: string;
  location?: string;
  is_verified: boolean;
  badge_label: string;
  unit_code?: string;
}

export interface SearchProfilesResponse {
  items: SearchProfileItem[];
  total: number;
  limit: number;
  offset: number;
  query: string;
}

export const searchApi = {
  async searchProfiles(params: {
    q: string;
    account_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<SearchProfilesResponse> {
    try {
      const res = await axiosClient.get<SearchProfilesResponse>('/search/profiles', {
        params: {
          q: params.q,
          account_type: params.account_type || undefined,
          limit: params.limit || 20,
          offset: params.offset || 0,
        },
      });
      return res.data;
    } catch {
      return {
        items: [],
        total: 0,
        limit: params.limit || 20,
        offset: params.offset || 0,
        query: params.q,
      };
    }
  },
};

export const userApi = {
  async getMe() {
    const res = await axiosClient.get('/users/me');
    return res.data;
  },

  async getVerificationStatus() {
    const res = await axiosClient.get('/users/me/verification-status');
    return res.data;
  },

  async updateUsername(username: string) {
    const res = await axiosClient.patch('/users/me/username', {
      username: username.trim(),
    });
    return res.data;
  },

  async uploadAvatar(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axiosClient.post('/users/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async uploadCover(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axiosClient.post('/users/me/cover', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async getFollowers(identifier: string): Promise<{ items: any[]; total: number }> {
    try {
      const res = await axiosClient.get(`/users/${encodeURIComponent(identifier)}/followers`);
      return res.data;
    } catch {
      return { items: [], total: 0 };
    }
  },

  async getFollowingUsers(identifier: string): Promise<{ items: any[]; total: number }> {
    try {
      const res = await axiosClient.get(`/users/${encodeURIComponent(identifier)}/following`);
      return res.data;
    } catch {
      return { items: [], total: 0 };
    }
  },

  async deleteAccount(payload: { password: string; reason?: string }) {
    const res = await axiosClient.post('/users/me/delete-account', payload);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Messaging Services & Types
// ---------------------------------------------------------------------------
export function resolveMediaUrl(url?: string): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
  const origin = base.replace(/\/api\/v1\/?$/, '');
  return `${origin}${url.startsWith('/') ? '' : '/'}${url}`;
}

export interface MessageItem {
  id: string;
  conversation_id: string;
  sender_id: string;
  recipient_id: string;
  content: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
  sender_name?: string;
  sender_avatar?: string;
}

export interface ConversationParticipant {
  id: string;
  username?: string;
  account_type?: string;
  name: string;
  avatar_url?: string;
  headline?: string;
}

export interface ConversationItem {
  id: string;
  participant: ConversationParticipant;
  status: 'REQUESTED' | 'ACCEPTED' | 'REJECTED';
  is_requester: boolean;
  can_reply: boolean;
  unread_count: number;
  last_message?: {
    id: string;
    content: string;
    sender_id: string;
    created_at: string;
    is_read: boolean;
  };
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationItem {
  messages: MessageItem[];
}

export interface UnreadCounts {
  messages: number;
  requests: number;
  total: number;
}

export const messagingApi = {
  async getConversations(folder: 'inbox' | 'requests' = 'inbox'): Promise<ConversationItem[]> {
    try {
      const res = await axiosClient.get<ConversationItem[]>('/messages/conversations', {
        params: { folder },
      });
      return normalizeList<ConversationItem>(res.data);
    } catch {
      return [];
    }
  },

  async getConversation(id: string): Promise<ConversationDetail | null> {
    try {
      const res = await axiosClient.get<ConversationDetail>(`/messages/conversations/${id}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async getConversationWithUser(userId: string): Promise<ConversationDetail | null> {
    try {
      const res = await axiosClient.get<ConversationDetail>(`/messages/conversations/with-user/${userId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async sendMessage(recipientId: string, content: string): Promise<MessageItem> {
    const res = await axiosClient.post<MessageItem>('/messages', {
      recipient_id: recipientId,
      content,
    });
    return res.data;
  },

  async acceptRequest(conversationId: string): Promise<ConversationItem> {
    const res = await axiosClient.post<ConversationItem>(`/messages/conversations/${conversationId}/accept`);
    return res.data;
  },

  async rejectRequest(conversationId: string): Promise<ConversationItem> {
    const res = await axiosClient.post<ConversationItem>(`/messages/conversations/${conversationId}/reject`);
    return res.data;
  },

  async getUnreadCounts(): Promise<UnreadCounts> {
    try {
      const res = await axiosClient.get<UnreadCounts>('/messages/unread-counts');
      return res.data;
    } catch {
      return { messages: 0, requests: 0, total: 0 };
    }
  },
};

// ---------------------------------------------------------------------------
// Public & Document Services
// ---------------------------------------------------------------------------
export const publicApi = {
  async getPlatformStats(): Promise<PublicPlatformStats | null> {
    try {
      const res = await axiosClient.get<PublicPlatformStats>('/public/platform-stats');
      return res.data;
    } catch {
      return null;
    }
  },

  async getPublicProfile(identifier: string): Promise<LivePublicProfile | null> {
    try {
      const res = await axiosClient.get<LivePublicProfile>(
        `/users/public/${encodeURIComponent(identifier)}`
      );
      return res.data;
    } catch {
      return null;
    }
  },

  async getPublicJobs(limit = 20): Promise<LiveJob[]> {
    try {
      const res = await axiosClient.get('/jobs/public', { params: { limit } });
      return normalizeList<LiveJob>(res.data);
    } catch {
      return [];
    }
  },

  async getPublicCourses(limit = 20): Promise<LiveCourse[]> {
    try {
      const res = await axiosClient.get('/courses/public', { params: { limit } });
      return normalizeList<LiveCourse>(res.data);
    } catch {
      return [];
    }
  },

  async getPlatformConfig(configKey: string): Promise<Record<string, any> | null> {
    try {
      const res = await axiosClient.get<Record<string, any>>(`/public/platform-config/${configKey}`);
      return res.data;
    } catch {
      return null;
    }
  },
};

export const documentApi = {
  async uploadDocument(file: File, documentType: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    const res = await axiosClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async getDocument(documentId: string) {
    const res = await axiosClient.get(`/documents/${documentId}`);
    return res.data;
  },
};

export const organizationDocumentApi = {
  async getMyDocuments(): Promise<OrgDocument[]> {
    try {
      const res = await axiosClient.get<OrgDocument[]>('/organization-documents/mine');
      return normalizeList<OrgDocument>(res.data);
    } catch {
      return [];
    }
  },

  async getOrganizationDocuments(orgId: string): Promise<OrgDocument[]> {
    try {
      const res = await axiosClient.get<OrgDocument[]>(`/organization-documents/organization/${orgId}`);
      return normalizeList<OrgDocument>(res.data);
    } catch {
      return [];
    }
  },

  async getDocument(docId: string): Promise<OrgDocument | null> {
    try {
      const res = await axiosClient.get<OrgDocument>(`/organization-documents/${docId}`);
      return res.data;
    } catch {
      return null;
    }
  },

  async uploadDocument(payload: OrgDocumentCreatePayload): Promise<OrgDocument> {
    const res = await axiosClient.post<OrgDocument>('/organization-documents', payload);
    return res.data;
  },

  async updateDocument(docId: string, payload: Partial<OrgDocumentCreatePayload>): Promise<OrgDocument> {
    const res = await axiosClient.patch<OrgDocument>(`/organization-documents/${docId}`, payload);
    return res.data;
  },

  async reviewDocument(docId: string, actionPayload: { action: string; remarks?: string; reason?: string }): Promise<OrgDocument> {
    const res = await axiosClient.post<OrgDocument>(`/organization-documents/${docId}/action`, actionPayload);
    return res.data;
  },
};

// Unified api object
export const api = {
  auth: authApi,
  candidate: candidateApi,
  employer: employerApi,
  institution: institutionApi,
  government: governmentApi,
  admin: adminApi,
  notifications: notificationApi,
  following: followingApi,
  messaging: messagingApi,
  search: searchApi,
  user: userApi,
  public: publicApi,
  documents: documentApi,
  orgDocuments: organizationDocumentApi,
};

export default api;

