import axios from "axios";

const API_BASE = "http://localhost:8000"; // replace with your backend URL

export const fetchUserProfile = async (userId) => {
    const token = localStorage.getItem("token");
  const res = await axios.get(`${API_BASE}/user/view?user_id=${userId}`,
     {
    headers: { Authorization: `Bearer ${token}` },}
  );
  return res.data;
};

export const fetchUserMacros = async (userId,date) => {
        const token = localStorage.getItem("token");
  const res = await axios.get(`${API_BASE}/macros/view?user_id=${userId}&date=${date}`
    ,
     {
    headers: { Authorization: `Bearer ${token}` },}
  );
  return res.data;
};
export const fetchUserMacrosFull = async (userId) => {
        const token = localStorage.getItem("token");
  const res = await axios.get(`${API_BASE}/macros/view_full?user_id=${userId}`
    ,
     {
    headers: { Authorization: `Bearer ${token}` },}
  );
  return res.data;
};

export const fetchWorkoutSummary = async (userId,date) => {
        const token = localStorage.getItem("token");

  const res = await axios.get(`${API_BASE}/workout/view?user_id=${userId}&date=${date}`
    ,
     {
    headers: { Authorization: `Bearer ${token}` },}
  );
  return res.data;
};

export const fetchFoodSummary = async (userId, date) => {
        const token = localStorage.getItem("token");

  const res = await axios.get(`${API_BASE}/calories/view?user_id=${userId}&date=${date}`
    ,
     {
    headers: { Authorization: `Bearer ${token}` },}
  );
  return res.data;
};
