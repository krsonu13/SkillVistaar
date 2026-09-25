import React, { useState, useEffect } from 'react';
import { Bell, Check, CheckCircle2, Filter } from 'lucide-react';
import DashboardLayout from '../components/dashboard/DashboardLayout';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';
import { notificationApi, LiveNotification } from '../services/api';

export const NotificationsPage: React.FC = () => {
  const [notifications, setNotifications] = useState<LiveNotification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchNotifications = async () => {
    setIsLoading(true);
    try {
      const items = await notificationApi.getNotifications(unreadOnly, 100);
      setNotifications(items || []);
    } catch {
      setNotifications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [unreadOnly]);

  const handleMarkRead = async (id: string) => {
    try {
      await notificationApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationApi.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setFeedback('All notifications marked as read.');
      setTimeout(() => setFeedback(null), 3000);
    } catch {
      // ignore
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <DashboardLayout activeTab="notifications">
      <div className="space-y-5 max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center">
                <Bell className="w-4 h-4" />
              </div>
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Notifications Center</h1>
              {unreadCount > 0 && (
                <Badge variant="teal" size="sm">
                  {unreadCount} Unread
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Real-time platform updates, verification status changes, and application telemetry
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setUnreadOnly(!unreadOnly)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                unreadOnly
                  ? 'bg-teal-50 border-teal-300 text-teal-800'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Filter className="w-3.5 h-3.5 inline mr-1" />
              {unreadOnly ? 'Showing Unread' : 'All Notifications'}
            </button>

            {unreadCount > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleMarkAllRead}
                leftIcon={<Check className="w-3.5 h-3.5" />}
                className="text-xs font-semibold"
              >
                Mark All as Read
              </Button>
            )}
          </div>
        </div>

        {feedback && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center gap-2 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{feedback}</span>
          </div>
        )}

        {/* Notifications List */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center space-y-3">
              <div className="w-8 h-8 border-3 border-teal-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500 font-medium">Fetching notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={Bell}
                title="No Notifications"
                description={
                  unreadOnly
                    ? 'You have caught up with all unread notices.'
                    : 'Your notification inbox is clean. System and application alerts will appear here.'
                }
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {notifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => !item.is_read && handleMarkRead(item.id)}
                  className={`p-4 flex items-start justify-between gap-3 text-xs transition cursor-pointer ${
                    !item.is_read
                      ? 'bg-teal-50/40 hover:bg-teal-50/70 border-l-4 border-l-teal-600'
                      : 'hover:bg-slate-50/60'
                  }`}
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="mt-1 shrink-0">
                      <span
                        className={`w-2.5 h-2.5 rounded-full block ${
                          !item.is_read ? 'bg-teal-600 ring-2 ring-teal-200' : 'bg-slate-300'
                        }`}
                      />
                    </div>
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{item.title}</span>
                        {item.notification_type && (
                          <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                            {item.notification_type}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-600 text-[11px] leading-relaxed">
                        {item.message || 'No additional message detail provided.'}
                      </p>
                      <span className="text-[10px] text-slate-400 block font-mono">
                        {item.created_at ? new Date(item.created_at).toLocaleString() : 'Recent'}
                      </span>
                    </div>
                  </div>

                  {!item.is_read && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMarkRead(item.id);
                      }}
                      className="text-[11px] font-semibold text-teal-700 hover:text-teal-800 shrink-0 px-2 py-1 rounded hover:bg-teal-100/50"
                    >
                      Mark read
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default NotificationsPage;
