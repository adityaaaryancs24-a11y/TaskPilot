import { useState, useEffect } from "react";

export function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("theme");
      if (stored) return stored as "light" | "dark";
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.style.setProperty("--bg-primary", "#1A1A1A");
      root.style.setProperty("--bg-surface", "#2D2D2D");
      root.style.setProperty("--text-primary", "#FFFFFF");
      root.style.setProperty("--text-secondary", "#B0A8A0");
      root.style.setProperty("--border-light", "#3D3D3D");
      root.style.setProperty("--bg-sidebar", "#1A1A1A");
    } else {
      root.classList.remove("dark");
      root.style.setProperty("--bg-primary", "#F6F2E9");
      root.style.setProperty("--bg-surface", "#FFFDF8");
      root.style.setProperty("--text-primary", "#111111");
      root.style.setProperty("--text-secondary", "#7A7A7A");
      root.style.setProperty("--border-light", "#E9E4D8");
      root.style.setProperty("--bg-sidebar", "#0D0D0D");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  return { theme, setTheme, toggleTheme: () => setTheme(theme === "light" ? "dark" : "light") };
}
