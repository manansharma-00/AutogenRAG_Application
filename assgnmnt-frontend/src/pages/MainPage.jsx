import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./MainPage.css";

const MainPage = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false); // New state to track upload success
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setMessage("");
    setUploadSuccess(false); // Reset the success message if a new file is selected
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setMessage("Please select a file.");
      return;
    }

    try {
      setUploading(true);

      const token = localStorage.getItem("token");
      if (!token) {
        setMessage("No token found, please log in first.");
        setUploading(false);
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      await axios.post("http://localhost:8000/upload", formData, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      setMessage("File uploaded successfully! Click Continue to chat");
      setUploading(false);
      setUploadSuccess(true);  // Set upload success state to true

      // Navigate to the QueryPage after successful file upload (optional if you want auto-redirect)
      // navigate("/query");

    } catch (error) {
      setMessage("Error uploading the file.");
      setUploading(false);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("token");
    setMessage("You have been signed out.");
    navigate("/signin");
  };

  return (
    <div className="main-page">
      <header>
        <h1>Upload Your Document</h1>
        {/* <button className="sign-out-btn" onClick={handleSignOut}>
          Sign Out
        </button> */}
      </header>

      <form onSubmit={handleSubmit} className="upload-form">
        <div className="upload-box">
          <label htmlFor="file-input" className="upload-label">
            <span className="upload-icon">📤</span>
            <p>Drag and drop your document here or click to browse</p>
          </label>
          <input
            id="file-input"
            type="file"
            onChange={handleFileChange}
            accept=".pdf,.docx,.txt"
          />
        </div>
        <small className="file-info">Supported formats: PDF, DOCX, TXT</small>
        {file && <p className="file-name">Selected File: {file.name}</p>} {/* Display the file name */}
        <button type="submit" className="upload-btn" disabled={!file}>
          {uploading ? "Uploading..." : "Upload File"}
        </button>
        {message && <p className="feedback">{message}</p>}
      </form>


      <div className="navigation-buttons">
        <button className="back-btn" onClick={() => navigate("/")}>
          Back
        </button>

        {/* Show Continue button only when upload is successful */}
        {uploadSuccess && (
          <button
            className="continue-btn"
            onClick={() => navigate("/query")}
            disabled={uploading}
          >
            Continue
          </button>
        )}
      </div>
    </div>
  );
};

export default MainPage;
