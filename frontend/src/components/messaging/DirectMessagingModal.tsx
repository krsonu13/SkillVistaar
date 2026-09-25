import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Send,
  ArrowLeft,
  MessageCircle,
  Inbox,
  Clock,
  Check,
  CheckCheck,
  UserCheck,
  UserX,
  AlertCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import {
  messagingApi,
  ConversationItem,
  ConversationDetail,
  MessageItem,
  resolveMediaUrl,
} from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import Button from '../common/Button';

interface DirectMessagingModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialRecipientId?: string;
  initialRecipientName?: string;
  initialRecipientAvatar?: string;
  initialRecipientUsername?: string;
}

export const DirectMessagingModal: React.FC<DirectMessagingModalProps> = ({
  isOpen,
  onClose,
  initialRecipientId,
  initialRecipientName,
  initialRecipientAvatar,
  initialRecipientUsername,
}) => {
  const { user: authUser } = useAuth();

  const [activeTab, setActiveTab] = useState<'inbox' | 'requests'>('inbox');
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [requests, setRequests] = useState<ConversationItem[]>([]);
  const [unreadCounts, setUnreadCounts] = useState({ messages: 0, requests: 0, total: 0 });

  const [selectedConversation, setSelectedConversation] = useState<ConversationDetail | null>(null);
  const [recipientTarget, setRecipientTarget] = useState<{
    id: string;
    name: string;
    username?: string;
    avatar?: string;
  } | null>(null);

  const [messageInput, setMessageInput] = useState('');
  const [loadingList, setLoadingList] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [sending, setSending] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollTimerRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Load lists
  const loadConversations = async () => {
    try {
      setLoadingList(true);
      const [inboxList, reqList, counts] = await Promise.all([
        messagingApi.getConversations('inbox'),
        messagingApi.getConversations('requests'),
        messagingApi.getUnreadCounts(),
      ]);
      setConversations(inboxList);
      setRequests(reqList);
      setUnreadCounts(counts);
    } catch {
      // ignore
    } finally {
      setLoadingList(false);
    }
  };

  // Open direct chat with given user
  const openDirectWithUser = async (
    userId: string,
    name?: string,
    username?: string,
    avatar?: string
  ) => {
    setRecipientTarget({ id: userId, name: name || 'User', username, avatar });
    setSelectedConversation(null);
    setLoadingChat(true);
    setErrorMessage(null);

    try {
      const conv = await messagingApi.getConversationWithUser(userId);
      if (conv) {
        setSelectedConversation(conv);
      }
    } catch {
      // Might not exist yet; will be created on first send
    } finally {
      setLoadingChat(false);
    }
  };

  // Refresh active conversation (polling)
  const refreshActiveConversation = async (convId: string) => {
    try {
      const updated = await messagingApi.getConversation(convId);
      if (updated) {
        setSelectedConversation((prev) => {
          if (prev && prev.id === convId) {
            return updated;
          }
          return prev;
        });
      }
    } catch {
      // ignore
    }
  };

  // Handle Initial Recipient when modal opens
  useEffect(() => {
    if (isOpen) {
      loadConversations();
      if (initialRecipientId && authUser?.id !== initialRecipientId) {
        openDirectWithUser(
          initialRecipientId,
          initialRecipientName,
          initialRecipientUsername,
          initialRecipientAvatar
        );
      }
    } else {
      setSelectedConversation(null);
      setRecipientTarget(null);
      setMessageInput('');
      setErrorMessage(null);
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    }
  }, [isOpen, initialRecipientId]);

  // Polling for active conversation every 4 seconds
  useEffect(() => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);

    if (isOpen && selectedConversation?.id) {
      pollTimerRef.current = setInterval(() => {
        refreshActiveConversation(selectedConversation.id);
      }, 4000);
    }

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [isOpen, selectedConversation?.id]);

  useEffect(() => {
    scrollToBottom();
  }, [selectedConversation?.messages]);

  // Send message
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const content = messageInput.trim();
    if (!content) return;

    const targetUserId =
      selectedConversation?.participant?.id || recipientTarget?.id;

    if (!targetUserId) return;

    setSending(true);
    setErrorMessage(null);

    try {
      const sentMsg = await messagingApi.sendMessage(targetUserId, content);
      setMessageInput('');

      // Refresh or populate conversation
      if (selectedConversation) {
        setSelectedConversation((prev) =>
          prev
            ? {
                ...prev,
                messages: [...prev.messages, sentMsg],
                last_message: {
                  id: sentMsg.id,
                  content: sentMsg.content,
                  sender_id: sentMsg.sender_id,
                  created_at: sentMsg.created_at,
                  is_read: false,
                },
              }
            : null
        );
      } else {
        // Conversation was just created
        const conv = await messagingApi.getConversationWithUser(targetUserId);
        if (conv) setSelectedConversation(conv);
      }

      // Update lists
      loadConversations();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  // Accept request
  const handleAcceptRequest = async (convId: string) => {
    setActionLoading(true);
    try {
      await messagingApi.acceptRequest(convId);
      const updated = await messagingApi.getConversation(convId);
      if (updated) setSelectedConversation(updated);
      loadConversations();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to accept message request.');
    } finally {
      setActionLoading(false);
    }
  };

  // Reject request
  const handleRejectRequest = async (convId: string) => {
    setActionLoading(true);
    try {
      await messagingApi.rejectRequest(convId);
      setSelectedConversation(null);
      setRecipientTarget(null);
      loadConversations();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to decline message request.');
    } finally {
      setActionLoading(false);
    }
  };

  if (!isOpen) return null;

  const currentParticipant =
    selectedConversation?.participant || recipientTarget;

  const isRequestReceived =
    selectedConversation?.status === 'REQUESTED' &&
    !selectedConversation?.is_requester;

  const isRequestSent =
    selectedConversation?.status === 'REQUESTED' &&
    selectedConversation?.is_requester;

  const isRejected = selectedConversation?.status === 'REJECTED';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl h-[560px] sm:h-[620px] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col">
        {/* MODAL HEADER */}
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2.5">
            {currentParticipant ? (
              <button
                onClick={() => {
                  setSelectedConversation(null);
                  setRecipientTarget(null);
                  setErrorMessage(null);
                  loadConversations();
                }}
                className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition mr-0.5"
                title="Back to Conversations"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
            ) : (
              <div className="w-8 h-8 rounded-full bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center font-bold">
                <MessageCircle className="w-4 h-4" />
              </div>
            )}

            {currentParticipant ? (
              <div className="flex items-center gap-2.5">
                <div className="relative">
                  {(currentParticipant as any).avatar_url || (currentParticipant as any).avatar ? (
                    <img
                      src={resolveMediaUrl((currentParticipant as any).avatar_url || (currentParticipant as any).avatar)}
                      alt={currentParticipant.name}
                      className="w-8 h-8 rounded-full object-cover border border-slate-200"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-bold flex items-center justify-center text-xs">
                      {currentParticipant.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                </div>
                <div>
                  <h3 className="text-xs sm:text-sm font-bold text-slate-900 leading-tight">
                    {currentParticipant.name}
                  </h3>
                  {currentParticipant.username && (
                    <p className="text-[11px] text-slate-400 font-mono">
                      @{currentParticipant.username}
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div>
                <h3 className="text-sm font-bold text-slate-900">Direct Messages</h3>
                <p className="text-[11px] text-slate-400">
                  Real-time encrypted conversations & message requests
                </p>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                if (selectedConversation?.id) {
                  refreshActiveConversation(selectedConversation.id);
                } else {
                  loadConversations();
                }
              }}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
              aria-label="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* MODAL BODY */}
        <div className="flex-1 flex flex-col overflow-hidden bg-slate-50/50">
          {/* VIEW A: CHAT THREAD */}
          {currentParticipant ? (
            <div className="flex-1 flex flex-col justify-between overflow-hidden">
              {/* Request Status Banners */}
              {isRequestReceived && (
                <div className="p-3 bg-amber-50 border-b border-amber-200 text-amber-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>
                      <strong>{currentParticipant.name}</strong> wants to send you a message request.
                      Accepting allows you both to chat directly.
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleAcceptRequest(selectedConversation!.id)}
                      disabled={actionLoading}
                      className="text-xs font-semibold py-1 px-3 bg-teal-600 hover:bg-teal-700 text-white"
                      leftIcon={<UserCheck className="w-3.5 h-3.5" />}
                    >
                      Accept
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRejectRequest(selectedConversation!.id)}
                      disabled={actionLoading}
                      className="text-xs font-semibold py-1 px-3 border-rose-200 text-rose-600 hover:bg-rose-50"
                      leftIcon={<UserX className="w-3.5 h-3.5" />}
                    >
                      Decline
                    </Button>
                  </div>
                </div>
              )}

              {isRequestSent && (
                <div className="p-2.5 bg-blue-50 border-b border-blue-200 text-blue-800 text-[11px] font-medium flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                  <span>
                    Message request sent. {currentParticipant.name} will be notified and can choose to accept or decline.
                  </span>
                </div>
              )}

              {isRejected && (
                <div className="p-2.5 bg-rose-50 border-b border-rose-200 text-rose-800 text-[11px] font-medium flex items-center gap-2">
                  <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                  <span>This message request was declined. Replies are closed.</span>
                </div>
              )}

              {errorMessage && (
                <div className="p-2.5 bg-rose-50 border-b border-rose-200 text-rose-800 text-xs flex items-center justify-between">
                  <span>{errorMessage}</span>
                  <button onClick={() => setErrorMessage(null)}>
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {/* Messages Container */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {loadingChat ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-6 h-6 text-teal-600 animate-spin" />
                  </div>
                ) : !selectedConversation || selectedConversation.messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center space-y-2 p-6">
                    <div className="w-12 h-12 rounded-full bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center">
                      <MessageCircle className="w-6 h-6" />
                    </div>
                    <p className="text-xs font-bold text-slate-800">
                      Start a conversation with {currentParticipant.name}
                    </p>
                    <p className="text-[11px] text-slate-400 max-w-xs">
                      Send your first message. If you haven't messaged before, this will create an inquiry request.
                    </p>
                  </div>
                ) : (
                  selectedConversation.messages.map((msg: MessageItem) => {
                    const isMe = msg.sender_id === authUser?.id;
                    const timeStr = new Date(msg.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    });

                    return (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed break-words shadow-2xs ${
                            isMe
                              ? 'bg-teal-700 text-white rounded-br-xs'
                              : 'bg-white text-slate-800 border border-slate-200 rounded-bl-xs'
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                        <div className="flex items-center gap-1 text-[10px] text-slate-400 mt-0.5 px-1 font-sans">
                          <span>{timeStr}</span>
                          {isMe && (
                            <span>
                              {msg.is_read ? (
                                <CheckCheck className="w-3 h-3 text-teal-600 inline" />
                              ) : (
                                <Check className="w-3 h-3 text-slate-400 inline" />
                              )}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input Form */}
              <div className="p-3 bg-white border-t border-slate-200">
                {isRejected ? (
                  <p className="text-xs text-center text-slate-400 py-1">
                    Conversation closed.
                  </p>
                ) : isRequestReceived ? (
                  <p className="text-xs text-center text-amber-700 py-1 font-medium">
                    Please accept the request above to reply to {currentParticipant.name}.
                  </p>
                ) : (
                  <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder={`Message ${currentParticipant.name}...`}
                      value={messageInput}
                      onChange={(e) => setMessageInput(e.target.value)}
                      disabled={sending}
                      className="flex-1 px-3.5 py-2 text-xs rounded-full border border-slate-300 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-teal-500 text-slate-800 placeholder-slate-400"
                    />
                    <button
                      type="submit"
                      disabled={!messageInput.trim() || sending}
                      className="p-2 rounded-full bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-40 transition shrink-0"
                      title="Send message"
                    >
                      {sending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </button>
                  </form>
                )}
              </div>
            </div>
          ) : (
            /* VIEW B: CONVERSATION LIST (INBOX & REQUESTS) */
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Tabs Bar */}
              <div className="flex border-b border-slate-200 bg-white px-4 shrink-0">
                <button
                  onClick={() => setActiveTab('inbox')}
                  className={`py-2.5 px-4 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
                    activeTab === 'inbox'
                      ? 'border-teal-600 text-teal-800'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Inbox className="w-3.5 h-3.5" />
                  <span>Messages</span>
                  {unreadCounts.messages > 0 && (
                    <span className="w-4 h-4 rounded-full bg-teal-600 text-white text-[10px] flex items-center justify-center font-bold">
                      {unreadCounts.messages}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('requests')}
                  className={`py-2.5 px-4 text-xs font-bold border-b-2 flex items-center gap-2 transition ${
                    activeTab === 'requests'
                      ? 'border-teal-600 text-teal-800'
                      : 'border-transparent text-slate-500 hover:text-slate-800'
                  }`}
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>Requests</span>
                  {unreadCounts.requests > 0 && (
                    <span className="w-4 h-4 rounded-full bg-amber-500 text-white text-[10px] flex items-center justify-center font-bold">
                      {unreadCounts.requests}
                    </span>
                  )}
                </button>
              </div>

              {/* List */}
              <div className="flex-1 overflow-y-auto divide-y divide-slate-100 bg-white">
                {loadingList ? (
                  <div className="flex items-center justify-center h-48">
                    <Loader2 className="w-6 h-6 text-teal-600 animate-spin" />
                  </div>
                ) : activeTab === 'inbox' ? (
                  conversations.length === 0 ? (
                    <div className="text-center py-12 px-4 space-y-2">
                      <MessageCircle className="w-8 h-8 text-slate-300 mx-auto" />
                      <p className="text-xs font-bold text-slate-700">No active messages</p>
                      <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                        Connect with verified professionals, employers, or institutions and start messaging directly.
                      </p>
                    </div>
                  ) : (
                    conversations.map((conv) => {
                      const timeStr = conv.last_message
                        ? new Date(conv.last_message.created_at).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                          })
                        : '';

                      return (
                        <div
                          key={conv.id}
                          onClick={() => {
                            setRecipientTarget(conv.participant);
                            setSelectedConversation(null);
                            openDirectWithUser(
                              conv.participant.id,
                              conv.participant.name,
                              conv.participant.username,
                              conv.participant.avatar_url
                            );
                          }}
                          className={`p-3.5 flex items-center gap-3 hover:bg-slate-50 cursor-pointer transition ${
                            conv.unread_count > 0 ? 'bg-teal-50/20' : ''
                          }`}
                        >
                          <div className="relative shrink-0">
                            {conv.participant.avatar_url ? (
                              <img
                                src={resolveMediaUrl(conv.participant.avatar_url)}
                                alt={conv.participant.name}
                                className="w-10 h-10 rounded-full object-cover border border-slate-200"
                              />
                            ) : (
                              <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-bold flex items-center justify-center text-sm">
                                {conv.participant.name.charAt(0).toUpperCase()}
                              </div>
                            )}
                            {conv.unread_count > 0 && (
                              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-teal-600 ring-2 ring-white" />
                            )}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <h4
                                className={`text-xs font-bold truncate ${
                                  conv.unread_count > 0 ? 'text-slate-900' : 'text-slate-800'
                                }`}
                              >
                                {conv.participant.name}
                              </h4>
                              <span className="text-[10px] text-slate-400 shrink-0 font-sans">
                                {timeStr}
                              </span>
                            </div>
                            <div className="flex items-center justify-between mt-0.5">
                              <p
                                className={`text-[11px] truncate max-w-[240px] sm:max-w-xs ${
                                  conv.unread_count > 0
                                    ? 'text-teal-900 font-semibold'
                                    : 'text-slate-500'
                                }`}
                              >
                                {conv.last_message?.content || 'No messages yet'}
                              </p>
                              {conv.unread_count > 0 && (
                                <span className="text-[10px] font-bold bg-teal-600 text-white rounded-full px-1.5 py-0.2 shrink-0">
                                  {conv.unread_count}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )
                ) : /* Requests Tab */
                requests.length === 0 ? (
                  <div className="text-center py-12 px-4 space-y-2">
                    <Clock className="w-8 h-8 text-slate-300 mx-auto" />
                    <p className="text-xs font-bold text-slate-700">No message requests</p>
                    <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                      Inquiries from platform users you haven't connected with will appear here.
                    </p>
                  </div>
                ) : (
                  requests.map((conv) => (
                    <div
                      key={conv.id}
                      onClick={() => {
                        setRecipientTarget(conv.participant);
                        setSelectedConversation(null);
                        openDirectWithUser(
                          conv.participant.id,
                          conv.participant.name,
                          conv.participant.username,
                          conv.participant.avatar_url
                        );
                      }}
                      className="p-3.5 flex items-center justify-between gap-3 hover:bg-slate-50 cursor-pointer transition bg-amber-50/15"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {conv.participant.avatar_url ? (
                          <img
                            src={resolveMediaUrl(conv.participant.avatar_url)}
                            alt={conv.participant.name}
                            className="w-10 h-10 rounded-full object-cover border border-slate-200 shrink-0"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-amber-100 border border-amber-200 text-amber-800 font-bold flex items-center justify-center text-sm shrink-0">
                            {conv.participant.name.charAt(0).toUpperCase()}
                          </div>
                        )}

                        <div className="min-w-0">
                          <h4 className="text-xs font-bold text-slate-900 truncate">
                            {conv.participant.name}
                          </h4>
                          <p className="text-[11px] text-slate-500 truncate max-w-[200px] sm:max-w-xs">
                            {conv.last_message?.content || 'Sent you a message request'}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                          Request
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DirectMessagingModal;
