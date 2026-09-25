import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowRight,
  ShieldCheck,
  Award,
  Users,
  Building2,
  GraduationCap,
  Landmark,
  CheckCircle2,
  TrendingUp,
  FileCheck2,
  ChevronRight,
  Target,
  BarChart3,
  X,
} from 'lucide-react';
import Navbar from '../components/common/Navbar';
import Footer from '../components/common/Footer';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import { AccountType } from '../types/auth';
import platformService, { PublicPlatformStats } from '../api/platformService';
import { publicApi } from '../services/api';

interface StakeholderDetail {
  id: AccountType;
  title: string;
  badge: string;
  tagline: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  features: string[];
  metrics: { value: string; label: string }[];
  ctaLabel: string;
}

const STAKEHOLDERS: StakeholderDetail[] = [
  {
    id: 'candidate',
    title: 'Candidates & Learners',
    badge: 'Job Seekers • Students • Apprentices',
    tagline: 'Verified Digital Skill Passports & Transparent Job Opportunities',
    description:
      'Build a tamper-proof digital profile backed by verified certifications. Match directly with certified employers, apprenticeships, and government-subsidized skilling cohorts.',
    icon: Users,
    features: [
      'DigiLocker integrated Skill Passport with verifiable credentials',
      'AI-driven skill-gap analysis with recommended upskilling paths',
      'Direct application to pre-verified enterprise & MSME vacancies',
      'State stipend & DBT scholarship entitlement tracking',
    ],
    metrics: [
      { value: 'NSQF', label: 'Framework Aligned' },
      { value: 'DigiLocker', label: 'Cryptographic Proof' },
    ],
    ctaLabel: 'Register as Candidate',
  },
  {
    id: 'employer',
    title: 'Industrial Employers',
    badge: 'Enterprises • MSMEs • Startups',
    tagline: 'Direct Access to Skill-Assessed, Pre-Screened Talent Pipelines',
    description:
      'Eliminate resume fraud with cryptographically verified credentials. Post opportunities, discover certified graduates, and run apprenticeship programs with compliance automation.',
    icon: Building2,
    features: [
      'Instant skill credential verification eliminating background delays',
      'Filter candidates by NSQF competency levels and practical scores',
      'Seamless apprenticeship posting with NAPS/NATS compliance',
      'Bulk talent discovery across central and state vocational hubs',
    ],
    metrics: [
      { value: '100%', label: 'Verified Integrity' },
      { value: 'Instant', label: 'Credential Audit' },
    ],
    ctaLabel: 'Register as Employer',
  },
  {
    id: 'institute',
    title: 'Training Institutes',
    badge: 'Vocational Centers • Polytechnics • ITIs',
    tagline: 'Accredited Curriculum Management, Batch Tracking & Placement Proof',
    description:
      'Manage NSQF-aligned training programs, track cohort attendance, issue verifiable digital completion certificates, and showcase transparent placement outcomes.',
    icon: GraduationCap,
    features: [
      'Automated batch creation and trainee progress monitoring',
      'Direct issuance of blockchain-anchored digital certificates',
      'Institutional dashboard for CSR funding & government scheme grants',
      'Industry connection portal for campus apprenticeship drives',
    ],
    metrics: [
      { value: 'Accredited', label: 'Curriculum Standards' },
      { value: 'Verifiable', label: 'Certificate Issuance' },
    ],
    ctaLabel: 'Register as Institute',
  },
  {
    id: 'government',
    title: 'Government & Public Bodies',
    badge: 'Ministries • State Skill Missions • District Committees',
    tagline: 'Real-Time Labor Market Intelligence, Scheme Audits & Policy Insight',
    description:
      'Monitor state-level skilling initiatives, track scheme disbursements, analyze district-level demand vs. supply trends, and maintain unified national skilling compliance.',
    icon: Landmark,
    features: [
      'Real-time district skill supply vs industry demand heatmaps',
      'Targeted monitoring of PMKVY, DDU-GKY and state-level schemes',
      'Direct Benefit Transfer (DBT) verification and fund tracking',
      'Unified data exchange for inter-departmental policymaking',
    ],
    metrics: [
      { value: '7-Tier', label: 'Governance Hierarchy' },
      { value: 'Real-Time', label: 'Audit Logging' },
    ],
    ctaLabel: 'Access Government Portal',
  },
];

