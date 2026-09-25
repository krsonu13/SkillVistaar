import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  LayoutDashboard,
  User as UserIcon,
  Bell,
  Settings,
  LogOut,
  Search,
} from 'lucide-react';
import Button from './Button';
import { useAuth } from '../../context/AuthContext';
import { useRealtime } from '../../context/RealtimeContext';
import { getDashboardPath } from '../../types/auth';
import { notificationApi } from '../../services/api';

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const { subscribe } = useRealtime();

  const isHome = location.pathname === '/';
  const isCurrent = (path: string) => location.pathname === path;

  // Fetch initial unread count if authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      setUnreadCount(0);
      return;
    }

    let isMounted = true;
    notificationApi.getUnreadCount().then((count) => {
      if (isMounted) setUnreadCount(count);
    }).catch(() => {});

    // Listen to real-time notification events
    const unsubNew = subscribe('NOTIFICATION_RECEIVED', () => {
      setUnreadCount((c) => c + 1);
    });
    const unsubRead = subscribe('NOTIFICATION_READ', () => {
      setUnreadCount((c) => Math.max(0, c - 1));
    });
    const unsubAllRead = subscribe('ALL_NOTIFICATIONS_READ', () => {
      setUnreadCount(0);
    });

    return () => {
      isMounted = false;
      unsubNew();
      unsubRead();
      unsubAllRead();
    };
  }, [isAuthenticated, subscribe]);

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      navigate('/login');
    }
  };

  const dashboardUrl = user ? getDashboardPath(user) : '/dashboard';
  const profileUrl = user?.username ? `/profile/@${user.username}` : user?.id ? `/profile/${user.id}` : '/dashboard';

  const roleLabel = user?.account_type
    ? user.account_type.replace('_', ' ')
    : 'User';

  const userDisplayName = user?.name || user?.username || (user?.email ? user.email.split('@')[0] : 'My Account');

  return (
    <header className="sticky top-0 z-40 w-full bg-white/95 backdrop-blur-md border-b border-slate-200/80 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Brand Logo & Tagline */}
          <Link
            to={isAuthenticated ? dashboardUrl : '/'}
            className="flex items-center gap-2.5 group"
          >
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-br from-teal-600 to-teal-800 flex items-center justify-center text-white shadow-sm shadow-teal-700/20 group-hover:scale-105 transition-transform duration-200">
              <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-teal-200" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-base sm:text-lg tracking-tight text-slate-900 font-sans">
                  Skill<span className="text-teal-700">Vistaar</span>
                </span>
                <span className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-teal-50 text-teal-700 border border-teal-200/60">
                  GovTech
                </span>
              </div>
              <span className="text-[10px] font-medium text-slate-500 tracking-wider uppercase -mt-0.5 hidden sm:block">
                Skill <span className="text-teal-600">•</span> Opportunity <span className="text-teal-600">•</span> Growth
              </span>
            </div>
          </Link>

          {/* Desktop Nav Links */}
          {isAuthenticated ? (
            <nav className="hidden lg:flex items-center gap-6 text-xs sm:text-sm font-medium text-slate-600">
              <Link
                to={dashboardUrl}
                className={`flex items-center gap-1.5 hover:text-teal-700 transition-colors py-1 ${
                  isCurrent(dashboardUrl) ? 'text-teal-700 font-semibold' : ''
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>
              <Link
                to={profileUrl}
                className={`flex items-center gap-1.5 hover:text-teal-700 transition-colors py-1 ${
                  location.pathname.startsWith('/profile') ? 'text-teal-700 font-semibold' : ''
                }`}
              >
                <UserIcon className="w-4 h-4" />
                <span>Public Profile</span>
              </Link>
              <Link
                to="/notifications"
                className={`relative flex items-center gap-1.5 hover:text-teal-700 transition-colors py-1 ${
                  isCurrent('/notifications') ? 'text-teal-700 font-semibold' : ''
                }`}
              >
                <Bell className="w-4 h-4" />
                <span>Notifications</span>
                {unreadCount > 0 && (
                  <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold leading-none text-white bg-teal-600 rounded-full">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Link>
              <Link
                to="/settings"
                className={`flex items-center gap-1.5 hover:text-teal-700 transition-colors py-1 ${
                  isCurrent('/settings') ? 'text-teal-700 font-semibold' : ''
                }`}
              >
                <Settings className="w-4 h-4" />
                <span>Settings</span>
              </Link>
            </nav>
          ) : isHome ? (
            <nav className="hidden lg:flex items-center gap-6 text-xs sm:text-sm font-medium text-slate-600">
              <a href="/#overview" className="hover:text-teal-700 transition-colors py-1">
                Ecosystem
              </a>
              <a href="/#stakeholders" className="hover:text-teal-700 transition-colors py-1">
                Stakeholders
              </a>
              <a href="/#features" className="hover:text-teal-700 transition-colors py-1">
                Key Capabilities
              </a>
              <a href="/#governance" className="hover:text-teal-700 transition-colors py-1 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                <span>Trust & Standards</span>
              </a>
            </nav>
          ) : (
            <nav className="hidden lg:flex items-center gap-4 text-xs sm:text-sm font-medium text-slate-600">
              <Link
                to="/search"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                <Search className="w-3.5 h-3.5 text-slate-500" />
                <span className="text-xs">Explore Directory & Jobs</span>
              </Link>
            </nav>
          )}

          {/* Desktop Right CTA / User Section */}
          {isAuthenticated ? (
            <div className="hidden sm:flex items-center gap-3">
              <div className="flex items-center gap-2 pl-3 border-l border-slate-200">
                <div className="w-8 h-8 rounded-full bg-teal-100 border border-teal-200 text-teal-800 flex items-center justify-center font-bold text-xs">
                  {userDisplayName.charAt(0).toUpperCase()}
                </div>
                <div className="flex flex-col text-left">
                  <span className="text-xs font-semibold text-slate-800 max-w-[130px] truncate leading-tight">
                    {userDisplayName}
                  </span>
                  <span className="text-[10px] font-medium text-slate-500 capitalize">
                    {roleLabel.toLowerCase()}
                  </span>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                className="font-medium text-xs px-2.5 py-1 text-slate-600 hover:text-red-600 hover:border-red-200 hover:bg-red-50"
                leftIcon={<LogOut className="w-3.5 h-3.5" />}
              >
                Sign Out
              </Button>
            </div>
          ) : (
            <div className="hidden sm:flex items-center gap-2.5">
              <Link to="/search" className="p-2 text-slate-500 hover:text-slate-800 transition">
                <Search className="w-4 h-4" />
              </Link>
              <Link to="/login">
                <Button
                  variant={isCurrent('/login') ? 'secondary' : 'outline'}
                  size="sm"
                  className="font-medium text-xs px-3"
                >
                  Sign In
                </Button>
              </Link>
              <Link to="/signup">
                <Button
                  variant="primary"
                  size="sm"
                  className="font-semibold text-xs px-3.5 shadow-sm"
                  rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                >
                  Create Account
                </Button>
              </Link>
            </div>
          )}

          {/* Mobile Menu Toggle */}
          <div className="flex sm:hidden items-center gap-2">
            {isAuthenticated ? (
              <button
                type="button"
                onClick={handleLogout}
                className="p-1.5 rounded-lg text-slate-500 hover:text-red-600 hover:bg-slate-100 transition"
                title="Log Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            ) : (
              <Link to="/login">
                <Button variant="outline" size="sm" className="text-xs px-2.5 py-1">
                  Sign In
                </Button>
              </Link>
            )}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition focus:outline-none"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-b border-slate-200 bg-white px-4 pt-3 pb-4 space-y-3 shadow-lg animate-in slide-in-from-top-2">
          {isAuthenticated ? (
            <div className="space-y-1 text-sm font-medium text-slate-700">
              <div className="pb-2 mb-2 border-b border-slate-100 flex items-center gap-2 px-3">
                <div className="w-7 h-7 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-xs">
                  {userDisplayName.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-900">{userDisplayName}</div>
                  <div className="text-[10px] text-slate-500 capitalize">{roleLabel.toLowerCase()}</div>
                </div>
              </div>
              <Link
                to={dashboardUrl}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-slate-100 transition"
              >
                <LayoutDashboard className="w-4 h-4 text-slate-500" />
                <span>Dashboard</span>
              </Link>
              <Link
                to={profileUrl}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-slate-100 transition"
              >
                <UserIcon className="w-4 h-4 text-slate-500" />
                <span>Public Profile</span>
              </Link>
              <Link
                to="/notifications"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-slate-100 transition"
              >
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-slate-500" />
                  <span>Notifications</span>
                </div>
                {unreadCount > 0 && (
                  <span className="inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold text-white bg-teal-600 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </Link>
              <Link
                to="/settings"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-slate-100 transition"
              >
                <Settings className="w-4 h-4 text-slate-500" />
                <span>Settings</span>
              </Link>
              <div className="pt-2 border-t border-slate-100">
                <Button
                  variant="outline"
                  size="md"
                  fullWidth
                  onClick={() => {
                    setMobileMenuOpen(false);
                    handleLogout();
                  }}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                  leftIcon={<LogOut className="w-4 h-4" />}
                >
                  Log Out
                </Button>
              </div>
            </div>
          ) : isHome ? (
            <>
              <div className="space-y-1 text-sm font-medium text-slate-700">
                <a
                  href="/#overview"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md hover:bg-slate-100 transition"
                >
                  Ecosystem Overview
                </a>
                <a
                  href="/#stakeholders"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md hover:bg-slate-100 transition"
                >
                  Stakeholders Directory
                </a>
                <a
                  href="/#features"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md hover:bg-slate-100 transition"
                >
                  Platform Capabilities
                </a>
                <a
                  href="/#governance"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md hover:bg-slate-100 transition"
                >
                  Trust & Standards
                </a>
              </div>

              <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                <Link
                  to="/signup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full"
                >
                  <Button variant="primary" size="md" fullWidth rightIcon={<ArrowRight className="w-4 h-4" />}>
                    Create Account
                  </Button>
                </Link>
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full"
                >
                  <Button variant="outline" size="md" fullWidth>
                    Already have an account? Sign In
                  </Button>
                </Link>
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <Link
                to="/search"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-md bg-slate-50 text-slate-700 font-medium text-sm"
              >
                <Search className="w-4 h-4 text-slate-500" />
                <span>Search Ecosystem Directory</span>
              </Link>
              <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                <Link
                  to="/signup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full"
                >
                  <Button variant="primary" size="md" fullWidth rightIcon={<ArrowRight className="w-4 h-4" />}>
                    Create Account
                  </Button>
                </Link>
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full"
                >
                  <Button variant="outline" size="md" fullWidth>
                    Sign In
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
    </header>
  );
};

export default Navbar;
