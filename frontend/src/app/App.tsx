import React from "react";
import { BrowserRouter } from "react-router-dom";
import { AppProviders } from "./providers";
import { AppRouter } from "./router";

export const App: React.FC = () => {
  return (
    <AppProviders>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </AppProviders>
  );
};

export default App;
