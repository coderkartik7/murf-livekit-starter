import React, { useState, useEffect } from 'react';
import { X, Plus, Search, RefreshCw, Send, CheckCircle2, AlertCircle, PhoneCall, MessageSquare, ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';

interface FeatureModalProps {
  title: string;
  onClose: () => void;
}

const API_BASE = 'http://localhost:8000/api';

export const FeatureModal: React.FC<FeatureModalProps> = ({ title, onClose }) => {
  const [activeTab, setActiveTab] = useState<'form' | 'list'>('form');
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Sales Ledger state
  const [saleItem, setSaleItem] = useState('');
  const [saleQty, setSaleQty] = useState('');
  const [saleUnit, setSaleUnit] = useState('kg');
  const [saleAmount, setSaleAmount] = useState('');

  // Credit Tracker state
  const [creditCustomer, setCreditCustomer] = useState('');
  const [creditAmount, setCreditAmount] = useState('');
  const [creditType, setCreditType] = useState<'given' | 'paid'>('given');
  const [creditNote, setCreditNote] = useState('');
  const [creditBalances, setCreditBalances] = useState<any[]>([]);

  // Leave Message state
  const [msgName, setMsgName] = useState('');
  const [msgText, setMsgText] = useState('');

  // Customer History state
  const [historyLogs, setHistoryLogs] = useState<any[]>([]);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  // Daily Summary state
  const [summaryData, setSummaryData] = useState<any>(null);

  // Shop Hours state
  const [hoursText, setHoursText] = useState('');
  const [addressText, setAddressText] = useState('');

  // Market Watch state
  const [commodity, setCommodity] = useState('');
  const [stateName, setStateName] = useState('');
  const [marketResult, setMarketResult] = useState<any>(null);

  // Escalations state
  const [escalations, setEscalations] = useState<any[]>([]);
  const [escalationsLoading, setEscalationsLoading] = useState(false);

  // Initial data loading for tabs/lists
  useEffect(() => {
    if (title === 'Credit Tracker') {
      fetchCreditBalances();
    } else if (title === 'Customer History') {
      fetchCustomerHistory();
    } else if (title === 'Daily Summary') {
      fetchDailySummary();
    } else if (title === 'Shop Hours') {
      fetchShopInfo();
    } else if (title === 'Escalations') {
      fetchEscalations();
    }
  }, [title]);

  const fetchCreditBalances = async () => {
    try {
      const res = await fetch(`${API_BASE}/credit/all`);
      const data = await res.json();
      if (data.status === 'success') {
        setCreditBalances(data.customers || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchCustomerHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/customer/history?user_role=owner`);
      const data = await res.json();
      if (data.status === 'success') {
        setHistoryLogs(data.history || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchDailySummary = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/daily-summary`);
      const data = await res.json();
      if (data.status === 'success') {
        setSummaryData(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchShopInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}/shop/info`);
      const data = await res.json();
      if (data.status === 'success') {
        setHoursText(data.hours || '');
        setAddressText(data.address || '');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchEscalations = async () => {
    setEscalationsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/escalations`);
      const data = await res.json();
      if (data.status === 'success') {
        setEscalations(data.escalations || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setEscalationsLoading(false);
    }
  };

  // Submit Handlers
  const handleLogSale = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${API_BASE}/sales/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_name: saleItem,
          quantity: parseFloat(saleQty),
          unit: saleUnit,
          amount: parseFloat(saleAmount),
          user_role: 'owner',
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMsg({ type: 'success', text: data.message });
        setSaleItem('');
        setSaleQty('');
        setSaleAmount('');
      } else {
        setStatusMsg({ type: 'error', text: data.message || 'Failed to log sale' });
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Server connection error' });
    } finally {
      setLoading(false);
    }
  };

  const handleLogCredit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${API_BASE}/credit/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: creditCustomer,
          amount: parseFloat(creditAmount),
          type: creditType,
          note: creditNote,
          user_role: 'owner',
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMsg({ type: 'success', text: data.message });
        setCreditCustomer('');
        setCreditAmount('');
        setCreditNote('');
        fetchCreditBalances();
      } else {
        setStatusMsg({ type: 'error', text: data.message || 'Failed to log credit' });
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Server connection error' });
    } finally {
      setLoading(false);
    }
  };

  const handleLeaveMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${API_BASE}/messages/leave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_name: msgName || 'Unknown',
          message_text: msgText,
          from_user_id: 'customer_ui',
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMsg({ type: 'success', text: data.message });
        setMsgName('');
        setMsgText('');
      } else {
        setStatusMsg({ type: 'error', text: data.message || 'Failed to send message' });
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Server connection error' });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateShopHours = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${API_BASE}/shop/hours`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hours_text: hoursText,
          address_text: addressText,
          shop_id: 'primary_shop',
        }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setStatusMsg({ type: 'success', text: data.message });
      } else {
        setStatusMsg({ type: 'error', text: data.message || 'Failed to update shop hours' });
      }
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Server connection error' });
    } finally {
      setLoading(false);
    }
  };

  const handleMarketWatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commodity.trim()) return;
    setLoading(true);
    setMarketResult(null);
    try {
      const params = new URLSearchParams({ commodity: commodity.trim() });
      if (stateName.trim()) params.append('state', stateName.trim());
      const res = await fetch(`${API_BASE}/market-price?${params.toString()}`);
      const data = await res.json();
      setMarketResult(data);
    } catch (err: any) {
      setMarketResult({ status: 'failed', message: err.message || 'Network request failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#1A1512]/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
      <div className="bg-[#FFFDF9] border-2 border-[#1A1512] rounded-3xl p-6 md:p-8 max-w-lg w-full shadow-2xl flex flex-col gap-5 relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full text-[#1A1512]/50 hover:text-[#C1502E] hover:bg-[#F0E4D3]/40 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-2xl font-bold font-serif text-[#1A1512]" style={{ fontFamily: 'Georgia, serif' }}>
          {title}
        </h3>

        {statusMsg && (
          <div
            className={`p-3 rounded-xl flex items-center gap-2 text-xs font-semibold ${
              statusMsg.type === 'success' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
            }`}
          >
            {statusMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* 1. Sales Ledger */}
        {title === 'Sales Ledger' && (
          <form onSubmit={handleLogSale} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Item Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Full Cream Milk, Rice, Sugar"
                value={saleItem}
                onChange={(e) => setSaleItem(e.target.value)}
                className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Quantity</label>
                <input
                  type="number"
                  step="any"
                  required
                  placeholder="e.g. 2"
                  value={saleQty}
                  onChange={(e) => setSaleQty(e.target.value)}
                  className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Unit</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. kg, packet, L"
                  value={saleUnit}
                  onChange={(e) => setSaleUnit(e.target.value)}
                  className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Total Amount (₹)</label>
              <input
                type="number"
                step="any"
                required
                placeholder="e.g. 120"
                value={saleAmount}
                onChange={(e) => setSaleAmount(e.target.value)}
                className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-3 font-semibold text-sm cursor-pointer disabled:opacity-50"
            >
              {loading ? 'Logging Sale...' : 'Log Sale'}
            </button>
          </form>
        )}

        {/* 2. Credit Tracker */}
        {title === 'Credit Tracker' && (
          <div className="flex flex-col gap-4">
            <div className="flex gap-2 border-b border-[#1A1512]/15 pb-2">
              <button
                type="button"
                onClick={() => setActiveTab('form')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
                  activeTab === 'form' ? 'bg-[#C1502E] text-white' : 'text-[#1A1512]/70 hover:bg-[#F0E4D3]/60'
                }`}
              >
                New Entry
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('list')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
                  activeTab === 'list' ? 'bg-[#C1502E] text-white' : 'text-[#1A1512]/70 hover:bg-[#F0E4D3]/60'
                }`}
              >
                Customer Balances
              </button>
            </div>

            {activeTab === 'form' ? (
              <form onSubmit={handleLogCredit} className="flex flex-col gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Customer Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ramesh Kumar"
                    value={creditCustomer}
                    onChange={(e) => setCreditCustomer(e.target.value)}
                    className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Amount (₹)</label>
                    <input
                      type="number"
                      step="any"
                      required
                      placeholder="e.g. 500"
                      value={creditAmount}
                      onChange={(e) => setCreditAmount(e.target.value)}
                      className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Type</label>
                    <select
                      value={creditType}
                      onChange={(e: any) => setCreditType(e.target.value)}
                      className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                    >
                      <option value="given">Given (Udhaar)</option>
                      <option value="paid">Paid (Repayment)</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Note (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Groceries purchase"
                    value={creditNote}
                    onChange={(e) => setCreditNote(e.target.value)}
                    className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="mt-2 w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-2.5 font-semibold text-sm cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Saving Entry...' : 'Save Credit Entry'}
                </button>
              </form>
            ) : (
              <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
                {creditBalances.length === 0 ? (
                  <p className="text-xs text-[#1A1512]/60 text-center py-4">No credit records logged yet.</p>
                ) : (
                  creditBalances.map((item, idx) => (
                    <div key={idx} className="p-3 bg-[#F0E4D3]/40 rounded-xl border border-[#1A1512]/10 flex justify-between items-center">
                      <div>
                        <span className="font-bold text-sm text-[#1A1512] block">{item.customer_name}</span>
                        <span className="text-[10px] text-[#1A1512]/70">
                          Given: ₹{item.total_given} | Paid: ₹{item.total_paid}
                        </span>
                      </div>
                      <span className={`font-bold text-sm ${item.balance > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                        Balance: ₹{item.balance}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {/* 3. Leave a Message */}
        {title === 'Leave a Message' && (
          <form onSubmit={handleLeaveMessage} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Your Name</label>
              <input
                type="text"
                placeholder="Defaults to Unknown"
                value={msgName}
                onChange={(e) => setMsgName(e.target.value)}
                className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Message for Owner</label>
              <textarea
                required
                rows={3}
                placeholder="e.g. Please save 2 packets of milk for tomorrow morning"
                value={msgText}
                onChange={(e) => setMsgText(e.target.value)}
                className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-3 font-semibold text-sm cursor-pointer disabled:opacity-50"
            >
              {loading ? 'Sending Message...' : 'Send Message'}
            </button>
          </form>
        )}

        {/* 4. Customer History (Owner Read-Only Merged View) */}
        {title === 'Customer History' && (
          <div className="flex flex-col gap-3 max-h-80 overflow-y-auto pr-1">
            {loading ? (
              <p className="text-xs text-[#1A1512]/60 text-center py-4">Loading customer history...</p>
            ) : historyLogs.length === 0 ? (
              <p className="text-xs text-[#1A1512]/60 text-center py-4">No recent activity or messages found.</p>
            ) : (
              historyLogs.map((item) => {
                const isExpanded = expandedLogId === item.id;
                const isMessage = item.type === 'message';
                return (
                  <div
                    key={item.id}
                    onClick={() => {
                      if (isMessage && item.summary !== item.full_text) {
                        setExpandedLogId(isExpanded ? null : item.id);
                      }
                    }}
                    className={`p-3 bg-[#F0E4D3]/40 rounded-xl border border-[#1A1512]/10 flex flex-col gap-1.5 transition-all ${
                      isMessage && item.summary !== item.full_text ? 'cursor-pointer hover:border-[#C1502E]/40 hover:bg-[#F0E4D3]/60' : ''
                    }`}
                  >
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex items-center gap-1.5">
                        {isMessage ? (
                          <span className="flex items-center gap-1 bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-md uppercase">
                            <MessageSquare className="w-3 h-3" />
                            Message
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded-md uppercase">
                            <PhoneCall className="w-3 h-3" />
                            Call
                          </span>
                        )}
                        <span className="font-bold text-[#1A1512]">{item.name}</span>
                      </div>
                      <span className="text-[10px] text-[#1A1512]/60">
                        {new Date(item.timestamp).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>

                    <div className="text-xs text-[#1A1512]/80 leading-relaxed flex justify-between items-start">
                      <span>{isExpanded ? item.full_text : item.summary}</span>
                      {isMessage && item.summary !== item.full_text && (
                        <button className="text-[#C1502E] ml-2 p-0.5 shrink-0">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* 5. Daily Summary */}
        {title === 'Daily Summary' && (
          <div className="flex flex-col gap-4">
            {loading ? (
              <p className="text-xs text-[#1A1512]/60 text-center py-4">Generating daily summary...</p>
            ) : summaryData ? (
              <div className="flex flex-col gap-3">
                <div className="p-4 bg-[#F0E4D3]/50 rounded-2xl border border-[#1A1512]/15 text-center flex flex-col gap-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#C1502E]">Total Sales Today</span>
                  <span className="text-3xl font-bold text-[#1A1512]">₹{summaryData.total_amount}</span>
                  <span className="text-xs text-[#1A1512]/70">{summaryData.transaction_count} transactions logged</span>
                </div>
                <div className="p-3 bg-[#FFFDF9] rounded-xl border border-[#1A1512]/10 flex justify-between items-center text-xs">
                  <span className="font-bold text-[#1A1512]">Best Selling Item</span>
                  <span className="font-bold text-[#C1502E]">{summaryData.best_selling_item}</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-[#1A1512]/60 text-center py-4">No summary data available.</p>
            )}
          </div>
        )}

        {/* 6. Shop Hours (UI Form Only) */}
        {title === 'Shop Hours' && (
          <form onSubmit={handleUpdateShopHours} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Shop Operating Hours</label>
              <input
                type="text"
                required
                placeholder="e.g. 8:00 AM - 9:30 PM (Mon-Sat)"
                value={hoursText}
                onChange={(e) => setHoursText(e.target.value)}
                className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Store Address / Location</label>
              <input
                type="text"
                required
                placeholder="e.g. Shop #4, Main Market, New Delhi"
                value={addressText}
                onChange={(e) => setAddressText(e.target.value)}
                className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2.5 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-3 font-semibold text-sm cursor-pointer disabled:opacity-50"
            >
              {loading ? 'Saving Shop Hours...' : 'Save Shop Hours'}
            </button>
          </form>
        )}

        {/* 7. Market Watch */}
        {title === 'Market Watch' && (
          <form onSubmit={handleMarketWatch} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">Commodity</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rice, Potato, Wheat"
                  value={commodity}
                  onChange={(e) => setCommodity(e.target.value)}
                  className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-[#1A1512]/75 mb-1 uppercase tracking-wider">State (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Delhi, Punjab"
                  value={stateName}
                  onChange={(e) => setStateName(e.target.value)}
                  className="w-full bg-[#F0E4D3]/40 border border-[#1A1512]/20 rounded-xl px-4 py-2 text-sm text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-2.5 font-semibold text-sm cursor-pointer disabled:opacity-50 flex justify-center items-center gap-2"
            >
              <Search className="w-4 h-4" />
              {loading ? 'Searching Agmarknet...' : 'Search Market Price'}
            </button>

            {marketResult && (
              <div className="mt-2 p-4 bg-[#F0E4D3]/40 border border-[#1A1512]/15 rounded-2xl flex flex-col gap-2">
                {marketResult.status === 'success' ? (
                  <>
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-sm text-[#1A1512]">{marketResult.commodity}</span>
                      <span className="text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-md">Live Data</span>
                    </div>
                    <p className="text-xl font-bold text-[#C1502E]">{marketResult.price}</p>
                    <p className="text-xs text-[#1A1512]/70">Market: {marketResult.market}, {marketResult.district} ({marketResult.state})</p>
                    <p className="text-[10px] text-[#1A1512]/50">Reported Date: {marketResult.date}</p>
                  </>
                ) : (
                  <div className="text-xs text-rose-700 font-medium">
                    {marketResult.message || 'Could not fetch market price data.'}
                  </div>
                )}
              </div>
            )}
          </form>
        )}

        {/* Escalations — Owner Read-Only View */}
        {title === 'Escalations' && (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-[#1A1512]/60 leading-relaxed">
                Disputes and unresolved issues escalated by the voice agent. The owner should follow up directly.
              </p>
              <button
                type="button"
                onClick={fetchEscalations}
                className="p-1.5 rounded-lg text-[#1A1512]/50 hover:text-[#C1502E] hover:bg-[#F0E4D3]/60 transition-colors cursor-pointer shrink-0"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {escalationsLoading ? (
              <p className="text-xs text-[#1A1512]/60 text-center py-4">Loading escalations...</p>
            ) : escalations.length === 0 ? (
              <div className="text-center py-6 flex flex-col items-center gap-2">
                <ShieldAlert className="w-8 h-8 text-[#1A1512]/20" />
                <p className="text-xs text-[#1A1512]/50">No open escalations. All disputes resolved!</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2 max-h-80 overflow-y-auto pr-1">
                {escalations.map((esc) => {
                  const urgencyColors: Record<string, string> = {
                    high: 'bg-rose-100 text-rose-800',
                    medium: 'bg-amber-100 text-amber-800',
                    low: 'bg-emerald-100 text-emerald-800',
                  };
                  const statusColors: Record<string, string> = {
                    open: 'bg-blue-100 text-blue-800',
                    resolved: 'bg-emerald-100 text-emerald-800',
                    closed: 'bg-[#1A1512]/10 text-[#1A1512]/60',
                  };
                  const urgencyClass = urgencyColors[esc.urgency?.toLowerCase()] ?? 'bg-gray-100 text-gray-700';
                  const statusClass = statusColors[esc.status?.toLowerCase()] ?? 'bg-gray-100 text-gray-700';

                  return (
                    <div
                      key={esc.escalation_id}
                      className="p-3 bg-[#F0E4D3]/40 rounded-xl border border-[#1A1512]/10 flex flex-col gap-2"
                    >
                      {/* Header row: ref ID + badges */}
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5">
                          <ShieldAlert className="w-3.5 h-3.5 text-[#C1502E] shrink-0" />
                          <span className="text-[11px] font-bold text-[#C1502E] font-mono tracking-widest">
                            {esc.escalation_id}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={`text-[9px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-md ${urgencyClass}`}>
                            {esc.urgency}
                          </span>
                          <span className={`text-[9px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-md ${statusClass}`}>
                            {esc.status}
                          </span>
                        </div>
                      </div>

                      {/* Caller + issue type */}
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-[#1A1512]">{esc.caller_name}</span>
                        <span className="text-[10px] font-semibold text-[#1A1512]/60 italic">
                          {esc.issue_type.replace(/_/g, ' ')}
                        </span>
                      </div>

                      {/* Summary */}
                      <p className="text-xs text-[#1A1512]/80 leading-relaxed border-l-2 border-[#C1502E]/30 pl-2">
                        {esc.summary}
                      </p>

                      {/* Footer: contact method + date */}
                      <div className="flex items-center justify-between text-[10px] text-[#1A1512]/50">
                        <span>Contact via: <strong className="text-[#1A1512]/70">{esc.contact_method}</strong></span>
                        <span>
                          {new Date(esc.created_at).toLocaleString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Interactive UI for voice-first features */}
        {['Check Availability', 'Order Status', 'Shop Hours & Location', 'Talk to the Shop', 'Nearby Offers'].includes(title) && (
          <div className="space-y-4">
            <p className="text-sm text-[#1A1512]/80 leading-relaxed">
              This is a voice-first interactive feature! Click <strong className="text-[#C1502E]">Start Talking</strong> on the home screen to speak directly with DukaanMitra.
            </p>
            <div className="bg-[#F0E4D3]/50 p-4 rounded-xl border border-[#1A1512]/10 text-center flex flex-col gap-1">
              <span className="text-xs font-bold text-[#C1502E] uppercase tracking-wider">Voice Assistant Active</span>
              <span className="text-xs text-[#1A1512]/70">Say: &quot;{title === 'Check Availability' ? 'Is milk in stock?' : title === 'Order Status' ? 'Check order ord_001' : 'What are your shop hours?'}&quot;</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
