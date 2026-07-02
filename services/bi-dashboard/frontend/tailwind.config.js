/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary:        'var(--color-primary)',
        secondary:      'var(--color-secondary)',
        success:        'var(--color-success)',
        warning:        'var(--color-warning)',
        danger:         'var(--color-danger)',
        'neutral-dark': 'var(--color-neutral-dark)',
        'neutral-light':'var(--color-neutral-light)',
        background:     'var(--color-background)',
        surface:        'var(--color-surface)',
        border:         'var(--color-border)',
        'row-alt':      'var(--color-row-alt)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      fontSize: {
        'h1':      ['20px', { lineHeight: '28px', fontWeight: '700' }],
        'h2':      ['15px', { lineHeight: '22px', fontWeight: '600' }],
        'h3':      ['13px', { lineHeight: '18px', fontWeight: '600' }],
        'body':    ['12px', { lineHeight: '18px', fontWeight: '400' }],
        'caption': ['11px', { lineHeight: '16px', fontWeight: '500' }],
        'kpi':     ['26px', { lineHeight: '1',    fontWeight: '700' }],
      },
      spacing: {
        'xs':  '4px',
        'sm':  '8px',
        'md':  '16px',
        'lg':  '24px',
        'xl':  '32px',
        '2xl': '48px',
      },
      borderRadius: {
        'sm':   '4px',
        'md':   '6px',
        'lg':   '8px',
        'full': '9999px',
      },
      boxShadow: {
        'sm': '0 1px 3px rgba(0,0,0,0.06)',
        'md': '0 4px 12px rgba(0,0,0,0.10)',
        'lg': '0 8px 24px rgba(0,0,0,0.14)',
      },
      width: {
        'sidebar': '240px',
        'sidebar-icons': '64px',
      },
    },
  },
  plugins: [],
};
