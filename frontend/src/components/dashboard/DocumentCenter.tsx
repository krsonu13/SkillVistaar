import React, { useState, useEffect } from 'react';
import {
  FileText,
  Upload,
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
  HelpCircle,
  ShieldAlert,
  Calendar,
  Building,
  History,
  RefreshCw,
  Plus,
  X,
  FileCheck,
} from 'lucide-react';
import { OrgDocument, OrgDocumentStatus, OrgDocumentType } from '../../types/document';
import { organizationDocumentApi } from '../../services/api';

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  REGISTRATION_CERTIFICATE: 'Incorporation / Registration Certificate',
  GOVERNMENT_APPROVAL: 'Government Approval / Gazette Notification',
  ACCREDITATION_DOCUMENT: 'Accreditation Document (NAAC / NBA / NCVET)',
  AFFILIATION_CERTIFICATE: 'University / Board Affiliation Certificate',
  PAN_GST_REGISTRATION: 'PAN / GSTIN Statutory Registration',
  ADDRESS_PROOF: 'Registered Office / Campus Address Proof',
  LICENSE_CERTIFICATE: 'Operating / Trade License Certificate',
  AUTHORIZATION_DOCUMENT: 'Statutory Authorization / Resolution',
  INSTITUTE_CERTIFICATE: 'Training Institute Recognition Certificate',
  INFRASTRUCTURE_AUDIT: 'Infrastructure & Safety Compliance Audit',
  OTHER: 'Other Statutory Compliance Document',
};

interface DocumentCenterProps {
  organizationId?: string;
  organizationName?: string;
  isVerifiedOrg?: boolean;
}

