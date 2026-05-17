import Navbar from "@/components/Navbar";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-6">Welcome to Dashboard</h1>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold">Upcoming Meetings</h2>
            <p className="text-gray-500 mt-2">No meetings scheduled</p>
            <button className="mt-4 bg-blue-500 text-white px-4 py-2 rounded w-full">
              Create Meeting
            </button>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold">Past Meetings</h2>
            <p className="text-gray-500 mt-2">No past meetings</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold">Quick Join</h2>
            <input type="text" placeholder="Enter meeting ID"
              className="w-full border p-2 rounded mt-2"/>
            <button className="w-full bg-green-500 text-white p-2 rounded mt-2">
              Join
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}