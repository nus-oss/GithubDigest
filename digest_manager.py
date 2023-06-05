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

</details>
"""

digest_content = """
Subscribe to this issue to receive a digest of all the issues in this repository.
"""

class DigestManager:
    """
    DigestManager is a class that manages the digest process.
    It is responsible for querying for issues and comments, as well as sending the digest to the target repository.

    args:
        target_repo: str - the repository to query for issues
        local_repo: str - the repository to send the digest to
        target_issue: str - the issue to send the digest to
        ignore_numbers: list[int] - a list of issue numbers to ignore, default to nothing
    """
    cursor:str = None
    target_repo: str
    local_repo: str
    timestamp: datetime
    target_issue: str
    complete: bool
    ignore_numbers: list[int]
    last_update_time: datetime
    query = MainQuery()

    def __init__(self, target_repo:str, local_repo:str, target_issue:str, ignore_numbers=[]) -> None:
        self.target_repo = target_repo
        self.local_repo = local_repo
        self.target_issue = target_issue
        self.complete = False
        self.ignore_numbers = ignore_numbers
        self.create_issue()
        self.update_last_change_date()

    def run_query(self, additional_queries: list[str] = []) -> dict:
        """
        run_query runs the main query to query for issues if the pagination of the main query is not complete.
        It will also run additional queries if provided. The additional queries are expected to be partial queries.

        args:
            additional_queries: list[str] - a list of additional queries to run
        """
        if not self.complete:
            additional_queries.append(
                self.query.partial_query(
                    self.target_repo,
                    helper.format_to_utc(self.last_update_time),
                    self.cursor)
            )
        res = run_queries(additional_queries)
        return res
    
    def get_result(self) -> list[GitIssue]:
        """
        get_result is a runs the main query to query for issues as well as fetch comments for each issue
        until all comments of each issue is fetched.

        returns:
            list[GitIssue] - a list of GitIssue objects
        """ 
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
        """
        update_cursor updates the cursor and complete flag based on the pageInfo of the main query.

        args:
            graphqlResult: dict - the result of the main query
        """
        self.cursor = graphqlResult["endCursor"]
        self.complete = not graphqlResult["hasNextPage"]
    
    def convert_data(self, graphqlResult: dict, ret: dict[str, GitIssue]):
        """
        convert_data converts the graphql result into GitIssue objects and stores them in the ret dictionary
        with the issue id as the key.

        args:
            graphqlResult: dict - the result of the main query
            ret: dict[str, GitIssue] - the dictionary to store the GitIssue objects, this will be mutated in place
        """
        for raw_issue in graphqlResult:
            if not raw_issue: 
                continue
            
            issue = GitIssue(raw_issue, (self.last_update_time, helper.get_now()))
            if issue.number in self.ignore_numbers or issue.id == self.target_issue:
                # ignore the target issue and the issues in the ignore list
                continue

            ret[issue.id] = issue
    
    def send_data(self, issues: list[GitIssue]):
        """
        send_data sends mutation to update the digest issue with the new data.
        It takes in a list of GitIssue objects and only sends the data if there are changes.

        args:
            issues: list[GitIssue] - a list of GitIssue objects
        """
        issues = [issue for issue in issues if issue.total_changes > 0]
        total_changes = sum([issue.total_changes for issue in issues])
        if total_changes == 0:
            # no changes were detected
            return

        r1 = UpdateIssue("update_issue").partial_query(self.target_issue, digest_content)
        r2 = AddComment("new_digest").partial_query(self.target_issue, digest_header.format(
                    time_start=helper.format_local(self.last_update_time),
                    time_end=helper.format_local(helper.get_now()),
                    all_changes=total_changes,
                    issues_changed=len(issues),
                    body='\n'.join([issue.to_markdown() for issue in issues])
                ))
        
        run_mutations([r1, r2])

    def find_repo_id(self) -> str:
        """
        find_repo_id finds the repo id of the target repo.
        """
        owner, repo = self.local_repo.split("/")
        q = FindRepoId("find_repo_id")
        res = q.run(owner=owner, repo=repo)

        return q.get_repo_id(res)
    
    def update_last_change_date(self):
        """
        update_last_change_date updates the last update time of the digest issue based on the last comment date.

        By default, if there are no comments in the digest issue, the last update time will
        be 3 days prior to the current time.
        """
        q = ReadLastCommentDate("read_last_comment")
        res = q.run(issue_id=self.target_issue)
        self.last_update_time = q.get_last_comment_date(res) or helper.get_n_day_prior(3)

    def create_issue(self):
        """
        create_issue creates the digest issue if it does not exist and update the target_issue field.
        If the target repo is the same as the local repo, then the issue number is added to the ignore list.
        """
        if self.target_issue:
            # issue already exist
            return
        repo_id = self.find_repo_id()
        q = CreateIssue("create_issue")
        res = q.run(repo_id=repo_id, title="Issues Digest", body=digest_content)

        self.target_issue = q.get_issue_id(res)
        if self.local_repo == self.target_repo:
            self.ignore_numbers.append(q.get_issue_number(res))
