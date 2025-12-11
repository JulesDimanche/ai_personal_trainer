import React, { useState, useEffect, useRef } from "react";
import dayjs from "dayjs";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Play, Square, MapPin, Timer, Navigation } from "lucide-react";
import NavBar from "@/components/NavBar";
import L from "leaflet";

export default function CardioTracker() {
  const API_URL = "https://ai-personal-trainer-xgko.onrender.com";
  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");
  const today = dayjs().format("YYYY-MM-DD");

  const [tracking, setTracking] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const [duration, setDuration] = useState(0);
  const [distance, setDistance] = useState(0);
  const [currentPosition, setCurrentPosition] = useState(null);
  const [lastPosition, setLastPosition] = useState(null);
  const [pathPoints, setPathPoints] = useState([]);
  const [cardioType, setCardioType] = useState("walking");
  const [status, setStatus] = useState("Ready to go?");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const watchIdRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    let interval;
    if (tracking && startTime) {
      interval = window.setInterval(() => {
        setDuration(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
      if (watchIdRef.current != null && navigator.geolocation) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, [tracking, startTime]);

  const formatDuration = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (totalSeconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  const handleLocationError = (err) => {
    console.error("Geolocation error:", err);
    setStatus("Location unavailable. Check permissions.");
    setError("Unable to access location. Please allow GPS and retry.");
  };

  // lightweight path render on canvas to show route
  // Initialize Leaflet Map + Update Polyline
useEffect(() => {
  if (!mapRef.current) return;

  // Create map only once
  if (!mapRef.current._leaflet_id) {
    const map = L.map(mapRef.current).setView([20, 80], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);
      setTimeout(() => map.invalidateSize(), 300);

    mapRef.current.map = map;
    mapRef.current.polyline = L.polyline([], { color: "lime", weight: 4 }).addTo(map);
  }

  const map = mapRef.current.map;
  const polyline = mapRef.current.polyline;

  if (pathPoints.length > 0) {
    const last = pathPoints[pathPoints.length - 1];

    polyline.addLatLng([last.latitude, last.longitude]);
    map.setView([last.latitude, last.longitude], 17);
  }
}, [pathPoints]);


  // Start tracking
  const startTracking = () => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported on this device.");
      return;
    }
    setError("");
    setTracking(true);
    const now = Date.now();
    setStartTime(now);
    setDuration(0);
    setDistance(0);
    setLastPosition(null);
    setPathPoints([]);
    setStatus("Finding GPS...");

    const id = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        const newPos = { latitude, longitude };
        setCurrentPosition(newPos);
        setStatus("Tracking...");

        setLastPosition((prev) => {
          if (prev) {
            const d = calculateDistance(prev, newPos);
            setDistance((prevD) => prevD + d);
          }
          return newPos;
        });
        setPathPoints((prev) => [...prev, newPos]);
      },
      handleLocationError,
      { enableHighAccuracy: true, maximumAge: 1000 }
    );

    watchIdRef.current = id;
  };

  const pauseTracking = () => {
    if (!tracking) return;
    if (watchIdRef.current != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setTracking(false);
    if (startTime) {
      const finalDuration = Math.floor((Date.now() - startTime) / 1000);
      setDuration(finalDuration);
    }
    setStatus("Paused");
  };

  const resumeTracking = () => {
    if (tracking) return;
    if (!navigator.geolocation) {
      setError("Geolocation not supported on this device.");
      return;
    }
    setError("");
    setTracking(true);
    const now = Date.now() - duration * 1000;
    setStartTime(now);
    setStatus("Resuming...");

    const id = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        const newPos = { latitude, longitude };
        setCurrentPosition(newPos);
        setStatus("Tracking...");

        setLastPosition((prev) => {
          if (prev) {
            const d = calculateDistance(prev, newPos);
            setDistance((prevD) => prevD + d);
          }
          return newPos;
        });
        setPathPoints((prev) => [...prev, newPos]);
      },
      handleLocationError,
      { enableHighAccuracy: true, maximumAge: 1000 }
    );

    watchIdRef.current = id;
  };

  const endTracking = () => {
    pauseTracking();
    setStatus("Session ready. Send to AI to save.");
  };

  const calculateDistance = (p1, p2) => {
    const R = 6371; // km
    const dLat = ((p2.latitude - p1.latitude) * Math.PI) / 180;
    const dLon = ((p2.longitude - p1.longitude) * Math.PI) / 180;
    const lat1 = (p1.latitude * Math.PI) / 180;
    const lat2 = (p2.latitude * Math.PI) / 180;

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // distance in km
  };

  const sendCardio = async (finalDuration, finalDistance) => {
    if (!user_id) {
      setError("User not logged in.");
      return;
    }
    setIsSubmitting(true);
    setError("");
    setStatus("Saving session...");
    const summaryText = `${cardioType} - ${finalDuration} s - ${finalDistance.toFixed(3)} km`;

    try {
      const payload = {
        user_id,
        date: today,
        text: summaryText,
      };
      console.log(payload);
      await fetch(`${API_URL}/workout/calculate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : undefined,
        },
        body: JSON.stringify(payload),
      });
      setStatus("Session saved.");
    } catch (err) {
      console.error("Submit error", err);
      setError("Failed to save cardio. Please retry.");
      setStatus("Save failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-neutral-950 text-white">
      <NavBar />
      <div className="p-4 flex flex-col gap-4 max-w-3xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-neutral-400">{today}</p>
            <h1 className="text-2xl font-bold">Cardio Tracker</h1>
          </div>
          <span className="text-sm text-neutral-400">{status}</span>
        </div>

        <Card className="bg-neutral-900 border-neutral-800">
          <CardContent className="p-4 flex flex-col gap-4">
            <div className="flex items-center gap-3 text-lg">
              <select
                className="bg-neutral-800 p-2 rounded-xl"
                value={cardioType}
                onChange={(e) => setCardioType(e.target.value)}
                disabled={tracking}
              >
                <option value="walking">Walking</option>
                <option value="running">Running</option>
                <option value="cycling">Cycling</option>
              </select>
            </div>

            <div className="w-full h-48 bg-neutral-800 rounded-xl overflow-hidden">
<div ref={mapRef} style={{ height: "300px", width: "100%" }} />
</div>


            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="flex items-center gap-3 text-lg bg-neutral-800 p-3 rounded-xl">
                <Timer className="w-5 h-5" />
                <div>
                  <p className="text-xs text-neutral-400">Duration</p>
                  <p className="text-xl font-semibold">{formatDuration(duration)}</p>
                </div>
              </div>

              <div className="flex items-center gap-3 text-lg bg-neutral-800 p-3 rounded-xl">
                <Navigation className="w-5 h-5" />
                <div>
                  <p className="text-xs text-neutral-400">Distance</p>
                  <p className="text-xl font-semibold">{distance.toFixed(2)} km</p>
                </div>
              </div>

              <div className="flex items-center gap-3 text-lg bg-neutral-800 p-3 rounded-xl">
                <MapPin className="w-5 h-5" />
                <div>
                  <p className="text-xs text-neutral-400">Location</p>
                  <p className="text-sm">
                    {currentPosition
                      ? `${currentPosition.latitude.toFixed(4)}, ${currentPosition.longitude.toFixed(4)}`
                      : "Waiting for GPS..."}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Button
                onClick={tracking ? pauseTracking : startTracking}
                className={`${tracking ? "bg-yellow-600 hover:bg-yellow-700" : "bg-green-600 hover:bg-green-700"
                  } text-white w-full py-3 rounded-xl text-lg`}
                disabled={isSubmitting}
              >
                <Play className="w-5 h-5 mr-2" />
                {tracking ? "Pause" : pathPoints.length > 0 ? "Resume" : "Start"}
              </Button>

              <Button
                onClick={endTracking}
                className="bg-red-600 hover:bg-red-700 text-white w-full py-3 rounded-xl text-lg"
                disabled={tracking || isSubmitting}
              >
                <Square className="w-5 h-5 mr-2" /> End
              </Button>

              <Button
                onClick={() => sendCardio(duration, distance)}
                className="bg-blue-600 hover:bg-blue-700 text-white w-full py-3 rounded-xl text-lg"
                disabled={tracking || duration === 0 || isSubmitting}
              >
                Send to AI
              </Button>
            </div>

            {!tracking && duration > 0 && (
              <div className="text-sm text-neutral-400">
                Session ready. Click Send to AI when you are done.
              </div>
            )}

            {error && <div className="text-sm text-red-400">{error}</div>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
