'use client';

import React, { useState } from 'react';
import { LayoutGrid, X, ChevronRight } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { cn } from '@/lib/shadcn/utils';
import { OWNER_FEATURES, CUSTOMER_FEATURES, type FeatureCard } from '@/lib/features-config';

interface FeatureModalProps {
  feature: FeatureCard;
  onClose: () => void;
}

function FeatureModal({ feature, onClose }: FeatureModalProps) {
  const [productQuery, setProductQuery] = useState('');
  const [orderQuery, setOrderQuery] = useState('ord_001');
  const [loading, setLoading] = useState(false);
  const [resultData, setResultData] = useState<any>(null);

  // Auto-fetch for Shop Hours on mount
  React.useEffect(() => {
    if (feature.title === 'Shop Hours & Location') {
      handleShopInfo();
    }
  }, [feature.title]);

  const handleProductSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!productQuery.trim()) return;
    setLoading(true);
    setResultData(null);
    try {
      const res = await fetch(`http://localhost:8000/api/products/lookup?name=${encodeURIComponent(productQuery)}`);
      const data = await res.json();
      setResultData(data);
    } catch (err) {
      setResultData({ status: 'error', message: 'Failed to connect to shop server.' });
    } finally {
      setLoading(false);
    }
  };

  const handleOrderCheck = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!orderQuery.trim()) return;
    setLoading(true);
    setResultData(null);
    try {
      const res = await fetch(`http://localhost:8000/api/orders/status?query=${encodeURIComponent(orderQuery)}`);
      const data = await res.json();
      setResultData(data);
    } catch (err) {
      setResultData({ status: 'error', message: 'Failed to fetch order status.' });
    } finally {
      setLoading(false);
    }
  };

  const handleShopInfo = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/shop/info');
      const data = await res.json();
      setResultData(data);
    } catch (err) {
      setResultData({ status: 'error', message: 'Failed to load shop information.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-[#1A1512]/40 backdrop-blur-sm flex items-center justify-center p-4 z-[200]"
      onClick={onClose}
    >
      <div
        className="bg-[#FFFDF9] border-2 border-[#1A1512] rounded-3xl p-6 md:p-8 max-w-md w-full shadow-xl flex flex-col gap-5 relative max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full text-[#1A1512]/50 hover:text-[#C1502E] hover:bg-[#F0E4D3]/40 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-[#F0E4D3]/60 text-[#C1502E] shrink-0">
            {feature.icon}
          </div>
          <h3 className="text-xl font-bold text-[#1A1512]" style={{ fontFamily: 'Georgia, serif' }}>
            {feature.title}
          </h3>
        </div>

        <p className="text-sm text-[#1A1512]/80 leading-relaxed">{feature.desc}</p>

        {/* Feature 1: Check Availability */}
        {feature.title === 'Check Availability' && (
          <div className="space-y-4">
            <form onSubmit={handleProductSearch} className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. Milk, Bread, Rice"
                value={productQuery}
                onChange={(e) => setProductQuery(e.target.value)}
                className="flex-1 px-3 py-2 text-sm bg-[#F0E4D3]/30 border border-[#1A1512]/20 rounded-xl text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
              <button
                type="submit"
                disabled={loading || !productQuery.trim()}
                className="px-4 py-2 bg-[#C1502E] text-[#FFFDF9] text-xs font-semibold rounded-xl hover:bg-[#A33E20] disabled:opacity-50 transition-colors cursor-pointer"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </form>

            {resultData && (
              <div className="bg-[#F0E4D3]/40 p-4 rounded-xl border border-[#1A1512]/10 space-y-2">
                {resultData.status === 'success' ? (
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-bold text-sm text-[#1A1512]">
                        {resultData.primary_match.name}
                      </span>
                      <span className="text-xs font-semibold bg-[#C1502E]/10 text-[#C1502E] px-2 py-0.5 rounded">
                        ₹{resultData.primary_match.price} / {resultData.primary_match.unit}
                      </span>
                    </div>
                    <p className="text-xs text-[#1A1512]/70">
                      Stock:{' '}
                      <strong className={resultData.primary_match.stock_qty > 0 ? 'text-green-700' : 'text-red-600'}>
                        {resultData.primary_match.stock_qty > 0
                          ? `${resultData.primary_match.stock_qty} available`
                          : 'Out of Stock'}
                      </strong>
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-[#C1502E] font-medium">{resultData.message}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Feature 2: Order Status */}
        {feature.title === 'Order Status' && (
          <div className="space-y-4">
            <form onSubmit={handleOrderCheck} className="flex gap-2">
              <input
                type="text"
                placeholder="Order ID (e.g. ord_001) or user_rahul"
                value={orderQuery}
                onChange={(e) => setOrderQuery(e.target.value)}
                className="flex-1 px-3 py-2 text-sm bg-[#F0E4D3]/30 border border-[#1A1512]/20 rounded-xl text-[#1A1512] focus:outline-none focus:border-[#C1502E]"
              />
              <button
                type="submit"
                disabled={loading || !orderQuery.trim()}
                className="px-4 py-2 bg-[#C1502E] text-[#FFFDF9] text-xs font-semibold rounded-xl hover:bg-[#A33E20] disabled:opacity-50 transition-colors cursor-pointer"
              >
                {loading ? 'Checking...' : 'Check'}
              </button>
            </form>

            {resultData && (
              <div className="bg-[#F0E4D3]/40 p-4 rounded-xl border border-[#1A1512]/10 space-y-2">
                {resultData.status === 'success' ? (
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-sm text-[#1A1512]">
                        Order #{resultData.latest_order.order_id}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#1A1512] text-[#FFFDF9]">
                        {resultData.latest_order.status}
                      </span>
                    </div>
                    <p className="text-xs text-[#1A1512]/80">
                      Slot: <strong>{resultData.latest_order.delivery_slot}</strong>
                    </p>
                    <p className="text-xs text-[#1A1512]/80">
                      Total: <strong>₹{resultData.latest_order.total}</strong>
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-[#C1502E] font-medium">{resultData.message}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Feature 3: Shop Hours & Location */}
        {feature.title === 'Shop Hours & Location' && (
          <div className="space-y-3">
            {loading ? (
              <div className="text-xs text-[#1A1512]/60 animate-pulse">Loading shop information...</div>
            ) : resultData && resultData.status === 'success' ? (
              <div className="bg-[#F0E4D3]/40 p-4 rounded-xl border border-[#1A1512]/10 space-y-2">
                <div>
                  <span className="text-[10px] uppercase font-bold text-[#C1502E] tracking-widest block">
                    Operating Hours
                  </span>
                  <p className="text-sm font-semibold text-[#1A1512]">{resultData.hours}</p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-[#C1502E] tracking-widest block">
                    Address
                  </span>
                  <p className="text-xs text-[#1A1512]/80">{resultData.address}</p>
                </div>
              </div>
            ) : (
              <p className="text-xs text-[#C1502E]">{resultData?.message || 'Unable to fetch shop details.'}</p>
            )}
          </div>
        )}

        {/* Default / Fallback cards */}
        {feature.title !== 'Check Availability' &&
          feature.title !== 'Order Status' &&
          feature.title !== 'Shop Hours & Location' && (
            <div className="bg-[#F0E4D3]/40 p-4 rounded-xl border border-[#1A1512]/10 text-center">
              <span className="text-xs font-bold text-[#C1502E] uppercase tracking-widest block mb-1">
                Voice Accessible
              </span>
              <span className="text-xs text-[#1A1512]/70">
                You can ask the voice assistant directly during a live call!
              </span>
            </div>
          )}

        <button
          onClick={onClose}
          className="w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-2.5 font-semibold text-sm cursor-pointer mt-2"
        >
          Close
        </button>
      </div>
    </div>
  );
}

interface ServicesSidebarProps {
  role: 'owner' | 'customer';
}

export function ServicesSidebar({ role }: ServicesSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState<FeatureCard | null>(null);

  const features = role === 'owner' ? OWNER_FEATURES : CUSTOMER_FEATURES;
  const label = role === 'owner' ? 'Owner Tools' : 'Quick Access';

  return (
    <>
      {/* Toggle Button — always visible */}
      <button
        id="services-sidebar-toggle"
        onClick={() => setIsOpen((v) => !v)}
        aria-label={isOpen ? 'Close services panel' : 'Open services panel'}
        aria-expanded={isOpen}
        className={cn(
          'fixed left-0 top-1/2 -translate-y-1/2 z-[100]',
          'flex flex-col items-center justify-center gap-1',
          'bg-[#FFFDF9] border border-[#1A1512]/20 border-l-0 rounded-r-xl',
          'px-2 py-4 shadow-md',
          'text-[#1A1512] hover:text-[#C1502E] hover:border-[#C1502E]/40 transition-all duration-200',
          'cursor-pointer',
          // On small screens, move to bottom for bottom-sheet feel
          'md:top-1/2 md:-translate-y-1/2',
        )}
      >
        {isOpen ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <LayoutGrid className="w-4 h-4" />
        )}
        <span
          className="text-[9px] font-bold uppercase tracking-widest"
          style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
        >
          {isOpen ? 'Close' : 'Services'}
        </span>
      </button>

      {/* Overlay for mobile — backdrop tap to close */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-[#1A1512]/20 z-[98] md:hidden"
            onClick={() => setIsOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            key="services-sidebar"
            id="services-sidebar"
            // Desktop: slide in from left
            initial={{ x: '-100%', opacity: 0.6 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '-100%', opacity: 0.6 }}
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            className={cn(
              'fixed left-0 top-[64px] bottom-0 z-[99]',
              'w-[270px]',
              'bg-[#FFFDF9] border-r border-[#1A1512]/15 shadow-xl',
              'flex flex-col overflow-hidden',
            )}
          >
            {/* Sidebar Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#1A1512]/10">
              <div className="flex items-center gap-2">
                {/* Mini awning motif */}
                <div
                  className="h-2 w-6 rounded-sm"
                  style={{
                    backgroundImage:
                      'repeating-linear-gradient(-45deg, #C1502E, #C1502E 4px, #F0E4D3 4px, #F0E4D3 8px)',
                  }}
                />
                <span
                  className="text-sm font-bold text-[#1A1512]"
                  style={{ fontFamily: 'Georgia, serif' }}
                >
                  {label}
                </span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-lg text-[#1A1512]/50 hover:text-[#C1502E] hover:bg-[#F0E4D3]/60 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Hint text */}
            <p className="px-4 pt-3 pb-1 text-[11px] text-[#1A1512]/50 leading-relaxed">
              Tap a feature to learn more — your call stays active.
            </p>

            {/* Feature Cards List */}
            <div className="flex-1 overflow-y-auto px-3 py-2 flex flex-col gap-2">
              {features.map((feat, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedFeature(feat)}
                  className={cn(
                    'w-full text-left rounded-xl px-3 py-3',
                    'bg-[#F0E4D3]/40 border border-[#1A1512]/10',
                    'hover:bg-[#FFFDF9] hover:border-[#C1502E]/30 hover:shadow-sm',
                    'active:scale-[0.98]',
                    'transition-all duration-150 cursor-pointer',
                    'flex items-start gap-3 group',
                  )}
                >
                  {/* Smaller icon in condensed sidebar card */}
                  <div className="shrink-0 p-1.5 rounded-lg bg-[#FFFDF9] border border-[#1A1512]/10 group-hover:border-[#C1502E]/20 transition-colors mt-0.5">
                    <div className="[&>svg]:w-4 [&>svg]:h-4 text-[#C1502E]">
                      {feat.icon}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-xs font-bold text-[#1A1512] leading-snug">
                        {feat.title}
                      </span>
                      {feat.statusText && (
                        <span className="text-[9px] font-bold uppercase tracking-wide bg-[#C1502E]/10 text-[#C1502E] px-1.5 py-0.5 rounded">
                          {feat.statusText}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#1A1512]/60 leading-snug mt-0.5 line-clamp-2">
                      {feat.desc}
                    </p>
                  </div>
                </button>
              ))}
            </div>

            {/* Footer role badge */}
            <div className="px-4 py-3 border-t border-[#1A1512]/10 flex items-center gap-2">
              <span className="text-[10px] font-semibold text-[#1A1512]/40 uppercase tracking-widest">
                {role === 'owner' ? 'Shop Owner View' : 'Customer View'}
              </span>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Feature Detail Modal */}
      <AnimatePresence>
        {selectedFeature && (
          <motion.div
            key="feature-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <FeatureModal
              feature={selectedFeature}
              onClose={() => setSelectedFeature(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
