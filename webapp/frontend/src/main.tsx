import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App, { AppStateProvider } from './App.tsx'
import { applyQuoteColorMode } from './lib/quoteColor'

// 首屏前应用涨跌配色（绿涨红跌 / 红涨绿跌），避免变量闪烁
applyQuoteColorMode()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AppStateProvider>
        <App />
      </AppStateProvider>
    </BrowserRouter>
  </StrictMode>,
)
