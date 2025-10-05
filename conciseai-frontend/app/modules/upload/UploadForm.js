import { useState } from "react";

export default function UploadForm({ onVideoSelect }) {
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      onVideoSelect(file);
    }
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow-md w-full max-w-lg text-center">
      <h2 className="text-2xl font-semibold mb-4 text-blue-700">
        🎥 Upload Lecture Video
      </h2>
      <input
        type="file"
        accept="video/*"
        onChange={handleFileChange}
        className="w-full border border-gray-300 p-2 rounded mb-2 cursor-pointer"
      />
      {selectedFile && (
        <p className="text-sm text-gray-600 mt-2">
          Selected: {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
        </p>
      )}
    </div>
  );
}
