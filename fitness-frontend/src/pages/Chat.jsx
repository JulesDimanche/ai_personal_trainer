import React, { useState, useRef, useEffect } from "react";
import NavBar from "@/components/NavBar";

export default function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  const user_id = localStorage.getItem("user_id");
  const token = localStorage.getItem("token");

  const API_URL = "https://ai-personal-trainer-xgko.onrender.com/query/answer";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text) return;

    setError("");

    // Show user message immediately
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setLoading(true);

    try {
      const payload = {
        user_id,
        query: text
      };

      const res = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Request failed");
      }

      const data = await res.json();
      let answer = data.answer;
      

      // If backend returned nested object like { answer: { answer: "text" } }
      if (answer && typeof answer === "object" && answer.answer) {
        answer = answer.answer;
      }

      // Final safety: convert only if still object
      if (typeof answer === "object") {
        answer = JSON.stringify(answer, null, 2);
}


setMessages(prev => [...prev, { role: "assistant", text: answer }]);


    } catch (err) {
      console.error("Error:", err);
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "⚠️ Something went wrong, please try again." }
      ]);
    }

    setLoading(false);
  };

  const handleEnter = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <NavBar />
      <div className="flex flex-col h-[calc(100vh-4rem)] p-4 gap-4">
        <div className="text-lg font-semibold">Chat Assistant</div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 bg-neutral-900 rounded-xl border border-neutral-800 space-y-3"
      >
        {messages.length === 0 && (
          <div className="text-center text-gray-400">
            Start the conversation...
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`max-w-3xl px-4 py-3 rounded-lg ${
              msg.role === "user"
                ? "bg-blue-600 text-white self-end ml-auto"
                : "bg-neutral-800 text-white self-start"
            }`}
          >
            <div className="whitespace-pre-wrap">{msg.text}</div>
            <div className="text-xs opacity-70 mt-1">{msg.role}</div>
          </div>
        ))}

        {loading && (
          <div className="bg-neutral-800 text-white rounded-lg px-4 py-2 w-fit">
            Thinking...
          </div>
        )}
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}

      <div className="flex gap-2">
        <textarea
          className="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl p-3 min-h-[48px] resize-none text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500"
          placeholder="Type your question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleEnter}
        />

        <button
          className="px-4 py-2 bg-blue-600 text-white rounded-xl disabled:opacity-50 hover:bg-blue-700"
          disabled={loading}
          onClick={sendMessage}
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
      </div>
    </div>
  );
}
