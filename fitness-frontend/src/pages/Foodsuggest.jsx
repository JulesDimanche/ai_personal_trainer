import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import dayjs from "dayjs";
import axios from "axios";
import { fetchUserMacros } from "@/lib/api";
import NavBar from "@/components/NavBar";

export default function Foodsuggest() {
  const today = dayjs().format("YYYY-MM-DD");   // always today's date

  const [cuisine, setCuisine] = useState("South Indian");
  const [mealType, setMealType] = useState("lunch");

  const [macroTargets, setMacroTargets] = useState(null);
  const [consumedMacros, setConsumedMacros] = useState(null);

  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState(null);
  const [error, setError] = useState("");

  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");
  const API_URL = "http://localhost:8000";

  // --------------------
  // FETCH TODAY'S MACROS
  // --------------------
  const fetchConsumedMacros = async () => {
    try {
      const res = await axios.get(`${API_URL}/calories/view`, {
        params: { user_id, date: today },
      });
      const summary = res.data.calorie_data?.summary || {};

      setConsumedMacros({
        calories: summary.total_calories || 0,
        protein: summary.Macros?.total_protein || 0,
        fat: summary.Macros?.total_fat || 0,
        carbs: summary.Macros?.total_carbs || 0,
      });
    } catch (err) {
      console.error("Fetch consumed macros error:", err);
    }
  };

  // --------------------
  // FETCH MACRO TARGETS
  // --------------------
  const fetchTargets = async () => {
    try {
      const res = await fetchUserMacros(user_id,today);
      const m = res.user_data;

      setMacroTargets({
        calories: m.Goal_Calories || 2000,
        protein: m.Protein_g || 150,
        fat: m.Fats_g || 65,
        carbs: m.Carbs_g || 200,
      });
    } catch (err) {
      console.error("Fetch targets error:", err);
    }
  };

  useEffect(() => {
    if (user_id) {
      fetchConsumedMacros();
      fetchTargets(today);
    }
  }, [user_id]);

  // --------------------
  // GET SUGGESTIONS
  // --------------------
  const handleGetSuggestions = async () => {
    if (!macroTargets || !consumedMacros) {
      setError("Macros not loaded yet.");
      return;
    }

    setLoading(true);
    setError("");
    setSuggestions(null);

    try {
      const payload = {
        user_id,
        cuisine,
        meal_type: mealType,
        target_macros: macroTargets,
        consumed_macros: consumedMacros,
      };

      const res = await fetch(`${API_URL}/food/suggest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      setSuggestions(data);
    } catch (err) {
      console.error("Suggestion error:", err);
      setError("Failed to fetch suggestions.");
    } finally {
      setLoading(false);
    }
  };

  const cuisines = [
    "South Indian",
    "North Indian",
    "Chinese",
    "Italian",
    "Mexican",
    "Thai",
    "Japanese",
    "Mediterranean",
    "American",
  ];

  const mealTypes = ["breakfast", "lunch", "dinner", "snack"];

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <NavBar />
      <div className="p-4">
        <h1 className="text-2xl font-bold text-center mb-4">
          🍽️ Meal Suggestions
        </h1>

        {/* Macro overview box */}
        {macroTargets && consumedMacros && (
          <div className="max-w-xl mx-auto p-4 bg-neutral-900 border border-neutral-700 rounded-xl mb-4">
            <h2 className="text-lg font-bold mb-2 text-blue-400">Today's Macros</h2>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <p className="font-semibold">{consumedMacros.calories}</p>
                <p className="text-xs text-neutral-400">Cal</p>
              </div>
              <div>
                <p className="font-semibold">{consumedMacros.protein}g</p>
                <p className="text-xs text-neutral-400">Protein</p>
              </div>
              <div>
                <p className="font-semibold">{consumedMacros.fat}g</p>
                <p className="text-xs text-neutral-400">Fat</p>
              </div>
              <div>
                <p className="font-semibold">{consumedMacros.carbs}g</p>
                <p className="text-xs text-neutral-400">Carbs</p>
              </div>
            </div>
          </div>
        )}

        {/* Input controls */}
        <div className="max-w-xl mx-auto p-4 bg-neutral-900 border border-neutral-800 rounded-xl mb-4">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-neutral-400 text-sm mb-1 block">Cuisine</label>
              <select
                className="w-full bg-neutral-800 p-3 rounded-xl"
                value={cuisine}
                onChange={(e) => setCuisine(e.target.value)}
              >
                {cuisines.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-neutral-400 text-sm mb-1 block">Meal Type</label>
              <select
                className="w-full bg-neutral-800 p-3 rounded-xl capitalize"
                value={mealType}
                onChange={(e) => setMealType(e.target.value)}
              >
                {mealTypes.map((m) => (
                  <option key={m} className="capitalize">{m}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleGetSuggestions}
            disabled={loading}
            className="w-full bg-blue-600 py-3 rounded-xl hover:bg-blue-700"
          >
            {loading ? "Loading..." : "🔍 Get Suggestions"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <p className="text-center text-red-400 mb-4">{error}</p>
        )}

        {/* Suggestions Display */}
        {Array.isArray(suggestions) && suggestions.length > 0 && (
          <div className="max-w-xl mx-auto space-y-4">
            {suggestions.map((item, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 bg-neutral-900 border border-neutral-800 rounded-xl"
              >
                <h2 className="text-lg font-bold text-blue-400 mb-2">
                  Suggestion {idx + 1}
                </h2>

                {/* Components list */}
                <div className="space-y-3 mb-4">
                  {item.components.map((comp, cIdx) => (
                    <div
                      key={cIdx}
                      className="bg-neutral-800 p-3 rounded-xl"
                    >
                      <div className="flex justify-between mb-1">
                        <p className="font-semibold text-white">
                          {comp.food_name}
                        </p>
                        <p className="text-xs text-blue-400">
                          {comp.calories} kcal
                        </p>
                      </div>

                      <p className="text-xs text-neutral-400 mb-2">
                        {comp.quantity}
                      </p>

                      <div className="flex gap-4 text-xs">
                        <span className="text-green-400">P: {comp.protein}g</span>
                        <span className="text-yellow-400">F: {comp.fat}g</span>
                        <span className="text-purple-400">C: {comp.carbs}g</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Total macros for this suggestion */}
                <div className="grid grid-cols-4 gap-4 bg-neutral-800 p-3 rounded-xl text-center">
                  <div>
                    <p className="font-bold">{item.total_macros.calories}</p>
                    <p className="text-xs text-neutral-400">Cal</p>
                  </div>

                  <div>
                    <p className="font-bold">{item.total_macros.protein}g</p>
                    <p className="text-xs text-neutral-400">Protein</p>
                  </div>

                  <div>
                    <p className="font-bold">{item.total_macros.fat}g</p>
                    <p className="text-xs text-neutral-400">Fat</p>
                  </div>

                  <div>
                    <p className="font-bold">{item.total_macros.carbs}g</p>
                    <p className="text-xs text-neutral-400">Carbs</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
