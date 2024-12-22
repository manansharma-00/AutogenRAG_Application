import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./SignIn.css";

const SignIn = () => {
  const [formData, setFormData] = useState({ usernameOrEmail: "", password: "" });
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const formDataEncoded = new URLSearchParams();
      formDataEncoded.append("username", formData.usernameOrEmail);
      formDataEncoded.append("password", formData.password);

      const response = await axios.post("http://localhost:8000/token", formDataEncoded, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      localStorage.setItem("token", response.data.access_token);
      setMessage("Login successful!");
      navigate("/main");
    } catch (error) {
      setMessage("Invalid credentials or an error occurred");
    }
  };

  return (
    <div className="signin-container">
      <div className="signin-card">
        <h1 className="signin-heading">Welcome Back</h1>
        <form onSubmit={handleSubmit} className="signin-form">
          <label htmlFor="usernameOrEmail" className="signin-label">
            Username or Email
          </label>
          <input
            type="text"
            name="usernameOrEmail"
            id="usernameOrEmail"
            placeholder="Enter your username or email"
            value={formData.usernameOrEmail}
            onChange={handleChange}
            className="signin-input"
            required
          />

          <label htmlFor="password" className="signin-label">
            Password
          </label>
          <input
            type="password"
            name="password"
            id="password"
            placeholder="Enter your password"
            value={formData.password}
            onChange={handleChange}
            className="signin-input"
            required
          />

          <button type="submit" className="signin-button">
            Sign In
          </button>
        </form>

        {message && <p className="signin-message">{message}</p>}

        <div className="signin-links">
          <a href="#" className="signin-link">
            Forgot Password?
          </a>
          <a href="/signup" className="signin-link">
            Sign Up
          </a>
        </div>
      </div>
    </div>
  );
};

export default SignIn;
