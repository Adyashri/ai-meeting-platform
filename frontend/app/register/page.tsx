export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center">Register</h1>
        <input type="text" placeholder="Full Name"
          className="w-full border p-2 rounded mb-4"/>
        <input type="email" placeholder="Email"
          className="w-full border p-2 rounded mb-4"/>
        <input type="password" placeholder="Password"
          className="w-full border p-2 rounded mb-4"/>
        <button className="w-full bg-green-500 text-white p-2 rounded">
          Register
        </button>
      </div>
    </div>
  );
}