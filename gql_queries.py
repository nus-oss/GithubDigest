from os import environ
from datetime import datetime
import sys
import helper
import requests
from string import Template
from graphql_query_templates import *

try:
    API_KEY = environ["GIT_SECRET"]
except KeyError:
    print("Token not available!", file=sys.stderr)
    exit(1)

url = "https://api.github.com/graphql"
headers = {
    "Authorization": f"token {API_KEY}",
}

def handle_errors(response: requests.Response) -> None:
    """
    If query fails, print the error message and exit the program

    args:
        response: requests.Response - the response object
    """
    if response.status_code != 200:
        print("Query failed to run by returning code of {}. {}".format(response.status_code, response.text), file=sys.stderr)
        exit(1)

    data = response.json()

    if 'errors' in data:
        errors = data["errors"]
        for error in errors:
            print("Error: {}".format(error["message"]), file=sys.stderr)
        exit(1)

def run_queries(queries: list[str]) -> dict:
    """
    Run a list of GraphQL queries to Github

    args:
        queries: list[str] - the list of queries to run
    
    returns:
        dict - the result of the query
    """
    payload = {
        "query": f"{{{','.join([q for q in queries])}}}"
    }
    response = requests.post(url, json=payload, headers=headers)
    handle_errors(response)
    return response.json()["data"]

def run_mutations(queries: list[str]) -> dict:
    """
    Run a list of GraphQL mutations to Github

    args:
        queries: list[str] - the list of mutations to run
    
    returns:
        dict - the result of the mutation
    """
    payload = {
        "query": f"mutation {{{','.join([q for q in queries])}}}"
    }

    response = requests.post(url, json=payload, headers=headers)
    handle_errors(response)
    return response.json()["data"]

class GithubQuery:
    """
    GithubQuery is a base class representing a GraphQL query to Github

    args:
        query: Template - the query template
        id: str - the id of the query
        mutation: bool - whether the query is a mutation
    """
    query: Template
    id: str
    mutation: bool

    def __init__(self, query: Template, id: str, mutation: bool = False):
        self.query = query
        self.id = id
        self.mutation = mutation

    def run(self, **kwargs) -> dict:
        """
        run runs the query with the given arguments

        args:
            kwargs: dict - the arguments to substitute into the query string
        """
        payload = {
            "query": f"{'mutation ' if self.mutation else ''}{{{self.partial_query(**kwargs)}}}"
        }

        response = requests.post(url, json=payload, headers=headers)
        handle_errors(response)
        return response.json()["data"]

    def partial_query(self, **kwargs) -> str:
        """
        partial_query returns a partial GraphQL query string with the given arguments substituted in

        args:
            kwargs: dict - the arguments to substitute into the query string
        """
        return f"{self.id}:{self.query.substitute(**kwargs)}"
    
    def read_result(self, graphql_result: dict) -> dict:
        """
        read_result reads the result of the query and returns the result of the query corresponding to the id
        of this query.

        args:
            graphql_result: dict - the result of the query

        returns:
            dict - the result of the query corresponding to the id of this query
        """
        return graphql_result[self.id]


class AddComment(GithubQuery):
    """
    AddComment represents a GraphQL mutation to add a comment to an issue

    args:
        id: str - the id of the query
    """
    def __init__(self, id: str):
        super().__init__(add_comment_template, id, mutation=True)

    def partial_query(self, issue_id:str, comment_body:str) -> str:
        return super().partial_query(issue_id=issue_id, comment_body=comment_body)
    
    def run(self, issue_id:str, comment_body:str) -> dict:
        return super().run(issue_id=issue_id, comment_body=comment_body)

