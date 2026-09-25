import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  LayoutDashboard,
  User,
  Briefcase,
  GraduationCap,
  Landmark,
  Shield,
  Bell,
  Search,
  Menu,
  X,
  LogOut,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Award,
  PlusCircle,
  Layers,
  FileCheck2,
  FileText,
  Settings,
  Users,
  TrendingUp,
  BookOpen,
  ShieldCheck,
  Sliders,
  UserCheck,
  MessageSquare,
} from 'lucide-react';
import { usePlatform } from '../../context/PlatformContext';
import { useAuth } from '../../context/AuthContext';
import { AccountType } from '../../types/auth';
import { searchApi, messagingApi, SearchProfileItem } from '../../services/api';
import Button from '../common/Button';
import DirectMessagingModal from '../messaging/DirectMessagingModal';

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeTab?: string;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children, activeTab: _activeTab }) => {
  const {
    currentRole,
    currentUser,
    notifications,
    unreadNotifsCount,
    markNotificationRead,
    markAllNotificationsRead,
  } = usePlatform();

  const { logout } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notifsOpen, setNotifsOpen] = useState(false);
  const [messagesModalOpen, setMessagesModalOpen] = useState(false);
  const [unreadMessagesCount, setUnreadMessagesCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchProfileItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchDropdownOpen, setSearchDropdownOpen] = useState(false);
  const searchContainerRef = React.useRef<HTMLDivElement>(null);

  // Poll unread messages
  useEffect(() => {
    let isMounted = true;
    const fetchUnread = async () => {
      try {
        const counts = await messagingApi.getUnreadCounts();
        if (isMounted) setUnreadMessagesCount(counts.total);
      } catch {
        // ignore
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const q = searchQuery.trim();
    if (q.length < 2) {
      setSearchResults([]);
      setIsSearching(false);
      setSearchDropdownOpen(false);
      return;
    }

    setIsSearching(true);
    const timer = setTimeout(async () => {
      try {
        const resp = await searchApi.searchProfiles({ q, limit: 6 });
        setSearchResults(resp.items);
        setSearchDropdownOpen(true);
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setSearchDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      setSearchDropdownOpen(false);
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    } else if (e.key === 'Escape') {
      setSearchDropdownOpen(false);
    }
  };

  const location = useLocation();
  const navigate = useNavigate();

  const roleLabels: Record<AccountType, string> = {
    candidate: 'Candidate',
    employer: 'Employer',
    institute: 'Institute',
    government: 'Government',
    admin: 'Platform Admin',
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Role-specific canonical navigation links
  const getNavLinks = () => {
    switch (currentRole) {
      case 'candidate':
        return [
          { name: 'Dashboard', path: '/candidate', icon: LayoutDashboard },
          { name: 'My Skills', path: '/candidate/skills', icon: Award },
          { name: 'Credentials', path: '/candidate/credentials', icon: Shield },
          { name: 'Explore Jobs', path: '/candidate/jobs', icon: Briefcase },
          { name: 'Applications', path: '/candidate/applications', icon: FileCheck2 },
          { name: 'Assessments', path: '/candidate/assessments', icon: CheckCircle2Icon },
          { name: 'Network', path: '/candidate/following', icon: Users },
          { name: 'Resume Vault', path: '/candidate/resume', icon: FileText },
          { name: 'Edit Profile', path: '/candidate/edit-profile', icon: UserCheck },
          { name: 'Public Profile', path: '/candidate/profile', icon: User },
        ];
      case 'employer':
        return [
          { name: 'Dashboard', path: '/employer', icon: LayoutDashboard },
          { name: 'Job Postings', path: '/employer/jobs', icon: Briefcase },
          { name: 'Candidate Pipeline', path: '/employer/applications', icon: Users },
          { name: 'Document Center', path: '/employer/documents', icon: FileText },
          { name: 'Company Profile', path: '/employer/profile', icon: ExternalLink },
          { name: 'Skill Assessments', path: '/employer/assessments', icon: Award },
          { name: 'Network', path: '/employer/following', icon: Users },
        ];
      case 'institute':
        return [
          { name: 'Dashboard', path: '/institution', icon: LayoutDashboard },
          { name: 'Batches & Courses', path: '/institution/courses', icon: GraduationCap },
          { name: 'Document Center', path: '/institution/documents', icon: FileText },
          { name: 'Faculty & Labs', path: '/institution/faculty', icon: Users },
          { name: 'Placements', path: '/institution/placements', icon: TrendingUp },
          { name: 'Institute Profile', path: '/institution/profile', icon: ExternalLink },
          { name: 'Skill Mappings', path: '/institution/skills', icon: BookOpen },
          { name: 'Network', path: '/institution/following', icon: Users },
        ];
      case 'government':
        return [
          { name: 'Dashboard', path: '/government', icon: LayoutDashboard },
          { name: 'Document Verification', path: '/government/documents', icon: ShieldCheck },
          { name: 'Jurisdiction Drill-down', path: '/government/drill-down', icon: Landmark },
          { name: 'Regional Trends', path: '/government/trends', icon: TrendingUp },
          { name: 'Skill Demand', path: '/government/demand', icon: Layers },
          { name: 'Accredited Entities', path: '/government/organizations', icon: Briefcase },
          { name: 'Network', path: '/government/following', icon: Users },
          { name: 'Public Nodal Page', path: '/government/profile', icon: ExternalLink },
        ];
      case 'admin':
      default:
        return [
          { name: 'Overview', path: '/admin', icon: LayoutDashboard },
          { name: 'Verification Center', path: '/admin/verification', icon: ShieldCheck },
          { name: 'User Management', path: '/admin/users', icon: Users },
          { name: 'Platform & Form Control', path: '/admin/platform-control', icon: Sliders },
          { name: 'Audit & History', path: '/admin/audit-logs', icon: FileText },
        ];
    }
  };

  const navLinks = getNavLinks();

  const getQuickAction = () => {
    switch (currentRole) {
      case 'candidate':
        return {
          label: '+ Add Skill',
          action: () => navigate('/candidate/skills'),
        };
      case 'employer':
        return {
          label: '+ Post New Job',
          action: () => navigate('/employer/jobs/create'),
        };
      case 'institute':
        return {
          label: '+ Add Course Batch',
          action: () => navigate('/institution/courses/create'),
        };
      case 'government':
        return {
          label: 'Regional Analytics',
          action: () => navigate('/government/trends'),
        };
      case 'admin':
        return {
          label: 'Verification Queue',
          action: () => navigate('/admin/verification'),
        };
    }
  };

  const quickAction = getQuickAction();

  return (
    <div className="min-h-screen bg-slate-50 font-sans selection:bg-teal-100 selection:text-teal-900">
      {/* ================================================================= */}
      {/* DESKTOP SIDEBAR - FIXED & STATIONARY (FULL 100VH VIEWPORT HEIGHT) */}
      {/* ================================================================= */}
      <aside
        className={`hidden md:flex flex-col fixed top-0 left-0 z-40 bg-white border-r border-slate-200/90 transition-all duration-200 ${
          sidebarCollapsed ? 'w-16' : 'w-56'
        }`}
        style={{ height: '100vh' }}
      >
        {/* User Header / Brand in Sidebar */}
        <div className="h-13 sm:h-14 px-3 border-b border-slate-200/90 flex items-center justify-between shrink-0 bg-white">
          {!sidebarCollapsed ? (
            <Link to="/" className="flex items-center gap-2 min-w-0" title="SkillVistaar">
              <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs shrink-0">
                <Sparkles className="w-4 h-4 text-teal-200" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-extrabold text-sm tracking-tight text-slate-900 truncate leading-tight">
                  Skill<span className="text-teal-700">Vistaar</span>
                </span>
                <span className="text-[9px] uppercase tracking-wider text-slate-400 font-semibold truncate leading-none">
                  {roleLabels[currentRole]}
                </span>
              </div>
            </Link>
          ) : (
            <Link to="/" className="mx-auto" title="SkillVistaar">
              <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs">
                <Sparkles className="w-4 h-4 text-teal-200" />
              </div>
            </Link>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 shrink-0"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Links - ONLY this internal area scrolls if menu exceeds viewport */}
        <nav className="p-2 space-y-1 flex-1 overflow-y-auto overflow-x-hidden">
          {navLinks.map((item, idx) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.path ||
              (item.path !== `/${currentRole}` && location.pathname.startsWith(item.path));
            return (
              <Link
                key={idx}
                to={item.path}
                className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs font-medium transition ${
                  isActive
                    ? 'bg-teal-50 text-teal-800 font-bold border border-teal-200/60 shadow-2xs'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                } ${sidebarCollapsed ? 'justify-center' : ''}`}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? 'text-teal-700' : 'text-slate-500'
                  }`}
                />
                {!sidebarCollapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer of Sidebar - Pinned to bottom (shrink-0) */}
        <div className="p-3 border-t border-slate-100 space-y-1 shrink-0 bg-white">
          <Link
            to="/settings"
            className={`flex items-center gap-2 p-2 rounded-lg hover:bg-slate-100 transition text-xs font-semibold text-slate-600 ${
              sidebarCollapsed ? 'justify-center' : ''
            }`}
            title="Settings & Passphrase"
          >
            <Settings className="w-4 h-4 text-slate-500 shrink-0" />
            {!sidebarCollapsed && <span>Settings</span>}
          </Link>
          <Link
            to={`/${currentRole}/profile`}
            className={`flex items-center gap-2 p-2 rounded-lg bg-slate-50 hover:bg-teal-50/60 border border-slate-200 transition text-xs font-semibold text-slate-700 ${
              sidebarCollapsed ? 'justify-center' : ''
            }`}
            title="View Public Profile"
          >
            <User className="w-4 h-4 text-teal-600 shrink-0" />
            {!sidebarCollapsed && <span>Public Profile</span>}
          </Link>
        </div>
      </aside>

      {/* ================================================================= */}
      {/* MOBILE DRAWER (Mobile/tablet navigation drawer) */}
      {/* ================================================================= */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex animate-in fade-in">
          <div className="w-64 bg-white h-full shadow-2xl p-4 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded bg-teal-600 flex items-center justify-center text-white">
                    <Sparkles className="w-4 h-4 text-teal-200" />
                  </div>
                  <span className="font-extrabold text-sm text-slate-900">SkillVistaar</span>
                </div>
                <button onClick={() => setMobileMenuOpen(false)} aria-label="Close Navigation">
                  <X className="w-5 h-5 text-slate-500" />
                </button>
              </div>

              <div className="space-y-1">
                {navLinks.map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={idx}
                      to={item.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-semibold text-slate-700 hover:bg-slate-100"
                    >
                      <Icon className="w-4 h-4 text-teal-600" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
                <Link
                  to="/notifications"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  <Bell className="w-4 h-4 text-teal-600" />
                  <span>Notifications</span>
                </Link>
                <Link
                  to="/settings"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  <Settings className="w-4 h-4 text-teal-600" />
                  <span>Settings</span>
                </Link>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 space-y-2">
              <Button
                variant="outline"
                size="sm"
                fullWidth
                onClick={handleLogout}
                leftIcon={<LogOut className="w-4 h-4" />}
              >
                Sign Out
              </Button>
            </div>
          </div>
          <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
        </div>
      )}

      {/* ================================================================= */}
      {/* MAIN CONTENT WRAPPER - PROPER LEFT OFFSET FOR FIXED SIDEBAR */}
      {/* ================================================================= */}
      <div
        className={`min-h-screen flex flex-col transition-[padding] duration-200 ${
          sidebarCollapsed ? 'md:pl-16' : 'md:pl-56'
        }`}
      >
        {/* COMPACT TOPBAR */}
        <header className="sticky top-0 z-30 h-13 sm:h-14 bg-white border-b border-slate-200/90 shadow-2xs flex items-center justify-between px-3 sm:px-6 shrink-0">
          <div className="flex items-center gap-2 sm:gap-4 min-w-0">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              aria-label="Toggle Navigation"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Mobile Brand Icon & Name */}
            <Link to="/" className="md:hidden flex items-center gap-2 shrink-0">
              <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center text-white shadow-xs">
                <Sparkles className="w-4 h-4 text-teal-200" />
              </div>
              <div className="flex flex-col">
                <span className="font-extrabold text-sm tracking-tight text-slate-900">
                  Skill<span className="text-teal-700">Vistaar</span>
                </span>
              </div>
            </Link>

            {/* Authenticated Workspace Badge (Read-only) */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200/90 shadow-2xs">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-600" />
              <span className="hidden xs:inline text-[11px] text-slate-500 font-medium">Workspace:</span>
              <span className="capitalize font-bold text-teal-900">{roleLabels[currentRole]}</span>
            </div>
          </div>

          {/* Global Search Bar with Live Autocomplete */}
          <div ref={searchContainerRef} className="hidden lg:flex items-center flex-1 max-w-md mx-6 relative">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search verified ministries, employers, candidates, @usernames..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                onFocus={() => {
                  if (searchResults.length > 0) setSearchDropdownOpen(true);
                }}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-slate-50/80 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800 placeholder-slate-400"
              />
            </div>

            {/* Live Autocomplete Dropdown */}
            {searchDropdownOpen && searchQuery.trim().length >= 2 && (
              <div className="absolute left-0 right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-2xl py-2 z-50 animate-in fade-in">
                <div className="px-3 py-1.5 border-b border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="font-bold text-slate-700 uppercase tracking-wider">
                    Verified Directory Results
                  </span>
                  {isSearching && <span className="text-teal-600 font-medium animate-pulse">Searching...</span>}
                </div>

                {!isSearching && searchResults.length === 0 ? (
                  <div className="px-4 py-6 text-center text-xs text-slate-500 space-y-1">
                    <p className="font-semibold text-slate-700">No verified accounts found</p>
                    <p className="text-[11px] text-slate-400">
                      Unverified, pending, or administrative accounts are excluded.
                    </p>
                  </div>
                ) : (
                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-50">
                    {searchResults.map((item) => {
                      const profileUrl = item.username ? `/profile/@${item.username}` : `/profile/${item.id}`;
                      return (
                        <Link
                          key={item.id}
                          to={profileUrl}
                          onClick={() => setSearchDropdownOpen(false)}
                          className="flex items-center gap-3 px-3.5 py-2.5 hover:bg-slate-50 transition text-left"
                        >
                          <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-100 flex items-center justify-center shrink-0 text-teal-700 font-bold text-xs">
                            {item.account_type === 'GOVERNMENT' ? (
                              <Landmark className="w-4 h-4" />
                            ) : item.account_type === 'EMPLOYER' ? (
                              <Briefcase className="w-4 h-4" />
                            ) : item.account_type === 'TRAINING_INSTITUTE' ? (
                              <GraduationCap className="w-4 h-4" />
                            ) : (
                              <User className="w-4 h-4" />
                            )}
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-xs text-slate-900 truncate">{item.name}</span>
                              {item.handle && (
                                <span className="text-[11px] font-mono text-slate-400 truncate">{item.handle}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-slate-500 truncate">
                              <span className="text-teal-700 font-semibold">{item.badge_label}</span>
                              {item.location && <span>• {item.location}</span>}
                            </div>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                )}

                <div className="px-3 py-2 border-t border-slate-100 bg-slate-50/60 rounded-b-xl flex items-center justify-between">
                  <span className="text-[11px] text-slate-400">Press ↵ Enter to view all</span>
                  <button
                    onClick={() => {
                      setSearchDropdownOpen(false);
                      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
                    }}
                    className="text-[11px] font-bold text-teal-700 hover:text-teal-900 transition"
                  >
                    View Directory Page &rarr;
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Topbar Right Tools */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Quick Action */}
            <Button
              variant="primary"
              size="sm"
              onClick={quickAction.action}
              className="text-[11px] font-semibold py-1.5 px-2.5 shadow-2xs hidden sm:inline-flex"
              leftIcon={<PlusCircle className="w-3.5 h-3.5" />}
            >
              {quickAction.label}
            </Button>

            {/* Direct Messages Button */}
            <button
              onClick={() => setMessagesModalOpen(true)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 relative transition"
              aria-label="Direct Messages"
              title="Direct Messages & Requests"
            >
              <MessageSquare className="w-4 h-4" />
              {unreadMessagesCount > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-teal-600 ring-2 ring-white" />
              )}
            </button>

            {/* Notifications Popover */}
            <div className="relative">
              <button
                onClick={() => setNotifsOpen(!notifsOpen)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 relative transition"
                aria-label="Notifications"
              >
                <Bell className="w-4 h-4" />
                {unreadNotifsCount > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-teal-600 ring-2 ring-white" />
                )}
              </button>

              {notifsOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-slate-200 py-2 z-50 animate-in fade-in">
                  <div className="px-3 py-2 border-b border-slate-100 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">Notifications</span>
                    <div className="flex items-center gap-2">
                      {unreadNotifsCount > 0 && (
                        <button
                          onClick={markAllNotificationsRead}
                          className="text-[11px] text-teal-700 hover:underline font-medium"
                        >
                          Mark all read
                        </button>
                      )}
                      <Link
                        to="/notifications"
                        onClick={() => setNotifsOpen(false)}
                        className="text-[11px] font-semibold text-slate-600 hover:text-teal-700"
                      >
                        View all
                      </Link>
                    </div>
                  </div>
                  <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-xs text-slate-400">
                        No notifications available
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          onClick={() => markNotificationRead(n.id)}
                          className={`p-3 text-xs cursor-pointer hover:bg-slate-50 transition flex items-start gap-2.5 ${
                            !n.isRead ? 'bg-teal-50/30' : ''
                          }`}
                        >
                          <div className="mt-0.5">
                            <span
                              className={`w-2 h-2 rounded-full block ${
                                !n.isRead ? 'bg-teal-600' : 'bg-slate-300'
                              }`}
                            />
                          </div>
                          <div className="flex-1">
                            <p className="font-semibold text-slate-900">{n.title}</p>
                            <p className="text-[11px] text-slate-600 leading-snug mt-0.5">{n.message}</p>
                            <span className="text-[10px] text-slate-400 mt-1 block">{n.time}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="p-2 border-t border-slate-100 text-center">
                    <Link
                      to="/notifications"
                      onClick={() => setNotifsOpen(false)}
                      className="text-[11px] font-semibold text-teal-700 hover:underline"
                    >
                      Open Notifications Center &rarr;
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Settings Link */}
            <Link
              to="/settings"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition"
              title="Settings & Passphrase"
            >
              <Settings className="w-4 h-4" />
            </Link>

            {/* User Profile Thumbnail */}
            <Link
              to={`/${currentRole}/profile`}
              className="flex items-center gap-2 pl-2 border-l border-slate-200 group"
              title="View Public Profile"
            >
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-teal-700 text-white flex items-center justify-center font-bold text-xs border border-slate-200 group-hover:ring-2 group-hover:ring-teal-500 transition">
                {currentUser.name ? currentUser.name[0].toUpperCase() : 'U'}
              </div>
              <div className="hidden xl:flex flex-col text-left">
                <span className="text-xs font-bold text-slate-900 truncate max-w-[110px] leading-tight">
                  {currentUser.name}
                </span>
                <span className="text-[10px] text-teal-700 font-medium">
                  @{currentUser.username}
                </span>
              </div>
            </Link>

            {/* Sign Out Button */}
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition ml-1"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* MAIN DASHBOARD CONTENT AREA */}
        <main className="flex-1 p-4 sm:p-6 lg:p-7 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>

      <DirectMessagingModal
        isOpen={messagesModalOpen}
        onClose={() => {
          setMessagesModalOpen(false);
          messagingApi.getUnreadCounts().then((c) => setUnreadMessagesCount(c.total)).catch(() => {});
        }}
      />
    </div>
  );
};

// Simple helper icon
const CheckCircle2Icon: React.FC<{ className?: string }> = ({ className }) => (
  <Award className={className} />
);

export default DashboardLayout;
