import axios from "axios";

const API_BASE_URL = "http://localhost:5000"; // Flask backend

export const uploadVideo = async (file) => {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await axios.post(`${API_BASE_URL}/videos`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    console.error("Upload failed:", error);
    throw error.response?.data || { error: "Upload failed" };
  }
};
