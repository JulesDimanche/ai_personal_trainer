import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

export default function Planner() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    age: "",
    gender: "male",
    weight_kg: "",
    height_cm: "",
    activity_level: "moderate",
    goal: "maintain",
    target_weeks: 8,
    target_weight_kg: "",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");
  const name = localStorage.getItem("name");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!user_id) {
      setError("User not logged in.");
      return;
    }

    const payload = {
      user_id,
      name,
      age: Number(form.age),
      gender: form.gender,
      weight_kg: Number(form.weight_kg),
      height_cm: Number(form.height_cm),
      activity_level: form.activity_level,
      goal: form.goal,
      target_weeks: Number(form.target_weeks),
      target_weight_kg: form.target_weight_kg ? Number(form.target_weight_kg) : null,
    };

    try {
      const res = await fetch("http://localhost:8000/macros/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        if (Array.isArray(data.detail)) {
          setError(data.detail[0].msg);
        } else {
          setError(data.detail || "Failed to save metrics");
        }
        return;
      }

      setSuccess("Macro plan created successfully!");
      navigate("/dashboard");
    } catch (err) {
      setError("Server error. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/30 via-neutral-900 to-purple-900/20 pointer-events-none" />
      <div className="absolute -left-14 -top-10 w-44 h-44 bg-blue-600/20 blur-3xl rounded-full" />
      <div className="absolute -right-16 bottom-0 w-60 h-60 bg-purple-600/10 blur-3xl rounded-full" />

      <div className="relative max-w-5xl mx-auto px-6 py-12 flex flex-col lg:flex-row gap-8 items-start">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 space-y-4"
        >
          <p className="text-sm uppercase tracking-[0.25em] text-blue-400">
            Planner
          </p>
          <h1 className="text-3xl sm:text-4xl font-bold leading-tight">
            Dial in your metrics to generate a tailored macro plan.
          </h1>
          <p className="text-neutral-400">
            Keep the same dark, focused workspace as the Food page. Your age,
            weight, goals, and activity level power the macro generator.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800">
              <p className="text-blue-400 font-semibold text-sm">AI macros</p>
              <p className="text-sm text-neutral-300">
                Uses your inputs to set calories and macros automatically.
              </p>
            </div>
            <div className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800">
              <p className="text-emerald-400 font-semibold text-sm">Synced</p>
              <p className="text-sm text-neutral-300">
                Plans feed straight into Food and Workout dashboards.
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
          <div className="bg-neutral-900/80 border border-neutral-800 rounded-2xl shadow-xl p-8 backdrop-blur space-y-4">
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-sm text-neutral-400">Your inputs</p>
                <h2 className="text-2xl font-bold">Setup Metrics</h2>
              </div>
              <span className="px-3 py-1 text-xs rounded-full bg-blue-600/20 text-blue-300 border border-blue-700/50">
                2 min
              </span>
            </div>

            {error && (
              <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                {error}
              </div>
            )}
            {success && (
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                {success}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Age</label>
                  <input
                    type="number"
                    name="age"
                    value={form.age}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Gender</label>
                  <select
                    name="gender"
                    value={form.gender}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Weight (kg)</label>
                  <input
                    type="number"
                    name="weight_kg"
                    value={form.weight_kg}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Height (cm)</label>
                  <input
                    type="number"
                    name="height_cm"
                    value={form.height_cm}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Activity level</label>
                  <select
                    name="activity_level"
                    value={form.activity_level}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="low">Low</option>
                    <option value="moderate">Moderate</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Goal</label>
                  <select
                    name="goal"
                    value={form.goal}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="maintain">Maintain Weight</option>
                    <option value="lose">Lose Weight</option>
                    <option value="gain">Gain Weight</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">Target weeks</label>
                  <input
                    type="number"
                    name="target_weeks"
                    value={form.target_weeks}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-sm text-neutral-300">
                    Target weight (kg) — optional
                  </label>
                  <input
                    type="number"
                    name="target_weight_kg"
                    value={form.target_weight_kg}
                    onChange={handleChange}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold shadow-lg hover:shadow-blue-700/30 transition transform hover:-translate-y-[1px]"
              >
                Save metrics
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
