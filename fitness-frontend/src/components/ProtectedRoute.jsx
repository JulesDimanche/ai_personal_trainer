import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children }) {
  // Check if user is logged in
  const token = localStorage.getItem("token");

  if (!token) {
    // Not authenticated → redirect to login
    return <Navigate to="/" replace />;
  }

  // Authenticated → show the requested page
  return children;
}
