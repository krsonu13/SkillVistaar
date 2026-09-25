import React from 'react';
import { X } from 'lucide-react';
import ProfileManagementSection from './ProfileManagementSection';

interface ProfileManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export const ProfileManagementModal: React.FC<ProfileManagementModalProps> = ({
  isOpen,
  onClose,
  onSaved,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150 overflow-y-auto">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-50 rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col my-8">
        {/* Header */}
        <div className="px-5 py-3.5 bg-white border-b border-slate-200 flex items-center justify-between shrink-0">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Edit Profile & Credentials</h3>
            <p className="text-[11px] text-slate-500">
              Update your public persona, verified competencies, and vocational history
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          <ProfileManagementSection
            isModal={true}
            onClose={onClose}
            onSaved={() => {
              if (onSaved) onSaved();
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default ProfileManagementModal;
