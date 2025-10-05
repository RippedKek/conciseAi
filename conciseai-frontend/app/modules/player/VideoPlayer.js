"use client";

import { useEffect, useState } from "react";

export default function VideoPlayer({ videoFile }) {
  const [videoURL, setVideoURL] = useState(null);

  useEffect(() => {
    if (videoFile) {
      // Create a local blob URL
      const url = URL.createObjectURL(videoFile);
      setVideoURL(url);

      // Cleanup when component unmounts or file changes
      return () => URL.revokeObjectURL(url);
    }
  }, [videoFile]);

  if (!videoFile) return null;

  return (
    <div className="bg-white mt-6 p-6 rounded-xl shadow-md w-full max-w-2xl">
      <h2 className="text-xl font-semibold mb-3 text-blue-700 flex items-center gap-2">
        ▶️ Video Preview
      </h2>

      {videoURL ? (
        <video
          src={videoURL}
          controls
          className="w-full h-[360px] rounded-md border border-gray-200"
        />
      ) : (
        <p className="text-gray-500 text-center mt-4">Loading video...</p>
      )}
    </div>
  );
}
