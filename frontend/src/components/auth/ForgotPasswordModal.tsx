import React, { useState } from 'react';
import { KeyRound, X, Mail, CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';
import InputField from '../common/InputField';
import Alert from '../common/Alert';
import { authService } from '../../api/authService';
import { AccountType } from '../../types/auth';

interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultIdentifier?: string;
  accountType: AccountType;
}

export const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({
  isOpen,
  onClose,
  defaultIdentifier = '',
  accountType,
}) => {
  const [identifier, setIdentifier] = useState(defaultIdentifier);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) {
      setError('Please enter your registered email or phone.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await authService.forgotPassword(identifier.trim(), accountType);
      setIsSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Unable to process reset request.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 p-5 sm:p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>

        {isSuccess ? (
          <div className="space-y-4 py-2">
            <div className="w-10 h-10 bg-teal-100 text-teal-700 rounded-full flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Reset Instructions Dispatched</h3>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                If an account exists for <span className="font-semibold text-slate-800">{identifier}</span> under{' '}
                <span className="capitalize font-semibold text-teal-700">{accountType}</span>, a secure recovery code has been sent.
              </p>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
              Please check your inbox or SMS. The recovery code will expire in 15 minutes.
            </div>
            <Button variant="primary" size="md" fullWidth onClick={onClose}>
              Back to Sign In
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center shrink-0">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Reset Your Password</h3>
                <p className="text-xs text-slate-500">
                  Recover access to your <span className="capitalize font-semibold text-teal-700">{accountType}</span> account
                </p>
              </div>
            </div>

            {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

            <InputField
              label="Registered Email or Mobile"
              placeholder="e.g. name@domain.gov.in or 9876543210"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              leftIcon={<Mail className="w-4 h-4" />}
              required
            />

            <div className="pt-2 flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="md"
                className="w-1/3"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-2/3"
                isLoading={isLoading}
              >
                Send Reset Code
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default ForgotPasswordModal;