export const LandingPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [activeTab, setActiveTab] = useState<AccountType>('candidate');
  const [stats, setStats] = useState<PublicPlatformStats | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [platformConfig, setPlatformConfig] = useState<any>(null);
  const [announcement, setAnnouncement] = useState<any>(null);
  const [announcementDismissed, setAnnouncementDismissed] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const [statsData, cfgData, annData] = await Promise.all([
          platformService.getPublicPlatformStats(),
          publicApi.getPlatformConfig('landing_content'),
          publicApi.getPlatformConfig('system_announcements'),
        ]);
        if (isMounted) {
          if (statsData) setStats(statsData);
          if (cfgData) setPlatformConfig(cfgData);
          if (annData) setAnnouncement(annData);
        }
      } catch {
        // keep defaults
      } finally {
        if (isMounted) setIsLoadingStats(false);
      }
    };
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  const verifiedParam = searchParams.get('verified');
  const loggedInParam = searchParams.get('logged_in');

  const currentStakeholder = STAKEHOLDERS.find((s) => s.id === activeTab) || STAKEHOLDERS[0];
  const CurrentIcon = currentStakeholder.icon;

  const handleDismissBanner = () => {
    setBannerDismissed(true);
    setSearchParams({});
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 selection:bg-teal-100 selection:text-teal-900">
      {/* Dynamic Status Toast Banner */}
      {!bannerDismissed && (verifiedParam || loggedInParam) && (
        <div className="bg-teal-700 text-white px-4 py-2 text-xs font-medium flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2 max-w-7xl mx-auto w-full">
            <CheckCircle2 className="w-4 h-4 text-teal-200 shrink-0" />
            <span>
              {verifiedParam
                ? 'OTP verification completed! Welcome to the SkillVistaar verified network.'
                : `Successfully authenticated as ${loggedInParam?.toUpperCase()}. Welcome back!`}
            </span>
            <button
              onClick={handleDismissBanner}
              className="ml-auto text-teal-200 hover:text-white p-1 rounded"
              aria-label="Dismiss banner"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      <Navbar />

      {/* Dynamic System Broadcast Announcement */}
      {!announcementDismissed && announcement?.banner_enabled && announcement.banner_message && (
        <div
          className={`px-4 py-2.5 text-xs font-medium border-b flex items-center justify-between ${
            announcement.severity === 'CRITICAL'
              ? 'bg-rose-600 text-white border-rose-700'
              : announcement.severity === 'WARNING'
              ? 'bg-amber-500 text-white border-amber-600'
              : announcement.severity === 'INFO'
              ? 'bg-sky-600 text-white border-sky-700'
              : 'bg-teal-800 text-teal-50 border-teal-900'
          }`}
        >
          <div className="flex items-center gap-2 max-w-7xl mx-auto w-full">
            <span className="font-bold uppercase tracking-wider text-[10px] px-1.5 py-0.5 rounded bg-black/20">
              {announcement.banner_title || 'Announcement'}
            </span>
            <span className="truncate">{announcement.banner_message}</span>
            <button
              onClick={() => setAnnouncementDismissed(true)}
              className="ml-auto text-white/80 hover:text-white p-0.5"
              aria-label="Dismiss announcement"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      <main className="flex-1">
        {/* Compact Hero Section */}
        <section className="relative overflow-hidden pt-8 pb-10 sm:pt-12 sm:pb-14 bg-gradient-to-b from-white via-slate-50 to-slate-100/70 border-b border-slate-200/80">
          {/* Subtle geometric pattern background */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f766e08_1px,transparent_1px),linear-gradient(to_bottom,#0f766e08_1px,transparent_1px)] bg-[size:28px_28px] pointer-events-none" />

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
            <div className="max-w-3xl mx-auto text-center space-y-4">
              {/* Badges */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold shadow-2xs">
                <span className="flex h-2 w-2 rounded-full bg-teal-500 animate-pulse" />
                <span>{platformConfig?.hero_badge || 'National Unified Skill & Opportunity Exchange'}</span>
              </div>

              {/* Headline */}
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
                {platformConfig?.hero_title ? (
                  platformConfig.hero_title
                ) : (
                  <>
                    Skill <span className="text-teal-600">|</span> Opportunity{' '}
                    <span className="text-teal-600">|</span> Growth
                  </>
                )}
              </h1>

              {/* Subtitle */}
              <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl mx-auto font-normal">
                {platformConfig?.hero_subtitle ||
                  'SkillVistaar interconnects ambitious talent, certified employers, accredited vocational institutes, and government policy bodies into a transparent, verifiable skilling and placement ecosystem.'}
              </p>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
                <Link to="/signup">
                  <Button
                    variant="primary"
                    size="lg"
                    className="shadow-md shadow-teal-600/20 px-5 text-xs sm:text-sm"
                    rightIcon={<ArrowRight className="w-4 h-4" />}
                  >
                    Create Free Account
                  </Button>
                </Link>
                <Link to="/login">
                  <Button
                    variant="outline"
                    size="lg"
                    className="px-5 text-xs sm:text-sm bg-white hover:bg-slate-50"
                  >
                    Stakeholder Login
                  </Button>
                </Link>
              </div>

              {/* Trust Indicators */}
              <div className="pt-2 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-500 font-medium">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                  NSQF Framework Aligned
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1">
                  <Award className="w-3.5 h-3.5 text-teal-600" />
                  DigiLocker Skill Passport
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                  100% Verifiable Credentials
                </span>
              </div>
            </div>

            {/* Platform Metrics Strip */}
            <div className="mt-8 max-w-4xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-white rounded-lg p-3.5 border border-slate-200/80 shadow-xs text-center">
                <p className="text-xl sm:text-2xl font-black text-slate-900 font-sans tracking-tight">
                  {isLoadingStats ? '...' : (stats?.verified_candidates ?? 0).toLocaleString()}
                </p>
                <p className="text-[11px] font-semibold text-teal-700 mt-0.5">
                  {platformConfig?.stats_candidates_label || 'Verified Candidates'}
                </p>
                <p className="text-[10px] text-slate-400">Indexed by competency</p>
              </div>
              <div className="bg-white rounded-lg p-3.5 border border-slate-200/80 shadow-xs text-center">
                <p className="text-xl sm:text-2xl font-black text-slate-900 font-sans tracking-tight">
                  {isLoadingStats ? '...' : (stats?.hiring_employers ?? 0).toLocaleString()}
                </p>
                <p className="text-[11px] font-semibold text-teal-700 mt-0.5">
                  {platformConfig?.stats_employers_label || 'Hiring Employers'}
                </p>
                <p className="text-[10px] text-slate-400">Enterprises & MSMEs</p>
              </div>
              <div className="bg-white rounded-lg p-3.5 border border-slate-200/80 shadow-xs text-center">
                <p className="text-xl sm:text-2xl font-black text-slate-900 font-sans tracking-tight">
                  {isLoadingStats ? '...' : (stats?.training_institutes ?? 0).toLocaleString()}
                </p>
                <p className="text-[11px] font-semibold text-teal-700 mt-0.5">
                  {platformConfig?.stats_institutes_label || 'Training Institutes'}
                </p>
                <p className="text-[10px] text-slate-400">Accredited academies</p>
              </div>
              <div className="bg-white rounded-lg p-3.5 border border-slate-200/80 shadow-xs text-center">
                <p className="text-xl sm:text-2xl font-black text-slate-900 font-sans tracking-tight">
                  {isLoadingStats ? '...' : (stats?.verified_credentials ?? 0).toLocaleString()}
                </p>
                <p className="text-[11px] font-semibold text-teal-700 mt-0.5">
                  {platformConfig?.stats_credentials_label || 'Verified Credentials'}
                </p>
                <p className="text-[10px] text-slate-400">Verifiable credentials</p>
              </div>
            </div>
          </div>
        </section>

        {/* Stakeholder Segmentation Hub */}
        <section id="stakeholders" className="py-10 sm:py-12 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-2xl mx-auto mb-6">
              <Badge variant="teal" size="sm" className="mb-2">
                Four Pillars of the Ecosystem
              </Badge>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                Designed for Every Stakeholder
              </h2>
              <p className="text-xs sm:text-sm text-slate-500 mt-1">
                Select your persona to discover tailored workflows, tools, and direct benefits.
              </p>
            </div>

            {/* Stakeholder Selector Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-w-3xl mx-auto mb-6">
              {STAKEHOLDERS.map((s) => {
                const Icon = s.icon;
                const isSelected = activeTab === s.id;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setActiveTab(s.id)}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border text-left transition-all duration-150 ${
                      isSelected
                        ? 'border-teal-600 bg-teal-50/60 ring-1 ring-teal-600 shadow-2xs'
                        : 'border-slate-200 bg-slate-50/70 hover:bg-slate-100 hover:border-slate-300'
                    }`}
                  >
                    <div
                      className={`w-7 h-7 rounded flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-teal-600 text-white' : 'bg-white text-slate-600 border border-slate-200'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <span className="block text-xs font-bold text-slate-900 truncate">
                        {s.title.split(' ')[0]}
                      </span>
                      <span className="block text-[10px] text-slate-500 truncate">
                        {s.id === 'government' ? 'Public' : s.badge.split('•')[0]}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Active Stakeholder Spotlight Card */}
            <div className="max-w-4xl mx-auto rounded-xl border border-slate-200 bg-gradient-to-br from-white via-slate-50/40 to-teal-50/20 p-5 sm:p-7 shadow-xs">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
                {/* Left Col Info */}
                <div className="lg:col-span-8 space-y-3.5">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg bg-teal-600 text-white flex items-center justify-center shadow-xs">
                      <CurrentIcon className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-lg sm:text-xl font-bold text-slate-900">
                        {currentStakeholder.title}
                      </h3>
                      <p className="text-xs text-teal-700 font-semibold">
                        {currentStakeholder.tagline}
                      </p>
                    </div>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                    {currentStakeholder.description}
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                    {currentStakeholder.features.map((feat, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-xs text-slate-700">
                        <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0 mt-0.5" />
                        <span>{feat}</span>
                      </div>
                    ))}
                  </div>

                  <div className="pt-2 flex items-center gap-3">
                    <Link to={`/signup?type=${currentStakeholder.id}`}>
                      <Button
                        variant="primary"
                        size="md"
                        rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                        className="text-xs font-semibold"
                      >
                        {currentStakeholder.ctaLabel}
                      </Button>
                    </Link>
                    <Link to={`/login?type=${currentStakeholder.id}`}>
                      <Button
                        variant="outline"
                        size="md"
                        className="text-xs bg-white hover:bg-slate-50"
                      >
                        Sign In as {currentStakeholder.title.split(' ')[0]}
                      </Button>
                    </Link>
                  </div>
                </div>

                {/* Right Col Key Stat Widget */}
                <div className="lg:col-span-4 bg-white border border-slate-200 rounded-lg p-4 shadow-2xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Impact Snapshot
                    </span>
                    <Badge variant="teal" size="sm">
                      Verified
                    </Badge>
                  </div>

                  <div className="space-y-3">
                    {currentStakeholder.metrics.map((m, idx) => (
                      <div key={idx} className="bg-slate-50 p-2.5 rounded border border-slate-100">
                        <div className="text-xl font-extrabold text-teal-700 font-sans">
                          {m.value}
                        </div>
                        <div className="text-xs font-medium text-slate-600 mt-0.5">
                          {m.label}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="pt-1 text-[11px] text-slate-500 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                    <span>Real-time authenticated audit stream</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Stakeholder 4-Card Overview Matrix (Compact) */}
            <div className="mt-8 max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {STAKEHOLDERS.map((item) => {
                const Icon = item.icon;
                return (
                  <div
                    key={item.id}
                    className="p-3.5 rounded-lg border border-slate-200 bg-white hover:border-teal-500/50 hover:shadow-xs transition flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="w-7 h-7 rounded bg-slate-100 text-teal-700 flex items-center justify-center">
                          <Icon className="w-4 h-4" />
                        </div>
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                          Portal
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-900 mt-2">
                        {item.title}
                      </h4>
                      <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                        {item.tagline}
                      </p>
                    </div>

                    <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between">
                      <Link
                        to={`/signup?type=${item.id}`}
                        className="text-[11px] font-semibold text-teal-700 hover:text-teal-800 flex items-center gap-1"
                      >
                        Join Portal <ChevronRight className="w-3 h-3" />
                      </Link>
                      <Link
                        to={`/login?type=${item.id}`}
                        className="text-[10px] text-slate-400 hover:text-slate-700"
                      >
                        Login
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Platform Core Capabilities Strip */}
        <section id="features" className="py-10 bg-slate-100/60 border-y border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-2xl mx-auto mb-7">
              <Badge variant="slate" size="sm" className="mb-2">
                Unified Architecture
              </Badge>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                Built on Trust, Transparency & Speed
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
                  <FileCheck2 className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-bold text-slate-900">Verifiable Skill Passport</h3>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Cryptographically secured credentials compatible with DigiLocker and National Academic Depository.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
                  <Target className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-bold text-slate-900">NSQF Competency Engine</h3>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Unified competency standards indexing jobs, certifications, and candidate skill scores objectively.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-bold text-slate-900">Apprenticeship & DBT Sync</h3>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Automated stipend processing and scheme eligibility verification with zero paperwork friction.
                </p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
                  <BarChart3 className="w-4 h-4" />
                </div>
                <h3 className="text-xs font-bold text-slate-900">District Analytics Mesh</h3>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Live labor demand heatmaps empowering policymakers and institutes with actionable industry trends.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Compact Call to Action Banner */}
        <section className="py-10 bg-gradient-to-r from-teal-800 to-slate-900 text-white">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-3.5">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight">
              Ready to Connect with India's Premier Skill Network?
            </h2>
            <p className="text-xs sm:text-sm text-teal-100 max-w-xl mx-auto">
              Join candidates, enterprises, certified training centers, and government bodies accelerating employment outcomes.
            </p>
            <div className="pt-1 flex flex-wrap items-center justify-center gap-3">
              <Link to="/signup">
                <Button
                  variant="primary"
                  size="md"
                  className="bg-white text-teal-900 hover:bg-teal-50 border-none font-bold text-xs"
                  rightIcon={<ArrowRight className="w-3.5 h-3.5 text-teal-900" />}
                >
                  Create Account
                </Button>
              </Link>
              <Link to="/login">
                <Button
                  variant="outline"
                  size="md"
                  className="border-teal-400/40 text-white hover:bg-white/10 text-xs"
                >
                  Existing User Login
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default LandingPage;
