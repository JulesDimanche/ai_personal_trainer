import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useUser } from "../context/UserContext";

export default function Signup() {
  const { login } = useUser(); // after signup we log the user in
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(e) {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("https://ai-personal-trainer-xgko.onrender.com/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          password: formData.password,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        if (Array.isArray(data.detail)) {
          // FastAPI validation errors
          setError(data.detail[0].msg);
        } else {
          setError(data.detail || "Signup failed");
        }

        setLoading(false);
        return;
      }

      localStorage.setItem("token", data.token);
      localStorage.setItem("user_id", data.user_id);
      localStorage.setItem("name", data.name);

      login({
        token: data.token,
        user_id: data.user_id,
        email: formData.email,
      });

      navigate("/Planner");
    } catch (err) {
      setError("Server error");
    }

    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/30 via-neutral-900 to-purple-900/20 pointer-events-none" />
      <div className="absolute -left-10 -top-10 w-48 h-48 bg-blue-600/20 blur-3xl rounded-full" />
      <div className="absolute -right-10 bottom-0 w-64 h-64 bg-purple-600/10 blur-3xl rounded-full" />

      <div className="relative max-w-4xl mx-auto px-6 py-12 flex flex-col lg:flex-row gap-8 items-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 space-y-4"
        >
          <p className="text-sm uppercase tracking-[0.25em] text-blue-400">
            Welcome
          </p>
          <h1 className="text-3xl sm:text-4xl font-bold leading-tight">
            Create your account and keep your nutrition and training in sync.
          </h1>
          <p className="text-neutral-400">
            Sign up to unlock personalized plans, macro tracking, and your AI
            coach. Stay in the same sleek dark mode experience as the Food
            planner.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800">
              <p className="text-blue-400 font-semibold text-sm">Secure</p>
              <p className="text-sm text-neutral-300">
                Your data stays private with token-based auth.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800">
              <p className="text-emerald-400 font-semibold text-sm">Synced</p>
              <p className="text-sm text-neutral-300">
                Calories and macros flow seamlessly into your planner.
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="flex-1 w-full"
        >
          <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl shadow-xl p-8 backdrop-blur">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-sm text-neutral-400">New here?</p>
                <h2 className="text-2xl font-bold">Create Account</h2>
              </div>
              <span className="px-3 py-1 text-xs rounded-full bg-blue-600/20 text-blue-300 border border-blue-700/50">
                1 min setup
              </span>
            </div>

            {error && (
              <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-sm text-neutral-300">Name</label>
                <input
                  type="text"
                  name="name"
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  value={formData.name}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="block text-sm text-neutral-300">Email</label>
                <input
                  type="email"
                  name="email"
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="block text-sm text-neutral-300">
                  Password
                </label>
                <input
                  type="password"
                  name="password"
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  value={formData.password}
                  onChange={handleChange}
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold shadow-lg hover:shadow-blue-700/30 transition transform hover:-translate-y-[1px] disabled:opacity-60"
              >
                {loading ? "Creating account..." : "Sign Up"}
              </button>
            </form>

            <p className="text-center text-sm text-neutral-400 mt-6">
              Already have an account?{" "}
              <Link to="/login" className="text-blue-400 font-medium">
                Login
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
