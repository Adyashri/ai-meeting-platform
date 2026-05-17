export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-100">
      <h1 className="text-4xl font-bold mb-4">AI Meeting Platform</h1>
      <p className="text-gray-600 mb-8">Smart meetings powered by AI</p>
      <div className="flex gap-4">
        <a href="/login" className="bg-blue-500 text-white px-6 py-2 rounded-lg">
          Login
        </a>
        <a href="/register" className="bg-green-500 text-white px-6 py-2 rounded-lg">
          Register
        </a>
      </div>
    </div>
  );
}