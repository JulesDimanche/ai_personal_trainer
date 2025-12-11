import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import dayjs from "dayjs";
import axios from "axios";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import NavBar from "@/components/NavBar";

export default function Progress() {
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [weight, setWeight] = useState("");
  const [weightData, setWeightData] = useState([]);
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");
  const API_URL = "https://ai-personal-trainer-xgko.onrender.com";

  // Fetch weight data for graph
  const fetchWeightData = async () => {
    if (!user_id) return;

    try {
      const res = await axios.get(`${API_URL}/progress/weight_view`, {
        params: { user_id: user_id },
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // Handle different response structures
      let weights = [];
      if (res.data.weights && Array.isArray(res.data.weights)) {
        weights = res.data.weights;
      } else if (Array.isArray(res.data)) {
        weights = res.data;
      }

      // Format data for the chart (sort by date and format)
      const formattedData = weights
        .map((item) => ({
          date: item.date,
          weight: typeof item.weight === 'number' ? item.weight : parseFloat(item.weight),
        }))
        .filter((item) => !isNaN(item.weight))
        .sort((a, b) => new Date(a.date) - new Date(b.date));

      setWeightData(formattedData);
    } catch (err) {
      console.error("Fetch weight data error", err);
      setError("Failed to fetch weight data. Check console for details.");
    }
  };

  useEffect(() => {
    fetchWeightData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user_id]);

  const handleSubmit = async () => {
    if (!weight.trim()) {
      setError("Please enter a weight value.");
      return;
    }

    const weightValue = parseFloat(weight);
    if (isNaN(weightValue) || weightValue <= 0) {
      setError("Please enter a valid weight value (greater than 0).");
      return;
    }

    setError("");
    setSuccess("");
    setLoading(true);

    if (!user_id) {
      setError("User not logged in.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/progress/weight_save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: user_id,
          date: date,
          weight: weightValue,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to save weight");
      }

      setSuccess("Weight saved successfully!");
      setWeight("");
      
      // Refresh the weight data to update the graph
      await fetchWeightData();
    } catch (err) {
      console.error("Submit error", err);
      setError(err.message || "Failed to save weight. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <NavBar />
      <div className="flex flex-col h-[calc(100vh-4rem)] p-4 gap-4">
      {/* Date Picker */}
      <div className="w-full flex justify-center mt-2">
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

      {/* Error/Success Messages */}
      {error && (
        <div className="w-full max-w-2xl mx-auto p-3 bg-red-900/20 border border-red-700 rounded-xl text-red-400 text-sm text-center">
          {error}
        </div>
      )}
      {success && (
        <div className="w-full max-w-2xl mx-auto p-3 bg-green-900/20 border border-green-700 rounded-xl text-green-400 text-sm text-center">
          {success}
        </div>
      )}

      {/* Weight Input Form */}
      <div className="w-full flex justify-center">
        <div className="w-full max-w-2xl p-4 bg-neutral-900 rounded-2xl border border-neutral-800">
          <h2 className="text-xl font-semibold mb-4">Log Weight</h2>
          <div className="flex gap-3">
            <Input
              type="number"
              step="0.1"
              placeholder="Enter weight (kg)"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              className="flex-1 bg-neutral-800 border-neutral-700 text-white placeholder-neutral-500"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleSubmit();
                }
              }}
            />
            <Button
              onClick={handleSubmit}
              disabled={loading}
              className="px-6 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </div>

      {/* Progress Graph */}
      <div className="flex-1 overflow-y-auto w-full flex justify-center">
        <div className="w-full max-w-4xl p-4 bg-neutral-900 rounded-2xl border border-neutral-800">
          <h2 className="text-xl font-semibold mb-4">Weight Progress</h2>
          {weightData.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-neutral-500">
              No weight data available. Start logging your weight to see progress!
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart
                data={weightData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="date"
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af" }}
                  tickFormatter={(value) => dayjs(value).format("MMM DD")}
                />
                <YAxis
                  stroke="#9ca3af"
                  tick={{ fill: "#9ca3af" }}
                  label={{ value: "Weight (kg)", angle: -90, position: "insideLeft", fill: "#9ca3af" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #374151",
                    borderRadius: "8px",
                    color: "#fff",
                  }}
                  labelFormatter={(value) => dayjs(value).format("DD MMM YYYY")}
                  formatter={(value) => [`${value} kg`, "Weight"]}
                />
                <Legend wrapperStyle={{ color: "#9ca3af" }} />
                <Line
                  type="monotone"
                  dataKey="weight"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={{ fill: "#3b82f6", r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Weight"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
      </div>
    </div>
  );
}
