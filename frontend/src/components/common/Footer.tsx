import React from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Shield, Lock, Award, HeartHandshake } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-slate-900 text-slate-300 border-t border-slate-800 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 lg:py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Brand Col */}
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded bg-teal-600 flex items-center justify-center text-white shadow-sm">
                <Sparkles className="w-4 h-4 text-teal-200" />
              </div>
              <span className="font-extrabold text-base tracking-tight text-white">
                Skill<span className="text-teal-400">Vistaar</span>
              </span>
            </div>
            <p className="text-slate-400 text-xs leading-relaxed max-w-sm">
              An integrated national skilling exchange unifying candidates, industrial employers, accredited training institutes, and state authorities into one transparent opportunity ecosystem.
            </p>
            <div className="flex items-center gap-2 pt-1 text-[11px] text-teal-400 font-semibold tracking-wider uppercase">
              <span>Skill</span>
              <span>•</span>
              <span>Opportunity</span>
              <span>•</span>
              <span>Growth</span>
            </div>
            <div className="pt-2 flex flex-wrap items-center gap-3 text-slate-400 text-[11px]">
              <span className="inline-flex items-center gap-1">
                <Shield className="w-3.5 h-3.5 text-teal-400" /> NSQF Aligned
              </span>
              <span className="inline-flex items-center gap-1">
                <Lock className="w-3.5 h-3.5 text-teal-400" /> Digilocker-Ready
              </span>
              <span className="inline-flex items-center gap-1">
                <Award className="w-3.5 h-3.5 text-teal-400" /> Tamper-Proof Badges
              </span>
            </div>
          </div>

          {/* Quick Links: Stakeholders */}
          <div className="space-y-2.5">
            <h4 className="text-white font-semibold text-xs uppercase tracking-wider">Stakeholders</h4>
            <ul className="space-y-1.5 text-slate-400">
              <li>
                <Link to="/signup?type=candidate" className="hover:text-teal-400 transition">
                  Candidate Portal
                </Link>
              </li>
              <li>
                <Link to="/signup?type=employer" className="hover:text-teal-400 transition">
                  Employer Talent Engine
                </Link>
              </li>
              <li>
                <Link to="/signup?type=institute" className="hover:text-teal-400 transition">
                  Training Institutes
                </Link>
              </li>
              <li>
                <Link to="/signup?type=government" className="hover:text-teal-400 transition">
                  Government & Schemes
                </Link>
              </li>
              <li>
                <Link to="/login" className="hover:text-teal-400 transition">
                  Stakeholder SSO Sign In
                </Link>
              </li>
            </ul>
          </div>

          {/* Capabilities */}
          <div className="space-y-2.5">
            <h4 className="text-white font-semibold text-xs uppercase tracking-wider">Capabilities</h4>
            <ul className="space-y-1.5 text-slate-400">
              <li><span className="hover:text-slate-300">Skill Passport (DigiLocker)</span></li>
              <li><span className="hover:text-slate-300">AI Role-Skill Matching</span></li>
              <li><span className="hover:text-slate-300">Apprenticeship Tracking</span></li>
              <li><span className="hover:text-slate-300">Direct Benefit Verification</span></li>
              <li><span className="hover:text-slate-300">District Skill Dashboards</span></li>
            </ul>
          </div>

          {/* Governance & Support */}
          <div className="space-y-2.5">
            <h4 className="text-white font-semibold text-xs uppercase tracking-wider">Governance</h4>
            <ul className="space-y-1.5 text-slate-400">
              <li><span className="hover:text-slate-300">Data Privacy Charter</span></li>
              <li><span className="hover:text-slate-300">National Registry Standards</span></li>
              <li><span className="hover:text-slate-300">API Documentation</span></li>
              <li><span className="hover:text-slate-300">Grievance Redressal</span></li>
              <li><span className="hover:text-slate-300">Helpdesk & Support</span></li>
            </ul>
          </div>
        </div>

        {/* Subfooter */}
        <div className="mt-8 pt-6 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5">
            <HeartHandshake className="w-4 h-4 text-teal-500" />
            <span>Empowering India's Demographic Dividend with Verified Opportunities.</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="hover:text-slate-200 cursor-pointer">Terms of Service</span>
            <span className="hover:text-slate-200 cursor-pointer">Privacy Policy</span>
            <span className="hover:text-slate-200 cursor-pointer">Security Compliance</span>
            <span className="text-slate-400">© {new Date().getFullYear()} SkillVistaar</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
