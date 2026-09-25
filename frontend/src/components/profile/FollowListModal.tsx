import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Search, Check, Plus, Shield, Loader2 } from 'lucide-react';
import { FollowUserItem } from '../../types/profile';
import Badge from '../common/Badge';
import { EmptyState } from '../common/EmptyState';
import { userApi, followingApi, resolveMediaUrl } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { toFrontendAccountType } from '../../types/auth';

interface FollowListModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: 'Followers' | 'Following';
  entityName: string;
  identifier?: string;
  initialUsers?: FollowUserItem[];
  onCountChange?: (delta: number) => void;
}

export const FollowListModal: React.FC<FollowListModalProps> = ({
  isOpen,
  onClose,
  title,
  entityName,
  identifier,
  initialUsers = [],
  onCountChange,
}) => {
  const [users, setUsers] = useState<FollowUserItem[]>(initialUsers);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const navigate = useNavigate();
  const { user: authUser } = useAuth();

  useEffect(() => {
    if (!isOpen) return;

    if (identifier) {
      setIsLoading(true);
      const fetchList = title === 'Followers'
        ? userApi.getFollowers(identifier)
        : userApi.getFollowingUsers(identifier);

      fetchList
        .then((res) => {
          const mapped: FollowUserItem[] = (res.items || []).map((u: any) => ({
            id: u.id || u.user_id,
            name: u.name || u.username || 'User',
            username: u.username || u.id,
            avatar: resolveMediaUrl(u.avatar_url) || '',
            role: toFrontendAccountType(u.account_type),
            headline: u.headline || (u.account_type ? u.account_type.replace('_', ' ') : 'Platform Member'),
            isFollowing: Boolean(u.is_following),
          }));
          setUsers(mapped);
        })
        .catch(() => {
          setUsers(initialUsers);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setUsers(initialUsers);
    }
  }, [isOpen, identifier, title]);

  if (!isOpen) return null;

  const toggleUserFollow = async (id: string) => {
    if (!authUser) {
      navigate('/login');
      return;
    }
    if (authUser.id === id) return;

    setActionLoadingId(id);
    const target = users.find((u) => u.id === id);
    const prevStatus = target ? target.isFollowing : false;

    // Optimistic UI update
    setUsers((prev) =>
      prev.map((u) => (u.id === id ? { ...u, isFollowing: !prevStatus } : u))
    );

    try {
      const res = await followingApi.toggleFollow('USER', id);
      if (res && res.is_following !== undefined) {
        setUsers((prev) =>
          prev.map((u) => (u.id === id ? { ...u, isFollowing: res.is_following } : u))
        );
        if (onCountChange) {
          onCountChange(res.is_following ? 1 : -1);
        }
      }
    } catch {
      // Revert on error
      setUsers((prev) =>
        prev.map((u) => (u.id === id ? { ...u, isFollowing: prevStatus } : u))
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleNavigateProfile = (username: string) => {
    onClose();
    navigate(`/profile/@${username}`);
  };

  const filtered = users.filter(
    (u) =>
      u.name.toLowerCase().includes(query.toLowerCase()) ||
      u.username.toLowerCase().includes(query.toLowerCase()) ||
      u.headline.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              {title} of {entityName}
            </h3>
            <p className="text-[11px] text-slate-500">
              Verified platform stakeholders & participants
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Filter */}
        <div className="p-3 border-b border-slate-100 bg-white">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder={`Search in ${title.toLowerCase()}...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-teal-500 bg-slate-50/50"
            />
          </div>
        </div>

        {/* User List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2.5 divide-y divide-slate-100">
          {isLoading ? (
            <div className="py-8 flex flex-col items-center justify-center text-slate-400 gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
              <span className="text-xs">Loading {title.toLowerCase()}...</span>
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              title={`No ${title.toLowerCase()} found`}
              description={`There are currently no ${title.toLowerCase()} recorded on this profile.`}
            />
          ) : (
            filtered.map((u) => {
              const isCurrentUser = authUser?.id === u.id;
              return (
                <div key={u.id} className="pt-2.5 first:pt-0 flex items-center justify-between gap-3">
                  <div
                    onClick={() => handleNavigateProfile(u.username)}
                    className="flex items-center gap-2.5 min-w-0 cursor-pointer group flex-1"
                  >
                    {u.avatar ? (
                      <img
                        src={u.avatar}
                        alt={u.name}
                        className="w-9 h-9 rounded-full object-cover border border-slate-200 shrink-0"
                      />
                    ) : (
                      <div className="w-9 h-9 rounded-full bg-teal-100 text-teal-800 font-bold text-xs flex items-center justify-center border border-teal-200 shrink-0">
                        {u.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-slate-900 group-hover:text-teal-700 transition truncate">
                          {u.name}
                        </span>
                        <Shield className="w-3 h-3 text-teal-600 shrink-0" />
                      </div>
                      <span className="text-[10px] text-slate-400 block truncate">
                        @{u.username}
                      </span>
                      <p className="text-[11px] text-slate-600 line-clamp-1 mt-0.5">
                        {u.headline}
                      </p>
                    </div>
                  </div>

                  {!isCurrentUser && (
                    <div className="shrink-0">
                      <button
                        onClick={() => toggleUserFollow(u.id)}
                        disabled={actionLoadingId === u.id}
                        className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all duration-150 flex items-center gap-1 ${
                          u.isFollowing
                            ? 'border border-slate-200 bg-slate-100 text-slate-700 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200'
                            : 'bg-teal-600 hover:bg-teal-700 text-white shadow-2xs'
                        }`}
                      >
                        {actionLoadingId === u.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : u.isFollowing ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-600" />
                            <span>Following</span>
                          </>
                        ) : (
                          <>
                            <Plus className="w-3 h-3" />
                            <span>Follow</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 text-center">
          <Badge variant="teal" size="sm">
            All connections cross-verified on SkillVistaar Registry
          </Badge>
        </div>
      </div>
    </div>
  );
};

export default FollowListModal;
