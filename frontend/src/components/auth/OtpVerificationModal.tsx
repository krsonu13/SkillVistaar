import React, { useState, useRef, useEffect } from 'react';
import { ShieldCheck, X, RefreshCw, CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';
import Alert from '../common/Alert';
import { authService } from '../../api/authService';
import { AccountType, AuthResponse } from '../../types/auth';
import { useAuth } from '../../context/AuthContext';

interface OtpVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  identifier: string;
  accountType: AccountType;
  onSuccess: (authData?: AuthResponse) => void;
}

export const OtpVerificationModal: React.FC<OtpVerificationModalProps> = ({
  isOpen,
  onClose,
  identifier,
  accountType,
  onSuccess,
}) => {
  const { setAuthSession } = useAuth();
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [timer, setTimer] = useState(30);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (isOpen) {
      setDigits(['', '', '', '', '', '']);
      setError(null);
      setIsSuccess(false);
      setTimer(30);
      setTimeout(() => {
        inputsRef.current[0]?.focus();
      }, 100);
    }
  }, [isOpen]);

  useEffect(() => {
    let interval: any;
    if (isOpen && timer > 0) {
      interval = setInterval(() => {
        setTimer((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isOpen, timer]);

  if (!isOpen) return null;

  const handleChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newDigits = [...digits];
    // Handle single character or paste
    if (value.length > 1) {
      const pasted = value.slice(0, 6).split('');
      pasted.forEach((char, idx) => {
        if (index + idx < 6) newDigits[index + idx] = char;
      });
      setDigits(newDigits);
      const nextFocus = Math.min(index + pasted.length, 5);
      inputsRef.current[nextFocus]?.focus();
      return;
    }

    newDigits[index] = value;
    setDigits(newDigits);
    setError(null);

    // Auto advance
    if (value && index < 5) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handleVerify = async () => {
    const code = digits.join('');
    if (code.length < 6) {
      setError('Please enter all 6 digits of the OTP.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const resp = await authService.verifyOtp({
        identifier,
        accountType,
        otp: code,
      });

      const token = resp.access_token || resp.token;
      if (token && resp.user) {
        setAuthSession(token, resp.user, resp.refresh_token);
      }

      setIsSuccess(true);
      setTimeout(() => {
        onSuccess(resp);
      }, 900);
    } catch (err: any) {
      setError(err.message || 'Verification failed. Please enter the valid 6-digit verification code sent to your contact.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (timer > 0) return;
    try {
      await authService.resendOtp(identifier, accountType);
      setTimer(30);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Could not resend OTP.');
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
          <div className="text-center py-6 space-y-3">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Verification Complete!</h3>
            <p className="text-xs text-slate-500">
              Your identity has been verified in the national registry. Redirecting to your workspace...
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Verify Your Account</h3>
                <p className="text-xs text-slate-500">
                  Enter the 6-digit security code sent to{' '}
                  <span className="font-semibold text-slate-700">{identifier}</span>
                </p>
              </div>
            </div>

            {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

            {/* OTP 6-Digit Boxes */}
            <div className="flex justify-between gap-2 pt-2">
              {digits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (inputsRef.current[idx] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={digit}
                  onChange={(e) => handleChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  className="w-11 h-12 text-center text-lg font-bold rounded-lg border border-slate-300 focus:border-teal-600 focus:ring-2 focus:ring-teal-500/20 text-slate-900 outline-none transition bg-white"
                />
              ))}
            </div>

            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-slate-500">Didn't receive code?</span>
              {timer > 0 ? (
                <span className="text-slate-400 font-medium">Resend in {timer}s</span>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  className="text-teal-600 hover:text-teal-700 font-semibold flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Resend OTP
                </button>
              )}
            </div>

            <div className="pt-2 flex gap-2">
              <Button
                variant="outline"
                size="md"
                className="w-1/3"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="md"
                className="w-2/3"
                isLoading={isLoading}
                onClick={handleVerify}
              >
                Verify & Proceed
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OtpVerificationModal;
