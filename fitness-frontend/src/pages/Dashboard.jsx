import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { fetchFoodSummary, fetchWorkoutSummary, fetchUserMacros } from "@/lib/api";

export default function Dashboard() {
  const navigate = useNavigate();

  const [food, setFood] = useState(null);
  const [workout, setWorkout] = useState(null);
  const [macros, setMacros] = useState(null);
  const [loading, setLoading] = useState(true);

  const userId = localStorage.getItem("user_id");
  const today = new Date().toISOString().split("T")[0];

  useEffect(() => {
    if (!userId) return;

    const load = async () => {
      try {
        const [foodRes, workoutRes, macrosRes] = await Promise.all([
          fetchFoodSummary(userId, today),
          fetchWorkoutSummary(userId, today),
          fetchUserMacros(userId)
        ]);

        const f = foodRes.calorie_data?.summary || {};
        setFood({
          calories: f.total_calories || 0,
          items: f.total_items || 0,
        });

        const w = workoutRes.workout_data?.summary || {};
        setWorkout({
          calories: w.total_calories_burned || 0,
          duration: w.total_duration_minutes || 0,
        });

        const m = macrosRes.user_data;
        setMacros({
          targetCalories: m.Goal_Calories,
          protein: m.Macros?.Protein_g,
          carbs: m.Macros?.Carbs_g,
          fats: m.Macros?.Fats_g,
        });

        setLoading(false);
      } catch (e) {
        console.error(e);
      }
    };

    load();
  }, [userId, today]);

  if (loading)
    return (
      <div className="p-6 animate-pulse space-y-4">
        <div className="h-8 bg-neutral-800 rounded-lg" />
        <div className="h-24 bg-neutral-800 rounded-xl" />
        <div className="h-32 bg-neutral-800 rounded-xl" />
        <div className="h-32 bg-neutral-800 rounded-xl" />
      </div>
    );

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      {/* Greeting */}
      <h1 className="text-3xl font-bold tracking-tight mb-4">
        Welcome Back <span className="text-blue-400">👋</span>
      </h1>

      {/* Today Overview */}
      <Card className="p-6 rounded-2xl bg-neutral-900 shadow-lg border border-neutral-800">
        <h2 className="text-xl font-semibold mb-3">Today's Overview</h2>
        <div className="flex justify-between text-neutral-300 text-sm">
          <p>Calories Consumed</p>
          <p className="font-semibold text-white">{food.calories} kcal</p>
        </div>
        <div className="flex justify-between text-neutral-300 text-sm mt-1">
          <p>Workout Calories Burned</p>
          <p className="font-semibold text-white">{workout.calories}</p>
        </div>
      </Card>

      {/* Nutrition */}
      <Card className="p-6 rounded-2xl bg-gradient-to-br from-neutral-900 to-neutral-800 shadow-xl border border-neutral-800">
        <h2 className="text-xl font-semibold mb-4">Today's Nutrition</h2>

        <div className="mb-3 text-sm text-neutral-300 flex justify-between">
          <span>Target Calories</span>
          <span className="text-white font-semibold">{macros.targetCalories} kcal</span>
        </div>

        <div className="w-full h-3 bg-neutral-700 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-blue-500"
            style={{ width: `${(food.calories / macros.targetCalories) * 100}%` }}
          />
        </div>

        <Button
          className="w-full rounded-xl bg-blue-600 hover:bg-blue-700"
          onClick={() => navigate("/food")}
        >
          Add Food Entry
        </Button>
      </Card>

      {/* Workout */}
      <Card className="p-6 rounded-2xl bg-neutral-900 shadow-xl border border-neutral-800">
        <h2 className="text-xl font-semibold mb-4">Today's Workout</h2>

        <div className="flex justify-between text-neutral-300 text-sm">
          <span>Calories Burned</span>
          <span className="text-white font-semibold">{workout.calories}</span>
        </div>
        <div className="flex justify-between text-neutral-300 text-sm mt-1">
          <span>Duration</span>
          <span className="text-white font-semibold">{workout.duration} mins</span>
        </div>

        <Button
          className="w-full mt-4 rounded-xl bg-green-600 hover:bg-green-700"
          onClick={() => navigate("/workout")}
        >
          Start Workout
        </Button>
      </Card>

      {/* Quick Actions */}
      <Card className="p-6 rounded-2xl bg-neutral-900 shadow-xl border border-neutral-800">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>

        <div className="grid grid-cols-2 gap-3">
          <Button className="rounded-xl bg-neutral-800 hover:bg-neutral-700" onClick={() => navigate("/food-entry")}>Add Food</Button>
          <Button className="rounded-xl bg-neutral-800 hover:bg-neutral-700" onClick={() => navigate("/workouts")}>Workout Plan</Button>
          <Button className="rounded-xl bg-neutral-800 hover:bg-neutral-700" onClick={() => navigate("/macros")}>Macros</Button>
          <Button className="rounded-xl bg-neutral-800 hover:bg-neutral-700" onClick={() => navigate("/progress")}>Log Weight</Button>
        </div>
      </Card>
    </div>
  );
}