class CreateIssue(GithubQuery):
    """
    CreateIssue represents a GraphQL mutation to create an issue

    args:
        id: str - the id of the query
    """
    def __init__(self, id: str):
        super().__init__(create_issue_template, id, mutation=True)


    def partial_query(self, repo_id:str, title:str, body:str) -> str:
        return super().partial_query(repo_id=repo_id, title=title, body=body)
    
    def run(self, repo_id:str, title:str, body:str) -> dict:
        return super().run(repo_id=repo_id, title=title, body=body)
    
    def get_issue_id(self, graphqlResult: dict) -> str:
        """
        get_issue_id returns the id of the issue created by this mutation

        args:
            graphqlResult: dict - the result of the query

        returns:
            str - the id of the issue created by this mutation
        """
        return self.read_result(graphqlResult)["issue"]["id"]
    
    def get_issue_number(self, graphqlResult: dict) -> int:
        """
        get_issue_number returns the issue number created by this mutation

        args:
            graphqlResult: dict - the result of the query

        returns:
            int - the issue number created by this mutation
        """
        return self.read_result(graphqlResult)["issue"]["number"]
    
class UpdateIssue(GithubQuery):
    """
    UpdateIssue represents a GraphQL mutation to update the body of an issue

    args:
        id: str - the id of the query
    """
    def __init__(self, id: str):
        super().__init__(update_issue_template, id)

    def partial_query(self, issue_id:str, issue_body:str) -> str:
        return super().partial_query(issue_id=issue_id, issue_body=issue_body)
    
    def run(self, issue_id:str, issue_body:str) -> dict:
        return super().run(issue_id=issue_id, issue_body=issue_body)

class FindRepoId(GithubQuery):
    """
    FindRepoId represents a GraphQL query to find the id of a repository

    args:
        id: str - the id of the query
    """
    def __init__(self, id: str):
        super().__init__(find_repo_id_template, id)

    def partial_query(self, owner:str, repo:str) -> str:
        return super().partial_query(owner=owner, repo=repo)
    
    def run(self, owner:str, repo:str) -> dict:
        return super().run(owner=owner, repo=repo)
    
    def get_repo_id(self, graphqlResult: dict) -> str:
        """
        get_repo_id returns the id of the repository

        args:
            graphqlResult: dict - the result of the query

        returns:
            str - the id of the repository
        """
        return self.read_result(graphqlResult)["id"]
    
class ReadLastCommentDate(GithubQuery):
    """
    ReadLastCommentDate represents a GraphQL query to read the date of the last comment on an issue

    args:
        id: str - the id of the query
    """
    def __init__(self, id: str):
        super().__init__(read_last_comment_template, id)

    def partial_query(self, issue_id: str) -> str:
        return super().partial_query(issue_id=issue_id)
    
    def run(self, issue_id:str) -> dict:
        return super().run(issue_id=issue_id)
    
    def get_last_comment_date(self, graphqlResult: dict) -> datetime | None:
        """
        get_last_comment_date returns the date of the last comment on the issue, or None if there are no comments

        args:
            graphqlResult: dict - the result of the query

        returns:
            datetime | None - the date of the last comment on the issue, or None if there are no comments
        """
        comments = super().read_result(graphqlResult)["comments"]["nodes"]
        if len(comments):
            return helper.convertToDateTime(comments[-1]["createdAt"])
        return None
    
class ReadComments(GithubQuery):
    """
    ReadComments represents a GraphQL query to read the comments on an issue

    args:
        id: str - the id of the query
    """
    def __init__(self, id: str):
        super().__init__(read_comments_template, id)
    
    def partial_query(self, url: str, cursor: str) -> str:
        return super().partial_query(url=url, cursor=cursor)
    
    def run(self, url: str, cursor: str) -> str:
        return super().run(url=url, cursor=cursor)

class MainQuery(GithubQuery):
    """
    MainQuery represents a GraphQL query to read the issues in a repository based on update time range
    """
    def __init__(self):
        super().__init__(main_query_template, "main")

    def partial_query(self, repo: str, timestamp: str, cursor: str = None) -> str:
        if not cursor:
            cursor = "null"
        else:
            cursor = f'"{cursor}"'
        return super().partial_query(repo=repo, timestamp=timestamp, cursor=cursor)
    
    def run(self, repo: str, timestamp: str, cursor: str = None) -> str:
        return super().run(repo=repo, timestamp=timestamp, cursor=cursor)
    
