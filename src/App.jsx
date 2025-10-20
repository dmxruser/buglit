import React, { useState, useEffect } from 'react';
import {
  Button,
  Page,
  PageSection,
  Title,
  Spinner,
  Bullseye,
  EmptyState,
  EmptyStateBody,
  DataList,
  DataListItem,
  DataListItemRow,
  DataListCell,
  Content,
  Card,
  CardBody,
  CardTitle,
  TextInput,
  CodeBlock,
  Gallery,
} from '@patternfly/react-core';

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
      const response = await fetch('http://12-7.0.0.1:8000/run-command', {
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

  if (loading) {
    return (
      <Bullseye>
        <Spinner />
      </Bullseye>
    );
  }

  if (!token) {
    return (
      <Page>
        <PageSection hasBodyWrapper={false} >
          <EmptyState titleText={<Title headingLevel="h1">Welcome to Buglit</Title>}>
            <EmptyStateBody>
              Please log in with your GitHub account to continue.
            </EmptyStateBody>
            <Button component="a" href="http://127.0.0.1:8000/login/github" variant="primary">
              Login with GitHub
            </Button>
          </EmptyState>
        </PageSection>
      </Page>
    );
  }

  return (
    <Page>
      <PageSection hasBodyWrapper={false} >
        <Title headingLevel="h1">Your Repositories</Title>
      </PageSection>

      <PageSection hasBodyWrapper={false}>
        {loading ? (
          <Spinner />
        ) : (
          <Gallery hasGutter>
            {repos.map(repo => (
              <Card key={repo} onClick={() => handleRepoClick(repo)} isClickable isSelectable className="repo-card">
                <CardTitle>{repo}</CardTitle>
              </Card>
            ))}
          </Gallery>
        )}
      </PageSection>

      {selectedRepo && !selectedIssue && (
        <PageSection hasBodyWrapper={false}>
          <Title headingLevel="h2">Issues for {selectedRepo}</Title>
          {issues.length > 0 ? (
            <DataList aria-label="Issues list">
              {issues.map(issue => (
                <DataListItem key={issue.number} className="issue-list-item"  aria-labelledby={`issue-${issue.number}`} onClick={() => handleIssueClick(issue)} isSelectable>
                  <DataListItemRow>
                    <DataListCell>
                      <Content>
                        <Content component="h3">{issue.title}</Content>
                        <Content component="p">Issue #{issue.number}</Content>
                      </Content>
                    </DataListCell>
                  </DataListItemRow>
                </DataListItem>
              ))}
            </DataList>
          ) : (
            <p>Loading issues for {selectedRepo}...</p>
          )}
        </PageSection>
      )}

      {selectedIssue && (
        <PageSection hasBodyWrapper={false}>
          <Button onClick={handleBackToIssues} variant="primary" style={{ marginBottom: '1rem' }}>
            Back to Issues
          </Button>
          <Card>
            <CardTitle>
              <Title headingLevel="h2">{selectedIssue.title}</Title>
            </CardTitle>
            <CardBody>
              <Content>
                <Content component="p">Issue #{selectedIssue.number}</Content>
                <Content component="p">{selectedIssue.body}</Content>
              </Content>

              <div style={{ marginTop: '1rem' }}>
                <TextInput
                  value={aiTextBox}
                  onChange={(_event, value) => setAiTextBox(value)}
                  aria-label="AI command input"
                  placeholder="Send a command to py..."
                />
                <Button onClick={handlePyAction} variant="primary" style={{ marginTop: '1rem' }}>
                  Send to Py
                </Button>
                <div style={{ marginTop: '1rem' }}>
                  {isThinking ? (
                    <Spinner />
                  ) : (
                    <CodeBlock>
                      <pre>{pyOutput}</pre>
                    </CodeBlock>
                  )}
                </div>
              </div>
            </CardBody>
          </Card>
        </PageSection>
      )}
    </Page>
  );
}

export default App;
