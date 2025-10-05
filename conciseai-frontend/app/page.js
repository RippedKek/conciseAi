"use client";

import { useState } from "react";
import Navbar from "../components/Navbar";
import UploadForm from "./modules/upload/UploadForm";
import VideoPlayer from "./modules/player/VideoPlayer";

export default function Home() {
  const [videoFile, setVideoFile] = useState(null);

  return (
    <div className="min-h-screen flex flex-col items-center">
      <Navbar />
      <main className="flex flex-col items-center justify-center p-6 w-full">
        <UploadForm onVideoSelect={setVideoFile} />
        <VideoPlayer videoFile={videoFile} />
      </main>
    </div>
  );
}
