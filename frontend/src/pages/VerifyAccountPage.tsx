import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ShieldCheck, ArrowRight, Sparkles, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import Button from '../components/common/Button';
import InputField from '../components/common/InputField';
import { authApi } from '../services/api';
import { AccountType } from '../types/auth';

export const VerifyAccountPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialIdentifier = searchParams.get('identifier') || '';
  const initialType = (searchParams.get('type') as AccountType) || 'candidate';

  const [identifier, setIdentifier] = useState(initialIdentifier);
  const [otp, setOtp] = useState('');
  const [accountType] = useState<AccountType>(initialType);
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);

    if (!identifier.trim()) {
      setFeedback({ type: 'error', message: 'Email or phone number is required.' });
      return;
    }
    if (!otp.trim() || otp.trim().length !== 6) {
      setFeedback({ type: 'error', message: 'Please enter a valid 6-digit OTP code.' });
      return;
    }

    setIsLoading(true);
    try {
      await authApi.verifyOtp({
        identifier: identifier.trim(),
        otp: otp.trim(),
        accountType,
      });
      setFeedback({ type: 'success', message: 'Account verified successfully! Redirecting to workspace...' });
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'OTP verification failed. Please check the code and try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (!identifier.trim()) {
      setFeedback({ type: 'error', message: 'Please provide email or phone number to resend OTP.' });
      return;
    }
    setIsResending(true);
    setFeedback(null);
    try {
      const res = await authApi.resendOtp(identifier.trim(), accountType);
      if ((res as any)?.dev_otp) {
        setDevOtp((res as any).dev_otp);
      }
      setFeedback({ type: 'success', message: 'A new 6-digit verification code has been dispatched.' });
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to resend OTP code.',
      });
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      {/* Top Header */}
      <header className="w-full bg-white border-b border-slate-200/80 py-3 px-4 sm:px-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs">
              <Sparkles className="w-4 h-4 text-teal-200" />
            </div>
            <div>
              <span className="font-extrabold text-base tracking-tight text-slate-900">
                Skill<span className="text-teal-700">Vistaar</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] text-slate-400 font-medium ml-2 uppercase tracking-wider">
                Identity Verification
              </span>
            </div>
          </Link>
          <Link to="/login" className="text-xs font-semibold text-teal-700 hover:underline">
            Back to Sign In
          </Link>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200/80 p-6 sm:p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="mx-auto w-12 h-12 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-teal-700 mb-2">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">
              Verify Account Identity
            </h1>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              Enter the 6-digit one-time password (OTP) sent to your registered contact method.
            </p>
          </div>

          {/* Development OTP Banner */}
          {devOtp && (
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-dashed border-amber-400 rounded-xl p-4 text-center space-y-2 shadow-sm">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 text-amber-800 text-xs font-bold uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                Development OTP (Demo Mode)
              </div>
              <p className="text-xs text-slate-600">
                Live SMS delivery is disabled in development. Use this generated code to verify:
              </p>
              <div className="flex items-center justify-center gap-2 py-1">
                <span className="font-mono text-3xl font-extrabold tracking-[0.25em] text-amber-900 bg-amber-100/80 px-4 py-1.5 rounded-lg border border-amber-300 select-all">
                  {devOtp}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setOtp(devOtp)}
                className="inline-flex items-center gap-1 text-xs text-amber-800 hover:text-amber-950 font-semibold underline decoration-amber-400 underline-offset-2"
              >
                Click to auto-fill code
              </button>
            </div>
          )}

          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs font-semibold flex items-center gap-2 animate-in fade-in ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border border-rose-200 text-rose-800'
              }`}
            >
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}

          <form onSubmit={handleVerify} className="space-y-4">
            <InputField
              label="Registered Email or Mobile Phone"
              placeholder="e.g. user@example.com or 9876543210"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />

            <div>
              <InputField
                label="6-Digit Verification OTP"
                type="text"
                placeholder="123456"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="font-mono text-center tracking-widest text-lg font-bold"
                required
              />
              <div className="flex justify-between items-center text-[11px] pt-1 text-slate-500">
                <span>Didn't receive code?</span>
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={isResending}
                  className="text-teal-700 font-semibold hover:underline flex items-center gap-1 disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 ${isResending ? 'animate-spin' : ''}`} />
                  Resend OTP
                </button>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              fullWidth
              isLoading={isLoading}
              rightIcon={<ArrowRight className="w-4 h-4" />}
              className="mt-2 text-xs font-semibold"
            >
              Verify & Enter Workspace
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default VerifyAccountPage;
