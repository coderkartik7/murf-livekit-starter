import React, { useState } from 'react';
import {
  OWNER_FEATURES,
  CUSTOMER_FEATURES,
  type FeatureCard,
} from '@/lib/features-config';
import { AlertCircle, RefreshCw, X } from 'lucide-react';


interface WelcomeViewProps {
  startButtonText?: string;
  onStartCall: () => void;
  micError?: string | null;
  onRetryMic?: () => void;
  role: 'owner' | 'customer';
  onChangeRole: () => void;
}

export const WelcomeView = ({
  startButtonText = 'START TALKING',
  onStartCall,
  micError,
  onRetryMic,
  role,
  onChangeRole,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [selectedFeature, setSelectedFeature] = useState<FeatureCard | null>(null);

  const features = role === 'owner' ? OWNER_FEATURES : CUSTOMER_FEATURES;

  return (
    <div
      ref={ref}
      className="w-full min-h-screen bg-[#F0E4D3] text-[#1A1512] flex flex-col items-center pt-[80px] pb-16 px-4 overflow-y-auto"
    >
      {/* Role Switch Affordance */}
      <div className="w-full max-w-5xl flex justify-end mb-4">
        <button
          onClick={onChangeRole}
          className="text-xs md:text-sm font-semibold text-[#1A1512]/60 hover:text-[#C1502E] transition-colors flex items-center gap-1 cursor-pointer"
        >
          {role === 'owner' ? 'Not a Shop Owner? Switch to Customer' : 'Shop Owner? Switch to Owner Panel'} &rarr;
        </button>
      </div>

      {/* Hero Section */}
      <div className="max-w-2xl text-center flex flex-col items-center gap-3 mt-1 md:mt-2">
        <h1
          className="text-3xl md:text-5xl font-bold tracking-tight text-[#1A1512]"
          style={{ fontFamily: 'Georgia, serif' }}
        >
          {role === 'owner' ? 'Run your shop, hands-free' : 'Talk to your local shop, anytime'}
        </h1>
        <p className="text-base md:text-lg text-[#1A1512]/80 max-w-lg font-normal leading-relaxed">
          {role === 'owner'
            ? 'Log sales, track stock, and manage customer calls in real-time — entirely by voice.'
            : 'Check stock, ask about store hours, or leave a message for the owner using your voice.'}
        </p>
      </div>

      {/* Mic Error Banner / Handling */}
      {micError ? (
        <div className="my-8 p-6 max-w-md w-full bg-[#FFFDF9] border-2 border-[#C1502E] rounded-2xl shadow-md flex flex-col items-center text-center gap-4">
          <AlertCircle className="w-10 h-10 text-[#C1502E]" />
          <div>
            <h3 className="font-bold text-lg text-[#1A1512] mb-1">Microphone Access Blocked</h3>
            <p className="text-sm text-[#1A1512]/80 leading-snug">
              Enable microphone access in your browser site settings to talk to Dukaan Mitra.
            </p>
          </div>
          <ol className="text-xs text-left bg-[#F0E4D3]/60 p-3 rounded-lg w-full flex flex-col gap-1 text-[#1A1512]/90">
            <li>1. Click lock/info icon next to URL bar</li>
            <li>2. Go to Site Settings → Microphone → Allow</li>
            <li>3. Click Try Again below</li>
          </ol>
          <button
            onClick={onRetryMic}
            className="flex items-center gap-2 bg-[#C1502E] text-white px-6 py-2.5 rounded-full font-semibold text-sm hover:opacity-90 transition-opacity"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
        </div>
      ) : (
        /* Center Interactive Circle Area */
        <div className="my-8 md:my-12 flex flex-col items-center gap-6">
          <div className="relative flex items-center justify-center">
            {/* Animated terracotta soundwave/ring centerpiece design */}
            <div className="relative w-[240px] h-[240px] md:w-[300px] md:h-[300px] flex items-center justify-center">
              {/* Outer Pulsing Glow Rings */}
              <div className="absolute inset-0 rounded-full border-4 border-[#C1502E]/10 animate-[ping_3s_infinite] motion-reduce:animate-none pointer-events-none" />
              <div className="absolute inset-4 rounded-full border-2 border-[#C1502E]/25 animate-[ping_2s_infinite] motion-reduce:animate-none pointer-events-none" />
              
              {/* Central Solid Circle with Wave motif */}
              <div className="relative w-[180px] h-[180px] md:w-[220px] md:h-[220px] rounded-full border-3 border-[#1A1512] bg-[#FFFDF9] shadow-lg flex flex-col items-center justify-center overflow-hidden">
                {/* Simulated Wave Lines inside Centerpiece */}
                <div className="flex gap-1.5 items-center justify-center h-16 w-full">
                  <div className="w-1.5 h-6 bg-[#C1502E] rounded-full animate-[pulse_1.2s_infinite_ease-in-out]" />
                  <div className="w-1.5 h-12 bg-[#C1502E] rounded-full animate-[pulse_1.5s_infinite_ease-in-out_0.2s]" />
                  <div className="w-1.5 h-16 bg-[#C1502E] rounded-full animate-[pulse_1.8s_infinite_ease-in-out_0.4s]" />
                  <div className="w-1.5 h-12 bg-[#C1502E] rounded-full animate-[pulse_1.5s_infinite_ease-in-out_0.6s]" />
                  <div className="w-1.5 h-6 bg-[#C1502E] rounded-full animate-[pulse_1.2s_infinite_ease-in-out_0.8s]" />
                </div>
                <span className="text-[10px] tracking-widest font-bold text-[#1A1512]/60 uppercase mt-2">Tap to talk</span>
              </div>
            </div>
          </div>

          {/* Primary Action Button */}
          <button
            onClick={onStartCall}
            className="bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-all duration-300 rounded-full px-10 py-4 font-bold text-sm md:text-base tracking-wider uppercase shadow-md active:scale-95 cursor-pointer"
          >
            {startButtonText}
          </button>
        </div>
      )}

      {/* Awning Motif Section Divider */}
      <div className="w-full max-w-4xl my-8 flex items-center gap-4">
        <div className="h-[2px] flex-1 bg-[#1A1512]/20" />
        <div
          className="h-3 w-28 rounded-full border border-[#1A1512]/30"
          style={{
            backgroundImage: 'repeating-linear-gradient(-45deg, #C1502E, #C1502E 8px, #F0E4D3 8px, #F0E4D3 16px)',
          }}
        />
        <div className="h-[2px] flex-1 bg-[#1A1512]/20" />
      </div>

      {/* Feature Cards Section */}
      <div className="w-full max-w-5xl mt-2">
        <div className="text-center mb-6">
          <h2
            className="text-xl md:text-2xl font-bold text-[#1A1512]"
            style={{ fontFamily: 'Georgia, serif' }}
          >
            Everything your dukaan needs
          </h2>
          <p className="text-sm text-[#1A1512]/70">
            {role === 'owner' ? 'Explore features tailored for shop owners' : 'Quick access options for shoppers'}
          </p>
        </div>

        {/* Scrollable / Grid layout */}
        <div className="flex md:grid md:grid-cols-3 gap-4 overflow-x-auto pb-4 px-2 snap-x snap-mandatory scrollbar-none">
          {features.map((feat, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedFeature(feat)}
              className="min-w-[260px] md:min-w-0 text-left snap-center bg-[#FFFDF9] border border-[#1A1512]/15 rounded-2xl p-5 shadow-sm hover:-translate-y-1 hover:shadow-md hover:border-[#C1502E]/40 transition-all duration-300 flex flex-col gap-3 group cursor-pointer"
            >
              <div className="flex justify-between items-start w-full">
                <div className="p-2.5 rounded-xl bg-[#F0E4D3]/60 w-fit group-hover:bg-[#C1502E]/10 transition-colors">
                  {feat.icon}
                </div>
                {feat.statusText && (
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-[#C1502E]/10 text-[#C1502E] px-2 py-0.5 rounded-md">
                    {feat.statusText}
                  </span>
                )}
              </div>
              <div>
                <h3 className="font-bold text-base text-[#1A1512] mb-1">{feat.title}</h3>
                <p className="text-xs text-[#1A1512]/75 leading-relaxed">{feat.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Clean Coming Soon / Detailed Modal Panel */}
      {selectedFeature && (
        <div className="fixed inset-0 bg-[#1A1512]/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-[#FFFDF9] border-2 border-[#1A1512] rounded-3xl p-6 md:p-8 max-w-md w-full shadow-xl flex flex-col gap-6 relative">
            <button
              onClick={() => setSelectedFeature(null)}
              className="absolute top-4 right-4 p-1 rounded-full text-[#1A1512]/50 hover:text-[#C1502E] hover:bg-[#F0E4D3]/40 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-4">
              <div className="p-3.5 rounded-2xl bg-[#F0E4D3]/60 text-[#C1502E]">
                {selectedFeature.icon}
              </div>
              <h3 className="text-xl font-bold font-serif text-[#1A1512]" style={{ fontFamily: 'Georgia, serif' }}>
                {selectedFeature.title}
              </h3>
            </div>
            <div className="space-y-4">
              <p className="text-sm text-[#1A1512]/80 leading-relaxed">
                {selectedFeature.desc}
              </p>
              <div className="bg-[#F0E4D3]/40 p-4 rounded-xl border border-[#1A1512]/10 text-center">
                <span className="text-xs font-bold text-[#C1502E] uppercase tracking-widest block mb-1">Coming soon</span>
                <span className="text-xs text-[#1A1512]/70">This feature is on its way. Use voice assistant mode to ask directly!</span>
              </div>
            </div>
            <button
              onClick={() => setSelectedFeature(null)}
              className="w-full bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-xl py-3 font-semibold text-sm cursor-pointer"
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
