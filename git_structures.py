from datetime import datetime
from gql_queries import ReadComments
import datetimehelper
from stringhelper import format_to_quote

issue_title_template = "# {title} [#{number}]({link})\n"

issue_template = """
`@{author}` {status} this issue on {date}
{body}


"""

comment_template = """
`@{author}` {status} this [comment]({link}) on {date}
{body}


"""

issue_simple_link_template = "[#{number}]({link})"

class ModifiableItem:
    """
    ModifiableItem is a base class for GraphQL objects that can be modified.
    These objects should contain the following fields in the query:
        - author: str
        - created_at: datetime
        - editor: str
        - edit_at: datetime
    
    args:
        graphqlResult: dict - the result of the GraphQL query
    """

    editor: str
    edit_at: datetime
    author: str
    created_at: datetime
    def __init__(self, graphqlResult: dict):
        self.editor = graphqlResult["editor"]["login"] if graphqlResult["editor"] else None
        self.edit_at = datetimehelper.convertToDateTime(graphqlResult["lastEditedAt"]) if graphqlResult["lastEditedAt"] else None
        self.author = graphqlResult["author"]["login"]
        self.created_at = datetimehelper.convertToDateTime(graphqlResult["createdAt"])

    @property
    def is_modified(self) -> bool:
        """
        is_modified returns true if the item has been modified, false otherwise

        returns:
            bool - true if the item has been modified, false otherwise
        """
        return self.editor != None

    @property
    def last_change_date(self) -> datetime:
        """
        last_change_date returns the date of the last change of the item.

        If the item has not been modified, it will return the date of creation,
        else it will return the date of the last modification.

        returns:
            datetime - the date of the last change
        """
        return self.edit_at if self.is_modified else self.created_at

    @property 
    def last_change_author(self) -> str:
        """
        last_change_author returns the author of the last change of the item.

        If the item has not been modified, it will return the author of creation,
        else it will return the author of the last modification.

        returns:
            str - the author of the last change
        """

        return self.editor if self.is_modified else self.author
    
    def get_status_str(self, time_range: tuple[datetime, datetime]) -> str:
        """
        get_status_str returns a string describing the status of the item within the time range.

        args:
            time_range: tuple[datetime, datetime] - the time range to check
        """
        ret = []
        if self.created_at >= time_range[0] and self.created_at <= time_range[1]:
            ret.append("created")
        if self.edit_at and self.edit_at >= time_range[0] and self.edit_at <= time_range[1]:
            ret.append("modified")
        return " and ".join(ret) if ret else "deleted"

    def within_time_range(self, time_range: tuple[datetime, datetime]) -> bool:
        return self.last_change_date >= time_range[0] and self.last_change_date <= time_range[1]

class GitComment(ModifiableItem):
    """
    GitComment is a class representing a comment on a GitHub issue.

    args:
        graphqlResult: dict - the result of the GraphQL query
        time_range: tuple[datetime, datetime] - the time range to check
    """

    source_link: str
    body: str
    time_range: tuple[datetime, datetime]
    def __init__(self, graphqlResult: dict, time_range: tuple[datetime, datetime]):
        super().__init__(graphqlResult)
        self.source_link = graphqlResult["url"]
        self.body = graphqlResult["body"]
        self.time_range = time_range

    def to_markdown(self) -> str:
        """
        to_markdown returns a markdown representation of the comment.

        returns:
            str - the markdown representation of the comment
        """
        return comment_template.format(
                author=self.last_change_author,
                link=self.source_link,
                date=datetimehelper.format_local(self.last_change_date),
                body=format_to_quote(self.body),
                status=self.get_status_str(self.time_range)
            )
    
    @property
    def is_deleted(self) -> bool:
        """
        is_deleted returns true if the comment has been deleted, false otherwise

        returns:
            bool - true if the comment has been deleted, false otherwise
        """
        return self.body == None
    

class GitIssue(ModifiableItem):
    """
    GitIssue is a class representing a GitHub issue.

    args:
        graphqlResult: dict - the result of the GraphQL query
        time_range: tuple[datetime, datetime] - the time range to check
    """

    url: str
    number: int
    time_range: tuple[datetime, datetime]
    title: str
    id: str
    body: str
    comments: list[GitComment]
    comments_query: ReadComments
    last_comment_cursor: str
    has_more_comments: bool

    def __init__(self, graphqlResult: dict, timeRange: tuple[datetime, datetime]):
        super().__init__(graphqlResult)
        self.url = graphqlResult["url"]
        self.number = graphqlResult["number"]
        self.time_range = timeRange
        self.title = graphqlResult["title"]
        self.id = graphqlResult["id"]
        self.body = graphqlResult["body"]
        self.comments = []
        self.comments_query = ReadComments(self.id)
        
        self.read_paginated_comments(graphqlResult)

    def read_paginated_comments(self, graphqlResult:dict):
        """
        read_paginated_comments reads all the comments of the issue.
        """
        self.last_comment_cursor = graphqlResult["comments"]["pageInfo"]["endCursor"] or "null"
        self.has_more_comments = graphqlResult["comments"]["pageInfo"]["hasNextPage"]

        for raw_comment in graphqlResult["comments"]["nodes"]:
            comment = GitComment(raw_comment, self.time_range)
            if comment.within_time_range(self.time_range) and not comment.is_deleted:
                self.comments.append(comment)
    
    def draft_gql_query(self) -> str:
        return self.comments_query.partial_query(self.url, self.last_comment_cursor)
    
    @property
    def simple_link(self) -> str:
        """
        simple_link returns the link to the issue without the domain.

        returns:
            str - the link to the issue without the domain
        """
        return issue_simple_link_template.format(number=self.number, link=self.url)

    @property
    def contains_changes(self) -> bool:
        return self.within_time_range(self.time_range)

    @property
    def has_more_data(self) -> bool:
        """
        has_more_data returns true if there are more comments to read, false otherwise.

        returns:
            bool - true if there are more comments to read, false otherwise
        """
        return self.has_more_comments
    
    @property
    def total_changes(self) -> int:
        """
        total_changes returns the total number of changes of the issue.

        returns:
            int - the total number of changes of the issue
        """
        return len(self.comments) + self.contains_changes
    
    def to_markdown(self) -> str:
        """
        to_markdown returns a markdown representation of the issue.

        returns:
            str - the markdown representation of the issue
        """
        header = issue_title_template.format(
            title = self.title,
            number = self.number,
            link = self.url)
        if self.contains_changes:
            header += issue_template.format(
                author=self.last_change_author,
                date=datetimehelper.format_local(self.last_change_date),
                status=self.get_status_str(self.time_range),
                body=format_to_quote(self.body)
            )
        self.comments.sort(key=lambda x: x.last_change_date)
        return header + ''.join([comment.to_markdown() for comment in self.comments])
