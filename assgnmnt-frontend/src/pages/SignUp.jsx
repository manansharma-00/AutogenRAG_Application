import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom"; // Import useNavigate for redirecting
import { Link } from "react-router-dom";  // Import Link for navigation
import "./SignUp.css";  // Import the CSS for styling

const SignUp = () => {
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [message, setMessage] = useState("");
  const [isFormValid, setIsFormValid] = useState(false);
  const navigate = useNavigate(); // Initialize the navigate function

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    // Update the formData state
    const updatedFormData = { ...formData, [name]: value };
    setFormData(updatedFormData);

    // Validation logic based on the updated formData
    setIsFormValid(
      updatedFormData.fullName &&
        updatedFormData.email &&
        updatedFormData.password &&
        updatedFormData.password === updatedFormData.confirmPassword
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      setMessage("Passwords do not match!");
      return;
    }

    try {
      const response = await axios.post("http://localhost:8000/signup", {
        username: formData.fullName, // The backend expects the username as the email
        email: formData.email,
        password: formData.password,
        confirm_password: formData.confirmPassword, // Send confirmPassword to the backend
      });
      
      setMessage("User created successfully!");
      
      // Redirect to the main page (e.g., '/')
      setTimeout(() => {
        navigate("/signin"); // Redirect to the home page
      }, 1500); // Delay to allow the message to be seen before redirecting
    } catch (error) {
      setMessage(error.response?.data?.detail || "An error occurred");
    }
  };

  return (
    <div className="signup-container">

      <h1>Create Your Account</h1>
      <div className="sign-in-link">
        <p>Already a user? <Link to="/signin">Sign In</Link></p> {/* Sign In Link */}
      </div>
      <form onSubmit={handleSubmit} className="signup-form">
        <div className="form-group">
          <label htmlFor="fullName">Full Name</label>
          <input
            type="text"
            name="fullName"
            id="fullName"
            placeholder="Enter your full name"
            value={formData.fullName}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            name="email"
            id="email"
            placeholder="Enter your email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            name="password"
            id="password"
            placeholder="Enter your password"
            value={formData.password}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input
            type="password"
            name="confirmPassword"
            id="confirmPassword"
            placeholder="Confirm your password"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
          />
        </div>

        <button type="submit" className="signup-btn" disabled={!isFormValid}>
          Sign Up
        </button>

        <p className="policy-notice">
          By signing up, you agree to our <a href="/terms">Terms of Service</a> and <a href="/privacy">Privacy Policy</a>.
        </p>

        {message && <p className="message">{message}</p>}
      </form>
    </div>
  );
};

export default SignUp;
