import React, { useState, useEffect } from 'react';

function App() {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [repoName, setRepoName] = useState('expressjs/express');
  const [currentRepo, setCurrentRepo] = useState('expressjs/express');

  useEffect(() => {
    const fetchIssues = async () => {
      setLoading(true);
      try {
        const response = await fetch(`http://127.0.0.1:8000/issues?repo=${currentRepo}`);
        const data = await response.json();
        setIssues(data);
      } catch (error) {
        console.error('Error fetching issues:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchIssues();
  }, [currentRepo]);

  const handleSubmit = (event) => {
    event.preventDefault();
    setCurrentRepo(repoName);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold underline mb-4">GitHub Issues for {currentRepo}</h1>
      
      <form onSubmit={handleSubmit} className="mb-4">
        <input 
          type="text" 
          value={repoName} 
          onChange={(e) => setRepoName(e.target.value)} 
          placeholder="Enter repo name (e.g., expressjs/express)" 
          className="border p-2 mr-2" 
        />
        <button type="submit" className="bg-blue-500 text-white p-2">Fetch Issues</button>
      </form>

      {loading ? (
        <p>Loading issues...</p>
      ) : (
        <ul>
          {issues.map(issue => (
            <li key={issue.number} className="border-b p-2">
              <h2 className="text-xl font-semibold">{issue.title}</h2>
              <p className="text-gray-600">Issue #{issue.number}</p>
              <p className="text-gray-800 mt-2">{issue.body}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;