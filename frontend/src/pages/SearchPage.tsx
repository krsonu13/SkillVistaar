import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import {
  Search,
  ShieldCheck,
  Building2,
  GraduationCap,
  Landmark,
  User,
  MapPin,
  ExternalLink,
  Plus,
  Check,
  X,
  Sparkles,
} from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Footer from '../components/common/Footer';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';
import { searchApi, followingApi, SearchProfileItem } from '../services/api';
import { useAuth } from '../context/AuthContext';

type FilterType = 'ALL' | 'GOVERNMENT' | 'EMPLOYER' | 'TRAINING_INSTITUTE' | 'CANDIDATE';

export const SearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const initialQuery = searchParams.get('q') || '';
  const initialType = (searchParams.get('type')?.toUpperCase() as FilterType) || 'ALL';

  const [query, setQuery] = useState(initialQuery);
  const [activeType, setActiveType] = useState<FilterType>(initialType);
  const [results, setResults] = useState<SearchProfileItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [followingMap, setFollowingMap] = useState<Record<string, boolean>>({});

  const performSearch = useCallback(async (q: string, type: FilterType) => {
    if (!q.trim()) {
      setResults([]);
      setTotalCount(0);
      return;
    }
    setLoading(true);
    try {
      const resp = await searchApi.searchProfiles({
        q: q.trim(),
        account_type: type === 'ALL' ? undefined : type,
        limit: 30,
      });
      setResults(resp.items);
      setTotalCount(resp.total);
    } catch {
      setResults([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const qParam = searchParams.get('q') || '';
    const typeParam = (searchParams.get('type')?.toUpperCase() as FilterType) || 'ALL';
    setQuery(qParam);
    setActiveType(typeParam);
    performSearch(qParam, typeParam);
  }, [searchParams, performSearch]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params: Record<string, string> = {};
    if (query.trim()) params.q = query.trim();
    if (activeType !== 'ALL') params.type = activeType;
    setSearchParams(params);
  };

  const handleTypeChange = (type: FilterType) => {
    setActiveType(type);
    const params: Record<string, string> = {};
    if (query.trim()) params.q = query.trim();
    if (type !== 'ALL') params.type = type;
    setSearchParams(params);
  };

  const handleToggleFollow = async (e: React.MouseEvent, item: SearchProfileItem) => {
    e.preventDefault();
    e.stopPropagation();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    const currentStatus = followingMap[item.id] ?? false;
    setFollowingMap((prev) => ({ ...prev, [item.id]: !currentStatus }));

    try {
      await followingApi.toggleFollow('USER', item.id);
    } catch {
      // Revert on failure
      setFollowingMap((prev) => ({ ...prev, [item.id]: currentStatus }));
    }
  };

  const getAccountIcon = (accType: string) => {
    switch (accType) {
      case 'GOVERNMENT':
        return <Landmark className="w-4 h-4 text-amber-600" />;
      case 'EMPLOYER':
        return <Building2 className="w-4 h-4 text-teal-600" />;
      case 'TRAINING_INSTITUTE':
        return <GraduationCap className="w-4 h-4 text-emerald-600" />;
      case 'CANDIDATE':
      default:
        return <User className="w-4 h-4 text-sky-600" />;
    }
  };

  const getBadgeVariant = (accType: string): 'amber' | 'blue' | 'emerald' | 'teal' => {
    switch (accType) {
      case 'GOVERNMENT':
        return 'amber';
      case 'EMPLOYER':
        return 'blue';
      case 'TRAINING_INSTITUTE':
        return 'emerald';
      case 'CANDIDATE':
      default:
        return 'teal';
    }
  };

  const filterTabs: { id: FilterType; label: string }[] = [
    { id: 'ALL', label: 'All Verified Accounts' },
    { id: 'GOVERNMENT', label: 'Government Bodies' },
    { id: 'EMPLOYER', label: 'Employers & Industry' },
    { id: 'TRAINING_INSTITUTE', label: 'Training Institutes' },
    { id: 'CANDIDATE', label: 'Verified Candidates' },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      <Navbar />

      <main className="flex-1 pb-16">
        {/* Search Bar Header */}
        <div className="bg-white border-b border-slate-200 py-8 px-4 sm:px-6 lg:px-8 shadow-2xs">
          <div className="max-w-4xl mx-auto space-y-4">
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-teal-50 text-teal-700 border border-teal-200/60">
                <Search className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  Global Directory & Verification Search
                </h1>
                <p className="text-xs text-slate-500">
                  Search across verified government bodies, registered employers, accredited institutes, and certified candidates.
                </p>
              </div>
            </div>

            {/* Input Form */}
            <form onSubmit={handleSearchSubmit} className="relative flex items-center">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by legal name, ministry, district, or @username (e.g. @bihar_skill)..."
                  className="w-full pl-10 pr-10 py-3 text-sm bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 placeholder-slate-400 font-medium transition"
                  autoFocus
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => {
                      setQuery('');
                      setResults([]);
                      setTotalCount(0);
                    }}
                    className="absolute right-3.5 top-3.5 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
              <Button
                type="submit"
                variant="primary"
                className="ml-2.5 py-3 px-6 text-xs font-bold rounded-xl shadow-xs"
              >
                Search
              </Button>
            </form>

            {/* Filter Pills */}
            <div className="flex overflow-x-auto gap-2 pt-1 pb-0.5 no-scrollbar">
              {filterTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTypeChange(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition border ${
                    activeType === tab.id
                      ? 'bg-teal-700 text-white border-teal-700 shadow-2xs'
                      : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200/80 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Results Container */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
          {/* Results Summary Bar */}
          {query.trim() && (
            <div className="flex items-center justify-between pb-4 text-xs text-slate-500 font-medium">
              <span>
                Found <strong className="text-slate-900 font-bold">{totalCount}</strong> verified result
                {totalCount === 1 ? '' : 's'} for &ldquo;{query}&rdquo;
              </span>
              <span className="flex items-center gap-1 text-[11px] text-teal-700">
                <ShieldCheck className="w-3.5 h-3.5" />
                Statutory Verified Accounts Only
              </span>
            </div>
          )}

          {/* Loading Indicator */}
          {loading && (
            <div className="py-16 text-center space-y-3">
              <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500 font-medium">Querying verified registry...</p>
            </div>
          )}

          {/* No Results Empty State */}
          {!loading && query.trim() && results.length === 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-2xs text-center">
              <EmptyState
                icon={Search}
                title="No Verified Accounts Found"
                description={`No verified organization, government unit, or candidate matched "${query}". Unverified, pending, and administrative accounts are excluded.`}
                actionText="Clear Search"
                onAction={() => {
                  setQuery('');
                  setSearchParams({});
                }}
              />
            </div>
          )}

          {/* Prompt to Search when empty */}
          {!loading && !query.trim() && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 shadow-2xs text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-700 mx-auto">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">Explore the SkillVistaar Verified Network</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Search verified government authorities, employers, accredited training institutes, and candidate profiles by name or @username.
              </p>
              <div className="flex flex-wrap justify-center gap-2 pt-2">
                <button
                  onClick={() => {
                    setQuery('bihar');
                    setSearchParams({ q: 'bihar' });
                  }}
                  className="px-3 py-1 rounded-full text-xs bg-slate-100 hover:bg-teal-50 text-slate-700 hover:text-teal-800 border border-slate-200 transition font-medium"
                >
                  @bihar_skill
                </button>
                <button
                  onClick={() => {
                    setQuery('msde');
                    setSearchParams({ q: 'msde' });
                  }}
                  className="px-3 py-1 rounded-full text-xs bg-slate-100 hover:bg-teal-50 text-slate-700 hover:text-teal-800 border border-slate-200 transition font-medium"
                >
                  @msde_central
                </button>
                <button
                  onClick={() => {
                    setQuery('pune');
                    setSearchParams({ q: 'pune' });
                  }}
                  className="px-3 py-1 rounded-full text-xs bg-slate-100 hover:bg-teal-50 text-slate-700 hover:text-teal-800 border border-slate-200 transition font-medium"
                >
                  @pune_skill
                </button>
              </div>
            </div>
          )}

          {/* Result Cards List */}
          {!loading && results.length > 0 && (
            <div className="space-y-3">
              {results.map((item) => {
                const profileUrl = item.username ? `/profile/@${item.username}` : `/profile/${item.id}`;
                const isFollowed = followingMap[item.id] ?? false;
                const isSelf = currentUser?.id === item.id;

                return (
                  <div
                    key={item.id}
                    className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-2xs hover:border-slate-300 hover:shadow-xs transition flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3.5 min-w-0">
                      {/* Avatar */}
                      <div className="w-11 h-11 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0">
                        {getAccountIcon(item.account_type)}
                      </div>

                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Link
                            to={profileUrl}
                            className="font-bold text-sm sm:text-base text-slate-900 hover:text-teal-700 transition truncate"
                          >
                            {item.name}
                          </Link>
                          {item.handle && (
                            <span className="text-xs font-mono font-medium text-slate-500">
                              {item.handle}
                            </span>
                          )}
                          <Badge variant={getBadgeVariant(item.account_type)} size="sm">
                            <ShieldCheck className="w-3 h-3 mr-1" />
                            {item.badge_label}
                          </Badge>
                        </div>

                        {item.headline && (
                          <p className="text-xs text-slate-600 line-clamp-1 font-medium">
                            {item.headline}
                          </p>
                        )}

                        {item.location && (
                          <div className="flex items-center gap-1 text-[11px] text-slate-400">
                            <MapPin className="w-3 h-3" />
                            <span>{item.location}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      {!isSelf && currentUser && (
                        <Button
                          variant={isFollowed ? 'outline' : 'secondary'}
                          size="sm"
                          onClick={(e) => handleToggleFollow(e, item)}
                          className="text-xs py-1.5 px-3"
                          leftIcon={isFollowed ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Plus className="w-3.5 h-3.5" />}
                        >
                          {isFollowed ? 'Following' : 'Follow'}
                        </Button>
                      )}

                      <Link to={profileUrl}>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs py-1.5 px-3 text-slate-700 hover:bg-slate-100"
                          rightIcon={<ExternalLink className="w-3 h-3" />}
                        >
                          View Profile
                        </Button>
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SearchPage;
