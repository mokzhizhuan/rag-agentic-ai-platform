import React from 'react';
import { createRoot } from 'react-dom/client';
import Keycloak from 'keycloak-js';
import App from './App';
import './style.css';

const keycloak = new Keycloak({
  url: 'http://localhost:8180', realm: 'rag-app', clientId: 'rag-frontend'
});

keycloak.init({ onLoad: 'login-required', pkceMethod: 'S256', checkLoginIframe: false })
  .then(() => {
    createRoot(document.getElementById('root')!).render(
      <React.StrictMode><App keycloak={keycloak} /></React.StrictMode>
    );
  }).catch((error) => {
    console.error('Keycloak authentication failed', error);
    createRoot(document.getElementById('root')!).render(
      <div style={{padding:32}}>Cannot connect to Keycloak. Check whether http://localhost:8180 is running, then refresh.</div>
    );
  });
