import React from 'react';
import {
  Store,
  Headset,
  Clock,
  CreditCard,
  BarChart3,
  TrendingUp,
  Search,
  FileText,
  MapPin,
  MessageSquare,
  Gift,
  Volume2,
  ShieldAlert
} from 'lucide-react';

export interface FeatureCard {
  icon: React.ReactNode;
  title: string;
  desc: string;
  statusText?: string;
}

export const OWNER_FEATURES: FeatureCard[] = [
  {
    icon: <Store className="w-6 h-6 text-[#C1502E]" />,
    title: 'Sales Ledger',
    desc: 'Log daily sales and stock updates instantly by voice',
  },
  {
    icon: <Headset className="w-6 h-6 text-[#C1502E]" />,
    title: 'Customer History',
    desc: 'View recent call logs, caller summaries, and customer activity history',
  },
  {
    icon: <Clock className="w-6 h-6 text-[#C1502E]" />,
    title: 'Shop Hours',
    desc: 'Manage and broadcast your store open & close timings',
  },
  {
    icon: <CreditCard className="w-6 h-6 text-[#C1502E]" />,
    title: 'Credit Tracker',
    desc: 'Keep clear tabs on customer udhaar and pending balances',
  },
  {
    icon: <BarChart3 className="w-6 h-6 text-[#C1502E]" />,
    title: 'Daily Summary',
    desc: 'Listen to a comprehensive spoken recap of day activity',
  },
  {
    icon: <TrendingUp className="w-6 h-6 text-[#C1502E]" />,
    title: 'Market Watch',
    desc: 'Track local competitor pricing and demand trends over time',
  },
  {
    icon: <ShieldAlert className="w-6 h-6 text-[#C1502E]" />,
    title: 'Escalations',
    desc: 'Review open disputes and unresolved issues flagged by the voice agent',
  },
];

export const CUSTOMER_FEATURES: FeatureCard[] = [
  {
    icon: <Search className="w-6 h-6 text-[#C1502E]" />,
    title: 'Check Availability',
    desc: 'Ask if a product or grocery item is in stock right now',
  },
  {
    icon: <FileText className="w-6 h-6 text-[#C1502E]" />,
    title: 'Order Status',
    desc: 'Check the delivery or pickup progress of your order',
  },
  {
    icon: <MapPin className="w-6 h-6 text-[#C1502E]" />,
    title: 'Shop Hours & Location',
    desc: 'Find out when the shop is open and where to visit',
  },
  {
    icon: <Volume2 className="w-6 h-6 text-[#C1502E]" />,
    title: 'Talk to the Shop',
    desc: 'Get general queries answered instantly by voice',
  },
  {
    icon: <MessageSquare className="w-6 h-6 text-[#C1502E]" />,
    title: 'Leave a Message',
    desc: 'Leave word or requests for the shop owner directly',
  },
  {
    icon: <Gift className="w-6 h-6 text-[#C1502E]" />,
    title: 'Nearby Offers',
    desc: 'Hear about current deals and exclusive local discounts',
    statusText: 'Upcoming',
  },
];
