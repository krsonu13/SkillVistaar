import React, { createContext, useContext, useState, useEffect } from 'react';
import { AccountType, normalizeAccountType, toFrontendAccountType } from '../types/auth';
import { useAuth } from './AuthContext';
import { UserProfile } from '../types/profile';
import { NotificationItem } from '../types/dashboard';
import platformService from '../api/platformService';

export const createEmptyProfile = (role: AccountType, user?: any): UserProfile => {
  const username = user?.email?.split('@')[0] || user?.phone || 'user';
  return {
    id: user?.id || 'current-user',
    username,
    name: user?.name || username,
    role,
    avatar: '',
    coverImage: '',
    headline: '',
    bio: '',
    location: '',
    website: '',
    isVerified: Boolean(user?.email_verified || user?.phone_verified),
    badgeType: role === 'government' ? 'gov_gold' : role === 'admin' ? 'admin' : 'digilocker',
    joinedDate: '2026',
    followersCount: 0,
    followingCount: 0,
    isFollowing: false,
    posts: [],
  };
};

interface MessageModalState {
  isOpen: boolean;
  recipientName: string;
  recipientRole: string;
}

interface ApplyModalState {
  isOpen: boolean;
  jobTitle: string;
  companyName: string;
}

interface PlatformContextType {
  currentRole: AccountType;
  currentUser: UserProfile;
  profiles: Record<string, UserProfile>;
  notifications: NotificationItem[];
  unreadNotifsCount: number;
  messageModal: MessageModalState;
  applyModal: ApplyModalState;
  switchRole: (role: AccountType) => void;
  toggleFollow: (username: string) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  openMessageModal: (name: string, role: string) => void;
  closeMessageModal: () => void;
  openApplyModal: (title: string, company: string) => void;
  closeApplyModal: () => void;
}

const PlatformContext = createContext<PlatformContextType | undefined>(undefined);

export const PlatformProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const authFrontendRole = user ? toFrontendAccountType(user.account_type) : null;

  const [currentRole, setCurrentRole] = useState<AccountType>(() => {
    if (authFrontendRole) return authFrontendRole;
    const saved = localStorage.getItem('sv_active_role');
    return (saved as AccountType) || 'candidate';
  });

  // Keep currentRole strictly synchronized with the authenticated user
  useEffect(() => {
    if (authFrontendRole && authFrontendRole !== currentRole) {
      setCurrentRole(authFrontendRole);
    }
  }, [authFrontendRole]);

  const [profiles, setProfiles] = useState<Record<string, UserProfile>>({});

  const [currentUser, setCurrentUser] = useState<UserProfile>(() => {
    return createEmptyProfile(currentRole, user);
  });

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  useEffect(() => {
    let isMounted = true;
    const fetchNotifs = async () => {
      const token = localStorage.getItem('sv_auth_token');
      if (!token) {
        setNotifications([]);
        return;
      }
      try {
        const liveNotifs = await platformService.getNotifications();
        if (isMounted) {
          setNotifications(
            liveNotifs.map((n) => ({
              id: n.id,
              title: n.title,
              message: n.message || '',
              time: n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Recent',
              type: 'info' as const,
              isRead: n.is_read,
            }))
          );
        }
      } catch {
        if (isMounted) setNotifications([]);
      }
    };

    fetchNotifs();
    return () => {
      isMounted = false;
    };
  }, [currentRole]);

  const [messageModal, setMessageModal] = useState<MessageModalState>({
    isOpen: false,
    recipientName: '',
    recipientRole: '',
  });

  const [applyModal, setApplyModal] = useState<ApplyModalState>({
    isOpen: false,
    jobTitle: '',
    companyName: '',
  });

  // Keep currentUser in sync when role or user switches
  useEffect(() => {
    const defaultProfile = createEmptyProfile(currentRole, user);
    setCurrentUser(defaultProfile);
    localStorage.setItem('sv_active_role', currentRole);
  }, [currentRole, user]);

  const switchRole = (role: AccountType) => {
    // Only allow if user actually has the requested role in their authorized roles list
    const canonical = normalizeAccountType(role);
    if (user && user.roles && user.roles.includes(canonical)) {
      setCurrentRole(role);
    } else {
      console.warn(`[PlatformContext] Blocked unauthorized role switch to "${role}". Authenticated role: ${user?.account_type}`);
    }
  };

  const toggleFollow = (username: string) => {
    const clean = username.toLowerCase().replace('@', '');
    setProfiles((prev) => {
      const target = prev[clean];
      if (!target) return prev;

      const nextFollowingState = !target.isFollowing;
      const nextCount = nextFollowingState
        ? target.followersCount + 1
        : Math.max(0, target.followersCount - 1);

      const updated = {
        ...prev,
        [clean]: {
          ...target,
          isFollowing: nextFollowingState,
          followersCount: nextCount,
        },
      };

      // Persist in localStorage
      const followMap = JSON.parse(localStorage.getItem('sv_following_map') || '{}');
      followMap[clean] = nextFollowingState;
      localStorage.setItem('sv_following_map', JSON.stringify(followMap));

      return updated;
    });
  };

  const markNotificationRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
    );
    platformService.markNotificationRead(id).catch(() => {});
  };

  const markAllNotificationsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
    platformService.markAllNotificationsRead().catch(() => {});
  };

  const openMessageModal = (name: string, role: string) => {
    setMessageModal({ isOpen: true, recipientName: name, recipientRole: role });
  };

  const closeMessageModal = () => {
    setMessageModal({ isOpen: false, recipientName: '', recipientRole: '' });
  };

  const openApplyModal = (title: string, company: string) => {
    setApplyModal({ isOpen: true, jobTitle: title, companyName: company });
  };

  const closeApplyModal = () => {
    setApplyModal({ isOpen: false, jobTitle: '', companyName: '' });
  };

  const unreadNotifsCount = notifications.filter((n) => !n.isRead).length;

  return (
    <PlatformContext.Provider
      value={{
        currentRole,
        currentUser,
        profiles,
        notifications,
        unreadNotifsCount,
        messageModal,
        applyModal,
        switchRole,
        toggleFollow,
        markNotificationRead,
        markAllNotificationsRead,
        openMessageModal,
        closeMessageModal,
        openApplyModal,
        closeApplyModal,
      }}
    >
      {children}
    </PlatformContext.Provider>
  );
};

export const usePlatform = (): PlatformContextType => {
  const context = useContext(PlatformContext);
  if (!context) {
    throw new Error('usePlatform must be used within a PlatformProvider');
  }
  return context;
};
