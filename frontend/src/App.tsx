import { useState } from "react";
import { Home } from "./pages/Home";
import { Navbar } from "./components/Navbar";
import { ChatWorkspace } from "./pages/ChatWorkspace";

export default function App() {
  const [view, setView] = useState<"home" | "chat">("home");

  const handleStart = () => {
    setView("chat");
  };

  return (
    <>
      <Navbar currentView={view} onNavigate={setView} />
      {view === "home" && <Home onStart={handleStart} />}
      {view === "chat" && <ChatWorkspace />}
    </>
  );
}
