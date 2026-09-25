import React from 'react';
import { Check, X } from 'lucide-react';

interface PasswordStrengthMeterProps {
  password?: string;
}

export const PasswordStrengthMeter: React.FC<PasswordStrengthMeterProps> = ({ password = '' }) => {
  const criteria = [
    { label: '8+ characters', met: password.length >= 8 },
    { label: 'Uppercase letter (A-Z)', met: /[A-Z]/.test(password) },
    { label: 'Number (0-9)', met: /[0-9]/.test(password) },
    { label: 'Special symbol (@$!%*#?&)', met: /[^A-Za-z0-9]/.test(password) },
  ];

  const score = criteria.filter((c) => c.met).length;

  const strengthLabels = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const barColors = [
    'bg-slate-200',
    'bg-rose-500',
    'bg-amber-500',
    'bg-teal-500',
    'bg-emerald-600',
  ];

  if (!password) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1.5 p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 text-xs">
      {/* Strength Bar */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium text-slate-500">
          Strength: <span className="font-semibold text-slate-800">{strengthLabels[score]}</span>
        </span>
        <div className="flex gap-1 flex-1 max-w-[120px] justify-end">
          {[1, 2, 3, 4].map((step) => (
            <div
              key={step}
              className={`h-1.5 flex-1 rounded-full transition-all duration-200 ${
                score >= step ? barColors[score] : 'bg-slate-200'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Criteria Grid */}
      <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-1">
        {criteria.map((item, idx) => (
          <div key={idx} className="flex items-center gap-1.5 text-[11px]">
            {item.met ? (
              <Check className="w-3 h-3 text-emerald-600 shrink-0" />
            ) : (
              <X className="w-3 h-3 text-slate-300 shrink-0" />
            )}
            <span className={item.met ? 'text-slate-700 font-medium' : 'text-slate-400'}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PasswordStrengthMeter;
