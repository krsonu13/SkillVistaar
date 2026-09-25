import React, { useState } from 'react';
import { X, Send, CheckCircle2, MessageSquare } from 'lucide-react';
import Button from '../common/Button';
import InputField from '../common/InputField';
import Alert from '../common/Alert';

interface MessageModalProps {
  isOpen: boolean;
  onClose: () => void;
  recipientName: string;
  recipientRole: string;
}

export const MessageModal: React.FC<MessageModalProps> = ({
  isOpen,
  onClose,
  recipientName,
  recipientRole,
}) => {
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sentSuccess, setSentSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) {
      setError('Please provide both a subject and message.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setTimeout(() => {
      setIsLoading(false);
      setSentSuccess(true);
      setTimeout(() => {
        setSentSuccess(false);
        setSubject('');
        setMessage('');
        onClose();
      }, 1400);
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center">
              <MessageSquare className="w-3.5 h-3.5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Direct Message</h3>
              <p className="text-[11px] text-slate-500">
                To: <span className="font-semibold text-slate-700">{recipientName}</span>{' '}
                <span className="capitalize text-teal-700">({recipientRole})</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        {sentSuccess ? (
          <div className="p-8 text-center space-y-2">
            <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
            <h4 className="text-sm font-bold text-slate-900">Inquiry Dispatched</h4>
            <p className="text-xs text-slate-500">
              Your message has been delivered to {recipientName}'s verified inbox.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSend} className="p-5 space-y-3.5">
            {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

            <InputField
              label="Subject / Inquiring Purpose"
              placeholder="e.g. Inquiry regarding apprenticeship opening / batch enrollment"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
            />

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Message Content <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Introduce yourself and specify your question or opportunity..."
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 text-slate-800"
                required
              />
              <span className="text-[10px] text-slate-400">
                Messages comply with the SkillVistaar Inter-Stakeholder Communication Code.
              </span>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <Button type="button" variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isLoading}
                rightIcon={<Send className="w-3.5 h-3.5" />}
              >
                Send Message
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default MessageModal;
