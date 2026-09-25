import React from 'react';
import { User, Briefcase, GraduationCap, Landmark, Shield, CheckCircle2 } from 'lucide-react';
import { AccountType } from '../../types/auth';

interface AccountTypeSelectorProps {
  selectedType: AccountType;
  onChange: (type: AccountType) => void;
  layout?: 'grid' | 'tabs';
  compact?: boolean;
}

interface StakeholderOption {
  id: AccountType;
  label: string;
  badge: string;
  sublabel: string;
  icon: React.ComponentType<{ className?: string }>;
}

const STAKEHOLDERS: StakeholderOption[] = [
  {
    id: 'candidate',
    label: 'Candidate',
    badge: 'Job Seeker / Student',
    sublabel: 'Verified skills & career opportunities',
    icon: User,
  },
  {
    id: 'employer',
    label: 'Employer',
    badge: 'Enterprises & MSMEs',
    sublabel: 'Skill-indexed hiring pipeline',
    icon: Briefcase,
  },
  {
    id: 'institute',
    label: 'Training Institute',
    badge: 'Colleges & NSDC Centers',
    sublabel: 'Curriculum & batch certification',
    icon: GraduationCap,
  },
  {
    id: 'government',
    label: 'Government',
    badge: 'Ministries & Nodal Bodies',
    sublabel: 'Policy, analytics & scheme monitoring',
    icon: Landmark,
  },
  {
    id: 'admin',
    label: 'Super Admin',
    badge: 'Platform Authority',
    sublabel: 'Full ecosystem governance & oversight',
    icon: Shield,
  },
];

export const AccountTypeSelector: React.FC<AccountTypeSelectorProps> = ({
  selectedType,
  onChange,
  layout = 'grid',
  compact = false,
}) => {
  if (layout === 'tabs') {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-5 p-1 bg-slate-100/90 rounded-lg border border-slate-200/80 gap-1">
        {STAKEHOLDERS.map((s) => {
          const Icon = s.icon;
          const isSelected = selectedType === s.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => onChange(s.id)}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-xs font-semibold transition-all duration-150 ${
                isSelected
                  ? 'bg-white text-teal-800 shadow-xs border border-teal-600/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-teal-600' : 'text-slate-400'}`} />
              <span className="truncate">{s.label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`grid ${compact ? 'grid-cols-2 gap-2' : 'grid-cols-1 sm:grid-cols-2 gap-2.5'}`}>
      {STAKEHOLDERS.map((s) => {
        const Icon = s.icon;
        const isSelected = selectedType === s.id;
        return (
          <div
            key={s.id}
            onClick={() => onChange(s.id)}
            className={`cursor-pointer rounded-lg border p-2.5 transition-all duration-150 text-left relative flex items-start gap-2.5 ${
              isSelected
                ? 'border-teal-600 bg-teal-50/40 ring-1 ring-teal-600 shadow-xs'
                : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/70'
            }`}
          >
            <div
              className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 transition-colors ${
                isSelected
                  ? 'bg-teal-600 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              <Icon className="w-4 h-4" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1">
                <span className="text-xs font-bold text-slate-900 truncate">
                  {s.label}
                </span>
                {isSelected && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                )}
              </div>
              <span className="block text-[10px] font-medium text-teal-700 truncate">
                {s.badge}
              </span>
              <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                {s.sublabel}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default AccountTypeSelector;
