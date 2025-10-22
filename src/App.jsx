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
  PageSidebar,
  Nav,
  NavList,
  NavItem
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

  const sortIssues = async (issues) => {
    try {
      const issueTitles = issues.map(issue => issue.title);
      const response = await fetch('http://127.0.0.1:8000/api/v1/ai/sort-issues', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ issue_titles: issueTitles })
      });
      const sortedTitles = await response.json();
      const sortedIssues = issues.slice().sort((a, b) => {
        const aIndex = sortedTitles.indexOf(a.title);
        const bIndex = sortedTitles.indexOf(b.title);
        if (aIndex === -1) return 1;
        if (bIndex === -1) return -1;
        return aIndex - bIndex;
      });
      setIssues(sortedIssues);
    } catch (error) {
      console.error('Error sorting issues:', error);
    }
  };

  const handleRepoClick = async (repoName) => {
    setSelectedRepo(repoName);
    setSelectedIssue(null); // Deselect issue when changing repo
    setIssues([]); // Clear previous issues
    try {
      const response = await fetch(`http://127.0.0.1:8000/issues?repo=${repoName}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setIssues(data);
      if (data.length > 0) {
        await sortIssues(data);
      }
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
      const response = await fetch('http://127.0.0.1:8000/run-command', {
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
      <Bullseye>
          <EmptyState>
            <EmptyStateBody>
              Please log in with your GitHub account to continue.
            </EmptyStateBody>
            <Button component="a" href="http://127.0.0.1:8000/login/github" variant="primary">
              Login with GitHub
            </Button>
          </EmptyState>
        </Bullseye>
    );
  }

  const sidebar = (
      <PageSidebar>
      <Nav>
        <NavList className='sidebar'>
          <Title headingLevel="h2">Repositories</Title>
          {repos.map((repo, index) => (
            <NavItem key={index} isActive={selectedRepo === repo} onClick={() => handleRepoClick(repo)}>
              {repo}
            </NavItem>
          ))}
        </NavList>
      </Nav>
    </PageSidebar>
  );

  return (
    <Page sidebar={sidebar}>
      {!selectedRepo && (
        <PageSection>
          <Title headingLevel="h1">Select a repository to begin</Title>
        </PageSection>
      )}

      {selectedRepo && !selectedIssue && (
        <PageSection>
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
        <PageSection>
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
                  Do that
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