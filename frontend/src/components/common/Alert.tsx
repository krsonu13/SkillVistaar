import React from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

interface AlertProps {
  type?: 'error' | 'success' | 'info' | 'warning';
  title?: string;
  message: string;
  onClose?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  type = 'info',
  title,
  message,
  onClose,
  className = '',
}) => {
  const styles = {
    error: {
      bg: 'bg-rose-50 border-rose-200 text-rose-800',
      icon: <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />,
    },
    success: {
      bg: 'bg-emerald-50 border-emerald-200 text-emerald-800',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />,
    },
    info: {
      bg: 'bg-teal-50 border-teal-200 text-teal-800',
      icon: <Info className="w-4 h-4 text-teal-600 shrink-0" />,
    },
    warning: {
      bg: 'bg-amber-50 border-amber-200 text-amber-800',
      icon: <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />,
    },
  };

  return (
    <div
      className={`flex items-start gap-2.5 p-3 rounded-lg border text-xs sm:text-sm ${styles[type].bg} ${className}`}
      role="alert"
    >
      <div className="mt-0.5">{styles[type].icon}</div>
      <div className="flex-1">
        {title && <p className="font-semibold">{title}</p>}
        <p className="font-medium text-slate-700 leading-relaxed">{message}</p>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-700 transition rounded-md"
          aria-label="Dismiss alert"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

export default Alert;
