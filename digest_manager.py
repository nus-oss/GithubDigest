from datetime import datetime, timedelta
from git_structures import GitIssue
from gql_queries import AddComment, UpdateIssue, MainQuery, FindRepoId, ReadLastCommentDate, CreateIssue, run_queries, run_mutations
import helper

digest_header = """<details>
<summary>
<h2>Digest Summary: {time_end}</h2>
<p>Tracked {all_changes} changes across {issues_changed} issues</p>
<p>From {time_start} to {time_end}</p>
</summary>

{body}

</summary>
"""

digest_content = """
Subscribe to this issue to receive a digest of all the issues in this repository.
"""

class DigestManager:
    cursor:str = None
    owner: str
    repo: str
    timestamp: datetime
    target_issue: str
    complete: bool
    ignore_numbers: list[int]
    last_update_time: datetime
    query = MainQuery()

    def __init__(self, owner:str, repo:str, target_issue:str, ignore_numbers=[]) -> None:
        self.owner = owner
        self.repo = repo
        self.target_issue = target_issue
        self.complete = False
        self.ignore_numbers = ignore_numbers
        self.last_update_time = datetime.now() - timedelta(days=1)
        self.create_issue()
        self.update_last_change_date()

    @property
    def repo_repr(self) -> str:
        return f"{self.owner}/{self.repo}"

    def run_query(self, additional_queries: list[str] = []) -> dict:
        if not self.complete:
            additional_queries.append(
                self.query.partial_query(
                    self.repo_repr,
                    self.last_update_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    self.cursor)
            )
        res = run_queries(additional_queries)
        return res
    
    def get_result(self) -> list[GitIssue]:
        ret: dict[str, GitIssue] = {}
        extra = []
        while not self.complete or (extra := [ret[key].draft_gql_query() for key in ret if ret[key].has_more_data]):
            res = self.run_query(extra)
            if not self.complete:
                main_res = self.query.read_result(res)
                self.update_cursor(main_res["pageInfo"])
                self.convert_data(main_res["nodes"], ret)
            if extra:
                for key in ret:
                    if ret[key].has_more_data:
                        ret[key].read_paginated_comments(ret[key].comments_query.read_result(res))
        
        return [ret[key] for key in ret]
    
    def update_cursor(self, graphqlResult: dict):
        self.cursor = graphqlResult["endCursor"]
        self.complete = not graphqlResult["hasNextPage"]
    
    def convert_data(self, graphqlResult: dict, ret: dict[str, GitIssue]):
        for raw_issue in graphqlResult:
            if (raw_issue and raw_issue["number"] not in self.ignore_numbers):
                issue = GitIssue(raw_issue, (self.last_update_time, datetime.now()))
                ret[issue.id] = issue
    
    def send_data(self, issues: list[GitIssue]):
        r1 = UpdateIssue("update_issue").partial_query(self.target_issue, digest_content)
        r2 = AddComment("new_digest").partial_query(self.target_issue, digest_header.format(
                    time_start=self.last_update_time.strftime("%Y-%m-%d %H:%M:%S"),
                    time_end=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    all_changes=sum([issue.total_changes for issue in issues]),
                    issues_changed=len(issues),
                    body='\n'.join([issue.to_markdown() for issue in issues])
                ))
        
        run_mutations([r1, r2])

    def find_repo_id(self) -> str:
        q = FindRepoId("find_repo_id")
        res = q.run(owner=self.owner, repo=self.repo)

        return q.get_repo_id(res)
    
    def update_last_change_date(self):
        q = ReadLastCommentDate("read_last_comment")
        res = q.run(issue_id=self.target_issue)
        self.last_update_time = q.get_last_comment_date(res) or helper.get_n_day_prior(3)

    def create_issue(self):
        if self.target_issue:
            # issue already exist
            return
        repo_id = self.find_repo_id()
        q = CreateIssue("create_issue")
        res = q.run(repo_id=repo_id, title="Issues Digest", body=digest_content)
        self.target_issue = q.get_issue_id(res)
        self.ignore_numbers.append(q.get_issue_number(res))

