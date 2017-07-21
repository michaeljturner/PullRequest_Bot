import json, requests
from datetime import datetime


# Class for interacting with the GitHub GraphQL API (APIv4)
class GitHubBot(object):
    

    def __init__(self):
        # GitHub Graph QL endpoint
        self.endpoint = "https://api.github.com/graphql"

        # GitHub Personal Access Token
        pat_file = open('personal_access_token', 'r')

        bearer_token = "Bearer %s" % pat_file.readline().replace('\n', '')
        self.auth = {"Authorization": bearer_token}

        pat_file.close()

        # GraphQL variables (initialized to default repository)
        self.variables = {"repo_owner": "mantidproject", "repo_name": "mantid"}

        # GraphQL results per page (max: 100)
        self.page_size = 100

        # Days a PR can be dormant, before becoming stale
        self.staleThreshold = 7


    # Sends GraphQL query as a JSON object
    # Returns reply as nested python dictionary
    def sendQuery(self, query):
        # Read query and variables into JSON string
        payload = json.dumps({"query": query, "variables": self.variables})

        # Convert python 'None' to GraphQL 'null' to allow optional variables
        payload = payload.replace("None", "null")

        # Post query, and recieve reply
        reply = requests.post(self.endpoint, payload, headers=self.auth)

        # Return nested python dictionary
        return reply.json()


    # Calculates the difference between time now and the input time in days
    def elapsedDays(self, timeString):
        inputTime = datetime.strptime(timeString, "%Y-%m-%dT%H:%M:%SZ")

        return (datetime.now() - inputTime).days
        
        
    # Fetches pull request number of all stale pull requests
    def fetchStalePullRequests(self):
        # GraphQL query
        query = """
query($repo_owner: String!, $repo_name: String!, $page_size: Int!, $cursor: String){
    repository(owner: $repo_owner, name: $repo_name){
        pullRequests(first: $page_size, after: $cursor, states: [OPEN]){
            pageInfo{
                hasNextPage
                endCursor
            }
            nodes{
                number
                updatedAt
            }
        }
    }
}
"""
        # Create optional cursor variable (used for pagination)
        self.variables['cursor'] = None
        # Set number of results per page (max: 100)
        self.variables['page_size'] = self.page_size

        # Container for Pull Request: number, updatedAt fields
        stalePRs = []
        
        # Fetch data from GitHub, iterate through Pull Requests if
        # there are more pages of data
        while True:
            #Store reply
            data = self.sendQuery(query)

            # Iterate through the nodes list, check if Pull Request is stale
            # If stale, append PR to list of stale Pull Requests
            for pullRequest in data['data']['repository']['pullRequests']['nodes']:
                # Check if pull request is stale
                days_dormant = self.elapsedDays(pullRequest['updatedAt'])
                
                if days_dormant >= self.staleThreshold:
                    stalePRs.append((pullRequest['number'], days_dormant))

            # If more pull requests, update cursor to point to new page
            if data['data']['repository']['pullRequests']['pageInfo']['hasNextPage']:
                self.variables['cursor'] = data['data']['repository']['pullRequests']\
                                           ['pageInfo']['endCursor']
            else:
                # No more data, stop pagination
                break

        # Remove non-default variables
        del self.variables['page_size'], self.variables['cursor']

        # Return stale Pull Requests as tuple (number, days elapsed)
        return stalePRs
        

if __name__ == '__main__':

    g = GitHubBot()

    stalePRs = g.fetchStalePullRequests()

    print(stalePRs)
