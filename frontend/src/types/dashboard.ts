

export interface StatCardData {
  title: string;
  value: string | number;
  change?: string;
  isPositive?: boolean;
  subtext: string;
  iconName: string;
}

export interface ActivityTimelineItem {
  id: string;
  title: string;
  timestamp: string;
  category: 'credential' | 'job' | 'batch' | 'scheme' | 'security' | 'general';
  description: string;
  actionUrl?: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  isRead: boolean;
  type: 'info' | 'success' | 'warning' | 'urgent';
  link?: string;
}

export interface CandidateApplicationTracker {
  id: string;
  jobTitle: string;
  companyName: string;
  appliedDate: string;
  status: 'Applied' | 'Reviewing' | 'Interview Scheduled' | 'Shortlisted' | 'Selected';
  matchScore: number;
}

export interface EmployerApplicantPipeline {
  id: string;
  candidateName: string;
  candidateRole: string;
  appliedFor: string;
  nsqfLevel: number;
  isVerified: boolean;
  matchScore: number;
  status: 'New' | 'Screened' | 'Interviewing' | 'Hired';
  avatar: string;
}

export interface InstituteBatchProgress {
  id: string;
  batchCode: string;
  courseTitle: string;
  totalStudents: number;
  attendancePercent: number;
  completionPercent: number;
  status: 'In Progress' | 'Assessment Phase' | 'Completed';
}

export interface GovtDistrictAnalytics {
  id: string;
  district: string;
  state: string;
  youthTrained: number;
  activeVacancies: number;
  demandSupplyRatio: string;
  prioritySector: string;
  placementRate: number;
}

export interface AdminAuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  target: string;
  status: 'Success' | 'Flagged' | 'Pending Review';
  ipAddress: string;
}
