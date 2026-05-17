export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">Login</h1>
        <input
          type="email"
          placeholder="Email"
          className="w-full border p-2 rounded mb-4"
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full border p-2 rounded mb-4"
        />
        <button className="w-full bg-blue-500 text-white p-2 rounded">
          Login
        </button>
      </div>
    </div>
  );
}export default function Home() {
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