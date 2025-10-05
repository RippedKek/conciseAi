"use client";
import { useState } from "react";
import { uploadVideo } from "../../services/api"; // 👈 import API function

export default function UploadForm({ onVideoSelect }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [responseMsg, setResponseMsg] = useState("");

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      onVideoSelect(file);
      setResponseMsg("");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert("Please select a file first!");
      return;
    }

    try {
      setUploading(true);
      setResponseMsg("Uploading... ⏳");

      const result = await uploadVideo(selectedFile);
      console.log("Upload response:", result);
      setResponseMsg(`✅ Uploaded successfully! Video ID: ${result.id}`);
    } catch (err) {
      setResponseMsg(`❌ ${err.error || "Upload failed"}`);
    } finally {
      setUploading(false);
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
          Selected: {selectedFile.name} (
          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
        </p>
      )}

      <button
        onClick={handleUpload}
        disabled={uploading}
        className="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {uploading ? "Uploading..." : "Upload to Server"}
      </button>

      {responseMsg && (
        <p className="mt-4 text-sm text-gray-700">{responseMsg}</p>
      )}
    </div>
  );
}
