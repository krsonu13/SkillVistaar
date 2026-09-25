import React, { useState } from 'react';
import { X, CheckCircle2, ShieldCheck, ArrowRight } from 'lucide-react';
import Button from '../common/Button';
import Badge from '../common/Badge';

interface JobApplyModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobTitle: string;
  companyName: string;
}

export const JobApplyModal: React.FC<JobApplyModalProps> = ({
  isOpen,
  onClose,
  jobTitle,
  companyName,
}) => {
  const [note, setNote] = useState('');
  const [includeDigilocker, setIncludeDigilocker] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setNote('');
        onClose();
      }, 1500);
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div>
            <h3 className="text-sm font-bold text-slate-900">1-Click Verified Application</h3>
            <p className="text-[11px] text-slate-500">
              Applying to <span className="font-semibold text-slate-800">{companyName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {submitted ? (
          <div className="p-8 text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
            <h4 className="text-sm font-bold text-slate-900">Application Submitted!</h4>
            <p className="text-xs text-slate-500">
              Your DigiLocker Skill Passport and credentials have been transmitted to {companyName}.
            </p>
          </div>
        ) : (
          <form onSubmit={handleApply} className="p-5 space-y-3.5">
            <div className="p-3 bg-teal-50/70 border border-teal-200/80 rounded-lg space-y-1">
              <span className="text-[10px] font-bold text-teal-800 uppercase tracking-wider">
                Position
              </span>
              <p className="text-xs font-bold text-slate-900">{jobTitle}</p>
              <div className="flex items-center gap-1.5 pt-1">
                <Badge variant="teal" size="sm">
                  NSQF Level 5/6 Matched
                </Badge>
                <Badge variant="emerald" size="sm">
                  94% Skill Match
                </Badge>
              </div>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-teal-600" />
                  Skill Passport Attachment
                </span>
                <span className="text-[10px] text-teal-700 font-semibold">Active</span>
              </div>
              <p className="text-[11px] text-slate-500">
                Your authenticated NSDC & NCVET certifications will be automatically bundled with verifiable hashes.
              </p>
              <label className="flex items-center gap-2 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={includeDigilocker}
                  onChange={(e) => setIncludeDigilocker(e.target.checked)}
                  className="w-3.5 h-3.5 rounded text-teal-600 border-slate-300"
                />
                <span className="text-[11px] text-slate-700 font-medium">
                  Share DigiLocker verified academic record
                </span>
              </label>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Short Note to Recruiter (Optional)
              </label>
              <textarea
                rows={2}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Mention availability or specific experience highlights..."
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500/20 text-slate-800"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button type="button" variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isLoading}
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
              >
                Confirm & Submit Application
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default JobApplyModal;
