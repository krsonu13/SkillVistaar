import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Sparkles,
  Lock,
  Mail,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import ForgotPasswordModal from '../components/auth/ForgotPasswordModal';
import OtpVerificationModal from '../components/auth/OtpVerificationModal';
import InputField from '../components/common/InputField';
import Button from '../components/common/Button';
import Alert from '../components/common/Alert';
import { getDashboardPath } from '../types/auth';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, user: currentUser, accountType: currentAccountType, isLoading: authLoading } = useAuth();

  const from = (location.state as any)?.from?.pathname;

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  const [errors, setErrors] = useState<{ identifier?: string; password?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isUnverifiedUser, setIsUnverifiedUser] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState<string | null>(null);
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [otpModalOpen, setOtpModalOpen] = useState(false);

  // If already authenticated and not loading, redirect to dashboard
  useEffect(() => {
    if (isAuthenticated && !authLoading && currentUser) {
      const norm = currentUser.account_type;
      const vStatus = currentUser.verification_status;
      if (norm !== 'SUPER_ADMIN' && ['EMPLOYER', 'TRAINING_INSTITUTE', 'GOVERNMENT'].includes(norm) && vStatus !== 'APPROVED') {
        navigate('/verification-pending', { replace: true });
      } else {
        const destination = from || getDashboardPath(currentUser);
        navigate(destination, { replace: true });
      }
    }
  }, [isAuthenticated, authLoading, currentUser, currentAccountType, from, navigate]);

  const validate = () => {
    const newErrors: { identifier?: string; password?: string } = {};

    if (!identifier.trim()) {
      newErrors.identifier = 'Email or Mobile Number is required';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setIsUnverifiedUser(false);
    setLoginSuccess(null);

    if (!validate()) return;

    setIsLoading(true);
    try {
      const authUser = await login({
        identifier: identifier.trim(),
        password,
        rememberMe,
      });

      const norm = authUser.account_type;
      const vStatus = authUser.verification_status;

      setLoginSuccess('Authentication successful! Redirecting to workspace...');
      setTimeout(() => {
        if (norm !== 'SUPER_ADMIN' && ['EMPLOYER', 'TRAINING_INSTITUTE', 'GOVERNMENT'].includes(norm) && vStatus !== 'APPROVED') {
          navigate('/verification-pending', { replace: true });
        } else {
          const destination = from || getDashboardPath(authUser);
          navigate(destination, { replace: true });
        }
      }, 400);
    } catch (err: any) {
      const msg = err.message || 'Invalid credentials or connection error. Please retry.';
      const unverified = err.isUnverified || err.status === 403 || String(msg).toLowerCase().includes('unverified');
      setIsUnverifiedUser(unverified);
      setServerError(msg);
    } finally {
      setIsLoading(false);
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
                Skill • Opportunity • Growth
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500 hidden sm:inline">New to SkillVistaar?</span>
            <Link to="/signup">
              <Button variant="outline" size="sm" className="text-xs font-semibold">
                Create Account
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8">
        <div className="w-full max-w-md">
          {/* Card Wrapper */}
          <div className="bg-white rounded-xl shadow-card border border-slate-200 p-5 sm:p-6 space-y-5">
            {/* Card Heading */}
            <div className="space-y-1 text-center">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-teal-50 border border-teal-200/80 text-[11px] font-semibold text-teal-700">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Unified Account Sign In</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                Sign In to SkillVistaar
              </h1>
              <p className="text-xs text-slate-500">
                Enter your registered credentials to access your dashboard
              </p>
            </div>

            {/* Banners */}
            {serverError && (
              <div className="space-y-2">
                <Alert
                  type={isUnverifiedUser ? 'warning' : 'error'}
                  message={serverError}
                  onClose={() => setServerError(null)}
                />
                {isUnverifiedUser && (
                  <div className="bg-amber-50 border border-amber-200/80 rounded-lg p-2.5 flex items-center justify-between text-xs text-amber-900">
                    <span className="font-medium">Verification pending for this account.</span>
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      className="py-1 px-3 text-xs"
                      onClick={() => setOtpModalOpen(true)}
                    >
                      Verify Now
                    </Button>
                  </div>
                )}
              </div>
            )}

            {loginSuccess && (
              <Alert
                type="success"
                title="Authenticated"
                message={loginSuccess}
              />
            )}

            {/* Form */}
            <form onSubmit={handleLogin} className="space-y-4" noValidate>
              <InputField
                label="Email or Mobile Number"
                placeholder="e.g. rahul@domain.com or 9876543210"
                value={identifier}
                onChange={(e) => {
                  setIdentifier(e.target.value);
                  if (errors.identifier) setErrors({ ...errors, identifier: undefined });
                }}
                error={errors.identifier}
                leftIcon={<Mail className="w-4 h-4" />}
                required
                helperText="Use your registered email or 10-digit mobile number."
              />

              <InputField
                label="Password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errors.password) setErrors({ ...errors, password: undefined });
                }}
                error={errors.password}
                leftIcon={<Lock className="w-4 h-4" />}
                required
              />

              {/* Options Row: Remember Me & Forgot Password */}
              <div className="flex items-center justify-between text-xs pt-0.5">
                <label className="flex items-center gap-2 cursor-pointer select-none text-slate-600 hover:text-slate-900">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded text-teal-600 border-slate-300 focus:ring-teal-500/20"
                  />
                  <span className="font-medium">Remember this device</span>
                </label>

                <button
                  type="button"
                  onClick={() => setForgotModalOpen(true)}
                  className="font-semibold text-teal-700 hover:text-teal-800 transition"
                >
                  Forgot password?
                </button>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                fullWidth
                isLoading={isLoading}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                className="font-semibold text-xs sm:text-sm py-2.5 mt-2 shadow-sm"
              >
                Sign In
              </Button>
            </form>

            {/* Bottom Link to Signup */}
            <div className="text-center pt-2 text-xs text-slate-600 border-t border-slate-100">
              Don't have an account yet?{' '}
              <Link
                to="/signup"
                className="font-bold text-teal-700 hover:text-teal-800 underline underline-offset-2"
              >
                Create an Account
              </Link>
            </div>
          </div>

          {/* Compliance notice */}
          <p className="text-[11px] text-center text-slate-400 mt-4">
            Protected by national public key infrastructure & end-to-end statutory verification.
          </p>
        </div>
      </main>

      {/* Forgot Password Modal */}
      <ForgotPasswordModal
        isOpen={forgotModalOpen}
        onClose={() => setForgotModalOpen(false)}
        defaultIdentifier={identifier}
        accountType="candidate"
      />

      {/* OTP Verification Modal */}
      <OtpVerificationModal
        isOpen={otpModalOpen}
        onClose={() => setOtpModalOpen(false)}
        identifier={identifier.trim()}
        accountType="candidate"
        onSuccess={(authData) => {
          setOtpModalOpen(false);
          const targetRole = authData?.user?.account_type || authData?.user?.accountType || 'candidate';
          navigate(getDashboardPath(targetRole), { replace: true });
        }}
      />
    </div>
  );
};

export default LoginPage;
