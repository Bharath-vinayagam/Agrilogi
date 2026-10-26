/**
 * Password Strength Validation Component
 * Displays real-time password strength feedback
 */

import React from 'react';
import { Check, X } from 'lucide-react';

interface PasswordStrengthProps {
  password: string;
  showRequirements?: boolean;
}

interface Requirement {
  label: string;
  test: (password: string) => boolean;
}

const requirements: Requirement[] = [
  {
    label: 'At least 8 characters',
    test: (pwd) => pwd.length >= 8,
  },
  {
    label: 'Contains a number or special character',
    test: (pwd) => /[\d!@#$%^&*(),.?":{}|<>]/.test(pwd),
  },
  {
    label: 'Contains uppercase and lowercase letters',
    test: (pwd) => /[a-z]/.test(pwd) && /[A-Z]/.test(pwd),
  },
];

export function calculatePasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  if (!password) {
    return { score: 0, label: '', color: 'bg-stone-200' };
  }

  let score = 0;

  // Length score
  if (password.length >= 8) score += 25;
  if (password.length >= 12) score += 10;
  if (password.length >= 16) score += 10;

  // Complexity score
  if (/[a-z]/.test(password)) score += 10;
  if (/[A-Z]/.test(password)) score += 10;
  if (/\d/.test(password)) score += 15;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 20;

  // Strength labels
  if (score < 30) return { score, label: 'Weak', color: 'bg-chilli' };
  if (score < 60) return { score, label: 'Fair', color: 'bg-yellow-500' };
  if (score < 80) return { score, label: 'Good', color: 'bg-field' };
  return { score, label: 'Strong', color: 'bg-soil' };
}

export const PasswordStrength: React.FC<PasswordStrengthProps> = ({
  password,
  showRequirements = true,
}) => {
  const strength = calculatePasswordStrength(password);
  const metRequirements = requirements.filter((req) => req.test(password));
  const allMet = metRequirements.length === requirements.length;

  if (!password) return null;

  return (
    <div className="space-y-2">
      {/* Strength bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-stone-500 font-semibold">Password Strength</span>
          {strength.label && (
            <span
              className={`font-bold ${
                strength.label === 'Weak'
                  ? 'text-chilli'
                  : strength.label === 'Fair'
                  ? 'text-yellow-600'
                  : strength.label === 'Good'
                  ? 'text-field'
                  : 'text-soil'
              }`}
            >
              {strength.label}
            </span>
          )}
        </div>
        <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${strength.color} transition-all duration-300`}
            style={{ width: `${strength.score}%` }}
          />
        </div>
      </div>

      {/* Requirements checklist */}
      {showRequirements && (
        <div className="space-y-1.5 pt-1">
          {requirements.map((req, idx) => {
            const met = req.test(password);
            return (
              <div key={idx} className="flex items-start gap-2 text-xs">
                {met ? (
                  <Check className="h-4 w-4 text-soil flex-shrink-0 mt-0.5" />
                ) : (
                  <X className="h-4 w-4 text-stone-400 flex-shrink-0 mt-0.5" />
                )}
                <span
                  className={`leading-tight ${
                    met ? 'text-stone-700 font-semibold' : 'text-stone-500'
                  }`}
                >
                  {req.label}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Success message */}
      {allMet && (
        <div className="rounded-lg bg-soil/5 border border-soil/20 px-3 py-2 text-xs text-soil font-semibold flex items-center gap-2">
          <Check className="h-4 w-4" />
          Password meets all requirements
        </div>
      )}
    </div>
  );
};

export default PasswordStrength;
