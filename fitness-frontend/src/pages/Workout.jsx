"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import dayjs from "dayjs";
import axios from "axios";

export default function Workout() {
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [text, setText] = useState("");
  const [entries, setEntries] = useState({ workouts: [], summary: null });
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ reps: [], weights: [] });
  const [deleteTarget, setDeleteTarget] = useState(null);

  // NEW: plans dropdown state
  const [plans, setPlans] = useState([]); // list of plan objects or names
  const [selectedPlan, setSelectedPlan] = useState(""); // plan name or "new"
  const [newPlanName, setNewPlanName] = useState("");
  const [calendarOpen, setCalendarOpen] = useState(false);

  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");
  const API_URL = "http://localhost:8000";

  const fetchEntries = async (selectedDate) => {
    try {
      const res = await axios.get(`${API_URL}/workout/view`, {
        params: { user_id: user_id, date: selectedDate }
      });

      console.log("Fetched entries:", res.data);

      // Normalize multiple possible response shapes into { workouts: [], summary: {} }
      const payload = res.data || {};
      let workouts = [];
      let summary = null;

      // Common shape: { workout_data: [ ... ], summary: {...} }
      if (Array.isArray(payload.workout_data)) {
        workouts = payload.workout_data;
        summary = payload.summary || null;
      } else if (payload.workout_data && typeof payload.workout_data === "object") {
        const wd = payload.workout_data;
        // shape: { plan_data: [...], summary: {...} }
        if (Array.isArray(wd.plan_data)) {
          workouts = wd.plan_data;
          summary = wd.summary || payload.summary || null;
        }
        // nested shape: { workout_data: { plan_data: [...], summary: {...} } }
        else if (wd.workout_data && typeof wd.workout_data === "object") {
          const inner = wd.workout_data;
          if (Array.isArray(inner)) {
            workouts = inner;
            summary = wd.summary || payload.summary || null;
          } else if (Array.isArray(inner.plan_data)) {
            workouts = inner.plan_data;
            summary = inner.summary || wd.summary || payload.summary || null;
          }
        }
      } else if (Array.isArray(payload)) {
        workouts = payload;
      }

      setEntries({ workouts, summary });

      // If response includes plan_name, auto-select it (optional)
      if (payload.plan_name && !selectedPlan) {
        setSelectedPlan(payload.plan_name);
      }
    } catch (err) {
      console.error("Fetch error", err);
    }
  };

  // NEW: fetch list of plans for the user
  const fetchPlans = async () => {
    if (!user_id) {
      console.log("❌ No user_id found.");
      return;
    }

    try {
      const res = await axios.get(`${API_URL}/workout/plan_view`, {
        params: { user_id, list_only: true }
      });
      let planList = [];

      if (Array.isArray(res.data?.plans)) {
        planList = res.data.plans;
      }
      setPlans(planList);

    } catch (err) {
      console.error("ERROR WHILE FETCHING PLANS", err);
    }
  };


  useEffect(() => {
    fetchEntries(date);
    fetchPlans();
    // Reset selected plan when date changes
    setSelectedPlan("");
    setNewPlanName("");
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
      await fetch(`${API_URL}/workout/calculate`, {
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
    }
  };

  // NEW: Save today's workout to server with selected plan
  // Replace your old handleSaveWorkout with this
  const handleSaveWorkout = async () => {
    setError("");
    if (!user_id) {
      setError("User not logged in.");
      return;
    }
    // assemble entries exactly as currently shown in UI
    const frontendEntries = entries.workouts.map((w) => ({
      exercise_name: w.exercise_name,
      muscle_group: w.muscle_group || "Other",
      reps: Array.isArray(w.reps) ? w.reps : (w.reps != null ? [w.reps] : []),
      weight: w.weight || null,
      sets: w.sets || (Array.isArray(w.reps) ? w.reps.length : 0),
      duration_minutes: w.duration_minutes || 0,
      calories_burned: w.calories_burned || 0
    }));

    const payload = {
      user_id,
      date,
      plan_name: selectedPlan === "new" ? (newPlanName.trim() || "Unnamed Plan") : selectedPlan,
      entries: frontendEntries
    };

    try {
      // call single endpoint that updates plan and daily log
      const res = await axios.post(`${API_URL}/workout/plan_save_and_upsert`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      console.log("Save all response:", res.data);

      if (res.data?.status === "success") {
        // refresh plan list and today's entries to reflect what's stored
        await fetchPlans();
        await fetchEntries(date);

        // if we created a new plan, select it
        if (selectedPlan === "new") {
          setSelectedPlan(payload.plan_name);
          setNewPlanName("");
        }
      } else {
        setError(res.data?.error || "Failed to save plan and daily workout.");
      }
    } catch (err) {
      console.error("Save error", err);
      setError("Failed to save. Check console for details.");
    }
  };

  // Group workouts by muscle group and keep the original index for edit/delete
  const groupedWorkouts = entries.workouts.reduce((acc, workout, idx) => {
    const muscleGroup = workout.muscle_group || "Other";
    if (!acc[muscleGroup]) {
      acc[muscleGroup] = [];
    }
    acc[muscleGroup].push({ ...workout, _idx: idx });
    return acc;
  }, {});

  // Calculate total sets per muscle group
  const getTotalSets = (workouts) => {
    return workouts.reduce((total, w) => total + (w.sets || 0), 0);
  };

  // Workout calories goal (default to 600, or can be fetched from user profile)
  const workoutCaloriesGoal = 600;
  const caloriesBurned = entries.summary?.total_calories_burned || 0;
  const durationMinutes = entries.summary?.total_duration_minutes || 0;

  const startEdit = (workout) => {
    const repsList = Array.isArray(workout.reps)
      ? workout.reps.filter((r) => r !== null && r !== undefined && r !== "")
      : workout.reps != null && workout.reps !== ""
        ? [workout.reps]
        : [];
    const weightsList = Array.isArray(workout.weight)
      ? workout.weight
      : repsList.map(() => workout.weight ?? 0);
    setEditingId(workout._idx);
    setEditForm({
      reps: repsList.map((r) => String(r)),
      weights: weightsList.map((w) => (w ?? 0).toString()),
    });
    setDeleteTarget(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm({ reps: [], weights: [] });
  };

  const handleSaveEdit = async (workout) => {
    setError("");
    if (!user_id) {
      setError("User not logged in.");
      return;
    }
    try {
      const payload = {
      user_id,
      date,
      exercise_name: workout.exercise_name,
      reps: editForm.reps.map((r) => Number(r)),
      weight: editForm.weights.map((w) => Number(w || 0)),
    };
    console.log("📤 Sending edit payload:", payload);
      await fetch(`${API_URL}/workout/edit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload)
      });
      setEditingId(null);
      await fetchEntries(date);
    } catch (err) {
      console.error("Edit error", err);
      setError("Failed to save edits.");
    }
  };

  const triggerDelete = (workout) => {
    setDeleteTarget(workout._idx);
    setEditingId(null);
  };

  const confirmDelete = async (workout,index) => {
    setError("");
    if (!user_id) {
      setError("User not logged in.");
      return;
    }
        try {
          console.log("📋 Workout object being deleted:", workout);
    const payload = {
      user_id,
      date,
      exercise_name: workout.exercise_name,
      set_index:index,
    };
    console.log("🗑️ Sending delete payload:", payload);
    
      await fetch(`${API_URL}/workout/delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      setDeleteTarget(null);
      await fetchEntries(date);
    } catch (err) {
      console.error("Delete error", err);
      setError("Failed to delete exercise.");
    }
  };

  return (
    <div className="flex flex-col h-screen bg-neutral-950 text-white">
      {/* Date Picker - Fixed at top */}
      <div className="w-full flex justify-center p-4 pt-4 pb-2">
        <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={`bg-neutral-900 text-white border-neutral-700 px-4 py-3 rounded-xl hover:bg-neutral-800 ${
                date !== dayjs().format("YYYY-MM-DD") ? "opacity-60" : ""
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

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-y-auto px-4">
        {/* Error Display */}
        {error && (
          <div className="w-full max-w-2xl mx-auto p-3 bg-red-900/20 border border-red-700 rounded-xl text-red-400 text-sm text-center mb-4">
            {error}
          </div>
        )}

        {/* Sticky Container for Progress Bar and Plan Selector */}
        <div className="sticky top-0 z-10 bg-neutral-950 pb-4 -mx-4 px-4">
        {/* Activity/Progress Bar */}
        <div className="w-full max-w-2xl mx-auto p-4 bg-neutral-900 rounded-2xl border border-neutral-800 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-neutral-300">
              Calories Burned: <span className="text-white font-semibold">{Math.round(caloriesBurned)}</span> / <span className="text-neutral-400">{workoutCaloriesGoal} Goal</span>
            </span>
            <span className="text-sm text-neutral-400">
              {Math.round(durationMinutes)} minutes
            </span>
          </div>
          <div className="w-full h-4 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-teal-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${Math.min((caloriesBurned / workoutCaloriesGoal) * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Plan selector + Save */}
        <div className="w-full max-w-2xl mx-auto bg-neutral-900 rounded-2xl border border-neutral-800 p-4 flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <label className="text-sm text-neutral-300 w-24">Plan</label>
          <select
            value={selectedPlan || ""}
            onChange={async (e) => {
              const chosen = e.target.value;

              setSelectedPlan(chosen);

              if (!chosen || chosen === "new") {
                return;
              }

              try {
                const res = await axios.get(`${API_URL}/workout/plan_view`, {
                  params: { user_id, plan_name: chosen }
                });


                // Extract workouts from backend response (plan.exercises)
                const wdata =
                  res.data?.plan?.exercises?.map(ex => ({
                    exercise_name: ex.name,
                    muscle_group: ex.muscle_group || "Other",
                    reps: ex.sets?.map(s => s.reps) || [],
                    weight: ex.sets?.[0]?.weight || null,
                    sets: ex.sets?.length || 0
                  })) || [];


                if (wdata.length > 0) {
                  setEntries({
                    workouts: wdata,
                    summary: null
                  });
                } else {
                  console.log("No exercises found in plan");
                }



              } catch (err) {
                console.error("ERROR WHILE LOADING PLAN", err);
              }
            }}

            className="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl p-2 text-white"
          >
            <option value="">-- Select plan --</option>
            {plans.map((p, idx) => (
              <option key={idx} value={p}>{p}</option>
            ))}
            <option value="new">Create new plan...</option>
          </select>

          <button
            onClick={handleSaveWorkout}
            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
          >
            Save
          </button>
        </div>

        {selectedPlan === "new" && (
          <div className="flex items-center gap-3">
            <label className="text-sm text-neutral-300 w-24">Plan name</label>
            <input
              value={newPlanName}
              onChange={(e) => setNewPlanName(e.target.value)}
              placeholder="Enter new plan name (e.g., Push)"
              className="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl p-2 text-white"
            />
          </div>
        )}

        {/* small hint */}
        <div className="text-xs text-neutral-500">
          Save ties today's workout to the chosen plan. If this is the first save for this plan, choose "Create new plan..." and enter a name.
        </div>
      </div>
      </div>

        {/* Workout Log */}
        <div className="grid gap-4 p-2 mt-2">
        {entries.workouts.length === 0 ? (
          <p className="text-center text-neutral-500">No workouts for this date.</p>
        ) : (
          Object.entries(groupedWorkouts).map(([muscleGroup, workouts], groupIdx) => {
            const totalSets = getTotalSets(workouts);
            return (
              <motion.div
                key={groupIdx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-2xl bg-neutral-900 border border-neutral-800 shadow hover:shadow-lg transition-all"
              >

                {/* Exercise List */}
                <div className="space-y-4">
                  {workouts.map((workout, workoutIdx) => {
                    let repsList = [];
                    if (Array.isArray(workout.reps)) {
                      repsList = workout.reps.filter((r) => r != null && r !== "");
                    } else if (workout.reps != null && workout.reps !== "") {
                      repsList = [workout.reps];
                    }
                    const weightsListRaw = Array.isArray(workout.weight)
                      ? workout.weight
                      : repsList.map(() => workout.weight ?? 0);
                    const weightsList = repsList.map(
                      (_, idx) => weightsListRaw[idx] ?? weightsListRaw[0] ?? 0
                    );

                    const setsCount = workout.sets || repsList.length || 0;
                    const isEditing = editingId === workout._idx;
                    const isDeleting = deleteTarget === workout._idx;

                    return (
                      <div
                        key={workoutIdx}
                        className="bg-neutral-800 p-4 rounded-xl border border-neutral-700"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h3 className="text-lg font-bold text-white">
                              {workout.exercise_name}
                            </h3>
                            <p className="text-xs text-neutral-400 mt-1">
                              {setsCount} Sets{workout.weight ? `, ${workout.weight}kg` : ""}
                              {workout.duration_minutes ? `, ${Math.round(workout.duration_minutes)} min` : ""}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {isEditing ? (
                              <>
                                <button
                                  onClick={() => handleSaveEdit(workout)}
                                  className="px-3 py-1 rounded-lg bg-emerald-600 text-white text-xs"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={cancelEdit}
                                  className="px-3 py-1 rounded-lg bg-neutral-700 text-white text-xs"
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => startEdit(workout)}
                                  className="px-3 py-1 rounded-lg bg-blue-600 text-white text-xs"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => triggerDelete(workout)}
                                  className={`px-3 py-1 rounded-lg text-white text-xs ${isDeleting ? "bg-red-700" : "bg-red-600"}`}
                                >
                                  Delete
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Sets and Reps Display / Edit */}
                        {isEditing ? (
                          <div className="mt-4 space-y-3">
                            <div className="grid gap-2 text-xs sm:grid-cols-3 md:grid-cols-4">
                              {editForm.reps.map((rep, repIdx) => (
                                <div
                                  key={repIdx}
                                  className="bg-neutral-750/50 bg-neutral-800 border border-neutral-700 rounded-lg p-2 space-y-2"
                                >
                                  <p className="text-[10px] text-neutral-400">Set {repIdx + 1}</p>
                                  <input
                                    type="number"
                                    value={rep}
                                    onChange={(e) => {
                                      const next = [...editForm.reps];
                                      next[repIdx] = e.target.value;
                                      setEditForm((prev) => ({ ...prev, reps: next }));
                                    }}
                                    className="w-full bg-neutral-700 border border-neutral-600 rounded px-2 py-1 text-white"
                                    placeholder="Reps"
                                  />
                                  <input
                                    type="number"
                                    value={editForm.weights[repIdx] ?? ""}
                                    onChange={(e) => {
                                      const next = [...editForm.weights];
                                      next[repIdx] = e.target.value;
                                      setEditForm((prev) => ({ ...prev, weights: next }));
                                    }}
                                    className="w-full bg-neutral-700 border border-neutral-600 rounded px-2 py-1 text-white"
                                    placeholder="Weight (kg)"
                                  />
                                </div>
                              ))}
                              <button
                                type="button"
                                className="px-2 py-2 rounded-lg bg-neutral-700 border border-dashed border-neutral-500 text-white"
                                onClick={() =>
                                  setEditForm((prev) => ({
                                    ...prev,
                                    reps: [...prev.reps, ""],
                                    weights: [...prev.weights, "0"],
                                  }))
                                }
                              >
                                + Set
                              </button>
                            </div>
                          </div>
                        ) : repsList.length > 0 ? (
                          <div className="mt-3">
                            <div
                              className={`grid gap-2 text-center text-xs ${
                                repsList.length <= 4
                                  ? "grid-cols-4"
                                  : repsList.length <= 6
                                    ? "grid-cols-6"
                                    : "grid-cols-4"
                              }`}
                            >
                              {repsList.map((rep, repIdx) => (
                                <div
                                  key={repIdx}
                                  className="bg-neutral-700 px-2 py-1.5 rounded-lg relative"
                                >
                                  <div className="font-semibold text-neutral-300 text-[10px]">
                                    Set {repIdx + 1}
                                  </div>
                                  <div className="font-bold text-white mt-1">{rep}</div>
                                  <div className="text-[10px] text-neutral-400 mt-1">
                                    {weightsList[repIdx] ?? 0} kg
                                  </div>
                                  {isDeleting && (
                                    <button
                                      className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-red-600 text-white text-[10px] px-2 py-1 rounded-full shadow"
                                      onClick={() => confirmDelete(workout, repIdx)}
                                    >
                                      🗑️
                                    </button>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="mt-3 text-xs text-neutral-500 italic">
                            No reps data available
                          </div>
                        )}

                        {/* Delete confirm when no reps */}
                        {isDeleting && repsList.length === 0 && (
                          <div className="mt-3">
                            <button
                              className="px-3 py-1 rounded-lg bg-red-600 text-white text-xs"
                              onClick={() => confirmDelete(workout,repIdx)}
                            >
                              Confirm delete
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            );
          })
        )}
        </div>
      </div>

      {/* Chat Input */}
      <div className="w-full flex gap-2 p-3 border-t border-neutral-800 bg-neutral-900 rounded-t-2xl">
        <input
          type="text"
          placeholder="Enter your workout in natural language..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl p-3 text-white placeholder-neutral-500"
          onKeyPress={(e) => e.key === "Enter" && handleSubmit()}
        />
        <button
          onClick={handleSubmit}
          className="px-5 py-3 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-medium shadow-md"
        >
          Add
        </button>
      </div>
    </div>
  );
}
