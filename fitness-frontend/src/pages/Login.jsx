import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch("https://ai-personal-trainer-xgko.onrender.com/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Invalid credentials");
        return;
      }

      localStorage.setItem("token", data.token);
      localStorage.setItem("user_id", data.user_id);
      localStorage.setItem("name", data.name);

      navigate("/dashboard");
    } catch (err) {
      setError("Something went wrong. Try again.");
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/30 via-neutral-900 to-purple-900/20 pointer-events-none" />
      <div className="absolute -left-14 -top-10 w-44 h-44 bg-blue-600/20 blur-3xl rounded-full" />
      <div className="absolute -right-16 bottom-0 w-60 h-60 bg-purple-600/10 blur-3xl rounded-full" />

      <div className="relative max-w-4xl mx-auto px-6 py-12 flex flex-col lg:flex-row gap-8 items-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 space-y-4"
        >
          <p className="text-sm uppercase tracking-[0.25em] text-blue-400">
            Welcome back
          </p>
          <h1 className="text-3xl sm:text-4xl font-bold leading-tight">
            Sign in to keep tracking meals, macros, and workouts.
          </h1>
          <p className="text-neutral-400">
            Log in to stay in the same dark, focused workspace you see in the
            Food planner. Your tokens and plans sync instantly.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800">
              <p className="text-blue-400 font-semibold text-sm">Fast entry</p>
              <p className="text-sm text-neutral-300">
                Jump straight to your dashboard and planner.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800">
              <p className="text-emerald-400 font-semibold text-sm">Secure</p>
              <p className="text-sm text-neutral-300">
                Protected login with token storage on device.
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
                <p className="text-sm text-neutral-400">Welcome back</p>
                <h2 className="text-2xl font-bold">Login</h2>
              </div>
              <span className="px-3 py-1 text-xs rounded-full bg-blue-600/20 text-blue-300 border border-blue-700/50">
                Secure
              </span>
            </div>

            {error && (
              <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-sm text-neutral-300">Email</label>
                <input
                  name="email"
                  type="email"
                  required
                  value={form.email}
                  onChange={handleChange}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-sm text-neutral-300">
                  Password
                </label>
                <input
                  name="password"
                  type="password"
                  required
                  value={form.password}
                  onChange={handleChange}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold shadow-lg hover:shadow-blue-700/30 transition transform hover:-translate-y-[1px]"
              >
                Login
              </button>
            </form>

            <p className="text-center text-sm text-neutral-400 mt-6">
              Don’t have an account?{" "}
              <Link to="/signup" className="text-blue-400 hover:underline">
                Sign up
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
