import React from "react";
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from "react-router-dom";
import SignUp from "./pages/SignUp";
import SignIn from "./pages/SignIn";
import MainPage from "./pages/MainPage";
import QueryPage from "./pages/QueryPage";
import './App.css';



function App() {
  return (
    <Router>
      <Header />
      <MainContent />
      <div className="main-content"></div>
      <Routes>
        <Route path="/signup" element={<SignUp />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/main" element={<MainPage />} />
        <Route path="/query" element={<QueryPage />} />
      </Routes>
      <Footer />
    </Router>
  );
}

function Header() {
  const navigate = useNavigate(); // Properly initialize navigate

  const handleSignOut = () => {
    localStorage.removeItem("token"); // Remove token from storage
    navigate("/signin", { replace: true }); // Navigate to /signin
  };

  return (
    <header className="header">
      <div className="logo">DocQuery: Intelligent Document Insights</div>
      <nav className="nav">
        <Link to="/">Dashboard</Link>
        <Link to="/about">About Us</Link>
        <Link to="/help">Support</Link>
        {/* <Link to="/signin">Sign Out</Link> */}
      </nav>
        <button className="sign-out-btn" onClick={handleSignOut}>Log Out</button>
    </header>
  );
}

function MainContent() {
  const navigate = useNavigate();  // Initialize the useNavigate hook
  // const location = useLocation();   // Get the current location/path
  
  const handleUploadClick = () => {
    const token = localStorage.getItem("token");
    if (token) {
      navigate("/main");  // User is signed in
    } else {
      navigate("/signup");  // Navigate to the sign-up page when the button is clicked
    }
  };

  // Render the upload section only on the home page
  if (location.pathname === "/") {
    return (
      <main className="hero">
        <div className="hero-content">
          <h1>Streamline Your Document Analysis</h1>
          <div className="hero-description">
          <p>DocQuery is a powerful platform that allows users to upload and manage documents in various formats (PDF, PPT, CSV, etc.), 
          providing intelligent NLP-powered search and query responses. Leverage advanced document parsing and retrieval to gain <br />
          instant insights and answers.</p>
          </div>
          <p>Sign Up now to Upload Your Documents and Get Instant Answers</p>
          <button className="cta-button" onClick={handleUploadClick}>Get Started</button>
        </div>
      </main>
    );
  }

  // Return null or an empty fragment for other pages
  return null;
}

function Footer() {
  return (
    <footer className="footer">
      <p>© 2024 DocQuery. All rights reserved.</p>
      <nav className="footer-links">
        <Link to="/privacy">Privacy Policy</Link>
        <Link to="/terms">Terms of Service</Link>
        <Link to="/contact">Contact Us</Link>
      </nav>
    </footer>
  );
}

export default App;
