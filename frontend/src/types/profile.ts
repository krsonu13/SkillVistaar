import { AccountType } from './auth';

export type VerificationBadgeType = 
  | 'digilocker' 
  | 'enterprise' 
  | 'nsqf' 
  | 'gov_gold' 
  | 'admin';

export interface VerifiedSkill {
  id: string;
  name: string;
  nsqfLevel: number;
  issuer: string; // e.g. National Skill Development Corporation (NSDC), NCVET
  credentialId: string;
  issuedDate: string;
  verificationHash: string; // Cryptographic audit hash
  category: string;
  scorePercent?: number;
}

export interface SelfDeclaredSkill {
  id: string;
  name: string;
  category: string;
  endorsements: number;
}

export interface EducationItem {
  id: string;
  institution: string;
  degree: string;
  fieldOfStudy: string;
  startDate: string;
  endDate: string;
  grade?: string;
}

export interface ExperienceItem {
  id: string;
  title: string;
  organization: string;
  employmentType: 'Full-time' | 'Apprenticeship' | 'Internship' | 'Contract';
  location: string;
  startDate: string;
  endDate: string | 'Present';
  description: string;
}

export interface ProjectItem {
  id: string;
  title: string;
  description: string;
  tags: string[];
  link?: string;
}

export interface JobItem {
  id: string;
  title: string;
  type: 'Full-time' | 'Apprenticeship' | 'Internship';
  location: string;
  salary: string;
  nsqfRequirement?: string;
  applicantsCount: number;
  postedAt: string;
  description: string;
  skills: string[];
}

export interface CourseItem {
  id: string;
  title: string;
  nsqfLevel: number;
  duration: string;
  mode: 'In-person' | 'Hybrid' | 'Online';
  enrolledCount: number;
  placementRate: string;
  certifiedBy: string;
  nextBatchDate: string;
}

export interface GovtSchemeItem {
  id: string;
  title: string;
  code: string;
  description: string;
  targetBeneficiaries: string;
  budgetAllocated: string;
  status: 'Active' | 'Under Review' | 'Upcoming';
  nodalMinistry: string;
}

export interface ActivityPost {
  id: string;
  authorId: string;
  authorName: string;
  authorUsername: string;
  authorAvatar: string;
  authorRole: AccountType;
  content: string;
  timestamp: string;
  likes: number;
  comments: number;
  isLiked?: boolean;
  tags?: string[];
  attachmentType?: 'badge' | 'job' | 'course' | 'scheme' | 'none';
  attachmentTitle?: string;
}

export interface FollowUserItem {
  id: string;
  name: string;
  username: string;
  avatar: string;
  role: AccountType;
  headline: string;
  isFollowing: boolean;
}

export interface UserProfile {
  id: string;
  username: string;
  name: string;
  role: AccountType;
  avatar: string;
  coverImage: string;
  headline: string;
  bio: string;
  location: string;
  website?: string;
  email?: string;
  isSelf?: boolean;
  profileCompletionPercentage?: number;
  isVerified: boolean;
  badgeType: VerificationBadgeType;
  joinedDate: string;
  
  // Social metrics
  followersCount: number;
  followingCount: number;
  isFollowing: boolean;

  // Candidate
  candidateDetails?: {
    status: string;
    verifiedSkills: VerifiedSkill[];
    selfDeclaredSkills: SelfDeclaredSkill[];
    education: EducationItem[];
    experience: ExperienceItem[];
    projects: ProjectItem[];
    certifications?: any[];
    coursesCompleted?: any[];
    achievements?: any[];
    languages?: any[];
    careerPreferences?: any;
    digilockerIdMasked?: string;
  };

  // Employer
  employerDetails?: {
    industry: string;
    companySize: string;
    foundedYear: string;
    headquarters: string;
    gstVerified: boolean;
    openJobs: JobItem[];
    techStack: string[];
  };

  // Training Institute
  instituteDetails?: {
    affiliation: string;
    accreditationCode: string;
    placementRate: string;
    coursesOffered: CourseItem[];
    campusLocations: string[];
    activeBatchesCount: number;
  };

  // Government
  governmentDetails?: {
    ministryDepartment: string;
    jurisdictionLevel: 'Central' | 'State' | 'District' | 'Autonomous';
    jurisdictionTerritory: string;
    activeSchemes: GovtSchemeItem[];
    nodalOfficersCount: number;
    annualBeneficiaries: string;
  };

  // Admin
  adminDetails?: {
    adminRoleTitle: string;
    clearanceLevel: string;
    systemResponsibilities: string[];
  };

  // Activity Feed
  posts: ActivityPost[];

  // RBAC Sensitive Data (Stripped on public views for other users)
  privateDetails?: {
    officialEmail: string;
    phone: string;
    nationalIdMasked?: string;
    residentialAddress?: string;
  };
}
