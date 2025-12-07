import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Avatar } from "@/components/ui/avatar";
import {
  fetchUserProfile,
  fetchUserMacros,
  fetchWorkoutSummary,
  fetchFoodSummary,
} from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import NavBar from "@/components/NavBar";

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState("personal");
  const [user, setUser] = useState(null);
  const [macros, setMacros] = useState(null);
  const [workout, setWorkout] = useState(null);
  const [foodSummary, setFoodSummary] = useState(null);

  const userId = localStorage.getItem("user_id");
  const today = new Date().toISOString().split("T")[0];
  const navigate = useNavigate();

  useEffect(() => {
    if (!userId) return;
    const fetchData = async () => {
      try {
        const [userData, macrosData, workoutData, foodData] = await Promise.all([
          fetchUserProfile(userId),
          fetchUserMacros(userId),
          fetchWorkoutSummary(userId, today),
          fetchFoodSummary(userId, today),
        ]);

        const u = userData.user_data;
        setUser({
          name: u.name,
          age: u.age,
          gender: u.gender,
          height: u.height_cm,
          weight: u.weight_kg,
          activityLevel: u.activity_level,
          goal: u.goal,
          targetWeeks: u.target_weeks,
          targetWeight: u.target_weight_kg,
        });

        const m = macrosData.user_data;
        setMacros({
          bmr: m.BMR,
          tdee: m.TDEE,
          goalCalories: m.Goal_Calories,
          protein: m.Macros?.Protein_g,
          fat: m.Macros?.Fats_g,
          carbs: m.Macros?.Carbs_g,
          fiber: m.Macros?.Fiber_g,
          goalType: m.goal_type,
          totalWeeks: m.total_weeks,
          startWeight: m.start_weight_kg,
          targetWeight: m.target_weight_kg,
          targetChange: m.Target_Change,
          weeklyPlan: m.Weekly_Plan,
          createdAt: m.created_at,
          updatedAt: m.updated_at,
        });

        const w = workoutData.workout_data?.summary || {};
        setWorkout({
          totalCalories: w.total_calories_burned || 0,
          totalDuration: w.total_duration_minutes || 0,
          totalExercises: w.total_exercises || 0,
          totalSets: w.total_sets || 0,
          totalReps: w.total_reps || 0,
        });

        const f = foodData.calorie_data?.summary || {};
        setFoodSummary({
          totalCalories: f.total_calories || 0,
          totalItems: f.total_items || 0,
        });
      } catch (err) {
        console.error("Error fetching profile data:", err);
      }
    };

    fetchData();
  }, [userId, today]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("name");
    navigate("/login");
  };

  if (!user || !macros) {
    return (
      <div className="min-h-screen bg-neutral-950 text-white flex items-center justify-center">
        <p className="text-neutral-400">Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white relative overflow-hidden">
      <NavBar />
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/30 via-neutral-900 to-purple-900/20 pointer-events-none" />
      <div className="absolute -left-14 -top-10 w-44 h-44 bg-blue-600/20 blur-3xl rounded-full" />
      <div className="absolute -right-16 bottom-0 w-60 h-60 bg-purple-600/10 blur-3xl rounded-full" />

      <div className="relative max-w-6xl mx-auto px-6 py-10 space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row md:items-center gap-4 bg-neutral-900/80 border border-neutral-800 rounded-2xl p-6 backdrop-blur"
        >
          <div className="flex items-center gap-4">
            <Avatar src={user.profilePhoto} alt={user.name} className="w-16 h-16" />
            <div>
              <p className="text-sm uppercase tracking-[0.25em] text-blue-400">
                Profile
              </p>
              <h2 className="text-2xl font-bold">{user.name}</h2>
              <p className="text-neutral-400">
                {user.age} yrs • {user.gender} • {user.height} cm • {user.weight} kg
              </p>
            </div>
          </div>
          <div className="flex-1 flex flex-wrap gap-3 justify-end">
            <div className="px-3 py-2 rounded-xl bg-neutral-800 border border-neutral-700 text-sm text-neutral-200">
              Goal: {user.goal}
            </div>
            <div className="px-3 py-2 rounded-xl bg-neutral-800 border border-neutral-700 text-sm text-neutral-200">
              Activity: {user.activityLevel}
            </div>
            <div className="px-3 py-2 rounded-xl bg-neutral-800 border border-neutral-700 text-sm text-neutral-200">
              Target Weeks: {user.targetWeeks}
            </div>
          </div>
        </motion.div>

        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="space-y-4"
        >
          <TabsList className="bg-neutral-900 border border-neutral-800">
            <TabsTrigger value="personal">Personal</TabsTrigger>
            <TabsTrigger value="macros">Macros & Goals</TabsTrigger>
            <TabsTrigger value="progress">Progress</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="personal">
            <Card className="bg-neutral-900/80 border border-neutral-800 text-white p-6 space-y-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-neutral-200">
                <p><span className="text-neutral-400">Name:</span> {user.name}</p>
                <p><span className="text-neutral-400">Age:</span> {user.age}</p>
                <p><span className="text-neutral-400">Gender:</span> {user.gender}</p>
                <p><span className="text-neutral-400">Height:</span> {user.height} cm</p>
                <p><span className="text-neutral-400">Weight:</span> {user.weight} kg</p>
                <p><span className="text-neutral-400">Activity:</span> {user.activityLevel}</p>
                <p><span className="text-neutral-400">Goal:</span> {user.goal}</p>
                <p><span className="text-neutral-400">Target Weeks:</span> {user.targetWeeks}</p>
                <p><span className="text-neutral-400">Target Weight:</span> {user.targetWeight || "—"}</p>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="macros">
            <Card className="bg-neutral-900/80 border border-neutral-800 text-white p-6 space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div className="p-3 rounded-xl bg-neutral-800 border border-neutral-700">
                  <p className="text-neutral-400 text-xs">Calories</p>
                  <p className="text-lg font-semibold">{Math.round(macros.goalCalories || 0)} kcal</p>
                </div>
                <div className="p-3 rounded-xl bg-neutral-800 border border-neutral-700">
                  <p className="text-neutral-400 text-xs">Protein</p>
                  <p className="text-lg font-semibold">{Math.round(macros.protein || 0)} g</p>
                </div>
                <div className="p-3 rounded-xl bg-neutral-800 border border-neutral-700">
                  <p className="text-neutral-400 text-xs">Carbs</p>
                  <p className="text-lg font-semibold">{Math.round(macros.carbs || 0)} g</p>
                </div>
                <div className="p-3 rounded-xl bg-neutral-800 border border-neutral-700">
                  <p className="text-neutral-400 text-xs">Fat</p>
                  <p className="text-lg font-semibold">{Math.round(macros.fat || 0)} g</p>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-neutral-200">
                <p><span className="text-neutral-400">BMR:</span> {Math.round(macros.bmr || 0)}</p>
                <p><span className="text-neutral-400">TDEE:</span> {Math.round(macros.tdee || 0)}</p>
                <p><span className="text-neutral-400">Goal Type:</span> {macros.goalType || "—"}</p>
                <p><span className="text-neutral-400">Start Weight:</span> {macros.startWeight || "—"} kg</p>
                <p><span className="text-neutral-400">Target Weight:</span> {macros.targetWeight || "—"} kg</p>
                <p><span className="text-neutral-400">Target Change:</span> {macros.targetChange || "—"}</p>
                <p><span className="text-neutral-400">Weeks:</span> {macros.totalWeeks || "—"}</p>
                <p><span className="text-neutral-400">Updated:</span> {macros.updatedAt ? new Date(macros.updatedAt).toLocaleDateString() : "—"}</p>
              </div>
              <div className="flex gap-3">
                <Button
                  className="bg-gradient-to-r from-blue-600 to-purple-600 text-white border-0 hover:shadow-blue-700/30"
                  onClick={() => navigate("/planner")}
                >
                  Regenerate Macros
                </Button>
                <Button variant="outline" className="border-neutral-700 text-neutral-100 hover:bg-neutral-800">
                  View Weekly Plan
                </Button>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="progress">
            <Card className="bg-neutral-900/80 border border-neutral-800 text-white p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-2xl bg-neutral-800 border border-neutral-700">
                  <p className="text-sm text-neutral-400">Today's calories</p>
                  <p className="text-2xl font-semibold">{Math.round(foodSummary?.totalCalories || 0)} kcal</p>
                  <p className="text-xs text-neutral-500 mt-1">
                    Items logged: {foodSummary?.totalItems || 0}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-neutral-800 border border-neutral-700">
                  <p className="text-sm text-neutral-400">Workout summary</p>
                  <p className="text-2xl font-semibold">{workout?.totalExercises || 0} exercises</p>
                  <p className="text-xs text-neutral-500 mt-1">
                    Duration: {Math.round(workout?.totalDuration || 0)} mins · Calories: {Math.round(workout?.totalCalories || 0)}
                  </p>
                </div>
              </div>
              <div className="p-4 rounded-2xl bg-neutral-800 border border-neutral-700 text-sm text-neutral-300">
                Future: weight history, BMI trend, target progress charts.
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="settings">
            <Card className="bg-neutral-900/80 border border-neutral-800 text-white p-6 space-y-3">
              <p className="text-sm text-neutral-300">Theme toggle, notifications, and privacy controls coming soon.</p>
              <Button
                variant="destructive"
                className="bg-red-600 hover:bg-red-700 text-white"
                onClick={handleLogout}
              >
                Logout
              </Button>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
