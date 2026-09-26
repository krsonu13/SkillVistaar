import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  User,
  GraduationCap,
  Landmark,
  Lock,
  Mail,
  Phone,
  Building,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  RotateCw,
  AtSign,
  Loader2,
} from 'lucide-react';
import AccountTypeSelector from '../components/auth/AccountTypeSelector';
import PasswordStrengthMeter from '../components/auth/PasswordStrengthMeter';
import InputField from '../components/common/InputField';
import SelectField from '../components/common/SelectField';
import Button from '../components/common/Button';
import Alert from '../components/common/Alert';
import Badge from '../components/common/Badge';
import { AccountType, getDashboardPath } from '../types/auth';
import { authService } from '../api/authService';
import { useAuth } from '../context/AuthContext';

const INDIAN_STATES = [
  { value: 'Andhra Pradesh', label: 'Andhra Pradesh' },
  { value: 'Assam', label: 'Assam' },
  { value: 'Bihar', label: 'Bihar' },
  { value: 'Delhi (NCT)', label: 'Delhi (NCT)' },
  { value: 'Gujarat', label: 'Gujarat' },
  { value: 'Haryana', label: 'Haryana' },
  { value: 'Karnataka', label: 'Karnataka' },
  { value: 'Kerala', label: 'Kerala' },
  { value: 'Madhya Pradesh', label: 'Madhya Pradesh' },
  { value: 'Maharashtra', label: 'Maharashtra' },
  { value: 'Odisha', label: 'Odisha' },
  { value: 'Punjab', label: 'Punjab' },
  { value: 'Rajasthan', label: 'Rajasthan' },
  { value: 'Tamil Nadu', label: 'Tamil Nadu' },
  { value: 'Telangana', label: 'Telangana' },
  { value: 'Uttar Pradesh', label: 'Uttar Pradesh' },
  { value: 'West Bengal', label: 'West Bengal' },
];

type SignupStep = 
  | 'PERSONA_AND_PRIMARY'
  | 'VERIFY_PRIMARY'
  | 'SECONDARY_CONTACT'
  | 'VERIFY_SECONDARY'
  | 'DETAILS_AND_TERMS';

