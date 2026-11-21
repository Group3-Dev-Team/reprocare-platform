import { Moon, Sun } from 'lucide-react';
import { toggleTheme, useTheme } from '../hooks/useTheme';

export function ThemeToggle() {
  const dark = useTheme() === 'dark';
  const Icon = dark ? Sun : Moon;
  return (
    <button
      className="icon-btn theme-toggle"
      type="button"
      aria-label="Dark mode"
      aria-pressed={dark}
      title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      onClick={toggleTheme}
    >
      <Icon size={19} aria-hidden="true" />
    </button>
  );
}
