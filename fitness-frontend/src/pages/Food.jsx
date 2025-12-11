// FOOD PAGE - Aesthetic Dark Mode Version (JSX)
import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import dayjs from "dayjs";
import axios from "axios";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { fetchUserMacros } from "@/lib/api";
import NavBar from "@/components/NavBar";
import { useNavigate } from "react-router-dom";

export default function Food() {
  const navigate = useNavigate();
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [text, setText] = useState("");
  const [entries, setEntries] = useState([]);
  const [macroTargets, setMacroTargets] = useState(null);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [error, setError] = useState("");

  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");
  const API_URL = "https://ai-personal-trainer-xgko.onrender.com";

  const fetchEntries = async (selectedDate) => {
    try {
      const res = await axios.get(`${API_URL}/calories/view`, {
        params: { user_id: user_id, date: selectedDate },
      });
      console.log(res.data.calorie_data?.summary)
      setEntries(res.data.calorie_data?.plan_data || []);
    } catch (err) {
      console.error("Fetch error", err);
    }
  };

  const fetchMacroTargets = async (date) => {
    try {
      if (!user_id) return;
      const res = await fetchUserMacros(user_id, date);
      const m = res.user_data;
      setMacroTargets({
        calories: m.Goal_Calories || 2000,
        protein: m.Protein_g || 150,
        fat: m.Fats_g || 65,
        carbs: m.Carbs_g || 200,
      });
    } catch (err) {
      console.error("Fetch macros error", err);
    }
  };

  useEffect(() => {
    fetchEntries(date);
    fetchMacroTargets(date);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, user_id]);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setError("");
    if (!user_id) {
      setError("User not logged in.");
      return;
    }

    try {
      await fetch(`${API_URL}/calories/calculate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_id: user_id, date, text }),
      });

      setText("");
      await fetchEntries(date);
    } catch (err) {
      console.error("Submit error", err);
      setError("Failed to add meal. Check console for details.");
    }
  };

  const handleDeleteFood = async (mealType, foodName) => {
    setError("");
    if (!user_id) {
      setError("User not logged in.");
      return;
    }

    try {
      const payload = {
        user_id,
        date,
        meal_type: mealType,
        food_name: foodName,
      };

      const res = await fetch(`${API_URL}/calories/delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const result = await res.json();

      if (result.status === "success" || res.ok) {
        await fetchEntries(date);
      } else {
        setError(result.message || "Failed to delete food item.");
      }
    } catch (err) {
      console.error("Delete error", err);
      setError("Failed to delete food item. Check console for details.");
    }
  };

  // Calculate daily totals
  const dailyTotals = entries.reduce(
    (acc, meal) => {
      const summary = meal.meal_summary || {};
      acc.calories += summary.total_calories || 0;
      acc.protein += summary.total_protein || 0;
      acc.fat += summary.total_fat || 0;
      acc.carbs += summary.total_carb || 0;
      return acc;
    },
    { calories: 0, protein: 0, fat: 0, carbs: 0 }
  );


  // Macro Donut Chart Component
  const MacroDonutChart = ({ current, target, label, color, unit = "" }) => {
    const percentage = target > 0 ? Math.min((current / target) * 100, 100) : 0;
    const data = [
      { name: "Consumed", value: percentage },
      { name: "Remaining", value: Math.max(100 - percentage, 0) },
    ];

    const COLORS = [color, "#2a2a2a"];

    return (
      <div className="flex flex-col items-center">
        <div className="relative w-32 h-32">
          <ResponsiveContainer width={128} height={128}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={25}
                outerRadius={35}
                startAngle={90}
                endAngle={-270}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-xs font-bold text-white">{Math.round(percentage)}%</div>
            </div>
          </div>
        </div>
        <div className="mt-2 text-center">
          <div className="text-xs text-neutral-400">{label}</div>
          <div className="text-xs font-semibold text-white">
            {Math.round(current)} / {Math.round(target)}
            {unit}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <NavBar />
      <div className="flex flex-col p-4 gap-4">
        {/* Date Picker */}
        <div className="w-full flex justify-center mt-2">
          <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={`bg-neutral-900 text-white border-neutral-700 px-4 py-3 rounded-xl hover:bg-neutral-800 ${date !== dayjs().format("YYYY-MM-DD") ? "opacity-60" : ""
                  }`}
              >
                📅 {dayjs(date).format("DD MMM YYYY")}
              </Button>
            </PopoverTrigger>

            <PopoverContent className="p-2 bg-neutral-900 border-neutral-700 text-white rounded-xl">
              <Calendar
                mode="single"
                selected={new Date(date)}
                onSelect={(d) => {
                  if (d) {
                    setDate(dayjs(d).format("YYYY-MM-DD"));
                    setCalendarOpen(false);
                  }
                }}
                className="rounded-xl"
              />
            </PopoverContent>
          </Popover>
        </div>

        <div className="w-full flex justify-center px-4">
          <Button
            onClick={() => navigate("/food_suggest")}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-4 py-3"
          >
            Go to Food Suggestions
          </Button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="w-full max-w-2xl mx-auto p-3 bg-red-900/20 border border-red-700 rounded-xl text-red-400 text-sm text-center">
            {error}
          </div>
        )}

        {/* Macros Progress Donut Charts */}
        {macroTargets && (
          <div className="w-full flex justify-center">
            <div className="grid grid-cols-4 gap-4 p-4 bg-neutral-900 rounded-2xl border border-neutral-800 max-w-2xl">
              <MacroDonutChart
                current={dailyTotals.calories}
                target={macroTargets.calories}
                label="Calories"
                color="#3b82f6"
                unit=" kcal"
              />
              <MacroDonutChart
                current={dailyTotals.protein}
                target={macroTargets.protein}
                label="Protein"
                color="#10b981"
                unit="g"
              />
              <MacroDonutChart
                current={dailyTotals.fat}
                target={macroTargets.fat}
                label="Fat"
                color="#f59e0b"
                unit="g"
              />
              <MacroDonutChart
                current={dailyTotals.carbs}
                target={macroTargets.carbs}
                label="Carbs"
                color="#8b5cf6"
                unit="g"
              />
            </div>
          </div>
        )}

        {/* Entries Section */}
        <div className="grid gap-4 p-2 mt-2">
          {entries.length === 0 ? (
            <p className="text-center text-neutral-500">No entries for this date.</p>
          ) : (
            entries.map((meal, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800 shadow hover:shadow-lg transition-all"
              >
                {/* HEADER */}
                <div className="flex items-center justify-between mb-3">
                  <p className="text-lg font-semibold capitalize text-blue-400">
                    {meal.meal_type}
                  </p>
                  <span className="text-sm font-semibold text-white">
                    ({Math.round(meal.meal_summary?.total_calories || 0)} kcal)
                  </span>
                </div>

                {/* ITEM LIST */}
                <div className="space-y-3 mb-4">
                  {meal.items.map((food, fIdx) => {
                    const totalMacros = (food.proteins || 0) + (food.fats || 0) + (food.carbs || 0);
                    const proteinPercent = totalMacros > 0 ? ((food.proteins || 0) / totalMacros) * 100 : 0;
                    const fatPercent = totalMacros > 0 ? ((food.fats || 0) / totalMacros) * 100 : 0;
                    const carbsPercent = totalMacros > 0 ? ((food.carbs || 0) / totalMacros) * 100 : 0;

                    return (
                      <div
                        key={fIdx}
                        className="group relative flex justify-between items-center bg-neutral-800 p-3 rounded-xl hover:bg-neutral-700 transition-colors"
                      >
                        <div className="flex flex-col flex-1">
                          <span className="font-medium text-white text-sm">{food.food}</span>
                          {/* Macro Bar - shown on hover */}
                          {totalMacros > 0 && (
                            <div className="mt-1.5 h-1.5 w-full bg-neutral-700 rounded-full overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                              <div className="h-full flex">
                                {proteinPercent > 0 && (
                                  <div
                                    className="bg-green-500 transition-all"
                                    style={{ width: `${proteinPercent}%` }}
                                  />
                                )}
                                {fatPercent > 0 && (
                                  <div
                                    className="bg-amber-500 transition-all"
                                    style={{ width: `${fatPercent}%` }}
                                  />
                                )}
                                {carbsPercent > 0 && (
                                  <div
                                    className="bg-purple-500 transition-all"
                                    style={{ width: `${carbsPercent}%` }}
                                  />
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-white font-bold text-sm">
                            {Math.round(food.calories || 0)} kcal
                          </span>
                          <button
                            onClick={() => handleDeleteFood(meal.meal_type, food.food)}
                            className="px-2 py-1 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs transition-colors"
                            title="Delete food item"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* MACROS BOX */}
                <div className="grid grid-cols-5 gap-2 text-center bg-neutral-800 p-3 rounded-xl">
                  <div>
                    <p className="font-semibold text-white text-sm">{meal.meal_summary.total_calories}</p>
                    <p className="text-xs text-neutral-400">Cal</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{meal.meal_summary.total_protein}</p>
                    <p className="text-xs text-neutral-400">Protein</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{meal.meal_summary.total_fat}</p>
                    <p className="text-xs text-neutral-400">Fat</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{meal.meal_summary.total_carb}</p>
                    <p className="text-xs text-neutral-400">Carbs</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white text-sm">{meal.meal_summary.total_fiber}</p>
                    <p className="text-xs text-neutral-400">Fiber</p>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>

        {/* Chat Input */}
        <div className="w-full flex gap-2 p-3 border-t border-neutral-800 bg-neutral-900 rounded-t-2xl">
          <><input
            type="text"
            placeholder="Enter your meal in natural language..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSubmit();
                setText("");
              }
            }}
            className="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl p-3 text-white placeholder-neutral-500" /><button
              onClick={handleSubmit}
              className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-md"
            >
              Add
            </button></>
        </div>
      </div>
    </div>
  );
}
