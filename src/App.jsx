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
  Masthead,
  MastheadMain,
  MastheadBrand,
  MastheadContent,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Select,
  SelectOption,
  MenuToggle
} from '@patternfly/react-core';

function App() {
  const [token, setToken] = useState(null);
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [issues, setIssues] = useState([]);
  const [categorizedIssues, setCategorizedIssues] = useState({ Major: [], Minor: [], Bug: [] });
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [aiTextBox, setAiTextBox] = useState('');
  const [pyOutput, setPyOutput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);

  const onToggle = isOpen => {
    setIsOpen(isOpen);
  };

  const onSelect = (event, selection) => {
    handleRepoSelect(selection);
    setIsOpen(false);
  };

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
        console.log('Fetched repos:', data);
        setRepos(data);
      } catch (error) {
        console.error('Error fetching repos:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRepos();
  }, [token]);

  const categorizeIssues = async (issues) => {
    try {
      const issueTitles = issues.map(issue => issue.title);
      const response = await fetch('http://127.0.0.1:8000/api/v1/ai/categorize-issues', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ issue_titles: issueTitles })
      });
      const categorized = await response.json();
      
      const categorizedWithFullIssues = {
        Major: categorized.Major.map(title => issues.find(i => i.title === title)).filter(Boolean),
        Minor: categorized.Minor.map(title => issues.find(i => i.title === title)).filter(Boolean),
        Bug: categorized.Bug.map(title => issues.find(i => i.title === title)).filter(Boolean),
      };
      console.log('Categorized issues:', categorizedWithFullIssues);
      setCategorizedIssues(categorizedWithFullIssues);
    } catch (error) {
      console.error('Error categorizing issues:', error);
    }
  };

  const handleRepoSelect = async (repoName) => {
    setSelectedRepo(repoName);
    setSelectedIssue(null);
    setIssues([]);
    setCategorizedIssues({ Major: [], Minor: [], Bug: [] });
    setSelectedCategory(null); // Reset selected category when a new repo is selected
    try {
      const response = await fetch(`http://127.0.0.1:8000/issues?repo=${repoName}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setIssues(data);
      if (data.length > 0) {
        await categorizeIssues(data);
      }
    } catch (error) {
      console.error(`Error fetching issues for ${repoName}:`, error);
    }
  };

  const handleIssueClick = (issue) => {
    console.log('Issue clicked:', issue);
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
      setPyOutput(data);
    } catch (error) {
      console.error('Error sending command to py:', error);
    } finally {
      setIsThinking(false);
    }
  };

  if (loading) {
    return <Bullseye><Spinner /></Bullseye>;
  }

  if (!token) {
    return (
      <Bullseye>
        <EmptyState>
          <EmptyStateBody>Please log in with your GitHub account to continue.</EmptyStateBody>
          <Button component="a" href="http://127.0.0.1:8000/login/github" variant="primary">
            Login with GitHub
          </Button>
        </EmptyState>
      </Bullseye>
    );
  }

  const headerToolbar = (
    <Toolbar>
      <ToolbarContent>
        <ToolbarItem>
          <Select
            variant="single"
            onSelect={onSelect}
            selections={selectedRepo}
            isOpen={isOpen}
            toggle={(toggleRef) => (
              <MenuToggle
                ref={toggleRef}
                onClick={() => onToggle(!isOpen)}
                isExpanded={isOpen}
              >
                {selectedRepo || 'Select a Repository'}
              </MenuToggle>
            )}
          >
            {repos.map((repo) => (
              <SelectOption key={repo} value={repo}>
                {repo}
              </SelectOption>
            ))}
          </Select>
        </ToolbarItem>
      </ToolbarContent>
    </Toolbar>
  );

  const header = (
    <Masthead>
      <MastheadMain>
        <MastheadBrand>Buglit</MastheadBrand>
      </MastheadMain>
      <MastheadContent>{headerToolbar}</MastheadContent>
    </Masthead>
  );

  const renderIssueList = (title, issues) => (
    <PageSection>
      <Title headingLevel="h2">{title}</Title>
      {issues && issues.length > 0 ? (
        <DataList aria-label={`${title} issues list`}>
          {issues.map(issue => (
            <DataListItem key={issue.number} className="issue-list-item" aria-labelledby={`issue-${issue.number}`} onClick={() => handleIssueClick(issue)} isSelectable>
              <DataListItemRow>
                <DataListCell>
                  <Content>
                    <Content component="h3">{issue.title}</Content>
                  </Content>
                </DataListCell>
              </DataListItemRow>
            </DataListItem>
          ))}
        </DataList>
      ) : (
        <p>No issues in this category.</p>
      )}
    </PageSection>
  );

  return (
    <Page header={header}>
      {!selectedRepo && (
        <PageSection>
          <EmptyState>
            <select className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
              <option>Select a repository</option>
            </select>
          </EmptyState>
        </PageSection>
      )}

      {selectedRepo && !selectedCategory && !selectedIssue && (
        <PageSection>
          <Title headingLevel="h2">Issue Categories</Title>
          <DataList aria-label="Issue categories">
            {Object.entries(categorizedIssues).map(([category, issues]) => (
              <DataListItem
                key={category}
                isSelectable
                onClick={() => setSelectedCategory(category)}
              >
                <DataListItemRow>
                  <DataListCell>
                    <Content>
                      <Content component="h3">{category}</Content>
                      <Content component="p">{issues.length} issues</Content>
                    </Content>
                  </DataListCell>
                </DataListItemRow>
              </DataListItem>
            ))}
          </DataList>
        </PageSection>
      )}

      {selectedRepo && selectedCategory && !selectedIssue && (
        <PageSection>
          <Button onClick={() => setSelectedCategory(null)} variant="primary" style={{ marginBottom: '1rem' }}>
            Back to Categories
          </Button>
          {renderIssueList(selectedCategory, categorizedIssues[selectedCategory])}
        </PageSection>
      )}

      {selectedRepo && selectedIssue && (
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
                  {isThinking ? <Spinner /> : <CodeBlock><pre>{pyOutput}</pre></CodeBlock>}
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