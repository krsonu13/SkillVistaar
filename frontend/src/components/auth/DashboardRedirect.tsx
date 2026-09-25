import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getDashboardPath } from '../../types/auth';
import { Sparkles, ShieldCheck } from 'lucide-react';

export const DashboardRedirect: React.FC = () => {
  const { isAuthenticated, isLoading, accountType } = useAuth();

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
            Authenticating and preparing your workspace...
          </p>
        </div>
        <div className="mt-6 w-48 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div className="w-full h-full bg-gradient-to-r from-teal-500 to-emerald-400 animate-[shimmer_1.5s_infinite]" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const destination = getDashboardPath(accountType);
  return <Navigate to={destination} replace />;
};

export default DashboardRedirect;
