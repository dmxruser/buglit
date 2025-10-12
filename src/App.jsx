import React, { useState, useEffect } from 'react';

function App() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [issues, setIssues] = useState([]);

  useEffect(() => {
    const fetchRepos = async () => {
      setLoading(true);
      try {
        const response = await fetch('http://127.0.0.1:8000/user/repos');
        const data = await response.json();
        setRepos(data);
      } catch (error) {
        console.error('Error fetching repos:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRepos();
  }, []);

  const handleRepoClick = async (repoName) => {
    setSelectedRepo(repoName);
    setIssues([]); // Clear previous issues
    try {
      const response = await fetch(`http://127.0.0.1:8000/issues?repo=${repoName}`);
      const data = await response.json();
      setIssues(data);
    } catch (error) {
      console.error(`Error fetching issues for ${repoName}:`, error);
    }
  };

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

      {selectedRepo && (
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-4">Issues for {selectedRepo}</h2>
          {issues.length > 0 ? (
            <ul>
              {issues.map(issue => (
                <li key={issue.number} className="border-b p-2">
                  <h3 className="text-xl font-semibold">{issue.title}</h3>
                  <p className="text-gray-600">Issue #{issue.number}</p>
                  <p className="text-gray-800 mt-2">{issue.body}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p>Loading issues for {selectedRepo}...</p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;