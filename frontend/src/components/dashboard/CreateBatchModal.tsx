import React, { useState } from 'react';
import { X, GraduationCap, CheckCircle2 } from 'lucide-react';
import Button from '../common/Button';
import InputField from '../common/InputField';
import SelectField from '../common/SelectField';

export interface NewBatchPayload {
  name: string;
  nsqfLevel: string;
  totalSeats: number;
  startDate: string;
  mode: string;
  campus: string;
}

interface CreateBatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (batch: NewBatchPayload) => void;
  instituteName: string;
}

export const CreateBatchModal: React.FC<CreateBatchModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  instituteName,
}) => {
  const [name, setName] = useState('');
  const [nsqfLevel, setNsqfLevel] = useState('NSQF Level 5');
  const [totalSeats, setTotalSeats] = useState(40);
  const [startDate, setStartDate] = useState('2026-10-15');
  const [mode, setMode] = useState('In-person (Precision Lab)');
  const [campus, setCampus] = useState('Campus 1 - Main Engineering Complex');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    setTimeout(() => {
      const newBatch: NewBatchPayload = {
        name: name.trim(),
        nsqfLevel,
        totalSeats: Number(totalSeats) || 30,
        startDate,
        mode,
        campus,
      };
      setIsSubmitting(false);
      setSuccessMsg(true);
      setTimeout(() => {
        setSuccessMsg(false);
        onSuccess(newBatch);
        onClose();
        setName('');
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
              <GraduationCap className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Create New Training Cohort</h2>
              <p className="text-[11px] text-slate-500">Register NSQF accredited vocational cohort for {instituteName}</p>
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
            <h3 className="text-sm font-bold text-slate-900">Cohort Registered & Sync Initiated!</h3>
            <p className="text-xs text-slate-500">
              Batch curricula details have been synchronized with the NSDC Registry portal.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-5 space-y-3.5 max-h-[80vh] overflow-y-auto">
            <InputField
              label="Course / Program Name"
              placeholder="e.g. Advanced Industrial Robotics & Automation"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <SelectField
                label="NSQF Level Qualification"
                value={nsqfLevel}
                onChange={(e) => setNsqfLevel(e.target.value)}
                options={[
                  { value: 'NSQF Level 4', label: 'NSQF Level 4 (Technician)' },
                  { value: 'NSQF Level 5', label: 'NSQF Level 5 (Senior Specialist)' },
                  { value: 'NSQF Level 6', label: 'NSQF Level 6 (Master Technician)' },
                  { value: 'NSQF Level 7', label: 'NSQF Level 7 (Technologist)' },
                ]}
              />

              <InputField
                label="Intake Seat Capacity"
                type="number"
                min={5}
                max={200}
                value={totalSeats}
                onChange={(e) => setTotalSeats(Number(e.target.value))}
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <InputField
                label="Cohort Commencement Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />

              <SelectField
                label="Instruction Mode"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                options={[
                  { value: 'In-person (Precision Lab)', label: 'In-person (Precision Lab)' },
                  { value: 'Hybrid (Theory Online + Lab)', label: 'Hybrid (Theory + Lab)' },
                  { value: 'Industrial Apprenticeship Integrated', label: 'Dual Apprenticeship Model' },
                ]}
              />
            </div>

            <InputField
              label="Assigned Campus / Training Facility"
              placeholder="e.g. Rohtas Technical Center - Block C"
              value={campus}
              onChange={(e) => setCampus(e.target.value)}
              required
            />

            <div className="p-3 bg-teal-50/60 rounded-lg border border-teal-100 text-[11px] text-teal-800 space-y-1">
              <p className="font-semibold">DigiLocker NAD Compliance Notice</p>
              <p className="text-slate-600">
                Upon completion of this cohort, graduates will automatically receive cryptographically signed certificates directly deposited into their DigiLocker accounts.
              </p>
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
                Register Cohort
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default CreateBatchModal;
