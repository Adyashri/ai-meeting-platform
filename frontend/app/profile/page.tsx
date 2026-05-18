import Navbar from "@/components/Navbar";

export default function ProfilePage() {
  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />
      <div className="p-8 max-w-2xl mx-auto">
        <div className="bg-white p-8 rounded-xl shadow text-center">
          <div className="w-24 h-24 bg-blue-500 rounded-full mx-auto mb-4 flex items-center justify-center">
            <p className="text-white text-4xl">👤</p>
          </div>
          <h1 className="text-2xl font-bold">Pallavi Adbale</h1>
          <p className="text-gray-500 mb-6">pallavi@example.com</p>
          <div className="grid grid-cols-2 gap-4 text-left">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-500 text-sm">Full Name</p>
              <p className="font-semibold">Pallavi Adbale</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-500 text-sm">Email</p>
              <p className="font-semibold">pallavi@example.com</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-500 text-sm">Role</p>
              <p className="font-semibold">Frontend Lead</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-gray-500 text-sm">Joined</p>
              <p className="font-semibold">May 2026</p>
            </div>
          </div>
          <button className="mt-6 bg-blue-500 text-white px-6 py-2 rounded-lg w-full">
            Edit Profile
          </button>
        </div>
      </div>
    </div>
  );
}