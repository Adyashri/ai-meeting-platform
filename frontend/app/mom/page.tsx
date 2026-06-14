"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function MOMPage() {
  const router       = useRouter();
  const searchParams = useSearchParams();

  const urlMeetingId = searchParams.get("meeting_id");

  const [meetingId, setMeetingId] = useState("");
  const [mom, setMom]             = useState<any>(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");

  useEffect(() => {
    if (urlMeetingId) {
      setMeetingId(urlMeetingId);
    }
  }, [urlMeetingId]);

  const generateMOM = async () => {
    if (!meetingId) {
      alert("Please enter Meeting ID!");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `http://localhost:8000/mom/generate/${meetingId}`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      if (response.ok) {
        setMom(data.mom);
      } else {
        setError(data.detail || "MOM generation failed");
      }
    } catch (err) {
      setError("Server error — is backend running?");
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = async () => {
    if (!meetingId) return;
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `http://localhost:8000/download/pdf/${meetingId}`,
        {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );
      if (response.ok) {
        const blob = await response.blob();
        const url  = window.URL.createObjectURL(blob);
        const a    = document.createElement("a");
        a.href     = url;
        a.download = `MOM_${meetingId}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      } else {
        alert("PDF download failed!");
      }
    } catch (err) {
      alert("Server error!");
    }
  };

  const downloadDOCX = async () => {
    if (!meetingId) return;
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `http://localhost:8000/download/docx/${meetingId}`,
        {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        }
      );
      if (response.ok) {
        const blob = await response.blob();
        const url  = window.URL.createObjectURL(blob);
        const a    = document.createElement("a");
        a.href     = url;
        a.download = `MOM_${meetingId}.docx`;
        a.click();
        window.URL.revokeObjectURL(url);
      } else {
        alert("DOCX download failed!");
      }
    } catch (err) {
      alert("Server error!");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">

      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">
            Minutes of Meeting
          </h1>
          <p className="text-gray-500 mt-1">
            AI-powered meeting summary
          </p>
        </div>
        <button
          onClick={() => router.push("/dashboard")}
          className="bg-gray-200 hover:bg-gray-300
                     text-gray-700 px-4 py-2 rounded-lg"
        >
          Back to Dashboard
        </button>
      </div>

      {/* Meeting ID Input */}
      <div className="bg-white p-6 rounded-xl shadow mb-6">
        <h2 className="text-lg font-semibold mb-4">
          Meeting ID
        </h2>
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Enter your meeting ID here"
            value={meetingId}
            onChange={(e) => setMeetingId(e.target.value)}
            className="flex-1 border border-gray-300 p-3
                       rounded-lg focus:outline-none
                       focus:border-blue-500"
          />
          <button
            onClick={generateMOM}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700
                       text-white px-6 py-3 rounded-lg
                       font-semibold disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate MOM"}
          </button>
        </div>
        {error && (
          <p className="text-red-500 mt-3 font-medium">
            {error}
          </p>
        )}
      </div>

      {/* MOM Display */}
      {mom && (
        <div className="space-y-6">

          {/* Download Buttons — PDF + DOCX */}
          <div className="flex justify-end gap-4">
            <button
              onClick={downloadDOCX}
              className="bg-blue-600 hover:bg-blue-700
                         text-white px-6 py-3 rounded-lg
                         font-semibold"
            >
              Download DOCX
            </button>
            <button
              onClick={downloadPDF}
              className="bg-green-600 hover:bg-green-700
                         text-white px-6 py-3 rounded-lg
                         font-semibold"
            >
              Download PDF
            </button>
          </div>

          {/* Summary */}
          {mom.summary && (
            <div className="bg-white p-6 rounded-xl shadow">
              <h2 className="text-xl font-bold text-blue-800 mb-3">
                Summary
              </h2>
              <p className="text-gray-700 leading-relaxed">
                {mom.summary}
              </p>
            </div>
          )}

          {/* Key Discussions */}
          {mom.key_discussions?.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow">
              <h2 className="text-xl font-bold text-blue-800 mb-4">
                Key Discussions
              </h2>
              <div className="space-y-3">
                {mom.key_discussions.map((d: any, i: number) => (
                  <div
                    key={i}
                    className="border-l-4 border-blue-500 pl-4"
                  >
                    <p className="font-semibold text-gray-800">
                      {d.topic}
                    </p>
                    <p className="text-gray-600 text-sm mt-1">
                      {d.details}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Decisions */}
          {mom.decisions?.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow">
              <h2 className="text-xl font-bold text-blue-800 mb-4">
                Decisions Made
              </h2>
              <div className="space-y-3">
                {mom.decisions.map((d: any, i: number) => (
                  <div
                    key={i}
                    className="flex gap-3 items-start"
                  >
                    <span className="bg-blue-100 text-blue-800
                                     font-bold px-2 py-1 rounded
                                     text-sm flex-shrink-0">
                      {i + 1}
                    </span>
                    <div>
                      <p className="font-semibold text-gray-800">
                        {d.decision}
                      </p>
                      <p className="text-gray-500 text-sm mt-1">
                        {d.reason}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Items */}
          {mom.action_items?.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow">
              <h2 className="text-xl font-bold text-blue-800 mb-4">
                Action Items
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-blue-800 text-white">
                      <th className="p-3 text-left">Task</th>
                      <th className="p-3 text-left">
                        Assigned To
                      </th>
                      <th className="p-3 text-left">Deadline</th>
                      <th className="p-3 text-left">Priority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mom.action_items.map(
                      (item: any, i: number) => (
                      <tr
                        key={i}
                        className={
                          i % 2 === 0 ? "bg-white" : "bg-gray-50"
                        }
                      >
                        <td className="p-3">{item.task}</td>
                        <td className="p-3">
                          {item.assigned_to}
                        </td>
                        <td className="p-3">{item.deadline}</td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded-full
                            text-xs font-bold ${
                            item.priority === "high"
                              ? "bg-red-100 text-red-700"
                              : item.priority === "medium"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-green-100 text-green-700"
                          }`}>
                            {item.priority?.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Next Meeting */}
          {mom.next_meeting &&
           mom.next_meeting !== "N/A" && (
            <div className="bg-blue-50 p-6 rounded-xl
                            border border-blue-200">
              <h2 className="text-xl font-bold
                             text-blue-800 mb-2">
                Next Meeting
              </h2>
              <p className="text-gray-700">
                {mom.next_meeting}
              </p>
            </div>
          )}

        </div>
      )}

    </div>
  );
}