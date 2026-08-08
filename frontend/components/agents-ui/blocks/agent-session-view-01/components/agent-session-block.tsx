'use client';

import React, { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';
import { Loader2, Mic, CheckCircle2, RotateCcw } from 'lucide-react';

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.2,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: { ease: 'easeOut', duration: 0.3 },
    },
    visible: {
      opacity: 1,
      transition: { delay: 0.2, ease: 'easeOut', duration: 0.3 },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'pointer-events-none h-6 bg-gradient-to-b from-[#F0E4D3] to-transparent',
        top && 'bg-gradient-to-b',
        bottom && 'bg-gradient-to-t',
        className
      )}
    />
  );
}

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  className?: string;
}

export function AgentSessionView_01({
  preConnectMessage,
  isPreConnectBufferEnabled,
  supportsChatInput = true,
  supportsVideoInput = true,
  supportsScreenShare = true,
  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,
  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();

  // State mapping for DukaanMitra
  // States: 'connecting' | 'listening' | 'thinking' | 'speaking' | 'disconnected'
  const isDisconnected = !session.isConnected;
  const currentState = isDisconnected ? 'disconnected' : agentState || 'connecting';

  const getStateDetails = () => {
    switch (currentState) {
      case 'connecting':
      case 'initializing':
        return {
          label: 'Connecting...',
          color: '#1A1512',
          icon: <Loader2 className="w-5 h-5 animate-spin text-[#C1502E]" />,
          ringColor: 'border-[#1A1512]/30',
          activeSpeaker: null,
        };
      case 'listening':
        return {
          label: 'Listening...',
          color: '#7A8B69',
          icon: <Mic className="w-5 h-5 text-[#7A8B69] animate-bounce motion-reduce:animate-none" />,
          ringColor: 'border-[#7A8B69] ring-4 ring-[#7A8B69]/20',
          activeSpeaker: 'user',
        };
      case 'thinking':
        return {
          label: 'Dukaan Mitra is thinking...',
          color: '#C1502E',
          icon: <Loader2 className="w-5 h-5 animate-spin text-[#C1502E]" />,
          ringColor: 'border-[#C1502E]/60',
          activeSpeaker: 'agent',
        };
      case 'speaking':
        return {
          label: 'Dukaan Mitra is speaking...',
          color: '#C1502E',
          icon: <div className="w-3 h-3 rounded-full bg-[#C1502E] animate-ping motion-reduce:animate-none" />,
          ringColor: 'border-[#C1502E] ring-4 ring-[#C1502E]/25',
          activeSpeaker: 'agent',
        };
      case 'disconnected':
      default:
        return {
          label: 'Call ended',
          color: '#1A1512',
          icon: <CheckCircle2 className="w-5 h-5 text-[#7A8B69]" />,
          ringColor: 'border-[#1A1512]/20',
          activeSpeaker: null,
        };
    }
  };

  const stateDetails = getStateDetails();

  // Dynamic visualizer color based on speaker state (Sage Green for Listening/User, Terracotta for Speaking/Agent)
  const visualizerColor = currentState === 'listening' ? '#7A8B69' : '#C1502E';

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: supportsVideoInput,
    screenShare: supportsScreenShare,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section
      ref={ref}
      className={cn('bg-[#F0E4D3] text-[#1A1512] relative z-10 w-full overflow-hidden flex flex-col', className)}
      {...props}
    >
      <Fade top className="absolute inset-x-0 top-0 z-10 h-16" />

      {/* Top Agent & Speaker Clarity Indicator Bar */}
      <div className="relative z-20 pt-4 px-6 flex flex-col items-center gap-2">
        {/* Status Pill */}
        <motion.div
          key={currentState}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="flex items-center gap-2.5 px-4 py-2 rounded-full bg-[#FFFDF9] border border-[#1A1512]/15 shadow-sm"
        >
          {stateDetails.icon}
          <span className="font-semibold text-sm text-[#1A1512]">{stateDetails.label}</span>
        </motion.div>

        {/* Speaker Clarity Highlights */}
        <div className="flex items-center gap-6 text-xs font-semibold mt-1">
          {/* User Speaker Badge */}
          <div
            className={cn(
              'flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all duration-300',
              stateDetails.activeSpeaker === 'user'
                ? 'bg-[#7A8B69]/15 border-[#7A8B69] text-[#7A8B69] scale-105 shadow-sm'
                : 'border-transparent text-[#1A1512]/40'
            )}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>You</span>
          </div>

          {/* Awning Divider */}
          <div
            className="h-2 w-8 rounded-full border border-[#1A1512]/20"
            style={{
              backgroundImage: 'repeating-linear-gradient(-45deg, #C1502E, #C1502E 4px, #F0E4D3 4px, #F0E4D3 8px)',
            }}
          />

          {/* DukaanMitra Agent Badge */}
          <div
            className={cn(
              'flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all duration-300',
              stateDetails.activeSpeaker === 'agent'
                ? 'bg-[#C1502E]/15 border-[#C1502E] text-[#C1502E] scale-105 shadow-sm'
                : 'border-transparent text-[#1A1512]/40'
            )}
          >
            <Image src="/logo.png" alt="Logo" width={14} height={14} className="object-contain" />
            <span>Dukaan Mitra</span>
          </div>
        </div>
      </div>

      {/* Transcript area */}
      <div className="absolute top-20 bottom-[100px] flex w-full flex-col md:bottom-[110px] pointer-events-none">
        <AnimatePresence>
          {chatOpen && (
            <motion.div
              {...CHAT_MOTION_PROPS}
              className="flex h-full w-full flex-col gap-4 space-y-3 transition-opacity duration-300 ease-out pointer-events-auto"
            >
              <AgentChatTranscript
                agentState={agentState}
                messages={messages}
                className="mx-auto w-full max-w-3xl [&_.is-user>div]:bg-[#7A8B69] [&_.is-user>div]:text-white [&_.is-user>div]:rounded-[22px] [&>div>div]:px-4 [&>div>div]:pt-16 md:[&>div>div]:px-6"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Tile layout / Audio Visualizer */}
      <TileLayout
        chatOpen={chatOpen}
        audioVisualizerType={audioVisualizerType || 'bar'}
        audioVisualizerColor={visualizerColor}
        audioVisualizerColorShift={audioVisualizerColorShift}
        audioVisualizerBarCount={audioVisualizerBarCount || 5}
        audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
        audioVisualizerRadialRadius={audioVisualizerRadialRadius}
        audioVisualizerGridRowCount={audioVisualizerGridRowCount}
        audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
        audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
      />

      {/* Bottom Control Area or Call Ended Reset */}
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-2 bottom-6 z-50 md:inset-x-6"
      >
        <div className="bg-[#F0E4D3] relative mx-auto w-full max-w-4xl pb-2 flex flex-col items-center">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />

          {isDisconnected ? (
            /* Call Ended View with Start New Call Button */
            <div className="flex flex-col items-center gap-3 p-4 bg-[#FFFDF9] border border-[#1A1512]/15 rounded-2xl shadow-md w-full max-w-md">
              <span className="font-semibold text-base text-[#1A1512]">Conversation ended</span>
              <button
                onClick={() => session.start()}
                className="flex items-center gap-2 bg-[#1A1512] text-[#FFFDF9] hover:bg-[#C1502E] transition-colors rounded-full px-8 py-3 font-bold text-sm uppercase tracking-wider shadow"
              >
                <RotateCcw className="w-4 h-4" />
                Start New Call
              </button>
            </div>
          ) : (
            <AgentControlBar
              variant="livekit"
              controls={controls}
              isChatOpen={chatOpen}
              isConnected={session.isConnected}
              onDisconnect={session.end}
              onIsChatOpenChange={setChatOpen}
              className="bg-[#FFFDF9] border border-[#1A1512]/15 shadow-sm rounded-full p-2 px-6 md:px-8 w-full"
            />
          )}
        </div>
      </motion.div>
    </section>
  );
}
