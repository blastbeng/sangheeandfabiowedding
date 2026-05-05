function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <header className="bg-blue-600 text-white p-4 text-center">
        <h1 className="text-2xl font-bold">React + Django</h1>
      </header>
      <main className="flex-grow p-4">
        <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white p-6 rounded shadow">
            <h2 className="text-xl font-semibold mb-2">Mobile View</h2>
            <p className="text-gray-700">Resize the window to see responsiveness.</p>
          </div>
          <div className="bg-white p-6 rounded shadow">
            <h2 className="text-xl font-semibold mb-2">Desktop View</h2>
            <p className="text-gray-700">This grid adjusts on larger screens.</p>
          </div>
        </div>
      </main>
      <footer className="bg-gray-800 text-white text-center p-4">
        <p>&copy; 2023 Frontend Project</p>
      </footer>
    </div>
  )
}

export default App
