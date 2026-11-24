import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import BrowserSession from './BrowserSession';
import './styles.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserSession><App /></BrowserSession></React.StrictMode>);
