import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, Lock, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getDashboardPath } from '../types/auth';
import Button from '../components/common/Button';

export const UnauthorizedPage: React.FC = () => {
  const { user, accountType, logout } = useAuth();
  const authorizedPath = getDashboardPath(accountType);

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-4 py-12 text-slate-100">
      <div className="max-w-md w-full bg-slate-800/80 backdrop-blur border border-slate-700 rounded-2xl p-6 sm:p-8 shadow-2xl text-center space-y-6">
        {/* Shield Icon */}
        <div className="mx-auto w-20 h-20 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
          <ShieldAlert className="w-10 h-10" />
        </div>

        {/* Text */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-semibold">
            <Lock className="w-3.5 h-3.5" />
            HTTP 403: Forbidden Access
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            Dashboard Access Restricted
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            Your account is authenticated as{' '}
            <strong className="text-teal-400 font-semibold">{accountType || 'a different role'}</strong>{' '}
            ({user?.email || user?.phone || 'Active User'}). You do not have permission to view or manage this workspace.
          </p>
        </div>

        {/* Details Box */}
        <div className="bg-slate-900/60 border border-slate-700/60 rounded-xl p-4 text-xs text-left space-y-2 text-slate-300">
          <div className="flex justify-between items-center py-1 border-b border-slate-800">
            <span className="text-slate-500">Authenticated Role</span>
            <span className="font-mono font-medium text-slate-200">{accountType || 'CANDIDATE'}</span>
          </div>
          <div className="flex justify-between items-center py-1 border-b border-slate-800">
            <span className="text-slate-500">Security Clearance</span>
            <span className="font-mono text-emerald-400 font-medium">Valid JWT Bearer</span>
          </div>
          <div className="flex justify-between items-center py-1">
            <span className="text-slate-500">Authorized Workspace</span>
            <span className="font-mono text-teal-300 font-semibold">{authorizedPath}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Link to={authorizedPath} className="flex-1">
            <Button variant="primary" className="w-full justify-center text-sm py-2.5">
              <ArrowLeft className="w-4 h-4 mr-1.5" />
              Go to My Dashboard
            </Button>
          </Link>
          <Button
            variant="outline"
            onClick={logout}
            className="border-slate-700 text-slate-300 hover:bg-slate-700/50 justify-center text-sm py-2.5"
          >
            <LogOut className="w-4 h-4 mr-1.5" />
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
};

export default UnauthorizedPage;
