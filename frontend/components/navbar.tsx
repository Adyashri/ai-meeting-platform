export default function Navbar() {
  return (
    <nav className="bg-blue-600 text-white px-6 py-4 flex justify-between items-center">
      <h1 className="text-xl font-bold">AI Meeting Platform</h1>
      <div className="flex gap-4">
        <a href="/dashboard" className="hover:underline">Dashboard</a>
        <a href="/meeting" className="hover:underline">Join Meeting</a>
        <a href="/login" className="bg-white text-blue-600 px-4 py-1 rounded">Logout</a>
      </div>
    </nav>
  );
}