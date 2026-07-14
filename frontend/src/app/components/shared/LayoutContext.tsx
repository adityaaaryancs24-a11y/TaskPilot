import { createContext, useContext, useState, ReactNode } from "react";

type LayoutContextType = {
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
  toggleSidebar: () => void;
  panelOpen: boolean;
  setPanelOpen: (v: boolean) => void;
  togglePanel: () => void;
};

const LayoutContext = createContext<LayoutContextType | null>(null);

export function LayoutProvider({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [panelOpen, setPanelOpen] = useState(true);

  return (
    <LayoutContext.Provider value={{
      sidebarOpen,
      setSidebarOpen,
      toggleSidebar: () => setSidebarOpen(v => !v),
      panelOpen,
      setPanelOpen,
      togglePanel: () => setPanelOpen(v => !v),
    }}>
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayout() {
  const ctx = useContext(LayoutContext);
  if (!ctx) throw new Error("useLayout must be used inside LayoutProvider");
  return ctx;
}
