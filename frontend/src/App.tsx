import { useState } from "react";
import { Dashboard } from "./pages/Dashboard";
import { Home } from "./pages/Home";
import { Navbar } from "./components/Navbar";
import { ChatWorkspace } from "./pages/ChatWorkspace";
import type { LaunchBrief } from "./types";
import { cloneBrief } from "./data/briefTemplates";

export default function App() {
  const [view, setView] = useState<"home" | "dashboard" | "chat">("home");
  const [prefillBrief, setPrefillBrief] = useState<LaunchBrief | null>(null);

  const handleStart = (brief?: LaunchBrief) => {
    setPrefillBrief(brief ? cloneBrief(brief) : null);
    setView("chat");
  };

  return (
    <>
      <Navbar currentView={view} onNavigate={setView} />
      {view === "home" && <Home onStart={handleStart} />}
      {view === "dashboard" && <Dashboard prefillBrief={prefillBrief} />}
      {view === "chat" && <ChatWorkspace />}
    </>
  );
}
