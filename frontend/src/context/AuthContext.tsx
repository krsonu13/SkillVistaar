import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  AuthUser,
  CanonicalAccountType,
  LoginPayload,
  normalizeAccountType,
  resolveUserCanonicalRole,
  toFrontendAccountType,
} from '../types/auth';
import { authService } from '../api/authService';

export interface AuthContextType {
  user: AuthUser | null;
  accountType: CanonicalAccountType | null;
  roles: string[];
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
  setAuthSession: (authToken: string, authUser: AuthUser, refreshToken?: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('sv_auth_token');
  });

  const [user, setUser] = useState<AuthUser | null>(() => {
    return authService.getCurrentUser();
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Derive accountType and roles safely (prioritizing SUPER_ADMIN)
  const accountType: CanonicalAccountType | null = user
    ? resolveUserCanonicalRole(user)
    : null;

  const roles: string[] = user?.roles || (accountType ? [accountType] : []);
  const isAuthenticated = Boolean(token && user);

  // Sync with PlatformContext role if present
  const syncPlatformRole = useCallback((canonicalType: CanonicalAccountType) => {
    const frontendRole = toFrontendAccountType(canonicalType);
    localStorage.setItem('sv_active_role', frontendRole);
  }, []);

  // Restore & verify session on mount
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      const storedToken = localStorage.getItem('sv_auth_token');
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const freshUser = await authService.getMe();
        if (isMounted) {
          setUser(freshUser);
          setToken(storedToken);
          syncPlatformRole(freshUser.account_type);
        }
      } catch (err: any) {
        console.warn('Session verification fallback to cached profile:', err.message);
        // If cached user exists, keep it so offline/temporary network hiccups do not log out
        const cached = authService.getCurrentUser();
        if (isMounted) {
          if (cached) {
            setUser(cached);
            setToken(storedToken);
            syncPlatformRole(cached.account_type);
          } else {
            // Invalid session
            localStorage.removeItem('sv_auth_token');
            localStorage.removeItem('sv_refresh_token');
            localStorage.removeItem('sv_user');
            setUser(null);
            setToken(null);
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, [syncPlatformRole]);

  const login = async (payload: LoginPayload): Promise<AuthUser> => {
    setIsLoading(true);
    try {
      const response = await authService.login(payload);
      const authToken = response.token || response.access_token;
      if (!authToken || !response.user) {
        throw new Error('Incomplete login response from server.');
      }

      setToken(authToken);
      setUser(response.user);
      syncPlatformRole(response.user.account_type);
      return response.user;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setToken(null);
      setIsLoading(false);
    }
  };

  const refreshUser = async (): Promise<AuthUser | null> => {
    try {
      const freshUser = await authService.getMe();
      setUser(freshUser);
      syncPlatformRole(freshUser.account_type);
      return freshUser;
    } catch {
      return null;
    }
  };

  const setAuthSession = useCallback(
    (authToken: string, authUser: AuthUser, refreshToken?: string) => {
      localStorage.setItem('sv_auth_token', authToken);
      if (refreshToken) {
        localStorage.setItem('sv_refresh_token', refreshToken);
      }
      const canonical = normalizeAccountType(authUser.account_type || (authUser as any).accountType);
      const normUser: AuthUser = {
        ...authUser,
        account_type: canonical,
        accountType: canonical,
        roles: authUser.roles || [canonical],
        isVerified: true,
      };
      localStorage.setItem('sv_user', JSON.stringify(normUser));
      setToken(authToken);
      setUser(normUser);
      syncPlatformRole(normUser.account_type);
    },
    [syncPlatformRole]
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        accountType,
        roles,
        token,
        isAuthenticated,
        isLoading,
        login,
        logout,
        refreshUser,
        setAuthSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
