import React, { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import { TokenSource } from 'livekit-client';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { RoleSelection } from '@/components/app/role-selection';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);
const MotionRoleSelection = motion.create(RoleSelection);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    ease: 'easeInOut',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, room } = useSessionContext();
  const { resolvedTheme } = useTheme();
  const [micError, setMicError] = useState<string | null>(null);
  const [role, setRole] = useState<'owner' | 'customer' | null>(null);

  // Load role from localStorage on mount
  useEffect(() => {
    const savedRole = localStorage.getItem('dukaanmitra_role') as 'owner' | 'customer' | null;
    if (savedRole === 'owner' || savedRole === 'customer') {
      setRole(savedRole);
    }
  }, []);

  const handleSelectRole = (selectedRole: 'owner' | 'customer') => {
    localStorage.setItem('dukaanmitra_role', selectedRole);
    setRole(selectedRole);
  };

  const handleStartCall = async () => {
    setMicError(null);
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        await navigator.mediaDevices.getUserMedia({ audio: true });
      }
      
      // Update token endpoint URL dynamically with user parameter if standard TokenSource is used
      // Since livekit session object wraps room connection options, we can set custom token endpoint or update TokenSource dynamically.
      // Let's pass query param to api route.
      const currentTokenSource = TokenSource.endpoint(`/api/token?user=${role || 'customer'}`);
      // Start connection with dynamic token endpoint
      start(currentTokenSource);
    } catch (err: unknown) {
      console.error('Microphone permission error:', err);
      const errorMessage =
        err instanceof Error ? err.message : 'Microphone permission was denied by browser.';
      setMicError(errorMessage);
    }
  };

  return (
    <AnimatePresence mode="wait">
      {/* Role Selection Screen */}
      {!isConnected && !role && (
        <MotionRoleSelection
          key="role-selection"
          {...VIEW_MOTION_PROPS}
          onSelect={handleSelectRole}
        />
      )}

      {/* Welcome view */}
      {!isConnected && role && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
          micError={micError}
          onRetryMic={handleStartCall}
          role={role}
          onChangeRole={() => setRole(null)}
        />
      )}
      {/* Session view */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
          audioVisualizerType={appConfig.audioVisualizerType}
          audioVisualizerColor={
            resolvedTheme === 'dark'
              ? appConfig.audioVisualizerColorDark
              : appConfig.audioVisualizerColor
          }
          audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
          audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
          audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
          audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
          audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
          className="fixed inset-0 top-[64px]"
        />
      )}
    </AnimatePresence>
  );
}

