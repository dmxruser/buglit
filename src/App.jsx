import React, { useState, useEffect } from 'react';
import { Button } from '@patternfly/react-core';
import { MdFavorite } from 'react-icons/md';

function App() {
  const [token, setToken] = useState(null);
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [issues, setIssues] = useState([]);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [aiTextBox, setAiTextBox] = useState('');
  const [pyOutput, setPyOutput] = useState('');
  const [isThinking, setIsThinking] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token');
    if (tokenFromUrl) {
      setToken(tokenFromUrl);
      localStorage.setItem('github_token', tokenFromUrl);
      window.history.replaceState({}, document.title, "/");
    } else {
      const tokenFromStorage = localStorage.getItem('github_token');
      if (tokenFromStorage) {
        setToken(tokenFromStorage);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const fetchRepos = async () => {
      if (!token) return;
      setLoading(true);
      try {
        const response = await fetch('http://127.0.0.1:8000/user/repos', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await response.json();
        setRepos(data);
      } catch (error) {
        console.error('Error fetching repos:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRepos();
  }, [token]);

  const handleRepoClick = async (repoName) => {
    setSelectedRepo(repoName);
    setIssues([]); // Clear previous issues
    try {
      const response = await fetch(`http://127.0.0.1:8000/issues?repo=${repoName}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setIssues(data);
    } catch (error) {
      console.error(`Error fetching issues for ${repoName}:`, error);
    }
  };

  const handleIssueClick = (issue) => {
    console.log('issue clicked:', issue);
    setSelectedIssue(issue);
  };

  const handleBackToIssues = () => {
    setSelectedIssue(null);
  };

  const handlePyAction = async () => {
    setIsThinking(true);
    setPyOutput('');
    try {
      const response = await fetch('http://1227.0.0.1:8000/run-command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ command: aiTextBox, issue: selectedIssue }),
      });
      const data = await response.text();
      console.log('raw response:', data);
      setPyOutput(data);
    } catch (error) {
      console.error('Error sending command to py:', error);
    } finally {
      setIsThinking(false);
    }
  };

  console.log('selectedIssue:', selectedIssue);

  if (loading) {
    return <div className="container mx-auto p-4 text-center">Loading...</div>;
  }

  if (!token) {
    return (
      <div className="container mx-auto p-4 text-center">
        <h1 className="text-3xl font-bold mb-4">Welcome to Buglit</h1>
        <p className="mb-4">Please log in with your GitHub account to continue.</p>
        <Button variant="primary">Hello PatternFly!</Button> <MdFavorite />
        <a href="http://127.0.0.1:8000/login/github" className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Login with GitHub
        </a>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold underline mb-4">Your Repositories</h1>
      {loading ? (
        <p>Loading repositories...</p>
      ) : (
        <ul>
          {repos.map(repo => (
            <li key={repo} className="border-b p-2 cursor-pointer hover:bg-gray-100" onClick={() => handleRepoClick(repo)}>
              <h2 className="text-xl font-semibold">{repo}</h2>
            </li>
          ))}
        </ul>
      )}

      {selectedRepo && !selectedIssue && (
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-4">Issues for {selectedRepo}</h2>
          {issues.length > 0 ? (
            <ul>
              {issues.map(issue => (
                <li key={issue.number} className="border-b p-2 cursor-pointer hover:bg-gray-100" onClick={() => handleIssueClick(issue)}>
                  <h3 className="text-xl font-semibold">{issue.title}</h3>
                  <p className="text-gray-600">Issue #{issue.number}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>Loading issues for {selectedRepo}...</p>
          )}
        </div>
      )}

      {selectedIssue && (
        <div className="mt-8">
          <button onClick={handleBackToIssues} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mb-4">
            Back to Issues
          </button>
          <h2 className="text-2xl font-bold mb-4">Issue Details</h2>
          <h3 className="text-xl font-semibold">{selectedIssue.title}</h3>
          <p className="text-gray-600">Issue #{selectedIssue.number}</p>
          <p className="text-gray-800 mt-2">{selectedIssue.body}</p>

          <div className="mt-4">
            <input 
              type="text" 
              value={aiTextBox}
              onChange={(e) => setAiTextBox(e.target.value)}
              className="border p-2 w-full mb-2"
              placeholder="Send a command to py..."
            />
            <button onClick={handlePyAction} className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
              Send to Py
            </button>
            <div className="border p-2 w-full mt-2 bg-gray-100 rounded">
              {isThinking ? (
                <p>Thinking...</p>
              ) : (
                <pre className="whitespace-pre-wrap">{pyOutput}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;