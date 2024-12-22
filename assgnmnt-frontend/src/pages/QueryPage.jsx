import React, { useState } from "react";
import axios from "axios";
import "./QueryPage.css";

const QueryPage = () => {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const response = await axios.post("http://localhost:8000/ask", { question });
      if (response.data.success) {
        const newAnswer = response.data.answer;
        setAnswer(newAnswer);
        setHistory([...history, { question, answer: newAnswer }]);
      } else {
        setError("Failed to retrieve an answer.");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred.");
    } finally {
      setLoading(false);
      setQuestion("");
    }
  };

  return (
    <div className="chat-container">
      <h1 className="chat-heading">Ask Your Question</h1>
      
      <div className="messages-container">
        {history.map((item, index) => (
          <div key={index} className="message-group">
            <div className="user-message">
              <div className="message-content">{item.question}</div>
            </div>
            <div className="assistant-message">
              <div className="message-content">{item.answer}</div>
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="message-group">
            <div className="user-message">
              <div className="message-content">{question}</div>
            </div>
            <div className="assistant-message">
              <div className="message-content loading">
                <div className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            <div className="message-content">{error}</div>
          </div>
        )}
      </div>

      <div className="input-container">
        <form onSubmit={handleSubmit}>
          <textarea
            placeholder="Type your question here..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows="1"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "..." : "Send"}
          </button>
        </form>
        {/* <button 
          className="nav-button" 
          onClick={() => window.location.href = "/upload"}
        >
          Back to Upload
        </button> */}
      </div>
    </div>
  );
};

export default QueryPage;