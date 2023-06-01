from os import environ
from datetime import datetime
import helper
import requests
from string import Template
from graphql_query_templates import *

try:
    API_KEY = environ["GIT_SECRET"]
except KeyError:
    API_KEY = "Token not available!"

url = "https://api.github.com/graphql"
headers = {
    "Authorization": f"token {API_KEY}",
}

def run_queries(queries: list[str]) -> dict:
    payload = {
        "query": f"{{{','.join([q for q in queries])}}}"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()["data"]

def run_mutations(queries: list[str]) -> dict:
    payload = {
        "query": f"mutation {{{','.join([q for q in queries])}}}"
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()["data"]

class GithubQuery:
    query: Template
    id: str
    mutation: bool

    def __init__(self, query: Template, id: str, mutation: bool = False):
        self.query = query
        self.id = id
        self.mutation = mutation

    def run(self, **kwargs) -> dict:
        payload = {
            "query": f"{'mutation ' if self.mutation else ''}{{{self.partial_query(**kwargs)}}}"
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()["data"]

    def partial_query(self, **kwargs) -> str:
        return f"{self.id}:{self.query.substitute(**kwargs)}"
    
    def read_result(self, graphql_result: dict) -> dict:
        return graphql_result[self.id]


class AddComment(GithubQuery):
    def __init__(self, id: str):
        super().__init__(add_comment_template, id, mutation=True)

    """
    :param issue_id: The ID of the issue to add a comment to
    :param comment_body: The body of the comment to add
    :return: A partial GraphQL query string
    """
    def partial_query(self, issue_id:str, comment_body:str) -> str:
        return super().partial_query(issue_id=issue_id, comment_body=comment_body)
    
    """
    :param issue_id: The ID of the issue to add a comment to
    :param comment_body: The body of the comment to add
    :return: graphquery result
    """
    def run(self, issue_id:str, comment_body:str) -> dict:
        return super().run(issue_id=issue_id, comment_body=comment_body)

class CreateIssue(GithubQuery):
    def __init__(self, id: str):
        super().__init__(create_issue_template, id, mutation=True)

    """
    :param repo_id: The ID of the repo to create an issue in
    :param title: The title of the issue to create
    :param body: The body of the issue to create
    :return: A partial GraphQL query string
    """
    def partial_query(self, repo_id:str, title:str, body:str) -> str:
        return super().partial_query(repo_id=repo_id, title=title, body=body)
    
    """
    :param repo_id: The ID of the repo to create an issue in
    :param title: The title of the issue to create
    :param body: The body of the issue to create
    :return: graphquery result
    """
    def run(self, repo_id:str, title:str, body:str) -> dict:
        return super().run(repo_id=repo_id, title=title, body=body)
    
    def get_issue_id(self, graphqlResult: dict) -> str:
        return self.read_result(graphqlResult)["issue"]["id"]
    
    def get_issue_number(self, graphqlResult: dict) -> int:
        return self.read_result(graphqlResult)["issue"]["number"]
    
class UpdateIssue(GithubQuery):
    def __init__(self, id: str):
        super().__init__(update_issue_template, id)

    """
    :param issue_id: The ID of the issue to update
    :param issue_body: The body of the issue to update
    :return: A partial GraphQL query string
    """
    def partial_query(self, issue_id:str, issue_body:str) -> str:
        return super().partial_query(issue_id=issue_id, issue_body=issue_body)
    
    """
    :param issue_id: The ID of the issue to update
    :param issue_body: The body of the issue to update
    :return: graphquery result
    """
    def run(self, issue_id:str, issue_body:str) -> dict:
        return super().run(issue_id=issue_id, issue_body=issue_body)

class FindRepoId(GithubQuery):
    def __init__(self, id: str):
        super().__init__(find_repo_id_template, id)

    """
    :param owner: The owner of the repo to find
    :param repo: The name of the repo to find
    :return: A partial GraphQL query string
    """
    def partial_query(self, owner:str, repo:str) -> str:
        return super().partial_query(owner=owner, repo=repo)
    
    """
    :param owner: The owner of the repo to find
    :param repo: The name of the repo to find
    :return: graphquery result
    """
    def run(self, owner:str, repo:str) -> dict:
        return super().run(owner=owner, repo=repo)
    
    """
    returns the id of the repository of a FindRepoId query
    :param graphqlResult: The result of the graphquery
    """
    def get_repo_id(self, graphqlResult: dict) -> str:
        return self.read_result(graphqlResult)["id"]
    
class ReadLastCommentDate(GithubQuery):
    def __init__(self, id: str):
        super().__init__(read_last_comment_template, id)

    """
    :param issue_id: The ID of the issue to read
    :return: A partial GraphQL query string
    """
    def partial_query(self, issue_id: str) -> str:
        return super().partial_query(issue_id=issue_id)
    
    """
    :param issue_id: The ID of the issue to read
    :return: graphquery result
    """
    def run(self, issue_id:str) -> dict:
        return super().run(issue_id=issue_id)
    
    """
    returns the last comment date of a ReadLastCommentDate query
    :param graphqlResult: The result of the graphquery
    """
    def get_last_comment_date(self, graphqlResult: dict) -> datetime | None:
        comments = super().read_result(graphqlResult)["comments"]["nodes"]
        if len(comments):
            return helper.convertToDateTime(comments[-1]["createdAt"])
        return None
    
class ReadComments(GithubQuery):
    def __init__(self, id: str):
        super().__init__(read_comments_template, id)
    
    """
    :param issue_id: The ID of the issue to read
    :param cursor: The cursor to read from
    :return: A partial GraphQL query string
    """
    def partial_query(self, url: str, cursor: str) -> str:
        return super().partial_query(url=url, cursor=cursor)
    
    """
    :param issue_id: The ID of the issue to read
    :param cursor: The cursor to read from
    :return: graphquery result
    """
    def run(self, url: str, cursor: str) -> str:
        return super().run(url=url, cursor=cursor)

class MainQuery(GithubQuery):
    def __init__(self):
        super().__init__(main_query_template, "main")

    """
    :param repo: The name of the repo to query
    :param timestamp: The timestamp to query from
    :param cursor: The cursor to query from
    :return: A partial GraphQL query string
    """
    def partial_query(self, repo: str, timestamp: str, cursor: str = None) -> str:
        if not cursor:
            cursor = "null"
        else:
            cursor = f'"{cursor}"'
        return super().partial_query(repo=repo, timestamp=timestamp, cursor=cursor)
    
    """
    :param repo: The name of the repo to query
    :param timestamp: The timestamp to query from
    :param cursor: The cursor to query from
    :return: graphquery result
    """
    def run(self, repo: str, timestamp: str, cursor: str = None) -> str:
        return super().run(repo=repo, timestamp=timestamp, cursor=cursor)
    
