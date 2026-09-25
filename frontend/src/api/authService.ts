import axiosClient from './axiosClient';
import {
  AccountType,
  AuthResponse,
  AuthUser,
  LoginPayload,
  normalizeAccountType,
  OtpVerificationPayload,
  resolveUserCanonicalRole,
  SignupPayload,
} from '../types/auth';

export const authService = {
  /**
   * Login user with identifier and password
   */
  async login(payload: LoginPayload): Promise<AuthResponse> {
    try {
      const response = await axiosClient.post<AuthResponse>('/auth/login', {
        identifier: payload.identifier.trim(),
        password: payload.password,
      });

      const data = response.data;
      const token = data.access_token || data.token;
      if (token) {
        localStorage.setItem('sv_auth_token', token);
      }
      if (data.refresh_token) {
        localStorage.setItem('sv_refresh_token', data.refresh_token);
      }
      if (data.user) {
        const canonical = resolveUserCanonicalRole(data.user);
        const normUser: AuthUser = {
          ...data.user,
          account_type: canonical,
          accountType: canonical,
          roles: data.user.roles || [canonical],
        };
        localStorage.setItem('sv_user', JSON.stringify(normUser));
        return {
          ...data,
          token,
          user: normUser,
        };
      }
      return {
        ...data,
        token,
      };
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Authentication failed. Please verify credentials.';
      const customError: any = new Error(msg);
      customError.status = err.response?.status;
      customError.isUnverified = err.response?.status === 403 || String(msg).toLowerCase().includes('unverified');
      throw customError;
    }
  },

  /**
   * Register a new account
   */
  async signup(payload: SignupPayload): Promise<AuthResponse> {
    try {
      let email: string | undefined = undefined;
      if ('email' in payload && payload.email) email = payload.email.trim();
      else if ('officialEmail' in payload && payload.officialEmail) email = payload.officialEmail.trim();

      let phone: string | undefined = undefined;
      if ('phone' in payload && (payload as any).phone) phone = (payload as any).phone.trim();
      else if ('contactPhone' in payload && (payload as any).contactPhone) phone = (payload as any).contactPhone.trim();
      else if ('coordinatorPhone' in payload && (payload as any).coordinatorPhone) phone = (payload as any).coordinatorPhone.trim();

      let fullName: string | undefined = undefined;
      if ('fullName' in payload && payload.fullName) fullName = payload.fullName.trim();
      else if ('nodalOfficerName' in payload && (payload as any).nodalOfficerName) fullName = (payload as any).nodalOfficerName.trim();

      let companyName: string | undefined = undefined;
      if ('companyName' in payload && payload.companyName) companyName = payload.companyName.trim();

      let instituteName: string | undefined = undefined;
      if ('instituteName' in payload && payload.instituteName) instituteName = payload.instituteName.trim();

      let departmentName: string | undefined = undefined;
      if ('departmentName' in payload && payload.departmentName) departmentName = payload.departmentName.trim();

      const backendPayload = {
        email: email || null,
        phone: phone || null,
        password: payload.password,
        account_type: normalizeAccountType(payload.accountType),
        fullName: fullName || companyName || instituteName || departmentName,
        companyName: companyName || null,
        instituteName: instituteName || null,
        departmentName: departmentName || null,
      };

      const response = await axiosClient.post<AuthResponse>('/auth/signup', backendPayload);
      return response.data;
    } catch (err: any) {
      let msg = err.response?.data?.detail ?? err.response?.data?.message ?? err.message;
      if (Array.isArray(msg)) {
        msg = msg.map((m: any) => m.msg || m.message || JSON.stringify(m)).join('; ');
      } else if (typeof msg === 'object' && msg !== null) {
        msg = msg.msg || msg.message || JSON.stringify(msg);
      }
      if (!msg || typeof msg !== 'string') {
        msg = 'Registration failed. Please check your details and try again.';
      }
      const customError: any = new Error(msg);
      customError.status = err.response?.status;
      throw customError;
    }
  },

  /**
   * Verify 6-digit OTP
   */
  async verifyOtp(payload: OtpVerificationPayload): Promise<AuthResponse> {
    try {
      const response = await axiosClient.post<AuthResponse>('/auth/verify-otp', {
        identifier: payload.identifier.trim(),
        otp: payload.otp.trim(),
        accountType: normalizeAccountType(payload.accountType),
      });

      const data = response.data;
      const token = data.access_token || data.token;
      if (token) {
        localStorage.setItem('sv_auth_token', token);
      }
      if (data.refresh_token) {
        localStorage.setItem('sv_refresh_token', data.refresh_token);
      }
      if (data.user) {
        const canonical = resolveUserCanonicalRole(data.user);
        const normUser: AuthUser = {
          ...data.user,
          account_type: canonical,
          accountType: canonical,
          roles: data.user.roles || [canonical],
          isVerified: true,
        };
        localStorage.setItem('sv_user', JSON.stringify(normUser));
        return {
          ...data,
          token,
          user: normUser,
        };
      }
      return data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'OTP verification failed. Please check the code.';
      throw new Error(msg);
    }
  },

  /**
   * Step 1: Start signup verification by sending REAL OTP to primary contact (Mobile or Email)
   */
  async startSignupVerification(
    accountType: string,
    channel: 'EMAIL' | 'PHONE',
    identifier: string
  ): Promise<{
    session_token: string;
    channel: string;
    identifier: string;
    expires_in_seconds: number;
    message: string;
    dev_otp?: string | null;
  }> {
    try {
      const res = await axiosClient.post('/auth/signup/start-verification', {
        account_type: normalizeAccountType(accountType),
        channel,
        identifier: identifier.trim(),
      });
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Failed to send verification code.';
      const customErr: any = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      customErr.status = err.response?.status;
      throw customErr;
    }
  },

  /**
   * Step 2: Verify primary contact OTP
   */
  async verifyPrimaryContact(
    sessionToken: string,
    otp: string
  ): Promise<{
    session_token: string;
    primary_verified: boolean;
    primary_channel: string;
    next_channel: string;
    message: string;
  }> {
    try {
      const res = await axiosClient.post('/auth/signup/verify-primary', {
        session_token: sessionToken,
        otp: otp.trim(),
      });
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Invalid verification code.';
      const customErr: any = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      customErr.status = err.response?.status;
      throw customErr;
    }
  },

  /**
   * Step 3: Send REAL OTP to the alternate contact
   */
  async sendSecondaryOtp(
    sessionToken: string,
    channel: 'EMAIL' | 'PHONE',
    identifier: string
  ): Promise<{
    session_token: string;
    channel: string;
    identifier: string;
    expires_in_seconds: number;
    message: string;
    dev_otp?: string | null;
  }> {
    try {
      const res = await axiosClient.post('/auth/signup/send-secondary-otp', {
        session_token: sessionToken,
        channel,
        identifier: identifier.trim(),
      });
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Failed to send secondary verification code.';
      const customErr: any = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      customErr.status = err.response?.status;
      throw customErr;
    }
  },

  /**
   * Step 4: Verify secondary contact OTP
   */
  async verifySecondaryContact(
    sessionToken: string,
    otp: string
  ): Promise<{
    session_token: string;
    both_verified: boolean;
    message: string;
  }> {
    try {
      const res = await axiosClient.post('/auth/signup/verify-secondary', {
        session_token: sessionToken,
        otp: otp.trim(),
      });
      return res.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Invalid verification code.';
      const customErr: any = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      customErr.status = err.response?.status;
      throw customErr;
    }
  },

  /**
   * Step 5: Final Account Creation
   */
  async completeSignup(
    sessionToken: string,
    password: string,
    termsAccepted: boolean,
    additionalData: Record<string, any>
  ): Promise<AuthResponse> {
    try {
      const res = await axiosClient.post<AuthResponse>('/auth/signup/complete', {
        session_token: sessionToken,
        password,
        terms_accepted: termsAccepted,
        additional_data: additionalData,
      });
      const data = res.data;
      const token = data.access_token || data.token;
      if (token) {
        localStorage.setItem('sv_auth_token', token);
      }
      if (data.refresh_token) {
        localStorage.setItem('sv_refresh_token', data.refresh_token);
      }
      if (data.user) {
        const canonical = normalizeAccountType(data.user.account_type || (data.user as any).accountType);
        const normUser: AuthUser = {
          ...data.user,
          account_type: canonical,
          accountType: canonical,
          roles: data.user.roles || [canonical],
        };
        localStorage.setItem('sv_user', JSON.stringify(normUser));
        return {
          ...data,
          token,
          user: normUser,
        };
      }
      return data;
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? err.message ?? 'Registration failed.';
      const customErr: any = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      customErr.status = err.response?.status;
      throw customErr;
    }
  },

  /**
   * Resend OTP
   */
  async resendOtp(identifier: string, accountType: AccountType): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axiosClient.post('/auth/resend-otp', {
        identifier: identifier.trim(),
        accountType: normalizeAccountType(accountType),
      });
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Unable to resend OTP.';
      throw new Error(msg);
    }
  },

  /**
   * Request password reset link / OTP
   */
  async forgotPassword(identifier: string, accountType: AccountType): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axiosClient.post('/auth/forgot-password', {
        identifier: identifier.trim(),
        accountType: normalizeAccountType(accountType),
      });
      return response.data;
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Unable to process password reset.';
      throw new Error(msg);
    }
  },

  /**
   * Fetch currently authenticated user profile from /auth/me
   */
  async getMe(): Promise<AuthUser> {
    const response = await axiosClient.get<AuthUser>('/auth/me');
    const user = response.data;
    const canonical = resolveUserCanonicalRole(user);
    const normUser: AuthUser = {
      ...user,
      account_type: canonical,
      accountType: canonical,
      roles: user.roles || [canonical],
    };
    localStorage.setItem('sv_user', JSON.stringify(normUser));
    return normUser;
  },

  /**
   * Refresh the access token
   */
  async refreshToken(): Promise<string> {
    const refreshTokenVal = localStorage.getItem('sv_refresh_token');
    if (!refreshTokenVal) throw new Error('No refresh token available');
    const response = await axiosClient.post<AuthResponse>('/auth/refresh', {
      refresh_token: refreshTokenVal,
    });
    const newToken = response.data.access_token || response.data.token;
    if (newToken) {
      localStorage.setItem('sv_auth_token', newToken);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('sv_refresh_token', response.data.refresh_token);
    }
    return newToken || '';
  },

  /**
   * Clear local storage and log out
   */
  async logout(): Promise<void> {
    const refreshTokenVal = localStorage.getItem('sv_refresh_token');
    if (refreshTokenVal) {
      try {
        await axiosClient.post('/auth/logout', { refresh_token: refreshTokenVal });
      } catch {
        // Silently continue if network or session expired
      }
    }
    localStorage.removeItem('sv_auth_token');
    localStorage.removeItem('sv_refresh_token');
    localStorage.removeItem('sv_user');
  },

  /**
   * Read cached user
   */
  getCurrentUser(): AuthUser | null {
    const raw = localStorage.getItem('sv_user');
    if (!raw) return null;
    try {
      const user = JSON.parse(raw);
      if (!user) return null;
      const canonical = normalizeAccountType(user.account_type || user.accountType);
      return {
        ...user,
        account_type: canonical,
        accountType: canonical,
        roles: user.roles || [canonical],
      };
    } catch {
      return null;
    }
  },

  /**
   * Check if a username is available
   */
  async checkUsernameAvailability(username: string): Promise<{
    available: boolean;
    username: string;
    message: string;
  }> {
    try {
      const res = await axiosClient.get('/auth/check-username', {
        params: { username: username.trim() },
      });
      return res.data;
    } catch (err: any) {
      return {
        available: false,
        username,
        message: err.response?.data?.detail || 'Username is not available.',
      };
    }
  },
};
