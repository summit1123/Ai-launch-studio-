import React from "react";
import { Rocket } from "lucide-react";

interface NavbarProps {
  currentView: "home" | "dashboard";
  onNavigate: (view: "home" | "dashboard") => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo" onClick={() => onNavigate("home")} style={{ cursor: 'pointer' }}>
          <Rocket className="logo-icon-svg" size={24} color="var(--accent)" />
          <span className="logo-text">AI Launch Studio</span>
        </div>
        
        <div className="navbar-links">
          <a href="#features" className="nav-link" onClick={(e) => {
            if (currentView !== "home") {
              onNavigate("home");
            }
          }}>Features</a>
          <a href="#vision" className="nav-link" onClick={(e) => {
            if (currentView !== "home") {
              onNavigate("home");
            }
          }}>Vision</a>
        </div>

        <div className="navbar-actions">
          {currentView === "home" ? (
            <button className="btn-primary-sm" onClick={() => onNavigate("dashboard")}>
              Launch Studio
            </button>
          ) : (
            <button className="btn-secondary-sm" onClick={() => onNavigate("home")}>
              Back to Home
            </button>
          )}
        </div>
      </div>
    </nav>
  );
};
