import React, { useState } from 'react';
import { X, Briefcase, Plus, CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';
import InputField from '../common/InputField';
import SelectField from '../common/SelectField';

export interface NewJobPayload {
  title: string;
  type: 'Full-time' | 'Apprenticeship' | 'Internship';
  location: string;
  salary: string;
  nsqfRequirement: string;
  description: string;
  skills: string[];
}

interface PostJobModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (job: NewJobPayload) => void;
  companyName: string;
}

export const PostJobModal: React.FC<PostJobModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  companyName,
}) => {
  const [title, setTitle] = useState('');
  const [jobType, setJobType] = useState<'Full-time' | 'Apprenticeship' | 'Internship'>('Full-time');
  const [location, setLocation] = useState('Pune, Maharashtra (On-site)');
  const [salary, setSalary] = useState('₹6.5 - 9.5 LPA');
  const [nsqfLevel, setNsqfLevel] = useState('NSQF Level 5 or higher');
  const [description, setDescription] = useState('');
  const [skillInput, setSkillInput] = useState('');
  const [skillsList, setSkillsList] = useState<string[]>([
    'Robotics Automation',
    'PLC Programming',
    'Industrial IoT',
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(false);

  if (!isOpen) return null;

  const handleAddSkill = () => {
    if (skillInput.trim() && !skillsList.includes(skillInput.trim())) {
      setSkillsList([...skillsList, skillInput.trim()]);
      setSkillInput('');
    }
  };

  const handleRemoveSkill = (skill: string) => {
    setSkillsList(skillsList.filter((s) => s !== skill));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    setTimeout(() => {
      const newJob: NewJobPayload = {
        title: title.trim(),
        type: jobType,
        location: location.trim(),
        salary: salary.trim(),
        nsqfRequirement: nsqfLevel,
        description: description.trim() || 'Role responsible for engineering execution and precision compliance.',
        skills: skillsList.length > 0 ? skillsList : ['Industrial Systems', 'Automation'],
      };
      setIsSubmitting(false);
      setSuccessMsg(true);
      setTimeout(() => {
        setSuccessMsg(false);
        onSuccess(newJob);
        onClose();
        // Reset form
        setTitle('');
        setDescription('');
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
              <Briefcase className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Post New Opportunity</h2>
              <p className="text-[11px] text-slate-500">Publish to SkillVistaar verified candidate talent pool</p>
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
            <h3 className="text-sm font-bold text-slate-900">Vacancy Published Successfully!</h3>
            <p className="text-xs text-slate-500">
              Your opening is now live and matched against verified candidates in {companyName}&apos;s jurisdiction.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-3.5 max-h-[80vh] overflow-y-auto">
            <InputField
              label="Position / Role Title"
              placeholder="e.g. Senior Mechatronics Engineer"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <SelectField
                label="Employment Type"
                value={jobType}
                onChange={(e) => setJobType(e.target.value as any)}
                options={[
                  { value: 'Full-time', label: 'Full-time Enterprise' },
                  { value: 'Apprenticeship', label: 'NAPS Apprenticeship' },
                  { value: 'Internship', label: 'Vocational Internship' },
                ]}
              />
              <SelectField
                label="Required NSQF Level"
                value={nsqfLevel}
                onChange={(e) => setNsqfLevel(e.target.value)}
                options={[
                  { value: 'NSQF Level 4', label: 'NSQF Level 4 (Technician)' },
                  { value: 'NSQF Level 5 or higher', label: 'NSQF Level 5 (Senior Tech)' },
                  { value: 'NSQF Level 6 or higher', label: 'NSQF Level 6 (Specialist)' },
                  { value: 'NSQF Level 7 (Master Specialist)', label: 'NSQF Level 7 (Master)' },
                ]}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <InputField
                label="Location / Mode"
                placeholder="e.g. Pune, Maharashtra (Hybrid)"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                required
              />
              <InputField
                label="Salary / Monthly Stipend"
                placeholder="e.g. ₹6.5 - 9.5 LPA or ₹22,000/mo"
                value={salary}
                onChange={(e) => setSalary(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Required Competencies & Skills
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. Python Scripting, SCADA"
                  value={skillInput}
                  onChange={(e) => setSkillInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddSkill();
                    }
                  }}
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs focus:ring-1 focus:ring-teal-500 focus:border-teal-500 outline-hidden"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddSkill}
                  className="text-xs"
                  leftIcon={<Plus className="w-3.5 h-3.5" />}
                >
                  Add
                </Button>
              </div>

              <div className="flex flex-wrap gap-1.5 mt-2">
                {skillsList.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-teal-50 text-teal-800 border border-teal-200"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(skill)}
                      className="text-teal-600 hover:text-teal-900"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Job Overview & Requirements
              </label>
              <textarea
                rows={3}
                placeholder="Describe key responsibilities, shift requirements, and statutory benefits..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:ring-1 focus:ring-teal-500 focus:border-teal-500 outline-hidden resize-none"
              />
            </div>

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
                Publish Opening
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default PostJobModal;
