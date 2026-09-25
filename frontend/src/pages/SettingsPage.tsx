import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Settings,
  Shield,
  Key,
  CheckCircle2,
  AlertCircle,
  User,
  Mail,
  Phone,
  Lock,
  LogOut,
  Trash2,
  X,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import DashboardLayout from '../components/dashboard/DashboardLayout';
import Button from '../components/common/Button';
import InputField from '../components/common/InputField';
import Badge from '../components/common/Badge';
import { useAuth } from '../context/AuthContext';
import { authApi, userApi } from '../services/api';

export const SettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Change Password Form State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordFeedback, setPasswordFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Account Management & Deletion State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteReason, setDeleteReason] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordFeedback(null);

    if (!currentPassword) {
      setPasswordFeedback({ type: 'error', message: 'Current password is required.' });
      return;
    }
    if (newPassword.length < 8) {
      setPasswordFeedback({ type: 'error', message: 'New password must be at least 8 characters long.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordFeedback({ type: 'error', message: 'New passwords do not match.' });
      return;
    }

    setPasswordLoading(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setPasswordFeedback({ type: 'success', message: 'Password updated successfully.' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordFeedback({
        type: 'error',
        message: err.message || 'Failed to update password. Please verify current password.',
      });
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      navigate('/login');
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deletePassword) {
      setDeleteError('Your current password is required to authorize permanent account deletion.');
      return;
    }
    setDeleteLoading(true);
    setDeleteError(null);
    try {
      await userApi.deleteAccount({
        password: deletePassword,
        reason: deleteReason.trim() || undefined,
      });
      await logout();
      navigate('/login');
    } catch (err: any) {
      setDeleteError(err?.response?.data?.detail || 'Failed to delete account. Please verify your password.');
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <DashboardLayout activeTab="settings">
      <div className="space-y-6 max-w-4xl mx-auto">
        {/* Header */}
        <div className="pb-3 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center">
              <Settings className="w-4 h-4" />
            </div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Account & Security Settings</h1>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage your authenticated credentials, security profile, and notification settings
          </p>
        </div>

        {/* Account Profile Summary */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <User className="w-4 h-4 text-teal-600" />
              Authenticated Identity
            </h2>
            <Badge variant="teal" size="sm">
              {user?.account_type || 'ACTIVE'}
            </Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
              <span className="text-slate-400 block font-semibold text-[10px] uppercase">Registered Email</span>
              <div className="flex items-center gap-1.5 font-medium text-slate-800">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                <span>{user?.email || 'No email attached'}</span>
              </div>
              <span className="text-[10px] font-semibold text-emerald-600">
                {user?.email_verified ? '✓ Verified via SMTP' : 'Unverified'}
              </span>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 space-y-1">
              <span className="text-slate-400 block font-semibold text-[10px] uppercase">Registered Mobile Phone</span>
              <div className="flex items-center gap-1.5 font-medium text-slate-800">
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                <span>{user?.phone || 'No phone attached'}</span>
              </div>
              <span className="text-[10px] font-semibold text-emerald-600">
                {user?.phone_verified ? '✓ Verified via SMS' : 'Unverified'}
              </span>
            </div>
          </div>
        </div>

        {/* Change Password Form */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
          <div className="pb-3 border-b border-slate-100">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Key className="w-4 h-4 text-teal-600" />
              Change Passphrase
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Ensure your account is secured with a strong passphrase containing uppercase, lowercase, numbers, and symbols.
            </p>
          </div>

          {passwordFeedback && (
            <div
              className={`p-3 rounded-lg text-xs font-semibold flex items-center gap-2 animate-in fade-in ${
                passwordFeedback.type === 'success'
                  ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border border-rose-200 text-rose-800'
              }`}
            >
              {passwordFeedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{passwordFeedback.message}</span>
            </div>
          )}

          <form onSubmit={handlePasswordChange} className="space-y-4 max-w-lg">
            <InputField
              label="Current Passphrase"
              type="password"
              placeholder="Enter your current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
              required
            />

            <InputField
              label="New Passphrase"
              type="password"
              placeholder="At least 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              leftIcon={<Key className="w-4 h-4 text-slate-400" />}
              required
            />

            <InputField
              label="Confirm New Passphrase"
              type="password"
              placeholder="Re-enter new passphrase"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              leftIcon={<Key className="w-4 h-4 text-slate-400" />}
              required
            />

            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={passwordLoading}
              className="text-xs font-semibold"
            >
              Update Password
            </Button>
          </form>
        </div>

        {/* Account Lifecycle & Danger Zone */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs p-5 space-y-4">
          <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <LogOut className="w-4 h-4 text-slate-600" />
                Session & Account Management
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Sign out of your active browser session or manage statutory account lifecycle.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="text-xs font-semibold text-slate-700 hover:text-slate-900"
              leftIcon={<LogOut className="w-3.5 h-3.5" />}
            >
              Sign Out
            </Button>
          </div>

          <div className="pt-2">
            <div className="p-4 rounded-xl bg-red-50/60 border border-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-xs font-bold text-red-900 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-red-600" />
                  Permanent Account Deletion
                </h3>
                <p className="text-[11px] text-red-700/90 mt-0.5 max-w-xl leading-relaxed">
                  Permanently deactivate this account, revoke all active cryptographic session tokens, and anonymize profile data. This statutory action cannot be reversed.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setDeleteModalOpen(true);
                  setDeleteError(null);
                  setDeletePassword('');
                  setDeleteReason('');
                }}
                className="shrink-0 text-xs font-bold text-red-600 border-red-300 hover:bg-red-100/70 hover:border-red-400"
                leftIcon={<Trash2 className="w-3.5 h-3.5" />}
              >
                Delete Account
              </Button>
            </div>
          </div>
        </div>

        {/* Delete Account Confirmation Modal */}
        {deleteModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
            <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-red-50/70">
                <div className="flex items-center gap-2">
                  <Trash2 className="w-4 h-4 text-red-600" />
                  <h3 className="text-sm font-bold text-red-950">Confirm Account Deletion</h3>
                </div>
                <button
                  onClick={() => setDeleteModalOpen(false)}
                  className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleDeleteAccount} className="p-5 space-y-4 text-xs">
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 space-y-1">
                  <p className="font-bold">Warning: Irreversible Statutory Action</p>
                  <p className="text-[11px] text-red-700 leading-relaxed">
                    Deleting your account will immediately revoke all sessions, anonymize personal identifiable details, and archive your activity under audit governance.
                  </p>
                </div>

                {deleteError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg font-semibold flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                    <span>{deleteError}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Confirm Your Passphrase *
                  </label>
                  <input
                    type="password"
                    placeholder="Enter current password to authorize"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-red-500 font-mono"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Reason for Deletion (Optional)
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Tell us why you are deleting your account..."
                    value={deleteReason}
                    onChange={(e) => setDeleteReason(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-slate-400"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setDeleteModalOpen(false)}
                    className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={deleteLoading}
                    className="px-4 py-2 text-xs font-bold rounded-lg bg-red-600 hover:bg-red-700 text-white shadow-sm flex items-center gap-1.5"
                  >
                    {deleteLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    Confirm Permanent Deletion
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Security & Cryptographic Compliance Card */}
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-teal-700" />
            <span className="text-xs font-bold text-slate-900">National PKI & Statutory RBAC Active</span>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            All account actions are immutably signed and logged to the central audit registry. Sensitive personal data
            is guarded with role-based access control complying with NCVET, DigiLocker, and NSDC trust frameworks.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default SettingsPage;
