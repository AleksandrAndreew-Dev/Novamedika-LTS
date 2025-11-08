import React, { useState, useEffect } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [message, setMessage] = useState("");
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`${API_URL}/`);
        setMessage(response.data.message);

        const healthResponse = await axios.get(`${API_URL}/health`);
        setHealth(healthResponse.data);
      } catch (error) {
        console.error("Error fetching data:", error);
        setMessage("Backend connection failed");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-center">
        <h1 className="text-2xl font-bold">Novamedika Frontend</h1>
        <p className="text-gray-600">Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-8 font-sans">
      <h1 className="text-3xl font-bold mb-6">Hello Novamedika</h1>
     <a href="http://api.localhost/docs">FastAPI Docs</a> 

      <div className="mb-6 p-4 bg-gray-100 rounded-lg shadow">
        <h3 className="text-xl font-semibold mb-2">Backend Status:</h3>
        <p>
          <span className="font-semibold">Message:</span> {message}
        </p>
        {health && (
          <div className="mt-2 space-y-1">
            <p>
              <span className="font-semibold">Status:</span>{" "}
              <span className="text-green-600">✅ {health.status}</span>
            </p>
            <p>
              <span className="font-semibold">Service:</span> {health.service}
            </p>
            <p>
              <span className="font-semibold">Version:</span> {health.version}
            </p>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-xl font-semibold mb-2">Environment:</h3>
        <ul className="list-disc list-inside space-y-1 text-gray-700">
          <li>
            <span className="font-semibold">API URL:</span> {API_URL}
          </li>
          <li>
            <span className="font-semibold">Frontend:</span> React{" "}
            {React.version}
          </li>
        </ul>
      </div>
    </div>
  );
}