export const DocumentCenter: React.FC<DocumentCenterProps> = ({
  organizationId: _organizationId,
  organizationName,
  isVerifiedOrg,
}) => {
  const [documents, setDocuments] = useState<OrgDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'VERIFIED' | 'PENDING' | 'ACTION_REQUIRED'>('ALL');
  
  // Modals state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDocForHistory, setSelectedDocForHistory] = useState<OrgDocument | null>(null);
  
  // Form state
  const [docType, setDocType] = useState<OrgDocumentType>('REGISTRATION_CERTIFICATE');
  const [title, setTitle] = useState('');
  const [docNumber, setDocNumber] = useState('');
  const [issuingAuthority, setIssuingAuthority] = useState('');
  const [issueDate, setIssueDate] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [fileName, setFileName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await organizationDocumentApi.getMyDocuments();
      setDocuments(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load organization documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '));
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setUploadError('Document title is required.');
      return;
    }
    setSubmitting(true);
    setUploadError(null);
    try {
      await organizationDocumentApi.uploadDocument({
        document_type: docType,
        title: title.trim(),
        document_number: docNumber.trim() || undefined,
        issuing_authority: issuingAuthority.trim() || undefined,
        issue_date: issueDate || undefined,
        expiry_date: expiryDate || undefined,
        file_name: fileName || 'statutory_document.pdf',
        file_url: `https://storage.skillvistaar.gov.in/docs/${encodeURIComponent(fileName || 'statutory_doc.pdf')}`,
        mime_type: 'application/pdf',
      });
      setIsUploadOpen(false);
      // Reset form
      setTitle('');
      setDocNumber('');
      setIssuingAuthority('');
      setIssueDate('');
      setExpiryDate('');
      setFileName('');
      await fetchDocuments();
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || 'Failed to submit document for verification.');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: OrgDocumentStatus) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            Statutory Verified
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-300 dark:border-blue-800">
            <RefreshCw className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 animate-spin" />
            Under Official Review
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
            <Clock className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            Verification Queued
          </span>
        );
      case 'REQUEST_INFORMATION':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border border-purple-300 dark:border-purple-800">
            <HelpCircle className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
            Information Requested
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
            <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
            Rejected
          </span>
        );
      case 'REVOKED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border border-red-300 dark:border-red-800">
            <ShieldAlert className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
            Revoked
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            Expired
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            {status}
          </span>
        );
    }
  };

  const filteredDocs = documents.filter((doc) => {
    if (activeFilter === 'VERIFIED') return doc.status === 'VERIFIED';
    if (activeFilter === 'PENDING') return doc.status === 'PENDING' || doc.status === 'UNDER_REVIEW';
    if (activeFilter === 'ACTION_REQUIRED') {
      return ['REQUEST_INFORMATION', 'REJECTED', 'REVOKED', 'EXPIRED'].includes(doc.status);
    }
    return true;
  });

  const countVerified = documents.filter((d) => d.status === 'VERIFIED').length;
  const countPending = documents.filter((d) => d.status === 'PENDING' || d.status === 'UNDER_REVIEW').length;
  const countActionReq = documents.filter((d) => ['REQUEST_INFORMATION', 'REJECTED', 'REVOKED', 'EXPIRED'].includes(d.status)).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              {organizationName ? `${organizationName} ` : ''}Statutory Document Center
            </h2>
            {isVerifiedOrg ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300">
                <FileCheck className="w-3.5 h-3.5 text-emerald-600" /> Fully Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300">
                <Clock className="w-3.5 h-3.5 text-amber-600" /> Pending Verification
              </span>
            )}
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Upload and track statutory compliance certificates, operating approvals, and regulatory documents verified by jurisdiction authorities.
          </p>
        </div>
        <button
          onClick={() => setIsUploadOpen(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <Upload className="w-4 h-4" />
          Upload Document
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-sm text-slate-500 dark:text-slate-400 font-medium">Total Documents</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">{documents.length}</div>
          <div className="text-xs text-slate-500 mt-1">Mandatory & statutory files</div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">Verified</div>
          <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 mt-1">{countVerified}</div>
          <div className="text-xs text-slate-500 mt-1">Validated by Gov Authority</div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-sm text-amber-600 dark:text-amber-400 font-medium">Pending Review</div>
          <div className="text-2xl font-bold text-amber-700 dark:text-amber-300 mt-1">{countPending}</div>
          <div className="text-xs text-slate-500 mt-1">Queued with district/state</div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-sm text-rose-600 dark:text-rose-400 font-medium">Action Required</div>
          <div className="text-2xl font-bold text-rose-700 dark:text-rose-300 mt-1">{countActionReq}</div>
          <div className="text-xs text-slate-500 mt-1">Queries or re-uploads needed</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setActiveFilter('ALL')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            activeFilter === 'ALL'
              ? 'bg-teal-50 text-teal-700 dark:bg-teal-950/60 dark:text-teal-300 font-semibold'
              : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
          }`}
        >
          All ({documents.length})
        </button>
        <button
          onClick={() => setActiveFilter('VERIFIED')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            activeFilter === 'VERIFIED'
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 font-semibold'
              : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
          }`}
        >
          Verified ({countVerified})
        </button>
        <button
          onClick={() => setActiveFilter('PENDING')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            activeFilter === 'PENDING'
              ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300 font-semibold'
              : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
          }`}
        >
          Pending Review ({countPending})
        </button>
        <button
          onClick={() => setActiveFilter('ACTION_REQUIRED')}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            activeFilter === 'ACTION_REQUIRED'
              ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-semibold'
              : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'
          }`}
        >
          Action Required ({countActionReq})
        </button>
      </div>

      {/* Documents List */}
      {loading ? (
        <div className="flex justify-center items-center py-16 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800">
          <RefreshCw className="w-8 h-8 text-teal-600 animate-spin" />
        </div>
      ) : error ? (
        <div className="p-6 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 rounded-xl text-center">
          <AlertCircle className="w-8 h-8 text-rose-600 dark:text-rose-400 mx-auto mb-2" />
          <p className="text-sm text-rose-800 dark:text-rose-200">{error}</p>
          <button
            onClick={fetchDocuments}
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-rose-700 hover:text-rose-900"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Try again
          </button>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-8 shadow-sm">
          <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">
            No Documents Found
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1">
            {activeFilter === 'ALL'
              ? 'No statutory documents uploaded yet. Upload your organization registration, recognition, and compliance certificates to initiate verification.'
              : `No documents currently in '${activeFilter.replace('_', ' ')}' state.`}
          </p>
          {activeFilter === 'ALL' && (
            <button
              onClick={() => setIsUploadOpen(true)}
              className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Upload First Document
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Document Details</th>
                  <th className="px-4 py-3.5">Issuing Authority</th>
                  <th className="px-4 py-3.5">Validity Dates</th>
                  <th className="px-4 py-3.5">Verification Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 mt-0.5">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {doc.title}
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {DOCUMENT_TYPE_LABELS[doc.document_type] || doc.document_type}
                          </div>
                          {doc.document_number && (
                            <div className="text-xs font-mono text-slate-600 dark:text-slate-300 mt-1">
                              ID: {doc.document_number}
                            </div>
                          )}
                          {doc.rejection_reason && (
                            <div className="mt-2 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/40 rounded p-2">
                              <span className="font-semibold">Rejection Reason:</span> {doc.rejection_reason}
                            </div>
                          )}
                          {doc.verification_remarks && doc.status === 'REQUEST_INFORMATION' && (
                            <div className="mt-2 text-xs text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900/40 rounded p-2">
                              <span className="font-semibold">Query from Verifier:</span> {doc.verification_remarks}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-4 text-slate-700 dark:text-slate-300">
                      <div className="flex items-center gap-1.5 text-sm">
                        <Building className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        <span>{doc.issuing_authority || 'Not Specified'}</span>
                      </div>
                    </td>

                    <td className="px-4 py-4 text-xs text-slate-600 dark:text-slate-400">
                      <div>
                        <span className="font-medium text-slate-700 dark:text-slate-300">Issued:</span>{' '}
                        {doc.issue_date || 'N/A'}
                      </div>
                      <div className="mt-1">
                        <span className="font-medium text-slate-700 dark:text-slate-300">Expires:</span>{' '}
                        {doc.expiry_date ? (
                          <span className={new Date(doc.expiry_date) < new Date() ? 'text-rose-600 font-semibold' : ''}>
                            {doc.expiry_date}
                          </span>
                        ) : (
                          'Perpetual / No Expiry'
                        )}
                      </div>
                    </td>

                    <td className="px-4 py-4">
                      {getStatusBadge(doc.status)}
                      {doc.verified_at && (
                        <div className="text-[11px] text-slate-500 mt-1">
                          Verified on {new Date(doc.verified_at).toLocaleDateString()}
                        </div>
                      )}
                    </td>

                    <td className="px-4 py-4 text-right space-x-2">
                      <button
                        onClick={() => setSelectedDocForHistory(doc)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                        title="View complete verification timeline"
                      >
                        <History className="w-3.5 h-3.5" />
                        History ({doc.history?.length || 0})
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upload Document Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-600">
                  <Upload className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  Upload Statutory Document
                </h3>
              </div>
              <button
                onClick={() => setIsUploadOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="mt-5 space-y-4">
              {uploadError && (
                <div className="p-3 bg-rose-50 dark:bg-rose-950/50 border border-rose-200 text-rose-800 dark:text-rose-200 rounded-lg text-sm">
                  {uploadError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Statutory Document Type *
                </label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value as OrgDocumentType)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  required
                >
                  {Object.entries(DOCUMENT_TYPE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Document Title / Description *
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Certificate of Incorporation 2024"
                  className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Registration / Certificate No.
                  </label>
                  <input
                    type="text"
                    value={docNumber}
                    onChange={(e) => setDocNumber(e.target.value)}
                    placeholder="e.g. U72200MH2020PTC123456"
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Issuing Authority
                  </label>
                  <input
                    type="text"
                    value={issuingAuthority}
                    onChange={(e) => setIssuingAuthority(e.target.value)}
                    placeholder="e.g. Ministry of Corporate Affairs / AICTE"
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Issue Date
                  </label>
                  <input
                    type="date"
                    value={issueDate}
                    onChange={(e) => setIssueDate(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                    Expiry Date (if applicable)
                  </label>
                  <input
                    type="date"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1.5">
                  Attach PDF or Scan Copy
                </label>
                <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg p-4 text-center hover:border-teal-500 transition-colors">
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="doc-file-upload"
                  />
                  <label
                    htmlFor="doc-file-upload"
                    className="cursor-pointer flex flex-col items-center justify-center"
                  >
                    <Upload className="w-8 h-8 text-slate-400 mb-1" />
                    <span className="text-sm font-medium text-teal-600 dark:text-teal-400">
                      {fileName ? fileName : 'Click to select statutory file (PDF/JPG)'}
                    </span>
                    <span className="text-xs text-slate-500 mt-0.5">
                      Max file size: 10MB. Certified statutory documents only.
                    </span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-sm flex items-center gap-2 disabled:opacity-50"
                >
                  {submitting && <RefreshCw className="w-4 h-4 animate-spin" />}
                  Submit for Statutory Verification
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* History Drawer / Modal */}
      {selectedDocForHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <History className="w-5 h-5 text-teal-600" />
                  Verification Audit History
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {selectedDocForHistory.title} ({DOCUMENT_TYPE_LABELS[selectedDocForHistory.document_type] || selectedDocForHistory.document_type})
                </p>
              </div>
              <button
                onClick={() => setSelectedDocForHistory(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              {selectedDocForHistory.history && selectedDocForHistory.history.length > 0 ? (
                <div className="relative pl-6 border-l-2 border-slate-200 dark:border-slate-800 space-y-6">
                  {selectedDocForHistory.history.map((h, idx) => (
                    <div key={h.id || idx} className="relative">
                      {/* Node point */}
                      <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-teal-500 border-4 border-white dark:border-slate-900" />
                      
                      <div className="bg-slate-50 dark:bg-slate-800/60 rounded-lg p-3.5 border border-slate-200/80 dark:border-slate-700/80">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                            {h.action}
                          </span>
                          <span className="text-xs text-slate-500">
                            {new Date(h.created_at).toLocaleString()}
                          </span>
                        </div>
                        
                        <div className="text-xs text-slate-600 dark:text-slate-400 mt-1 flex items-center gap-2">
                          <span>Status:</span>
                          <span className="font-mono bg-slate-200 dark:bg-slate-700 px-1.5 py-0.5 rounded">
                            {h.previous_status || 'INITIAL'}
                          </span>
                          <span>&rarr;</span>
                          <span className="font-mono font-semibold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/60 px-1.5 py-0.5 rounded">
                            {h.new_status}
                          </span>
                        </div>

                        {h.remarks && (
                          <div className="mt-2 text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-800">
                            <span className="font-medium text-slate-500">Remarks:</span> {h.remarks}
                          </div>
                        )}

                        {h.reason && (
                          <div className="mt-2 text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 p-2 rounded border border-rose-200 dark:border-rose-900/40">
                            <span className="font-semibold">Reason:</span> {h.reason}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 text-sm">
                  No history records available yet for this document.
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedDocForHistory(null)}
                className="px-4 py-2 text-sm font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentCenter;