export const SignupPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuthSession } = useAuth();

  // Selected persona / account type
  const [accountType, setAccountType] = useState<AccountType>(() => {
    const rawType = searchParams.get('type');
    if (rawType && ['candidate', 'employer', 'institute', 'government'].includes(rawType)) {
      return rawType as AccountType;
    }
    return 'candidate';
  });

  // Step state
  const [currentStep, setCurrentStep] = useState<SignupStep>('PERSONA_AND_PRIMARY');
  const [sessionToken, setSessionToken] = useState<string>('');

  // Primary Contact State
  const [primaryChannel, setPrimaryChannel] = useState<'EMAIL' | 'PHONE'>('EMAIL');
  const [primaryIdentifier, setPrimaryIdentifier] = useState<string>('');
  const [primaryOtp, setPrimaryOtp] = useState<string>('');
  const [, setPrimaryVerified] = useState<boolean>(false);

  // Secondary Contact State
  const [secondaryChannel, setSecondaryChannel] = useState<'EMAIL' | 'PHONE'>('PHONE');
  const [secondaryIdentifier, setSecondaryIdentifier] = useState<string>('');
  const [secondaryOtp, setSecondaryOtp] = useState<string>('');
  const [, setSecondaryVerified] = useState<boolean>(false);

  // Development OTP State & Verification States
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [primaryStatus, setPrimaryStatus] = useState<'idle' | 'verified' | 'invalid' | 'expired'>('idle');
  const [secondaryStatus, setSecondaryStatus] = useState<'idle' | 'verified' | 'invalid' | 'expired'>('idle');

  // Countdown timers
  const [timerPrimary, setTimerPrimary] = useState<number>(600);
  const [timerSecondary, setTimerSecondary] = useState<number>(600);
  const [cooldownPrimary, setCooldownPrimary] = useState<number>(0);
  const [cooldownSecondary, setCooldownSecondary] = useState<number>(0);

  // Additional Details State
  // Candidate
  const [candidateName, setCandidateName] = useState('');
  const [candidateStatus, setCandidateStatus] = useState('student');
  const [candidateSkill, setCandidateSkill] = useState('Information Technology');
  const [candidateState, setCandidateState] = useState('Maharashtra');

  // Employer
  const [employerCompany, setEmployerCompany] = useState('');
  const [employerIndustry, setEmployerIndustry] = useState('IT & Software');
  const [employerSize, setEmployerSize] = useState('11-50');
  const [employerGst, setEmployerGst] = useState('');
  const [employerWebsite, setEmployerWebsite] = useState('');

  // Institute
  const [instName, setInstName] = useState('');
  const [instAffiliation, setInstAffiliation] = useState('NCVET');
  const [instState, setInstState] = useState('Maharashtra');
  const [instCity, setInstCity] = useState('');
  const [instDomain, setInstDomain] = useState('Automotive');

  // Government
  const [govtDept, setGovtDept] = useState('');
  const [govtOfficer, setGovtOfficer] = useState('');
  const [govtDesignation, setGovtDesignation] = useState('');
  const [govtState, setGovtState] = useState('Maharashtra');
  const [govtLevel, setGovtLevel] = useState<'Central' | 'State' | 'District'>('State');

  // Password & Security
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);

  // Username State
  const [username, setUsername] = useState('');
  const [usernameStatus, setUsernameStatus] = useState<'idle' | 'checking' | 'available' | 'unavailable'>('idle');
  const [usernameMessage, setUsernameMessage] = useState<string>('');

  // Status & Feedback
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Real-time username validation effect
  useEffect(() => {
    const clean = username.trim().toLowerCase().replace(/^@/, '');
    if (!clean) {
      setUsernameStatus('idle');
      setUsernameMessage('');
      return;
    }

    if (clean.length < 3) {
      setUsernameStatus('unavailable');
      setUsernameMessage('Username must be at least 3 characters.');
      return;
    }

    if (!/^[a-zA-Z0-9_.]{3,30}$/.test(clean)) {
      setUsernameStatus('unavailable');
      setUsernameMessage('Only letters, numbers, underscores, and dots are allowed (3-30 chars).');
      return;
    }

    setUsernameStatus('checking');
    const timer = setTimeout(async () => {
      try {
        const res = await authService.checkUsernameAvailability(clean);
        if (res.available) {
          setUsernameStatus('available');
          setUsernameMessage(`@${res.username} is available!`);
        } else {
          setUsernameStatus('unavailable');
          setUsernameMessage(res.message);
        }
      } catch {
        setUsernameStatus('idle');
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [username]);

  useEffect(() => {
    const rawType = searchParams.get('type');
    if (rawType && ['candidate', 'employer', 'institute', 'government'].includes(rawType)) {
      setAccountType(rawType as AccountType);
    }
  }, [searchParams]);

  // Timers countdown
  useEffect(() => {
    let interval: any;
    if (currentStep === 'VERIFY_PRIMARY' && timerPrimary > 0) {
      interval = setInterval(() => setTimerPrimary((t) => t - 1), 1000);
    } else if (currentStep === 'VERIFY_SECONDARY' && timerSecondary > 0) {
      interval = setInterval(() => setTimerSecondary((t) => t - 1), 1000);
    }
    return () => clearInterval(interval);
  }, [currentStep, timerPrimary, timerSecondary]);

  // Cooldown countdowns
  useEffect(() => {
    let interval: any;
    if (cooldownPrimary > 0 || cooldownSecondary > 0) {
      interval = setInterval(() => {
        setCooldownPrimary((c) => (c > 0 ? c - 1 : 0));
        setCooldownSecondary((c) => (c > 0 ? c - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [cooldownPrimary, cooldownSecondary]);

  // Format seconds to mm:ss
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // STEP 1: Send Primary OTP
  const handleSendPrimaryOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setFieldErrors({});

    const val = primaryIdentifier.trim();
    if (!val) {
      setFieldErrors({ primary: primaryChannel === 'EMAIL' ? 'Please enter an email address.' : 'Please enter a mobile phone number.' });
      return;
    }
    if (primaryChannel === 'EMAIL' && (!val.includes('@') || val.length < 5)) {
      setFieldErrors({ primary: 'Please enter a valid email address.' });
      return;
    }
    if (primaryChannel === 'PHONE' && val.replace(/\D/g, '').length < 10) {
      setFieldErrors({ primary: 'Please enter a valid 10-digit mobile number.' });
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.startSignupVerification(accountType, primaryChannel, val);
      setSessionToken(res.session_token);
      setTimerPrimary(res.expires_in_seconds || 600);
      setDevOtp(res.dev_otp || null);
      setPrimaryStatus('idle');
      setSuccessNotice(`Verification code sent to ${val}.`);
      setCurrentStep('VERIFY_PRIMARY');
    } catch (err: any) {
      const msg = err.message || 'Failed to send verification code.';
      setServerError(msg);
      const match = msg.match(/wait\s+(\d+)\s+seconds/i);
      if (match) {
        setCooldownPrimary(parseInt(match[1], 10));
      } else if (err.status === 429) {
        setCooldownPrimary(60);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // STEP 2: Verify Primary OTP
  const handleVerifyPrimaryOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setFieldErrors({});

    const otp = primaryOtp.trim();
    if (otp.length !== 6 || !/^\d+$/.test(otp)) {
      setFieldErrors({ otp: 'Please enter the 6-digit verification code.' });
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.verifyPrimaryContact(sessionToken, otp);
      setPrimaryVerified(true);
      setPrimaryStatus('verified');
      const nextChan = res.next_channel === 'EMAIL' ? 'EMAIL' : 'PHONE';
      setSecondaryChannel(nextChan);
      setSuccessNotice(res.message);
      setDevOtp(null);
      setCurrentStep('SECONDARY_CONTACT');
    } catch (err: any) {
      const isExpired = err.status === 410 || (err.message && err.message.toLowerCase().includes('expired'));
      setPrimaryStatus(isExpired ? 'expired' : 'invalid');
      setServerError(err.message || 'Invalid verification code.');
    } finally {
      setIsLoading(false);
    }
  };

  // STEP 3: Send Secondary OTP
  const handleSendSecondaryOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setFieldErrors({});

    const val = secondaryIdentifier.trim();
    if (!val) {
      setFieldErrors({ secondary: secondaryChannel === 'EMAIL' ? 'Please enter an email address.' : 'Please enter a mobile number.' });
      return;
    }
    if (secondaryChannel === 'EMAIL' && (!val.includes('@') || val.length < 5)) {
      setFieldErrors({ secondary: 'Please enter a valid email address.' });
      return;
    }
    if (secondaryChannel === 'PHONE' && val.replace(/\D/g, '').length < 10) {
      setFieldErrors({ secondary: 'Please enter a valid 10-digit mobile number.' });
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.sendSecondaryOtp(sessionToken, secondaryChannel, val);
      setTimerSecondary(res.expires_in_seconds || 600);
      setDevOtp(res.dev_otp || null);
      setSecondaryStatus('idle');
      setSuccessNotice(`Verification code sent to ${val}.`);
      setCurrentStep('VERIFY_SECONDARY');
    } catch (err: any) {
      const msg = err.message || 'Failed to send secondary verification code.';
      setServerError(msg);
      const match = msg.match(/wait\s+(\d+)\s+seconds/i);
      if (match) {
        setCooldownSecondary(parseInt(match[1], 10));
      } else if (err.status === 429) {
        setCooldownSecondary(60);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // STEP 4: Verify Secondary OTP
  const handleVerifySecondaryOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setFieldErrors({});

    const otp = secondaryOtp.trim();
    if (otp.length !== 6 || !/^\d+$/.test(otp)) {
      setFieldErrors({ otp: 'Please enter the 6-digit verification code.' });
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.verifySecondaryContact(sessionToken, otp);
      setSecondaryVerified(true);
      setSecondaryStatus('verified');
      setSuccessNotice(res.message);
      setDevOtp(null);
      setCurrentStep('DETAILS_AND_TERMS');
    } catch (err: any) {
      const isExpired = err.status === 410 || (err.message && err.message.toLowerCase().includes('expired'));
      setSecondaryStatus(isExpired ? 'expired' : 'invalid');
      setServerError(err.message || 'Invalid verification code.');
    } finally {
      setIsLoading(false);
    }
  };

  // STEP 5: Complete Account Creation
  const handleCompleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    setFieldErrors({});

    const errs: Record<string, string> = {};
    if (!password) errs.password = 'Password is required.';
    else if (password.length < 8) errs.password = 'Password must be at least 8 characters.';
    if (password !== confirmPassword) errs.confirmPassword = 'Passwords do not match.';
    if (!termsAccepted) errs.terms = 'You must accept the Terms of Service and Privacy Policy.';

    if (accountType === 'candidate' && !candidateName.trim()) {
      errs.name = 'Full name is required.';
    } else if (accountType === 'employer' && !employerCompany.trim()) {
      errs.company = 'Company name is required.';
    } else if (accountType === 'institute' && !instName.trim()) {
      errs.institute = 'Institute name is required.';
    } else if (accountType === 'government') {
      if (!govtDept.trim()) errs.dept = 'Department name is required.';
      if (!govtOfficer.trim()) errs.officer = 'Nodal officer name is required.';
    }

    if (username.trim()) {
      if (usernameStatus === 'unavailable') {
        errs.username = usernameMessage || 'Please choose an available username.';
      }
    }

    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }

    setIsLoading(true);

    let additionalData: Record<string, any> = {};
    if (username.trim()) {
      additionalData.username = username.trim().toLowerCase().replace(/^@/, '');
    }

    if (accountType === 'candidate') {
      additionalData = {
        ...additionalData,
        fullName: candidateName,
        status: candidateStatus,
        primarySkill: candidateSkill,
        state: candidateState,
      };
    } else if (accountType === 'employer') {
      additionalData = {
        ...additionalData,
        companyName: employerCompany,
        industry: employerIndustry,
        companySize: employerSize,
        gstOrCin: employerGst,
        website: employerWebsite,
      };
    } else if (accountType === 'institute') {
      additionalData = {
        ...additionalData,
        instituteName: instName,
        affiliationBody: instAffiliation,
        state: instState,
        city: instCity,
        domain: instDomain,
      };
    } else {
      additionalData = {
        ...additionalData,
        departmentName: govtDept,
        nodalOfficerName: govtOfficer,
        designation: govtDesignation,
        state: govtState,
        level: govtLevel,
      };
    }

    try {
      const resp = await authService.completeSignup(
        sessionToken,
        password,
        termsAccepted,
        additionalData
      );

      if (resp.token && resp.user) {
        setAuthSession(resp.token, resp.user, resp.refresh_token);
        const vStatus = resp.user.verification_status;
        const norm = resp.user.account_type;

        // Redirect unverified institutional accounts to the verification-pending gateway
        if (norm !== 'SUPER_ADMIN' && ['EMPLOYER', 'TRAINING_INSTITUTE', 'GOVERNMENT'].includes(norm) && vStatus !== 'APPROVED') {
          navigate('/verification-pending', { replace: true });
        } else {
          const dest = getDashboardPath(resp.user.account_type || accountType);
          navigate(dest, { replace: true });
        }
      } else {
        navigate(`/login?type=${accountType}&registered=1`, { replace: true });
      }
    } catch (err: any) {
      setServerError(err.message || 'Account creation failed. Please check details.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step indices
  const stepMap: Record<SignupStep, number> = {
    PERSONA_AND_PRIMARY: 1,
    VERIFY_PRIMARY: 2,
    SECONDARY_CONTACT: 3,
    VERIFY_SECONDARY: 4,
    DETAILS_AND_TERMS: 5,
  };

  const getEmailAndPhoneDisplay = () => {
    const email = primaryChannel === 'EMAIL' ? primaryIdentifier : secondaryIdentifier;
    const phone = primaryChannel === 'PHONE' ? primaryIdentifier : secondaryIdentifier;
    return { email, phone };
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
            <span className="text-slate-500 hidden sm:inline">Already registered?</span>
            <Link to={`/login?type=${accountType}`}>
              <Button variant="outline" size="sm" className="text-xs font-semibold">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 py-6 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto w-full">
        <div className="bg-white rounded-xl shadow-card border border-slate-200 p-5 sm:p-8 space-y-6">
          {/* Progress Header */}
          <div className="border-b border-slate-100 pb-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-700">
                Step {stepMap[currentStep]} of 5 — Sequential Dual-Contact Onboarding
              </span>
              <Badge variant="teal" size="sm">
                Real OTP Verification
              </Badge>
            </div>

            {/* Stepper Bar */}
            <div className="grid grid-cols-5 gap-1.5 pt-1">
              {[1, 2, 3, 4, 5].map((s) => (
                <div
                  key={s}
                  className={`h-1.5 rounded-full transition-colors ${
                    stepMap[currentStep] >= s ? 'bg-teal-600' : 'bg-slate-200'
                  }`}
                />
              ))}
            </div>

            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight pt-1">
              {currentStep === 'PERSONA_AND_PRIMARY' && 'Choose Persona & Primary Contact'}
              {currentStep === 'VERIFY_PRIMARY' && `Verify Primary Contact (${primaryChannel})`}
              {currentStep === 'SECONDARY_CONTACT' && `Enter Secondary Contact (${secondaryChannel})`}
              {currentStep === 'VERIFY_SECONDARY' && `Verify Secondary Contact (${secondaryChannel})`}
              {currentStep === 'DETAILS_AND_TERMS' && 'Complete Profile & Accept Terms'}
            </h1>
            <p className="text-xs text-slate-500">
              SkillVistaar requires verified dual-contact credentials (mobile & email) before activating your account.
            </p>
          </div>

          {/* Alert messages */}
          {serverError && (
            <div className="space-y-2">
              <Alert
                type={serverError.toLowerCase().includes('already registered') ? 'warning' : 'error'}
                title={serverError.toLowerCase().includes('already registered') ? 'Account Exists' : undefined}
                message={serverError}
                onClose={() => setServerError(null)}
              />
              {serverError.toLowerCase().includes('already registered') && (
                <div className="bg-amber-50 border border-amber-200/90 rounded-lg p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-amber-950">
                  <span>An account with these credentials already exists. You can sign in directly.</span>
                  <Link to={`/login?type=${accountType}`}>
                    <Button type="button" variant="primary" size="sm" className="py-1 px-3 text-xs shrink-0">
                      Sign In Now
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          )}

          {successNotice && (
            <Alert
              type="success"
              message={successNotice}
              onClose={() => setSuccessNotice(null)}
            />
          )}

          {/* ========================================================= */}
          {/* STEP 1: Persona & Primary Contact */}
          {/* ========================================================= */}
          {currentStep === 'PERSONA_AND_PRIMARY' && (
            <form onSubmit={handleSendPrimaryOtp} className="space-y-6">
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  1. Select Account Persona
                </label>
                <AccountTypeSelector
                  selectedType={accountType}
                  onChange={(type) => setAccountType(type)}
                  layout="grid"
                  compact={false}
                />
              </div>

              <div className="border-t border-slate-100 pt-5 space-y-4">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  2. Choose Primary Verification Method
                </label>

                <div className="flex gap-4">
                  <label className={`flex-1 flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition ${
                    primaryChannel === 'EMAIL' ? 'border-teal-600 bg-teal-50/50 text-teal-900' : 'border-slate-200 hover:border-slate-300'
                  }`}>
                    <input
                      type="radio"
                      name="primaryChannel"
                      checked={primaryChannel === 'EMAIL'}
                      onChange={() => {
                        setPrimaryChannel('EMAIL');
                        setPrimaryIdentifier('');
                        setFieldErrors({});
                      }}
                      className="text-teal-600 focus:ring-teal-500"
                    />
                    <Mail className="w-4 h-4 text-teal-600 shrink-0" />
                    <div>
                      <div className="text-xs font-bold">Email Address</div>
                      <div className="text-[11px] text-slate-500">Receive 6-digit code via SMTP email</div>
                    </div>
                  </label>

                  <label className={`flex-1 flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition ${
                    primaryChannel === 'PHONE' ? 'border-teal-600 bg-teal-50/50 text-teal-900' : 'border-slate-200 hover:border-slate-300'
                  }`}>
                    <input
                      type="radio"
                      name="primaryChannel"
                      checked={primaryChannel === 'PHONE'}
                      onChange={() => {
                        setPrimaryChannel('PHONE');
                        setPrimaryIdentifier('');
                        setFieldErrors({});
                      }}
                      className="text-teal-600 focus:ring-teal-500"
                    />
                    <Phone className="w-4 h-4 text-teal-600 shrink-0" />
                    <div>
                      <div className="text-xs font-bold">Mobile Phone</div>
                      <div className="text-[11px] text-slate-500">Receive 6-digit code via SMS</div>
                    </div>
                  </label>
                </div>

                <InputField
                  label={primaryChannel === 'EMAIL' ? 'Official / Personal Email Address' : '10-Digit Mobile Number'}
                  type={primaryChannel === 'EMAIL' ? 'email' : 'tel'}
                  placeholder={primaryChannel === 'EMAIL' ? 'e.g. yourname@example.com' : 'e.g. 9876543210'}
                  value={primaryIdentifier}
                  onChange={(e) => setPrimaryIdentifier(e.target.value)}
                  error={fieldErrors.primary}
                  leftIcon={primaryChannel === 'EMAIL' ? <Mail className="w-4 h-4 text-slate-400" /> : <Phone className="w-4 h-4 text-slate-400" />}
                  required
                />
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isLoading}
                  disabled={isLoading || cooldownPrimary > 0}
                  className="w-full justify-center"
                >
                  {cooldownPrimary > 0 ? (
                    `Please wait ${cooldownPrimary}s`
                  ) : (
                    <>Send Verification Code <ArrowRight className="w-4 h-4 ml-1.5" /></>
                  )}
                </Button>
              </div>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 2: Verify Primary Contact */}
          {/* ========================================================= */}
          {currentStep === 'VERIFY_PRIMARY' && (
            <form onSubmit={handleVerifyPrimaryOtp} className="space-y-6">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  {primaryChannel === 'EMAIL' ? <Mail className="w-4 h-4 text-teal-600" /> : <Phone className="w-4 h-4 text-teal-600" />}
                  <span>Code dispatched to: <strong>{primaryIdentifier}</strong></span>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentStep('PERSONA_AND_PRIMARY')}
                  className="text-teal-700 hover:underline font-semibold"
                >
                  Change
                </button>
              </div>

              {/* Development OTP Banner */}
              {devOtp && (
                <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-dashed border-amber-400 rounded-xl p-4 text-center space-y-2 shadow-sm">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 text-amber-800 text-xs font-bold uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                    Development OTP (Demo Mode)
                  </div>
                  <p className="text-xs text-slate-600">
                    Live SMS delivery is disabled in development. Use this generated 6-digit code to verify:
                  </p>
                  <div className="flex items-center justify-center gap-2 py-1">
                    <span className="font-mono text-3xl font-extrabold tracking-[0.25em] text-amber-900 bg-amber-100/80 px-4 py-1.5 rounded-lg border border-amber-300 select-all">
                      {devOtp}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setPrimaryOtp(devOtp);
                      setFieldErrors((prev) => {
                        const next = { ...prev };
                        delete next.otp;
                        return next;
                      });
                    }}
                    className="inline-flex items-center gap-1 text-xs text-amber-800 hover:text-amber-950 font-semibold underline decoration-amber-400 underline-offset-2"
                  >
                    Click to auto-fill code
                  </button>
                </div>
              )}

              {/* Status Banners */}
              {primaryStatus === 'verified' && (
                <div className="bg-emerald-50 border border-emerald-300 rounded-lg p-3 flex items-center gap-2 text-xs text-emerald-800 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Verified! Proceeding to next step...</span>
                </div>
              )}
              {primaryStatus === 'invalid' && (
                <div className="bg-rose-50 border border-rose-300 rounded-lg p-3 flex items-center gap-2 text-xs text-rose-800 font-semibold">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>Invalid verification code. Please check the code and try again.</span>
                </div>
              )}
              {(primaryStatus === 'expired' || timerPrimary === 0) && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 flex items-center gap-2 text-xs text-amber-800 font-semibold">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Verification code has expired (10-minute limit). Please click "Resend Code" below.</span>
                </div>
              )}

              <div className="space-y-2">
                <InputField
                  label="Enter 6-Digit Verification Code"
                  type="text"
                  placeholder="• • • • • •"
                  maxLength={6}
                  value={primaryOtp}
                  onChange={(e) => {
                    setPrimaryOtp(e.target.value.replace(/\D/g, ''));
                    if (primaryStatus !== 'idle') setPrimaryStatus('idle');
                  }}
                  error={fieldErrors.otp}
                  className="text-center font-mono text-xl tracking-widest"
                  required
                />
                <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                  <span>Code expires in: <strong className="font-mono text-slate-800">{formatTime(timerPrimary)}</strong></span>
                  <button
                    type="button"
                    onClick={handleSendPrimaryOtp}
                    disabled={isLoading || timerPrimary > 540}
                    className="text-teal-700 hover:underline font-semibold disabled:text-slate-400 flex items-center gap-1"
                  >
                    <RotateCw className="w-3 h-3" />
                    {timerPrimary > 540 ? `Resend in ${timerPrimary - 540}s` : 'Resend Code'}
                  </button>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  onClick={() => setCurrentStep('PERSONA_AND_PRIMARY')}
                  className="flex-1 justify-center"
                >
                  <ArrowLeft className="w-4 h-4 mr-1.5" /> Back
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isLoading}
                  className="flex-1 justify-center"
                >
                  Verify Primary Contact <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              </div>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 3: Secondary Contact Entry */}
          {/* ========================================================= */}
          {currentStep === 'SECONDARY_CONTACT' && (
            <form onSubmit={handleSendSecondaryOtp} className="space-y-6">
              {/* Primary verified banner */}
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex items-center gap-2 text-xs text-emerald-800 font-medium">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Primary verified: <strong>{primaryIdentifier}</strong> ({primaryChannel})</span>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Enter Alternate Contact ({secondaryChannel})
                  </label>
                  <span className="text-[11px] text-teal-700 font-semibold">Dual-Verification Required</span>
                </div>
                <p className="text-xs text-slate-500">
                  To prevent account takeover and guarantee communication reliability, SkillVistaar requires both email and mobile to be confirmed.
                </p>

                <InputField
                  label={secondaryChannel === 'PHONE' ? '10-Digit Mobile Phone Number' : 'Personal / Official Email Address'}
                  type={secondaryChannel === 'PHONE' ? 'tel' : 'email'}
                  placeholder={secondaryChannel === 'PHONE' ? 'e.g. 9876543210' : 'e.g. user@example.com'}
                  value={secondaryIdentifier}
                  onChange={(e) => setSecondaryIdentifier(e.target.value)}
                  error={fieldErrors.secondary}
                  leftIcon={secondaryChannel === 'PHONE' ? <Phone className="w-4 h-4 text-slate-400" /> : <Mail className="w-4 h-4 text-slate-400" />}
                  required
                />
              </div>

              <div className="flex gap-3 pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isLoading}
                  disabled={isLoading || cooldownSecondary > 0}
                  className="w-full justify-center"
                >
                  {cooldownSecondary > 0 ? (
                    `Please wait ${cooldownSecondary}s`
                  ) : (
                    <>Send Verification Code to {secondaryChannel.toLowerCase()} <ArrowRight className="w-4 h-4 ml-1.5" /></>
                  )}
                </Button>
              </div>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 4: Verify Secondary Contact */}
          {/* ========================================================= */}
          {currentStep === 'VERIFY_SECONDARY' && (
            <form onSubmit={handleVerifySecondaryOtp} className="space-y-6">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  {secondaryChannel === 'EMAIL' ? <Mail className="w-4 h-4 text-teal-600" /> : <Phone className="w-4 h-4 text-teal-600" />}
                  <span>Code dispatched to: <strong>{secondaryIdentifier}</strong></span>
                </div>
                <button
                  type="button"
                  onClick={() => setCurrentStep('SECONDARY_CONTACT')}
                  className="text-teal-700 hover:underline font-semibold"
                >
                  Change
                </button>
              </div>

              {/* Development OTP Banner */}
              {devOtp && (
                <div className="bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-dashed border-amber-400 rounded-xl p-4 text-center space-y-2 shadow-sm">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 text-amber-800 text-xs font-bold uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                    Development OTP (Demo Mode)
                  </div>
                  <p className="text-xs text-slate-600">
                    Live SMS delivery is disabled in development. Use this generated 6-digit code to verify:
                  </p>
                  <div className="flex items-center justify-center gap-2 py-1">
                    <span className="font-mono text-3xl font-extrabold tracking-[0.25em] text-amber-900 bg-amber-100/80 px-4 py-1.5 rounded-lg border border-amber-300 select-all">
                      {devOtp}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSecondaryOtp(devOtp);
                      setFieldErrors((prev) => {
                        const next = { ...prev };
                        delete next.otp;
                        return next;
                      });
                    }}
                    className="inline-flex items-center gap-1 text-xs text-amber-800 hover:text-amber-950 font-semibold underline decoration-amber-400 underline-offset-2"
                  >
                    Click to auto-fill code
                  </button>
                </div>
              )}

              {/* Status Banners */}
              {secondaryStatus === 'verified' && (
                <div className="bg-emerald-50 border border-emerald-300 rounded-lg p-3 flex items-center gap-2 text-xs text-emerald-800 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Verified! Proceeding to next step...</span>
                </div>
              )}
              {secondaryStatus === 'invalid' && (
                <div className="bg-rose-50 border border-rose-300 rounded-lg p-3 flex items-center gap-2 text-xs text-rose-800 font-semibold">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>Invalid verification code. Please check the code and try again.</span>
                </div>
              )}
              {(secondaryStatus === 'expired' || timerSecondary === 0) && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 flex items-center gap-2 text-xs text-amber-800 font-semibold">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Verification code has expired (10-minute limit). Please click "Resend Code" below.</span>
                </div>
              )}

              <div className="space-y-2">
                <InputField
                  label="Enter 6-Digit Verification Code"
                  type="text"
                  placeholder="• • • • • •"
                  maxLength={6}
                  value={secondaryOtp}
                  onChange={(e) => {
                    setSecondaryOtp(e.target.value.replace(/\D/g, ''));
                    if (secondaryStatus !== 'idle') setSecondaryStatus('idle');
                  }}
                  error={fieldErrors.otp}
                  className="text-center font-mono text-xl tracking-widest"
                  required
                />
                <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                  <span>Code expires in: <strong className="font-mono text-slate-800">{formatTime(timerSecondary)}</strong></span>
                  <button
                    type="button"
                    onClick={handleSendSecondaryOtp}
                    disabled={isLoading || timerSecondary > 540}
                    className="text-teal-700 hover:underline font-semibold disabled:text-slate-400 flex items-center gap-1"
                  >
                    <RotateCw className="w-3 h-3" />
                    {timerSecondary > 540 ? `Resend in ${timerSecondary - 540}s` : 'Resend Code'}
                  </button>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  onClick={() => setCurrentStep('SECONDARY_CONTACT')}
                  className="flex-1 justify-center"
                >
                  <ArrowLeft className="w-4 h-4 mr-1.5" /> Back
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isLoading}
                  className="flex-1 justify-center"
                >
                  Verify Secondary Contact <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              </div>
            </form>
          )}

          {/* ========================================================= */}
          {/* STEP 5: Additional Details, Password & Terms Acceptance */}
          {/* ========================================================= */}
          {currentStep === 'DETAILS_AND_TERMS' && (
            <form onSubmit={handleCompleteAccount} className="space-y-6">
              {/* Verification Summary Banner */}
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3.5 flex items-center justify-between text-xs text-emerald-900">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
                  <div>
                    <div className="font-bold">Dual-Contact Verification Complete</div>
                    <div className="text-emerald-700 text-[11px]">
                      Email: {getEmailAndPhoneDisplay().email} • Mobile: {getEmailAndPhoneDisplay().phone}
                    </div>
                  </div>
                </div>
                <Badge variant="emerald" size="sm">
                  Verified
                </Badge>
              </div>

              <div className="border-t border-slate-100 pt-4">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Account Details & Security Credentials
                </label>
              </div>

              {/* Public Username / Profile Handle */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <AtSign className="w-3.5 h-3.5 text-primary-600" />
                    Public Profile Handle (@username)
                  </label>
                  <span className="text-[11px] text-slate-400 font-medium">Optional • Auto-generated if empty</span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 font-semibold text-sm">
                    @
                  </div>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_.]/g, ''))}
                    placeholder="e.g. rohtas_skill, aarav_dev, techcorp"
                    maxLength={30}
                    className={`w-full pl-8 pr-10 py-2.5 bg-white text-sm rounded-lg border transition-colors outline-none focus:ring-2 ${
                      fieldErrors.username || usernameStatus === 'unavailable'
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-100'
                        : usernameStatus === 'available'
                        ? 'border-emerald-400 focus:border-emerald-500 focus:ring-emerald-100'
                        : 'border-slate-200 focus:border-primary-500 focus:ring-primary-100'
                    }`}
                  />
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    {usernameStatus === 'checking' && (
                      <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
                    )}
                    {usernameStatus === 'available' && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    )}
                    {(usernameStatus === 'unavailable' || fieldErrors.username) && (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                </div>
                {(usernameMessage || fieldErrors.username) && (
                  <p className={`text-xs font-medium ${
                    usernameStatus === 'available'
                      ? 'text-emerald-600'
                      : 'text-red-500'
                  }`}>
                    {fieldErrors.username || usernameMessage}
                  </p>
                )}
                <p className="text-[11px] text-slate-500">
                  Your unique handle for public search and verified profile. Lowercase letters, numbers, underscores, and dots (3-30 chars).
                </p>
              </div>

              {/* CANDIDATE FIELDS */}
              {accountType === 'candidate' && (
                <div className="space-y-4">
                  <InputField
                    label="Full Name (As per Aadhaar / Official ID)"
                    placeholder="e.g. Aarav Mehta"
                    value={candidateName}
                    onChange={(e) => setCandidateName(e.target.value)}
                    error={fieldErrors.name}
                    leftIcon={<User className="w-4 h-4 text-slate-400" />}
                    required
                  />

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <SelectField
                      label="Current Professional Status"
                      options={[
                        { value: 'student', label: 'Student / Enrolled Scholar' },
                        { value: 'job_seeker', label: 'Job Seeker / Actively Looking' },
                        { value: 'employed', label: 'Employed Professional' },
                        { value: 'apprentice', label: 'Apprentice Trainee' },
                      ]}
                      value={candidateStatus}
                      onChange={(e) => setCandidateStatus(e.target.value)}
                    />
                    <SelectField
                      label="State / Union Territory"
                      options={INDIAN_STATES}
                      value={candidateState}
                      onChange={(e) => setCandidateState(e.target.value)}
                    />
                  </div>

                  <InputField
                    label="Primary Skill / Specialization"
                    placeholder="e.g. Information Technology, Full Stack, Data Science"
                    value={candidateSkill}
                    onChange={(e) => setCandidateSkill(e.target.value)}
                  />
                </div>
              )}

              {/* EMPLOYER FIELDS */}
              {accountType === 'employer' && (
                <div className="space-y-4">
                  <InputField
                    label="Registered Enterprise / Company Name"
                    placeholder="e.g. Tata Motors Ltd"
                    value={employerCompany}
                    onChange={(e) => setEmployerCompany(e.target.value)}
                    error={fieldErrors.company}
                    leftIcon={<Building className="w-4 h-4 text-slate-400" />}
                    required
                  />

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <SelectField
                      label="Industry Domain"
                      options={[
                        { value: 'IT & Software', label: 'IT, Cloud & Software Services' },
                        { value: 'Manufacturing', label: 'Automotive & Heavy Manufacturing' },
                        { value: 'Healthcare', label: 'Healthcare & Pharmaceuticals' },
                        { value: 'Renewable Energy', label: 'Renewable Energy & Solar Tech' },
                      ]}
                      value={employerIndustry}
                      onChange={(e) => setEmployerIndustry(e.target.value)}
                    />
                    <SelectField
                      label="Enterprise Size"
                      options={[
                        { value: '1-10', label: '1 - 10 Employees (Seed / Startup)' },
                        { value: '11-50', label: '11 - 50 Employees' },
                        { value: '51-200', label: '51 - 200 Employees' },
                        { value: '201-1000', label: '201 - 1,000 Employees' },
                        { value: '1000+', label: '1,000+ Employees (Large Corporate)' },
                      ]}
                      value={employerSize}
                      onChange={(e) => setEmployerSize(e.target.value)}
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <InputField
                      label="GSTIN or CIN (Optional for Initial Draft)"
                      placeholder="e.g. 27AABCT1332L1Z5"
                      value={employerGst}
                      onChange={(e) => setEmployerGst(e.target.value)}
                    />
                    <InputField
                      label="Corporate Website URL"
                      placeholder="https://company.com"
                      value={employerWebsite}
                      onChange={(e) => setEmployerWebsite(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* TRAINING INSTITUTE FIELDS */}
              {accountType === 'institute' && (
                <div className="space-y-4">
                  <InputField
                    label="Training Institute / Polytechnic Name"
                    placeholder="e.g. Rohtas Government Polytechnic"
                    value={instName}
                    onChange={(e) => setInstName(e.target.value)}
                    error={fieldErrors.institute}
                    leftIcon={<GraduationCap className="w-4 h-4 text-slate-400" />}
                    required
                  />

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <SelectField
                      label="Accreditation / Affiliation Body"
                      options={[
                        { value: 'NCVET', label: 'NCVET Regulated Body' },
                        { value: 'NSDC', label: 'NSDC Training Partner' },
                        { value: 'AICTE', label: 'AICTE Technical Institute' },
                        { value: 'DGT', label: 'DGT / ITI Affiliated' },
                      ]}
                      value={instAffiliation}
                      onChange={(e) => setInstAffiliation(e.target.value)}
                    />
                    <SelectField
                      label="Primary Sector Focus"
                      options={[
                        { value: 'Automotive', label: 'Automotive & EV Technology' },
                        { value: 'IT-ITeS', label: 'IT-ITeS & Cloud Architecture' },
                        { value: 'Electronics', label: 'Electronics & Semiconductor Assembly' },
                        { value: 'Healthcare', label: 'Healthcare & Paramedical Skills' },
                      ]}
                      value={instDomain}
                      onChange={(e) => setInstDomain(e.target.value)}
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <SelectField
                      label="State"
                      options={INDIAN_STATES}
                      value={instState}
                      onChange={(e) => setInstState(e.target.value)}
                    />
                    <InputField
                      label="City / Campus Location"
                      placeholder="e.g. Pune, Patna, Bengaluru"
                      value={instCity}
                      onChange={(e) => setInstCity(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* GOVERNMENT FIELDS */}
              {accountType === 'government' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <InputField
                      label="Government Department / Directorate"
                      placeholder="e.g. Department of Skill Development"
                      value={govtDept}
                      onChange={(e) => setGovtDept(e.target.value)}
                      error={fieldErrors.dept}
                      leftIcon={<Landmark className="w-4 h-4 text-slate-400" />}
                      required
                    />
                    <InputField
                      label="Designated Nodal Officer Name"
                      placeholder="e.g. Rajesh Kumar"
                      value={govtOfficer}
                      onChange={(e) => setGovtOfficer(e.target.value)}
                      error={fieldErrors.officer}
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <SelectField
                      label="Administrative Level"
                      options={[
                        { value: 'Central', label: 'Central Government' },
                        { value: 'State', label: 'State Government' },
                        { value: 'District', label: 'District Administration' },
                      ]}
                      value={govtLevel}
                      onChange={(e) => setGovtLevel(e.target.value as any)}
                    />
                    <SelectField
                      label="State / Jurisdiction"
                      options={INDIAN_STATES}
                      value={govtState}
                      onChange={(e) => setGovtState(e.target.value)}
                    />
                    <InputField
                      label="Officer Designation"
                      placeholder="e.g. District Skill Officer"
                      value={govtDesignation}
                      onChange={(e) => setGovtDesignation(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {/* Password Section */}
              <div className="border-t border-slate-100 pt-4 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <InputField
                      label="Create Account Password"
                      type="password"
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      error={fieldErrors.password}
                      leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
                      required
                    />
                    <PasswordStrengthMeter password={password} />
                  </div>

                  <InputField
                    label="Confirm Password"
                    type="password"
                    placeholder="Repeat password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    error={fieldErrors.confirmPassword}
                    leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
                    required
                  />
                </div>
              </div>

              {/* Terms and Conditions Checkbox */}
              <div className="border-t border-slate-100 pt-4 space-y-3">
                <label className="flex items-start gap-3 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={termsAccepted}
                    onChange={(e) => setTermsAccepted(e.target.checked)}
                    className="mt-0.5 w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
                  />
                  <span className="text-xs text-slate-600 leading-normal">
                    I agree to the SkillVistaar{' '}
                    <a href="#terms" className="text-teal-700 font-semibold hover:underline">
                      Terms of Service
                    </a>
                    ,{' '}
                    <a href="#privacy" className="text-teal-700 font-semibold hover:underline">
                      Privacy Policy
                    </a>
                    , and consent to electronic credential issuance & verification in accordance with National Skill Qualifications Framework standards.
                  </span>
                </label>
                {fieldErrors.terms && (
                  <p className="text-xs text-rose-600 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> {fieldErrors.terms}
                  </p>
                )}
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  isLoading={isLoading}
                  disabled={!termsAccepted}
                  className="w-full justify-center font-bold text-sm py-3"
                >
                  Create SkillVistaar Account <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
};

export default SignupPage;
