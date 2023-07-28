from datetime import datetime, timedelta
from git_structures import GitIssue
from gql_queries import AddComment, LockIssue, ReadIssueLock, UnlockIssue, UpdateIssue, MainQuery, FindRepoId, ReadLastCommentDate, CreateIssue, run_queries, run_mutations
import datetimehelper

digest_header = """<details>
<summary>
<h2>Digest Summary: {time_end}</h2>
<p>... contains {all_changes} changes across {issues_changed} issues, since {time_start} (timezone: {tz})</p>
</summary>

{body}

{additional_issues}
</details>
"""

additional_issues_template = """[details to some update were omitted due to post length limitations]
Issues omitted: {links}"""

digest_content = """
Subscribe to this issue to receive a periodic compilation of latest updates to this issue tracker.
Unsubscribe from this issue if you are not interested to receive such periodic updates.
"""

MAX_BODY_SIZE = 65536 - 1000 # buffer for the digest header

class DigestManager:
    """
    DigestManager is a class that manages the digest process.
    It is responsible for querying for issues and comments, as well as sending the digest to the target repository.

    args:
        target_repo: str - the repository to query for issues
        local_repo: str - the repository to send the digest to
        digest_issue: str - the issue to send the digest to
        ignored_issues: list[int] - a list of issue numbers to ignore, default to nothing
    """
    cursor:str = None
    target_repo: str
    local_repo: str
    timestamp: datetime
    digest_issue: str
    complete: bool
    ignored_issues: list[int]
    last_update_time: datetime
    query = MainQuery()

    def __init__(self, target_repo:str, local_repo:str, digest_issue:str, ignored_issues=[]) -> None:
        self.target_repo = target_repo
        self.local_repo = local_repo
        self.digest_issue = digest_issue
        self.complete = False
        self.ignored_issues = ignored_issues
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
                    datetimehelper.format_to_utc(self.last_update_time),
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
        
        return sorted([ret[key] for key in ret], key=lambda issue: issue.number)

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
            
            issue = GitIssue(raw_issue, (self.last_update_time, datetimehelper.get_now()))
            if issue.number in self.ignored_issues or issue.id == self.digest_issue:
                # ignore the target issue and the issues in the ignore list
                continue

            ret[issue.id] = issue

    def get_default_size(self, issues: list[GitIssue]) -> int:
        """
        get_default_size gets the body of the issue and returns the default size without any body

        args:
            issue: GitIssue - the issue to get the body from
        """
        issues = [issue for issue in issues]
        total_changes = sum([issue.total_changes for issue in issues])
        return len(digest_header.format(
                    time_start=datetimehelper.format_local(self.last_update_time),
                    time_end=datetimehelper.format_local(datetimehelper.get_now()),
                    all_changes=total_changes,
                    issues_changed=len(issues),
                    body='',
                    additional_issues='',
                    tz=datetimehelper.localtz.zone
                ))
    
    def is_locked(self):
        """
        is_locked checks if the digest issue is locked.
        """
        q = ReadIssueLock("read_issue_lock")
        res = q.run(issue_id=self.digest_issue)
        return q.is_locked(res)

    def lock_issue(self):
        """
        lock_issue locks the digest issue.
        """
        q = LockIssue("lock_issue")
        q.run(issue_id=self.digest_issue)

    def unlock_issue(self):
        """
        unlock_issue unlocks the digest issue.
        """
        q = UnlockIssue("unlock_issue")
        q.run(issue_id=self.digest_issue)

    @staticmethod
    def _retain_lock(func: callable):
        """
        decorator that retains the lock state of the digest issue.
        """
        def lock_wrapper(self, *args, **kwargs):
            locked = self.is_locked()
            if locked:
                self.unlock_issue()
            try:
                func(self, *args, **kwargs)
            finally:
                if locked:
                    self.lock_issue()
        return lock_wrapper
    
    @_retain_lock
    def send_data(self, issues: list[GitIssue]):
        """
        send_data sends mutation to update the digest issue with the new data.
        It takes in a list of GitIssue objects and only sends the data if there are changes.

        args:
            issues: list[GitIssue] - a list of GitIssue objects
        """
        total_changes = sum([issue.total_changes for issue in issues])
        if total_changes == 0:
            # no changes were detected
            return
        
        content: list[str] = []
        shortened_content: list[str] = []
        curr_len = 0
        availabe_len = MAX_BODY_SIZE - self.get_default_size(issues)

        length_exceeded = False

        for issue in issues:
            if (length_exceeded):
                shortened_content.append(issue.simple_link)
                continue
            content.append(issue.to_markdown())
            curr_len += len(content[-1])

            if curr_len > availabe_len:
                content.pop()
                shortened_content.append(issue.simple_link)
                length_exceeded = True
        
        additional_issues_str = ""
        if shortened_content:
            additional_issues_str = additional_issues_template.format(links = ' '.join(shortened_content))
            


        r1 = UpdateIssue("update_issue").partial_query(self.digest_issue, digest_content)
        r2 = AddComment("new_digest").partial_query(self.digest_issue, digest_header.format(
                    time_start=datetimehelper.format_local(self.last_update_time),
                    time_end=datetimehelper.format_local(datetimehelper.get_now()),
                    all_changes=total_changes,
                    issues_changed=len(issues),
                    body=''.join(content),
                    additional_issues=additional_issues_str,
                    tz=datetimehelper.localtz.zone
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
        res = q.run(issue_id=self.digest_issue)
        self.last_update_time = q.get_last_comment_date(res) or datetimehelper.get_n_day_prior(10)

    def create_issue(self):
        """
        create_issue creates the digest issue if it does not exist and update the target_issue field.
        If the target repo is the same as the local repo, then the issue number is added to the ignore list.
        """
        if self.digest_issue:
            # issue already exist
            return
        repo_id = self.find_repo_id()
        q = CreateIssue("create_issue")
        res = q.run(repo_id=repo_id, title=f"[{self.target_repo}] Issues Digest", body=digest_content)

        self.digest_issue = q.get_issue_id(res)
        if self.local_repo == self.target_repo:
            self.ignored_issues.append(q.get_issue_number(res))
