import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { normalizeAccountType } from '../../types/auth';
import { Sparkles, ShieldCheck } from 'lucide-react';
import UnauthorizedPage from '../../pages/UnauthorizedPage';

interface ProtectedRouteProps {
  allowedRoles?: string[];
  children?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  allowedRoles,
  children,
}) => {
  const { isAuthenticated, isLoading, accountType, roles, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white px-4">
        <div className="relative mb-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-teal-500 to-emerald-400 flex items-center justify-center shadow-lg shadow-teal-500/20 animate-pulse">
            <Sparkles className="w-8 h-8 text-slate-950" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-slate-900 border-2 border-slate-950 flex items-center justify-center">
            <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
          </div>
        </div>
        <div className="text-center">
          <h2 className="text-xl font-bold tracking-tight text-white mb-1">SkillVistaar</h2>
          <p className="text-sm text-slate-400 animate-pulse">
            Verifying credentials and security clearance...
          </p>
        </div>
        <div className="mt-6 w-48 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div className="w-full h-full bg-gradient-to-r from-teal-500 to-emerald-400 animate-[shimmer_1.5s_infinite]" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const currentNorm = accountType ? normalizeAccountType(accountType) : 'CANDIDATE';
  const isSuperAdmin = currentNorm === 'SUPER_ADMIN' || roles.includes('SUPER_ADMIN');

  // Check role authorization if specific roles are required
  if (allowedRoles && allowedRoles.length > 0) {
    const normalizedAllowed = allowedRoles.map((r) => normalizeAccountType(r));

    // SUPER_ADMIN must NEVER open /government routes; redirect to /admin
    if (isSuperAdmin && !normalizedAllowed.includes('SUPER_ADMIN') && normalizedAllowed.includes('GOVERNMENT')) {
      return <Navigate to="/admin" replace />;
    }

    if (!isSuperAdmin) {
      const hasPermission =
        normalizedAllowed.includes(currentNorm) ||
        roles.some((r) => normalizedAllowed.includes(normalizeAccountType(r)));

      if (!hasPermission) {
        return <UnauthorizedPage />;
      }
    }
  }

  // Statutory Verification Gate:
  // Institutional stakeholders must have an APPROVED verification status to access functional dashboards.
  if (!isSuperAdmin && ['EMPLOYER', 'TRAINING_INSTITUTE', 'GOVERNMENT'].includes(currentNorm)) {
    const vStatus = user?.verification_status;
    const isExemptRoute =
      location.pathname.startsWith('/verification-pending') ||
      location.pathname.startsWith('/settings') ||
      location.pathname.startsWith('/logout');

    if (vStatus && vStatus !== 'APPROVED' && !isExemptRoute) {
      return <Navigate to="/verification-pending" replace />;
    }
  }

  return children ? <>{children}</> : <Outlet />;
};

export default ProtectedRoute;
