export type OrgDocumentType =
  | 'REGISTRATION_CERTIFICATE'
  | 'GOVERNMENT_APPROVAL'
  | 'ACCREDITATION_DOCUMENT'
  | 'AFFILIATION_CERTIFICATE'
  | 'PAN_GST_REGISTRATION'
  | 'ADDRESS_PROOF'
  | 'LICENSE_CERTIFICATE'
  | 'AUTHORIZATION_DOCUMENT'
  | 'INSTITUTE_CERTIFICATE'
  | 'INFRASTRUCTURE_AUDIT'
  | 'OTHER';

export type OrgDocumentStatus =
  | 'PENDING'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'REQUEST_INFORMATION'
  | 'EXPIRED'
  | 'REVOKED';

export interface OrgDocumentHistory {
  id: string;
  document_id: string;
  actor_user_id?: string;
  action: string;
  previous_status?: string | null;
  new_status: string;
  remarks?: string | null;
  reason?: string | null;
  created_at: string;
}

export interface OrgDocument {
  id: string;
  organization_id: string;
  document_id?: string | null;
  document_type: string;
  title: string;
  document_number?: string | null;
  issuing_authority?: string | null;
  issue_date?: string | null;
  expiry_date?: string | null;
  file_name?: string | null;
  file_url?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  status: OrgDocumentStatus;
  uploaded_by_user_id: string;
  verifier_user_id?: string | null;
  verification_remarks?: string | null;
  rejection_reason?: string | null;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
  history?: OrgDocumentHistory[];
}

export interface OrgDocumentCreatePayload {
  document_type: string;
  title: string;
  document_number?: string;
  issuing_authority?: string;
  issue_date?: string;
  expiry_date?: string;
  file_name?: string;
  file_url?: string;
  file_size?: number;
  mime_type?: string;
  document_id?: string;
}

export interface PendingVerificationDocument extends OrgDocument {
  organization_name: string;
  organization_type: string;
  jurisdiction_name: string;
  government_unit_id?: string;
}
