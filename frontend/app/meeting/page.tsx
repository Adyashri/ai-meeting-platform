export default function MeetingPage() {
  return (
    <div className="min-h-screen bg-black text-white p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Meeting Room</h1>
        <button className="bg-red-500 px-4 py-2 rounded">
          End Meeting
        </button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg h-64 flex items-center justify-center">
          <p className="text-gray-400">Camera Feed 1</p>
        </div>
        <div className="bg-gray-800 rounded-lg h-64 flex items-center justify-center">
          <p className="text-gray-400">Camera Feed 2</p>
        </div>
      </div>
      <div className="flex justify-center gap-4 mt-6">
        <button className="bg-gray-700 px-6 py-2 rounded">Mute</button>
        <button className="bg-gray-700 px-6 py-2 rounded">Camera</button>
        <button className="bg-gray-700 px-6 py-2 rounded">Chat</button>
        <button className="bg-gray-700 px-6 py-2 rounded">Share</button>
      </div>
    </div>
  );
}