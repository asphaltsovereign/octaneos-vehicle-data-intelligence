import React from 'react';
import { createRoot } from 'react-dom/client';
import Workshop from './Workshop';
import './styles.css';
import './workspace/theme.css';

const isLab = new URLSearchParams(location.search).get('lab') === '1';

async function demoEnabled() {
  if (!isLab) return false;
  try {
    const base = import.meta.env.VITE_API_BASE || location.origin;
    const response = await fetch(`${base}/api/config`);
    return response.ok && Boolean((await response.json()).demo);
  } catch { return false; }
}

void demoEnabled().then(async (showLab) => {
  const Legacy = showLab ? (await import('./Legacy')).default : null;
  createRoot(document.getElementById('root')!).render(
    <React.StrictMode>{Legacy ? <Legacy /> : <Workshop />}</React.StrictMode>,
  );
});
