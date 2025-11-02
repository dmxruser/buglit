import React, { useState, useEffect } from 'react';
import { MdArrowBack } from 'react-icons/md';
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
    console.log('Selected repo:', selection);  // Debug log
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
        const response = await fetch('/user/repos', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await response.json();
        console.log('Raw repos data:', data);
        // Make sure repos are in the correct format
        const formattedRepos = Array.isArray(data) ? data : [];
        console.log('Formatted repos:', formattedRepos);
        setRepos(formattedRepos);
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
      const response = await fetch('/api/v1/ai/categorize-issues', {
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
      setCategorizedIssues(categorizedWithFullIssues);
    } catch (error) {
      console.error('Error categorizing issues:', error);
    }
  };

  const handleRepoSelect = async (repoName) => {
    console.log('handleRepoSelect called with:', repoName);  // Debug log
    if (!repoName) {
      console.error('No repo name provided to handleRepoSelect');
      return;
    }
    setSelectedRepo(repoName);
    setSelectedIssue(null);
    setIssues([]);
    setCategorizedIssues({ Major: [], Minor: [], Bug: [] });
    try {
      console.log(`Fetching issues for repo: ${repoName}`);  // Debug log
      const response = await fetch(`/issues?repo=${repoName}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      console.log('Fetched issues:', data);  // Debug log
      setIssues(data);
      if (data.length > 0) {
        await categorizeIssues(data);
      }
    } catch (error) {
      console.error(`Error fetching issues for ${repoName}:`, error);
    }
  };

  const handleIssueClick = (issue) => {
    setSelectedIssue(issue);
  };

  const handleBackToIssues = () => {
    setSelectedIssue(null);
    setSelectedCategory(null);
  };
  
  const handleCategorySelect = (category) => {
    setSelectedCategory(category);
  };

  const handlePyAction = async () => {
    setIsThinking(true);
    setPyOutput('');
    try {
      const response = await fetch('/run-command', {
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
          <Button component="a" href="/login/github" variant="primary">
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
      <PageSection>
        <Select
          variant="single"
          onToggle={(_event, isOpen) => setIsOpen(isOpen)}
          onSelect={onSelect}
          selections={selectedRepo}
          isOpen={isOpen}
          toggle={(toggleRef) => (
            <MenuToggle ref={toggleRef} onClick={() => setIsOpen(!isOpen)} isExpanded={isOpen}>
              {selectedRepo || "Select a Repository"}
            </MenuToggle>
          )}
          style={{ width: '300px' }}
        >
          {repos.map((repo) => (
            <SelectOption key={repo} value={repo} className="repo-option-text">
              {repo}
            </SelectOption>
          ))}
        </Select>
        {!selectedRepo && (
          <EmptyState style={{ marginTop: '1rem' }}>
            <EmptyStateBody>
              Please select a repository to begin.
            </EmptyStateBody>
          </EmptyState>
        )}
      </PageSection>

      {selectedRepo && !selectedIssue && (
        <>
          {!selectedCategory ? (
            <PageSection>
              <Title headingLevel="h2">Categories</Title>
              <DataList aria-label="Issue categories">
                {Object.entries(categorizedIssues).map(([category, issues]) => (
                  <DataListItem
                    key={category}
                    isSelectable
                    onClick={() => handleCategorySelect(category)}
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
          ) : (
            <PageSection>
              <Button
                variant="link"
                icon={<MdArrowBack />}
                onClick={() => setSelectedCategory(null)}
                style={{ marginBottom: '1rem' }}
                iconPosition="left"
              >
                Back to Categories
              </Button>
              {renderIssueList(selectedCategory, categorizedIssues[selectedCategory])}
            </PageSection>
          )}
        </>
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
// Added a comment to force re-evaluation