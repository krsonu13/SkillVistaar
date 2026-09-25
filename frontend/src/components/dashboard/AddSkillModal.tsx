import React, { useState } from 'react';
import { X, Award, ShieldCheck, CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';
import InputField from '../common/InputField';
import SelectField from '../common/SelectField';

export interface NewSkillPayload {
  name: string;
  category: string;
  isVerifiedRequest: boolean;
  nsqfLevel?: number;
  issuer?: string;
  credentialId?: string;
  scorePercent?: number;
}

interface AddSkillModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (skill: NewSkillPayload) => void;
}

export const AddSkillModal: React.FC<AddSkillModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [skillType, setSkillType] = useState<'verified' | 'self_declared'>('verified');
  const [name, setName] = useState('');
  const [category, setCategory] = useState('Information Technology & Systems');
  const [nsqfLevel, setNsqfLevel] = useState('6');
  const [issuer, setIssuer] = useState('National Skill Development Corporation (NSDC)');
  const [credentialId, setCredentialId] = useState('');
  const [scorePercent, setScorePercent] = useState('92');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    setTimeout(() => {
      const isVer = skillType === 'verified';
      const payload: NewSkillPayload = {
        name: name.trim(),
        category,
        isVerifiedRequest: isVer,
        nsqfLevel: isVer ? Number(nsqfLevel) || 5 : undefined,
        issuer: isVer ? issuer : undefined,
        credentialId: isVer ? credentialId || `NSDC-${Date.now().toString().slice(-6)}` : undefined,
        scorePercent: isVer ? Number(scorePercent) || 85 : undefined,
      };

      setIsSubmitting(false);
      setSuccessMsg(true);
      setTimeout(() => {
        setSuccessMsg(false);
        onSuccess(payload);
        onClose();
        setName('');
        setCredentialId('');
        setNotes('');
      }, 1000);
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/80">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center border border-teal-100">
              <Award className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Add Skill to Digital Passport</h2>
              <p className="text-[11px] text-slate-500">Record self-declared or NSQF DigiLocker verified competency</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {successMsg ? (
          <div className="p-8 text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-teal-600 mx-auto animate-bounce" />
            <h3 className="text-sm font-bold text-slate-900">Skill Added to Passport!</h3>
            <p className="text-xs text-slate-500">
              {skillType === 'verified'
                ? 'Credential submitted for statutory anchoring against DigiLocker and NSDC registries.'
                : 'Self-declared competency recorded and visible to recruiters on your public profile.'}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
            {/* Mode Selector */}
            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-lg">
              <button
                type="button"
                onClick={() => setSkillType('verified')}
                className={`py-2 px-3 text-xs font-bold rounded-md flex items-center justify-center gap-1.5 transition ${
                  skillType === 'verified'
                    ? 'bg-white text-teal-800 shadow-2xs border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                Verified NSQF Credential
              </button>

              <button
                type="button"
                onClick={() => setSkillType('self_declared')}
                className={`py-2 px-3 text-xs font-bold rounded-md flex items-center justify-center gap-1.5 transition ${
                  skillType === 'self_declared'
                    ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Award className="w-3.5 h-3.5 text-slate-500" />
                Self-Declared Skill
              </button>
            </div>

            <InputField
              label="Competency / Skill Title"
              placeholder={
                skillType === 'verified'
                  ? 'e.g. Industrial Automation & PLC Programming'
                  : 'e.g. Python Scripting & Data Wrangling'
              }
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <SelectField
              label="Skill Domain / Sector"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              options={[
                { value: 'Information Technology & Systems', label: 'Information Technology & DevOps' },
                { value: 'Automotive & Precision Manufacturing', label: 'Automotive & Precision Manufacturing' },
                { value: 'Electronics & Hardware', label: 'Electronics & Hardware' },
                { value: 'Healthcare & Paramedical', label: 'Healthcare & Paramedical' },
                { value: 'Construction & Civil Infrastructure', label: 'Construction & Infrastructure' },
                { value: 'Green Energy & Solar Systems', label: 'Green Energy & Power' },
              ]}
            />

            {skillType === 'verified' ? (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <SelectField
                    label="NSQF Level Qualification"
                    value={nsqfLevel}
                    onChange={(e) => setNsqfLevel(e.target.value)}
                    options={[
                      { value: '4', label: 'NSQF Level 4 (Technician)' },
                      { value: '5', label: 'NSQF Level 5 (Senior Technician)' },
                      { value: '6', label: 'NSQF Level 6 (Specialist)' },
                      { value: '7', label: 'NSQF Level 7 (Master Specialist)' },
                    ]}
                  />

                  <SelectField
                    label="Issuing Statutory Body"
                    value={issuer}
                    onChange={(e) => setIssuer(e.target.value)}
                    options={[
                      { value: 'National Skill Development Corporation (NSDC)', label: 'NSDC / Sector Skill Council' },
                      { value: 'NCVET Authorized Board', label: 'NCVET Authorized Board' },
                      { value: 'Directorate General of Training (DGT)', label: 'DGT / Craftsmen Training Scheme' },
                      { value: 'State Skill Development Mission', label: 'State Skill Development Mission' },
                    ]}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <InputField
                    label="Certificate / Credential ID"
                    placeholder="e.g. NSDC-CERT-2025-9921"
                    value={credentialId}
                    onChange={(e) => setCredentialId(e.target.value)}
                    required
                  />

                  <InputField
                    label="Assessment Score (%)"
                    type="number"
                    min={40}
                    max={100}
                    value={scorePercent}
                    onChange={(e) => setScorePercent(e.target.value)}
                  />
                </div>

                <div className="p-3 bg-teal-50/70 border border-teal-200/80 rounded-lg text-[11px] text-teal-800 space-y-1">
                  <p className="font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-teal-600" />
                    Cryptographic Anchor Guarantee
                  </p>
                  <p className="text-slate-600">
                    Your certificate will be verified against the National Academic Depository hash registry and awarded a tamper-proof digital badge.
                  </p>
                </div>
              </>
            ) : (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Experience Summary & Evidence
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe your practical application or project usage for peer endorsements..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:ring-1 focus:ring-teal-500 focus:border-teal-500 outline-hidden resize-none"
                />
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <Button type="button" variant="outline" size="sm" onClick={onClose} className="text-xs">
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isSubmitting}
                className="text-xs font-semibold px-4"
              >
                Add to Passport
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default AddSkillModal;
