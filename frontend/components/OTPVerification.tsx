/**
 * OTP Verification Component
 * Handles OTP input, verification, and resend functionality
 */

import React, { useState, useEffect, useRef } from 'react';
import { Check, Clock, RefreshCw, AlertCircle } from 'lucide-react';

interface OTPVerificationProps {
  userId: string;
  phone: string;
  onVerified: () => void;
  onSendOTP?: () => Promise<void>;
  autoSend?: boolean;
}

export const OTPVerification: React.FC<OTPVerificationProps> = ({
  userId,
  phone,
  onVerified,
  onSendOTP,
  autoSend = false,
}) => {
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [expiresIn, setExpiresIn] = useState(300); // 5 minutes
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Auto-send OTP on mount if enabled
  useEffect(() => {
    if (autoSend && onSendOTP) {
      handleSendOTP();
    }
  }, []);

  // Countdown timers
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  useEffect(() => {
    if (expiresIn > 0 && !success) {
      const timer = setTimeout(() => setExpiresIn(expiresIn - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [expiresIn, success]);

  const handleSendOTP = async () => {
    if (resendCooldown > 0) return;

    setLoading(true);
    setError('');

    try {
      if (onSendOTP) {
        await onSendOTP();
      } else {
        const response = await fetch('http://localhost:8000/api/auth/send-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, phone }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Failed to send OTP');
        }

        if (data.otp) {
          // Development mode - show OTP
          setError(`DEV MODE: Your OTP is ${data.otp}`);
        }
      }

      setResendCooldown(60);
      setExpiresIn(300);
    } catch (err: any) {
      setError(err.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    // Only allow digits
    if (value && !/^\d$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-verify when all 6 digits are entered
    if (newOtp.every((digit) => digit !== '') && newOtp.join('').length === 6) {
      handleVerifyOTP(newOtp.join(''));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    const newOtp = pastedData.split('').concat(Array(6).fill('')).slice(0, 6);
    setOtp(newOtp);

    if (pastedData.length === 6) {
      handleVerifyOTP(pastedData);
    }
  };

  const handleVerifyOTP = async (otpValue: string) => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, otp: otpValue }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Verification failed');
      }

      if (data.verified) {
        setSuccess(true);
        setTimeout(() => onVerified(), 1000);
      } else {
        throw new Error(data.message || 'Invalid OTP');
      }
    } catch (err: any) {
      setError(err.message || 'Verification failed');
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="rounded-lg bg-soil/5 border border-soil/20 p-4 flex items-center gap-3 animate-fadeIn">
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-soil flex items-center justify-center">
          <Check className="h-6 w-6 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-soil">Phone Verified!</p>
          <p className="text-xs text-stone-600">Your phone number has been successfully verified.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Instructions */}
      <div className="rounded-lg bg-stone-50 border border-stone-200 p-3">
        <p className="text-xs text-stone-700 leading-relaxed">
          We've sent a 6-digit verification code to <span className="font-bold">{phone}</span>.
          Enter it below to verify your phone number.
        </p>
      </div>

      {/* OTP Input */}
      <div>
        <label className="block text-xs font-extrabold uppercase tracking-wider text-stone-600 mb-2">
          Enter OTP Code
        </label>
        <div className="flex gap-2 justify-center" onPaste={handlePaste}>
          {otp.map((digit, index) => (
            <input
              key={index}
              ref={(el) => (inputRefs.current[index] = el)}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleOtpChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              className="w-12 h-14 text-center text-xl font-bold border-2 border-stone-300 rounded-lg focus:border-soil focus:ring-2 focus:ring-soil/20 outline-none transition-all"
              disabled={loading || success}
            />
          ))}
        </div>
      </div>

      {/* Timer */}
      {expiresIn > 0 && !success && (
        <div className="flex items-center justify-center gap-2 text-xs text-stone-500">
          <Clock className="h-4 w-4" />
          <span>
            Code expires in{' '}
            <span className="font-bold text-stone-700">
              {Math.floor(expiresIn / 60)}:{String(expiresIn % 60).padStart(2, '0')}
            </span>
          </span>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="rounded-lg bg-chilli/10 border border-chilli/20 p-3 flex items-start gap-2 text-chilli animate-fadeIn">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <span className="text-xs font-bold leading-tight">{error}</span>
        </div>
      )}

      {/* Resend button */}
      <div className="text-center">
        <button
          type="button"
          onClick={handleSendOTP}
          disabled={loading || resendCooldown > 0}
          className="inline-flex items-center gap-2 text-xs font-bold text-soil hover:underline disabled:text-stone-400 disabled:no-underline transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend OTP'}
        </button>
      </div>
    </div>
  );
};

export default OTPVerification;
