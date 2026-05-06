const Event = () => (
  <div className="max-w-2xl mx-auto bg-white p-6 rounded shadow">
    <h2 className="text-2xl font-bold mb-4">Hey there! 🎉</h2>
    <p className="mb-4">We're so excited to celebrate with you.</p>
    
    <div className="mb-6">
      <h3 className="text-xl font-semibold mb-2">Event Details</h3>
      <p><strong>Date:</strong> [Insert Date]</p>
      <p><strong>Location:</strong> [Insert Location]</p>
    </div>

    <div className="border-t pt-4">
      <h3 className="text-lg font-semibold mb-3">Download Event Info</h3>
      <div className="flex flex-col gap-3">
        <a
          href="/static/pdf/SangHee_and_Fabio_schedule.pdf"
          download
          className="inline-block px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 transition"
        >
          📅 Download Schedule
        </a>
      </div>
    </div>
  </div>
);
export default Event;
