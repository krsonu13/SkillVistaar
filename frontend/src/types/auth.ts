export type AccountType = 'candidate' | 'employer' | 'institute' | 'government' | 'admin';

export type CanonicalAccountType =
  | 'CANDIDATE'
  | 'EMPLOYER'
  | 'TRAINING_INSTITUTE'
  | 'GOVERNMENT'
  | 'SUPER_ADMIN';

export interface AuthUser {
  id: string;
  email: string | null;
  phone: string | null;
  username?: string | null;
  name?: string;
  account_type: CanonicalAccountType;
  accountType?: AccountType | CanonicalAccountType;
  roles: string[];
  is_active?: boolean;
  is_suspended?: boolean;
  email_verified?: boolean;
  phone_verified?: boolean;
  isVerified?: boolean;
  verification_status?: 'PENDING' | 'UNDER_REVIEW' | 'MORE_INFORMATION_REQUIRED' | 'APPROVED' | 'REJECTED' | 'SUSPENDED' | string;
  government_unit_id?: string | null;
}

/**
 * Normalizes any role string variation to canonical uppercase format:
 * CANDIDATE, EMPLOYER, TRAINING_INSTITUTE, GOVERNMENT, SUPER_ADMIN
 */
export function normalizeAccountType(raw: string | undefined | null): CanonicalAccountType {
  if (!raw) return 'CANDIDATE';
  const clean = raw.trim().toUpperCase();
  if (clean === 'CANDIDATE') return 'CANDIDATE';
  if (clean === 'EMPLOYER') return 'EMPLOYER';
  if (clean === 'INSTITUTE' || clean === 'TRAINING_INSTITUTE') return 'TRAINING_INSTITUTE';
  if (clean === 'GOVERNMENT') return 'GOVERNMENT';
  if (clean === 'ADMIN' || clean === 'SUPER_ADMIN') return 'SUPER_ADMIN';
  return 'CANDIDATE';
}

/**
 * Normalizes any role string variation to frontend lowercase format:
 * candidate, employer, institute, government, admin
 */
export function toFrontendAccountType(raw: string | undefined | null): AccountType {
  const norm = normalizeAccountType(raw);
  switch (norm) {
    case 'CANDIDATE':
      return 'candidate';
    case 'EMPLOYER':
      return 'employer';
    case 'TRAINING_INSTITUTE':
      return 'institute';
    case 'GOVERNMENT':
      return 'government';
    case 'SUPER_ADMIN':
      return 'admin';
    default:
      return 'candidate';
  }
}

/**
 * Resolves effective canonical account type, prioritizing SUPER_ADMIN
 * if present in roles or account_type.
 */
export function resolveUserCanonicalRole(user: Partial<AuthUser> | null | undefined): CanonicalAccountType {
  if (!user) return 'CANDIDATE';
  if (
    user.roles?.includes('SUPER_ADMIN') ||
    user.account_type === 'SUPER_ADMIN' ||
    (user as any).accountType === 'SUPER_ADMIN' ||
    (user as any).accountType === 'admin'
  ) {
    return 'SUPER_ADMIN';
  }
  return normalizeAccountType(user.account_type || (user as any).accountType);
}

/**
 * Returns canonical destination dashboard path based on role or user object:
 * CANDIDATE -> /candidate
 * EMPLOYER -> /employer
 * TRAINING_INSTITUTE -> /institution
 * GOVERNMENT -> /government
 * SUPER_ADMIN -> /admin
 */
export function getDashboardPath(accountTypeOrUser: string | Partial<AuthUser> | undefined | null): string {
  if (accountTypeOrUser && typeof accountTypeOrUser === 'object') {
    const canonical = resolveUserCanonicalRole(accountTypeOrUser);
    return canonical === 'SUPER_ADMIN' ? '/admin' : getDashboardPath(canonical);
  }
  const norm = normalizeAccountType(accountTypeOrUser as string);
  switch (norm) {
    case 'CANDIDATE':
      return '/candidate';
    case 'EMPLOYER':
      return '/employer';
    case 'TRAINING_INSTITUTE':
      return '/institution';
    case 'GOVERNMENT':
      return '/government';
    case 'SUPER_ADMIN':
      return '/admin';
    default:
      return '/candidate';
  }
}

export interface StakeholderMeta {
  id: AccountType;
  title: string;
  badge: string;
  description: string;
  iconName: string;
  identifierPlaceholder: string;
  identifierLabel: string;
}

export interface LoginPayload {
  identifier: string; // Email or Phone (or official ID for govt)
  password: string;
  accountType?: AccountType | CanonicalAccountType | string;
  rememberMe?: boolean;
}

export interface CandidateRegisterPayload {
  accountType: 'candidate';
  fullName: string;
  email: string;
  phone: string;
  status: 'student' | 'fresher' | 'experienced' | 'unemployed';
  primarySkill: string;
  state: string;
  password: string;
  confirmPassword: string;
  termsAccepted: boolean;
}

export interface EmployerRegisterPayload {
  accountType: 'employer';
  companyName: string;
  officialEmail: string;
  contactPhone: string;
  industry: string;
  companySize: '1-15' | '16-50' | '51-200' | '201-1000' | '1000+';
  gstOrCin?: string;
  website?: string;
  password: string;
  confirmPassword: string;
  termsAccepted: boolean;
}

export interface InstituteRegisterPayload {
  accountType: 'institute';
  instituteName: string;
  affiliationBody: 'NSDC' | 'NCVET' | 'State Technical Board' | 'UGC/AICTE' | 'Independent/Private';
  officialEmail: string;
  coordinatorPhone: string;
  state: string;
  city: string;
  trainingSectors: string[];
  password: string;
  confirmPassword: string;
  termsAccepted: boolean;
}

export interface GovernmentRegisterPayload {
  accountType: 'government';
  departmentName: string;
  nodalOfficerName: string;
  officialEmail: string; // Must be .gov.in or official domain
  contactPhone: string;
  designation: string;
  stateOrUnionTerritory: string;
  nodalLevel: 'Central' | 'State' | 'District' | 'Autonomous Agency';
  password: string;
  confirmPassword: string;
  termsAccepted: boolean;
}

export type SignupPayload = 
  | CandidateRegisterPayload 
  | EmployerRegisterPayload 
  | InstituteRegisterPayload 
  | GovernmentRegisterPayload;

export interface AuthResponse {
  success: boolean;
  message: string;
  access_token?: string;
  refresh_token?: string;
  token?: string;
  token_type?: string;
  user?: AuthUser;
}

export interface OtpVerificationPayload {
  identifier: string;
  accountType: AccountType;
  otp: string;
}
