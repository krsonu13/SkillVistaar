import axiosClient from './axiosClient';

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

export interface AdminStats {
  users: {
    total: number;
    active: number;
    suspended: number;
    by_type: Record<string, number>;
  };
  government_units_count: number;
  organizations_count: number;
  total_audit_logs: number;
}

export interface PlatformUser {
  id: string;
  email?: string;
  phone?: string;
  account_type: string;
  is_active: boolean;
  is_suspended: boolean;
  email_verified: boolean;
  phone_verified: boolean;
  government_unit_id?: string | null;
  roles: string[];
}

export interface AuditLogRecord {
  id: string;
  actor_user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  description?: string;
  ip_address?: string;
  created_at: string;
}

export interface VerificationAppRecord {
  id: string;
  applicant_user_id: string;
  verifier_user_id?: string | null;
  government_unit_id?: string | null;
  status: string;
  application_type: string;
  submitted_data?: Record<string, any>;
  remarks?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at?: string;
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

export interface CandidateSkillRecord {
  id: string;
  candidate_profile_id: string;
  skill_id: string;
  status: string;
  notes?: string;
  created_at: string;
}

export interface CandidateCredentialRecord {
  id: string;
  candidate_profile_id: string;
  credential_type: string;
  title: string;
  issuer_name: string;
  status: string;
  verification_hash?: string;
  document_url?: string;
  created_at: string;
}

export interface PublicPlatformStats {
  verified_candidates: number;
  hiring_employers: number;
  training_institutes: number;
  verified_credentials: number;
  active_jobs: number;
  verification_authority: string;
}

export interface LiveJob {
  id: string;
  organization_id?: string;
  title: string;
  description?: string;
  location?: string;
  employment_type?: string;
  salary_min?: number;
  salary_max?: number;
  openings?: number;
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
  applicant_headline?: string;
  applicant_email?: string;
  applicant_phone?: string;
  status: string;
  cover_letter?: string;
  job_title?: string;
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

export interface LivePublicProfile {
  id: string;
  username?: string;
  handle?: string;
  is_following?: boolean;
  is_self?: boolean;
  email?: string;
  phone?: string;
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
  location?: string;
  avatar?: string;
  cover_image?: string;
  profile_completion_percentage?: number;
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
  employer_details?: {
    legal_name?: string;
    verification_status?: string;
    open_jobs?: any[];
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

export const platformService = {
  /**
   * Fetch government dashboard analytics for current jurisdiction
   */
  async getGovernmentDashboard(): Promise<GovtDashboardStats | null> {
    try {
      const resp = await axiosClient.get<GovtDashboardStats>('/government/dashboard');
      return resp.data;
    } catch {
      return null;
    }
  },

  /**
   * Fetch government hierarchy tree
   */
  async getGovernmentHierarchy(): Promise<GovtUnitNode[]> {
    try {
      const resp = await axiosClient.get<GovtUnitNode[]>('/government-units/hierarchy');
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Fetch super admin stats
   */
  async getAdminStats(): Promise<AdminStats | null> {
    try {
      const resp = await axiosClient.get<AdminStats>('/admin/stats');
      return resp.data;
    } catch {
      return null;
    }
  },

  /**
   * Fetch users list (Super Admin)
   */
  async getUsers(accountType?: string, limit = 50): Promise<PlatformUser[]> {
    try {
      const resp = await axiosClient.get<PlatformUser[]>('/admin/users', {
        params: {
          account_type: accountType || undefined,
          limit,
        },
      });
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Update user status (Super Admin suspend / reactivate)
   */
  async updateUserStatus(userId: string, is_active?: boolean, is_suspended?: boolean, reason?: string) {
    try {
      const resp = await axiosClient.patch(`/admin/users/${userId}/status`, {
        is_active,
        is_suspended,
        reason,
      });
      return resp.data;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Failed to update user status');
    }
  },

  /**
   * Fetch audit logs (Super Admin / Authorized Govt)
   */
  async getAuditLogs(limit = 20): Promise<AuditLogRecord[]> {
    try {
      const resp = await axiosClient.get<{ items: AuditLogRecord[] }>('/audit-logs/', {
        params: { limit },
      });
      return resp.data.items || [];
    } catch {
      return [];
    }
  },

  /**
   * Fetch verification applications (Govt / Super Admin)
   */
  async getVerificationApplications(status?: string): Promise<VerificationAppRecord[]> {
    try {
      const resp = await axiosClient.get<VerificationAppRecord[]>('/verification-applications', {
        params: status ? { status } : undefined,
      });
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Approve a verification application
   */
  async approveVerificationApplication(id: string): Promise<VerificationAppRecord> {
    const resp = await axiosClient.post(`/verification-applications/${id}/approve`);
    return resp.data;
  },

  /**
   * Reject a verification application
   */
  async rejectVerificationApplication(id: string, reason?: string): Promise<VerificationAppRecord> {
    const resp = await axiosClient.post(`/verification-applications/${id}/reject`, null, {
      params: reason ? { reason } : undefined,
    });
    return resp.data;
  },

  /**
   * Fetch organizations
   */
  async getOrganizations(type?: 'EMPLOYER' | 'TRAINING_INSTITUTE') {
    try {
      const resp = await axiosClient.get('/organizations', {
        params: type ? { organization_type: type } : undefined,
      });
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Fetch candidate's own profile
   */
  async getCandidateProfile() {
    try {
      const resp = await axiosClient.get('/candidates/me/profile');
      return resp.data;
    } catch {
      return null;
    }
  },

  /**
   * Fetch candidate's own skills
   */
  async getCandidateSkills(): Promise<CandidateSkillRecord[]> {
    try {
      const resp = await axiosClient.get<CandidateSkillRecord[]>('/candidates/me/skills');
      return Array.isArray(resp.data) ? resp.data : ((resp.data as any)?.items || []);
    } catch {
      try {
        const resp2 = await axiosClient.get<any>('/candidate/skills');
        return Array.isArray(resp2.data) ? resp2.data : (resp2.data?.items || []);
      } catch {
        return [];
      }
    }
  },

  /**
   * Fetch candidate's own credentials
   */
  async getCandidateCredentials(): Promise<CandidateCredentialRecord[]> {
    try {
      const resp = await axiosClient.get<CandidateCredentialRecord[]>('/candidates/me/credentials');
      return Array.isArray(resp.data) ? resp.data : ((resp.data as any)?.items || []);
    } catch {
      try {
        const resp2 = await axiosClient.get<any>('/candidate/credentials');
        return Array.isArray(resp2.data) ? resp2.data : (resp2.data?.items || []);
      } catch {
        return [];
      }
    }
  },

  /**
   * Add a new candidate skill
   */
  async addCandidateSkill(skill_id: string, _notes?: string) {
    try {
      const resp = await axiosClient.post('/candidate/skills', {
        skill_id,
        proficiency_level: 'INTERMEDIATE',
        years_of_experience: 1,
        is_primary: false,
      });
      return resp.data;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || err.message || 'Failed to add skill');
    }
  },

  /**
   * Add a new candidate credential
   */
  async addCandidateCredential(payload: {
    credential_type: string;
    title: string;
    issuer_name: string;
    issued_date?: string;
    document_url?: string;
  }) {
    try {
      const resp = await axiosClient.post('/candidates/me/credentials', payload);
      return resp.data;
    } catch (err: any) {
      throw new Error(err.response?.data?.detail || 'Failed to add credential');
    }
  },

  /**
   * Fetch pending verification applications
   */
  async getPendingVerifications(): Promise<VerificationAppRecord[]> {
    try {
      const resp = await axiosClient.get<VerificationAppRecord[]>('/verification/pending');
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Review organization status
   */
  async reviewOrganization(orgId: string, status: string, remarks?: string) {
    const resp = await axiosClient.post(`/organizations/${orgId}/review`, {
      status,
      remarks,
    });
    return resp.data;
  },

  /**
   * Review verification application
   */
  async reviewVerificationApplication(appId: string, status: string, reason?: string, remarks?: string) {
    const resp = await axiosClient.post(`/verification/applications/${appId}/review`, {
      status,
      reason,
      remarks,
    });
    return resp.data;
  },

  /**
   * Fetch live platform aggregate statistics for public landing page
   */
  async getPublicPlatformStats(): Promise<PublicPlatformStats | null> {
    try {
      const resp = await axiosClient.get<PublicPlatformStats>('/public/platform-stats');
      return resp.data;
    } catch {
      return null;
    }
  },

  /**
   * Fetch real public profile for candidate, employer, or institute
   */
  async getPublicProfile(identifier: string): Promise<LivePublicProfile | null> {
    try {
      const resp = await axiosClient.get<LivePublicProfile>(`/users/public/${encodeURIComponent(identifier)}`);
      return resp.data;
    } catch {
      return null;
    }
  },

  /**
   * Fetch live jobs posted by current employer's organization
   */
  async getEmployerJobs(): Promise<LiveJob[]> {
    try {
      const resp = await axiosClient.get<LiveJob[]>('/jobs/me/organization');
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Post a new job by employer
   */
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
    const resp = await axiosClient.post<LiveJob>('/jobs', payload);
    return resp.data;
  },

  /**
   * Fetch real applications received for employer's organization
   */
  async getEmployerApplications(): Promise<LiveJobApplication[]> {
    try {
      const resp = await axiosClient.get<LiveJobApplication[]>('/applications/organization/mine');
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Update job application status (SHORTLISTED, REJECTED, ACCEPTED, etc.)
   */
  async updateApplicationStatus(applicationId: string, status: string, notes?: string) {
    const resp = await axiosClient.patch(`/applications/${applicationId}/status`, {
      status,
      notes,
    });
    return resp.data;
  },

  /**
   * Fetch training institute dashboard
   */
  async getInstituteDashboard() {
    try {
      const resp = await axiosClient.get('/institutions/me/dashboard');
      return resp.data;
    } catch {
      return null;
    }
  },

  /**
   * Fetch courses for an institution or platform
   */
  async getCourses(institutionId?: string): Promise<LiveCourse[]> {
    try {
      const url = institutionId ? `/courses/institutions/${institutionId}` : '/courses';
      const resp = await axiosClient.get<LiveCourse[]>(url);
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Create course by training institution
   */
  async createCourse(payload: {
    title: string;
    description?: string;
    level?: string;
    duration_weeks?: number;
    organization_id?: string;
  }): Promise<LiveCourse> {
    const resp = await axiosClient.post<LiveCourse>('/courses', payload);
    return resp.data;
  },

  /**
   * Fetch candidate's own job applications
   */
  async getCandidateApplications(): Promise<LiveJobApplication[]> {
    try {
      const resp = await axiosClient.get<{ applications: LiveJobApplication[]; total: number }>('/applications/mine');
      return resp.data?.applications || [];
    } catch {
      return [];
    }
  },

  /**
   * Apply for a job as candidate
   */
  async applyForJob(jobId: string, payload: {
    cover_letter?: string;
    resume_document_id?: string;
    consent_to_share_profile?: boolean;
  }) {
    const resp = await axiosClient.post(`/applications/jobs/${jobId}`, payload);
    return resp.data;
  },

  /**
   * Fetch recommended jobs for candidate
   */
  async getRecommendedJobs(limit = 10): Promise<LiveJob[]> {
    try {
      const resp = await axiosClient.get<LiveJob[]>('/recommendations/jobs', { params: { limit } });
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Fetch recommended courses for candidate
   */
  async getRecommendedCourses(limit = 10): Promise<LiveCourse[]> {
    try {
      const resp = await axiosClient.get<LiveCourse[]>('/recommendations/courses', { params: { limit } });
      return resp.data;
    } catch {
      return [];
    }
  },

  /**
   * Fetch user notifications
   */
  async getNotifications(unreadOnly = false, limit = 50): Promise<LiveNotification[]> {
    try {
      const resp = await axiosClient.get<{ items: LiveNotification[] }>('/notifications', {
        params: { unread_only: unreadOnly, limit },
      });
      return resp.data.items || [];
    } catch {
      return [];
    }
  },

  /**
   * Get unread notification count
   */
  async getUnreadNotificationCount(): Promise<number> {
    try {
      const resp = await axiosClient.get<{ unread_count: number }>('/notifications/unread-count');
      return resp.data.unread_count || 0;
    } catch {
      return 0;
    }
  },

  /**
   * Mark a notification as read
   */
  async markNotificationRead(id: string): Promise<void> {
    try {
      await axiosClient.post(`/notifications/${id}/read`);
    } catch {
      // ignore
    }
  },

  /**
   * Mark all notifications as read
   */
  async markAllNotificationsRead(): Promise<void> {
    try {
      await axiosClient.post('/notifications/read-all');
    } catch {
      // ignore
    }
  },

  /**
   * Follow a user or organization
   */
  async follow(targetType: string, targetId: string) {
    const resp = await axiosClient.post('/following', {
      target_type: targetType,
      target_id: targetId,
    });
    return resp.data;
  },

  /**
   * Unfollow
   */
  async unfollow(targetId: string) {
    const resp = await axiosClient.delete(`/following/${targetId}`);
    return resp.data;
  },
};

export default platformService;
