import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

export default function NavBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const userName = localStorage.getItem("name") || "User";

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("name");
    navigate("/login");
  };

  const isActive = (path) => {
    return location.pathname === path;
  };

  const navLinks = [
    { path: "/dashboard", label: "Dashboard", icon: "🏠" },
    { path: "/food", label: "Food", icon: "🍽️" },
    { path: "/workout", label: "Workout", icon: "💪" },
    { path: "/progress", label: "Progress", icon: "📊" },
    { path: "/chat", label: "Chat", icon: "💬" },
    { path: "/profile", label: "Profile", icon: "👤" },
  ];

  return (
    <nav className="w-full bg-neutral-900 border-b border-neutral-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <Link to="/dashboard" className="flex items-center space-x-2">
            <span className="text-xl font-bold text-white">Fitness Tracker</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map((link) => (
              <Link key={link.path} to={link.path}>
                <Button
                  variant="ghost"
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    isActive(link.path)
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "text-neutral-300 hover:bg-neutral-800 hover:text-white"
                  }`}
                >
                  <span className="mr-2">{link.icon}</span>
                  {link.label}
                </Button>
              </Link>
            ))}
          </div>

          {/* User Info & Logout */}
          <div className="flex items-center space-x-4">
            <span className="hidden sm:block text-sm text-neutral-400">
              {userName}
            </span>
            <Button
              onClick={handleLogout}
              className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-medium"
            >
              Logout
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden pb-4">
          <div className="flex flex-wrap gap-2">
            {navLinks.map((link) => (
              <Link key={link.path} to={link.path} className="flex-1 min-w-[100px]">
                <Button
                  variant="ghost"
                  className={`w-full px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                    isActive(link.path)
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "text-neutral-300 hover:bg-neutral-800 hover:text-white"
                  }`}
                >
                  <span className="mr-1">{link.icon}</span>
                  {link.label}
                </Button>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}

