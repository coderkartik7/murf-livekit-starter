'use client';

import React from 'react';
import { Store, User } from 'lucide-react';

interface RoleSelectionProps {
  onSelect: (role: 'owner' | 'customer') => void;
}

export function RoleSelection({ onSelect }: RoleSelectionProps) {
  return (
    <div className="w-full min-h-screen bg-[#F0E4D3] text-[#1A1512] flex flex-col items-center justify-center px-4 py-16">
      {/* Decorative awning lines */}
      <div className="w-full max-w-md mb-8 flex items-center justify-center">
        <div
          className="h-4 w-48 rounded-full border-2 border-[#1A1512]"
          style={{
            backgroundImage: 'repeating-linear-gradient(-45deg, #C1502E, #C1502E 12px, #F0E4D3 12px, #F0E4D3 24px)',
          }}
        />
      </div>

      <div className="text-center max-w-md mb-12">
        <h1
          className="text-4xl font-bold tracking-tight text-[#1A1512] mb-3"
          style={{ fontFamily: 'Georgia, serif' }}
        >
          Welcome to DukaanMitra
        </h1>
        <p className="text-lg text-[#1A1512]/80">
          Who is this assistant helping today?
        </p>
      </div>

      {/* Two Large Clickable Cards */}
      <div className="flex flex-col sm:flex-row gap-6 w-full max-w-2xl px-4">
        {/* Shop Owner Card */}
        <button
          onClick={() => onSelect('owner')}
          className="flex-1 bg-[#FFFDF9] border-2 border-[#1A1512] rounded-3xl p-8 flex flex-col items-center text-center gap-6 shadow-md hover:-translate-y-1.5 active:scale-95 transition-all duration-300 group cursor-pointer"
        >
          {/* Custom Illustrated Icon Container */}
          <div className="w-24 h-24 rounded-2xl bg-[#7A8B69]/15 border-2 border-[#7A8B69] flex items-center justify-center text-[#7A8B69] group-hover:bg-[#C1502E]/10 group-hover:border-[#C1502E] group-hover:text-[#C1502E] transition-all duration-300">
            <Store className="w-12 h-12 stroke-[1.5]" />
          </div>
          <div>
            <h2
              className="text-2xl font-bold text-[#1A1512] mb-2"
              style={{ fontFamily: 'Georgia, serif' }}
            >
              Shop Owner
            </h2>
            <p className="text-sm text-[#1A1512]/70 leading-relaxed">
              Log sales, manage credit balances, track stock updates, and generate daily voice summaries.
            </p>
          </div>
        </button>

        {/* Customer Card */}
        <button
          onClick={() => onSelect('customer')}
          className="flex-1 bg-[#FFFDF9] border-2 border-[#1A1512] rounded-3xl p-8 flex flex-col items-center text-center gap-6 shadow-md hover:-translate-y-1.5 active:scale-95 transition-all duration-300 group cursor-pointer"
        >
          {/* Custom Illustrated Icon Container */}
          <div className="w-24 h-24 rounded-2xl bg-[#C1502E]/15 border-2 border-[#C1502E] flex items-center justify-center text-[#C1502E] group-hover:bg-[#7A8B69]/10 group-hover:border-[#7A8B69] group-hover:text-[#7A8B69] transition-all duration-300">
            <User className="w-12 h-12 stroke-[1.5]" />
          </div>
          <div>
            <h2
              className="text-2xl font-bold text-[#1A1512] mb-2"
              style={{ fontFamily: 'Georgia, serif' }}
            >
              Customer
            </h2>
            <p className="text-sm text-[#1A1512]/70 leading-relaxed">
              Check product availability, inquire about shop hours & location, or leave a message.
            </p>
          </div>
        </button>
      </div>
    </div>
  );
}
