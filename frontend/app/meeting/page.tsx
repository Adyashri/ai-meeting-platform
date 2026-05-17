import Navbar from "@/components/Navbar";

export default function MeetingPage() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Navbar />
      <div className="p-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-gray-800 rounded-lg h-64 flex items-center justify-center">
            <p className="text-gray-400">Your Camera</p>
          </div>
          <div className="bg-gray-800 rounded-lg h-64 flex items-center justify-center">
            <p className="text-gray-400">Participant Camera</p>
          </div>
        </div>
        <div className="flex justify-center gap-4 mt-6">
          <button className="bg-gray-700 px-6 py-3 rounded-lg">🎤 Mute</button>
          <button className="bg-gray-700 px-6 py-3 rounded-lg">📷 Camera</button>
          <button className="bg-gray-700 px-6 py-3 rounded-lg">💬 Chat</button>
          <button className="bg-gray-700 px-6 py-3 rounded-lg">🖥️ Share</button>
          <button className="bg-red-600 px-6 py-3 rounded-lg">📵 End</button>
        </div>
      </div>
    </div>
  );
}